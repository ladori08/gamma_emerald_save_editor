from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable

from .item_mod_templates import ITEM_MOD_TEMPLATES, TEMPLATE_BY_KEY
from .save_service import is_game_running


GAME_VERSION = "GE-1.0.0"
MANIFEST_PRODUCT = "Gamma Emerald Save Editor Item Mod"
INSTALLED_PAK_NAME = "PokemonEmerald-Windows_0_P.pak"
INTERNAL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,47}$")
BALL_TYPES = (
    "PokeBall", "GreatBall", "UltraBall", "MasterBall", "SafariBall", "NetBall", "DiveBall",
    "NestBall", "RepeatBall", "TimerBall", "LuxuryBall", "PremierBall", "DuskBall", "HealBall",
    "QuickBall", "CherishBall", "ShimmerBall",
)
VITAMIN_STATS = ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed")
POKEMON_TYPES = (
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison", "Ground",
    "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy",
)
VITAMIN_EV_AMOUNTS = (1, 2, 3, 4, 6, 7, 9, 10, 12, 14, 18, 21, 28, 36, 42, 63, 84, 126, 252)
VITAMIN_STAT_CAP = 100
VITAMIN_TOTAL_CAP = 510
HELD_COMPOSABLE_FIELDS = (
    "AttackMultiplier",
    "DefenseMultiplier",
    "SpecialAttackMultiplier",
    "SpecialDefenseMultiplier",
    "SpeedMultiplier",
    "HPRestorePerTurn",
)
# FourCC "CSTM" interpreted as a positive big-endian int32. ItemID is numeric-only in GE-1.0.0,
# so the UI pairs this recognizable namespace with a separate CSTM-###### display tag.
CUSTOM_ITEM_ID_BASE = int.from_bytes(b"CSTM", "big")
CUSTOM_ITEM_ID_MAX_SEQUENCE = 999_999


class ModBuilderError(RuntimeError):
    pass


def custom_item_id_tag(item_id: int) -> str | None:
    sequence = int(item_id) - CUSTOM_ITEM_ID_BASE
    if 1 <= sequence <= CUSTOM_ITEM_ID_MAX_SEQUENCE:
        return f"CSTM-{sequence:06d}"
    return None


def custom_item_id_state_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    root = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return root / "GammaEmeraldSaveEditor" / "item-id-sequence.json"


def allocate_custom_item_id(
    state_path: Path | str | None = None,
    *,
    used_ids: Iterable[int] = (),
) -> int:
    """Reserve the next persistent numeric ID in the editor's recognizable CSTM namespace."""
    path = Path(state_path) if state_path is not None else custom_item_id_state_path()
    next_sequence = 1
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("format") != 1 or data.get("namespace") != "CSTM":
                raise ValueError("unknown state format")
            next_sequence = int(data["next_sequence"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModBuilderError(f"Custom Item ID counter is invalid: {path}") from exc
    if not 1 <= next_sequence <= CUSTOM_ITEM_ID_MAX_SEQUENCE:
        raise ModBuilderError("The CSTM custom Item ID namespace is exhausted or its counter is invalid.")
    used = {int(value) for value in used_ids}
    sequence = next_sequence
    while CUSTOM_ITEM_ID_BASE + sequence in used and sequence <= CUSTOM_ITEM_ID_MAX_SEQUENCE:
        sequence += 1
    if sequence > CUSTOM_ITEM_ID_MAX_SEQUENCE:
        raise ModBuilderError("The CSTM custom Item ID namespace is exhausted.")
    item_id = CUSTOM_ITEM_ID_BASE + sequence
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(
                {"format": 1, "namespace": "CSTM", "next_sequence": sequence + 1},
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError as exc:
        raise ModBuilderError(f"Could not reserve the next custom Item ID: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return item_id


@dataclass(frozen=True, slots=True)
class ItemModSpec:
    internal_name: str
    display_name: str
    description: str
    item_id: int
    buy_price: int
    sell_price: int
    hp_restore_amount: int
    template_key: str = "DA_Potion"
    property_overrides: dict[str, object] = field(default_factory=dict)
    visual_template_key: str | None = None

    @property
    def template(self):
        return TEMPLATE_BY_KEY.get(self.template_key)

    @property
    def visual_template(self):
        return TEMPLATE_BY_KEY.get(self.visual_template_key or self.template_key)

    @property
    def archetype(self) -> str:
        return self.template.archetype if self.template else "Unknown"

    @property
    def pocket(self) -> str:
        return {"Berry": "Berries", "TM": "TMs", "Poké Ball": "Pokeballs"}.get(self.archetype, "Items")

    def validated(self) -> "ItemModSpec":
        if not INTERNAL_NAME_RE.fullmatch(self.internal_name):
            raise ModBuilderError(
                "Internal name must be 3-48 ASCII characters: start with a letter, then letters, numbers or _."
            )
        display = self.display_name.strip()
        description = self.description.strip()
        if not display or len(display) > 64 or any(ord(char) < 32 for char in display):
            raise ModBuilderError("Display name must be 1-64 characters without control characters.")
        if not description or len(description) > 512 or any(
            ord(char) < 32 and char not in "\r\n\t" for char in description
        ):
            raise ModBuilderError("Description must be 1-512 characters without control characters.")
        if not 100_000 <= int(self.item_id) <= 2_147_483_647:
            raise ModBuilderError("Item ID must be between 100000 and 2147483647 to reduce collision risk.")
        if not 0 <= int(self.buy_price) <= 2_000_000_000:
            raise ModBuilderError("Buy price must be between 0 and 2000000000.")
        if not 0 <= int(self.sell_price) <= 2_000_000_000:
            raise ModBuilderError("Sell price must be between 0 and 2000000000.")
        if self.sell_price > self.buy_price and self.buy_price != 0:
            raise ModBuilderError("Sell price cannot exceed buy price.")
        if not 1 <= int(self.hp_restore_amount) <= 9999:
            raise ModBuilderError("HP restored must be between 1 and 9999.")
        template = self.template
        if template is None:
            raise ModBuilderError(f"Unknown or unavailable item template: {self.template_key}.")
        visual_template = self.visual_template
        if visual_template is None:
            raise ModBuilderError(f"Unknown or unavailable visual template: {self.visual_template_key}.")
        if visual_template.archetype != template.archetype:
            raise ModBuilderError("Visual and behavior templates must belong to the selected item category.")
        editable = set(template.editable_fields)
        if template.archetype == "Held Item":
            editable.update(HELD_COMPOSABLE_FIELDS)
        unknown = set(self.property_overrides) - editable
        if unknown:
            raise ModBuilderError(f"Template {template.label} cannot safely edit: {', '.join(sorted(unknown))}.")
        overrides = dict(self.property_overrides)
        if template.archetype == "HP Restore" and "HPRestoreAmount" in template.editable_fields:
            overrides["HPRestoreAmount"] = int(self.hp_restore_amount)
        for name, value in overrides.items():
            if name in {"HPRestoreAmount", "BerryHPRestore"} and not 0 <= int(value) <= 9999:
                raise ModBuilderError(f"{name} must be between 0 and 9999.")
            if name in {
                "CatchRateModifier", "BerryActivationThreshold", "HPRestorePerTurn",
                "TypeBoostMultiplier", "AttackMultiplier", "DefenseMultiplier",
                "SpecialAttackMultiplier", "SpecialDefenseMultiplier", "SpeedMultiplier",
            } and not 0 <= float(value) <= 1000:
                raise ModBuilderError(f"{name} must be between 0 and 1000.")
            if name == "PokeballType" and value not in BALL_TYPES:
                raise ModBuilderError("PokeballType is not a GE-1.0.0 runtime enum value.")
            if name == "VitaminStat" and value not in VITAMIN_STATS:
                raise ModBuilderError("VitaminStat is invalid.")
            if name == "EVBoostAmount" and int(value) not in VITAMIN_EV_AMOUNTS:
                raise ModBuilderError("EVBoostAmount must be one of the verified Vitamin dropdown values.")
            if name == "BoostedType" and value not in POKEMON_TYPES:
                raise ModBuilderError("BoostedType is invalid.")
            if name == "TeachableMove":
                if not isinstance(value, dict) or not {"package", "asset"} <= set(value):
                    raise ModBuilderError("TeachableMove requires a verified package and generated-class name.")
        return ItemModSpec(
            internal_name=self.internal_name,
            display_name=display,
            description=description,
            item_id=int(self.item_id),
            buy_price=int(self.buy_price),
            sell_price=int(self.sell_price),
            hp_restore_amount=int(self.hp_restore_amount),
            template_key=self.template_key,
            property_overrides=overrides,
            visual_template_key=visual_template.key,
        )

    def helper_payload(self) -> dict[str, object]:
        valid = self.validated()
        assert valid.template is not None
        object_name = f"DA_{valid.internal_name}"
        return {
            "source_object_name": valid.template.object_name,
            "source_package_path": valid.template.package_path,
            "object_name": object_name,
            "package_path": f"/Game/Items/{object_name}",
            # ItemDataManager keys its lookup map by this FName. Existing assets use
            # their player-facing name here, including spaces (for example Super Potion).
            "item_name": valid.display_name,
            "display_name": valid.display_name,
            "description": valid.description,
            "item_id": valid.item_id,
            "buy_price": valid.buy_price,
            "sell_price": valid.sell_price,
            "property_overrides": valid.property_overrides,
            "visual_template_key": valid.visual_template.key,
        }


@dataclass(frozen=True, slots=True)
class ModToolchain:
    game_root: Path | None
    game_executable: Path | None
    base_pak: Path | None
    dotnet: Path | None
    helper_dll: Path | None
    repak: Path | None
    usmap: Path | None
    template_root: Path | None

    def template_path(self, template_key: str) -> Path | None:
        template = TEMPLATE_BY_KEY.get(template_key)
        return self.template_root / template.relative_path if self.template_root and template else None

    @property
    def installed_pak(self) -> Path | None:
        if self.game_root is None:
            return None
        return self.game_root / "PokemonEmerald" / "Content" / "Paks" / INSTALLED_PAK_NAME

    @property
    def installed_manifest(self) -> Path | None:
        pak = self.installed_pak
        return Path(str(pak) + ".gamma-editor.json") if pak else None

    @property
    def ready(self) -> bool:
        return self.templates_ready and all(
            path is not None and path.is_file()
            for path in (
                self.game_executable,
                self.base_pak,
                self.dotnet,
                self.helper_dll,
                self.repak,
                self.usmap,
            )
        )

    @property
    def templates_ready(self) -> bool:
        if self.template_root is None or not self.template_root.is_dir():
            return False
        return all(
            (self.template_root / template.relative_path).is_file()
            and (self.template_root / template.relative_path).with_suffix(".uexp").is_file()
            for template in ITEM_MOD_TEMPLATES
        )

    def status_rows(self) -> tuple[tuple[str, str, bool], ...]:
        rows = (
            ("Game executable", self.game_executable),
            ("Base game pak", self.base_pak),
            (".NET runtime", self.dotnet),
            ("Asset writer helper", self.helper_dll),
            ("Pak writer", self.repak),
            ("GE-1.0.0 mapping", self.usmap),
            ("41 supported ItemData templates", self.template_root),
        )
        result = tuple(
            (
                label,
                str(path) if path else "Not found",
                bool(path and path.is_file()),
            )
            for label, path in rows[:-1]
        )
        return result + ((rows[-1][0], str(self.template_root) if self.template_root else "Not found", self.templates_ready),)


@dataclass(frozen=True, slots=True)
class BuiltItemMod:
    pak_path: Path
    manifest_path: Path
    sha256: str
    spec: ItemModSpec
    specs: tuple[ItemModSpec, ...] = ()

    @property
    def all_specs(self) -> tuple[ItemModSpec, ...]:
        """Every item carried by the patch, including legacy single-item builds."""
        return self.specs or (self.spec,)


def _unique_paths(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            yield resolved


def _candidate_roots() -> Iterable[Path]:
    configured = os.environ.get("GAMMA_EMERALD_GAME_DIR")
    seeds = [Path.cwd(), Path(sys.executable).resolve().parent, Path(__file__).resolve().parent]
    if configured:
        seeds.insert(0, Path(configured))
    for seed in seeds:
        yield seed
        yield from seed.parents


def _find_game_root() -> Path | None:
    for root in _unique_paths(_candidate_roots()):
        if (root / "PokemonEmerald.exe").is_file() and (
            root / "PokemonEmerald" / "Content" / "Paks" / "PokemonEmerald-Windows.pak"
        ).is_file():
            return root
    return None


def _first_file(candidates: Iterable[Path]) -> Path | None:
    return next((path for path in _unique_paths(candidates) if path.is_file()), None)


def discover_toolchain() -> ModToolchain:
    game_root = _find_game_root()
    configured = os.environ.get("GAMMA_EMERALD_MOD_TOOLS")
    roots: list[Path] = []
    if configured:
        roots.append(Path(configured))
    if game_root:
        roots.extend((game_root / "_third_party_downloads", game_root / "gamma_emerald_save_editor"))
    roots.extend(Path(__file__).resolve().parents)
    roots = list(_unique_paths(roots))

    game_executable = (
        game_root / "PokemonEmerald" / "Binaries" / "Win64" / "PokemonEmerald-Win64-Shipping.exe"
        if game_root
        else None
    )
    base_pak = (
        game_root / "PokemonEmerald" / "Content" / "Paks" / "PokemonEmerald-Windows.pak"
        if game_root
        else None
    )
    dotnet = _first_file(root / "dotnet-sdk" / "dotnet.exe" for root in roots)
    helper = _first_file(root / "asset-parser" / "bin" / "Release" / "net8.0" / "AssetParser.dll" for root in roots)
    repak = _first_file(
        candidate
        for root in roots
        for candidate in (root / "repak" / "repak-local.exe", root / "repak" / "repak.exe")
    )
    usmap = _first_file(
        candidate
        for root in roots
        for candidate in (
            root / "runtime_assets" / "mappings" / GAME_VERSION / "PokemonEmerald-5.6.1-44394996+++UE5+Release-5.6-24b12662.usmap",
            root / "gamma_emerald_save_editor" / "runtime_assets" / "mappings" / GAME_VERSION / "PokemonEmerald-5.6.1-44394996+++UE5+Release-5.6-24b12662.usmap",
        )
    )
    template_file = _first_file(
        candidate
        for root in roots
        for candidate in (
            root / "item_template_assets" / "PokemonEmerald" / "Content" / "Items" / "DA_Potion.uasset",
            root / "item_schema_assets" / "PokemonEmerald" / "Content" / "Items" / "DA_Potion.uasset",
        )
    )
    template = template_file.parents[3] if template_file else None
    return ModToolchain(game_root, game_executable, base_pak, dotnet, helper, repak, usmap, template)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _run_checked(command: list[str], *, cwd: Path) -> None:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ModBuilderError(f"Mod tool failed to start: {exc}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout or "No diagnostic output").strip()
        raise ModBuilderError(f"Mod tool failed ({result.returncode}): {detail[-1200:]}")


def _validated_specs(items: Iterable[ItemModSpec]) -> tuple[ItemModSpec, ...]:
    items = tuple(item.validated() for item in items)
    checks = (
        ("Item ID", [item.item_id for item in items]),
        ("internal asset name", [item.internal_name.casefold() for item in items]),
        ("display / Bag name", [item.display_name.casefold() for item in items]),
    )
    for label, values in checks:
        if len(values) != len(set(values)):
            raise ModBuilderError(f"The custom item pack already contains that {label}.")
    return items


def _validated_item_bundle(
    spec: ItemModSpec,
    bundled_specs: Iterable[ItemModSpec] = (),
) -> tuple[ItemModSpec, ...]:
    return _validated_specs((*bundled_specs, spec))


def replace_item_in_bundle(
    items: Iterable[ItemModSpec],
    original_item_id: int,
    replacement: ItemModSpec,
) -> tuple[ItemModSpec, ...]:
    """Replace one item while preserving save-facing identity and category."""
    current = _validated_specs(items)
    matches = [index for index, item in enumerate(current) if item.item_id == int(original_item_id)]
    if len(matches) != 1:
        raise ModBuilderError("The installed custom item selected for editing no longer exists uniquely.")
    index = matches[0]
    original = current[index]
    updated = replacement.validated()
    if (
        updated.item_id != original.item_id
        or updated.internal_name != original.internal_name
        or updated.display_name != original.display_name
    ):
        raise ModBuilderError(
            "Editing must preserve Item ID, internal asset name and display / Bag name to avoid orphaned save references."
        )
    if updated.archetype != original.archetype:
        raise ModBuilderError("Editing must preserve the item category to avoid moving existing Bag references.")
    result = list(current)
    result[index] = updated
    return _validated_specs(result)


def remove_item_from_bundle(
    items: Iterable[ItemModSpec],
    item_id: int,
) -> tuple[ItemModSpec, ...]:
    """Remove exactly one installed custom item by its stable numeric identity."""
    current = _validated_specs(items)
    remaining = tuple(item for item in current if item.item_id != int(item_id))
    if len(remaining) != len(current) - 1:
        raise ModBuilderError("The installed custom item selected for removal no longer exists uniquely.")
    return remaining


def _manifest_data(specs: tuple[ItemModSpec, ...], pak_path: Path, digest: str) -> dict[str, object]:
    primary = specs[-1]
    return {
        "product": MANIFEST_PRODUCT,
        "format": 2,
        "target_game_version": GAME_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "pak_file": pak_path.name,
        "pak_sha256": digest,
        # Keep the newest item in the legacy fields so older editor builds can still
        # identify the patch. Format 2 readers use the complete items collection.
        "template": TEMPLATE_BY_KEY[primary.template_key].label,
        "item": asdict(primary),
        "items": [asdict(item) for item in specs],
    }


def build_item_mod(
    spec: ItemModSpec,
    output_directory: Path | str,
    toolchain: ModToolchain | None = None,
    *,
    bundled_specs: Iterable[ItemModSpec] = (),
) -> BuiltItemMod:
    specs = _validated_item_bundle(spec, bundled_specs)
    valid = specs[-1]
    tools = toolchain or discover_toolchain()
    if is_game_running():
        raise ModBuilderError("Close Pokémon Gamma Emerald before building a mod.")
    if not tools.ready:
        missing = ", ".join(label for label, _value, ok in tools.status_rows() if not ok)
        raise ModBuilderError(f"Item Mod Builder toolchain is incomplete: {missing}.")
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    pak_path = output / f"GammaEditor-{valid.internal_name}.pak"
    manifest_path = Path(str(pak_path) + ".gamma-editor.json")
    if pak_path.exists() or manifest_path.exists():
        raise ModBuilderError(f"Output already exists: {pak_path.name}. Choose another internal name or folder.")

    template_path = tools.template_path(valid.template_key)
    if template_path is None or not template_path.is_file() or not template_path.with_suffix(".uexp").is_file():
        raise ModBuilderError(f"Selected template files are missing: {valid.template_key}.")
    assert tools.dotnet and tools.helper_dll and tools.repak and tools.usmap
    with tempfile.TemporaryDirectory(prefix=".gamma-item-build-", dir=output) as temp_name:
        temp = Path(temp_name)
        item_directory = temp / "stage" / "PokemonEmerald" / "Content" / "Items"
        item_directory.mkdir(parents=True)
        for index, item in enumerate(specs):
            source = tools.template_path(item.template_key)
            if source is None or not source.is_file() or not source.with_suffix(".uexp").is_file():
                raise ModBuilderError(f"Selected template files are missing: {item.template_key}.")
            asset_path = item_directory / f"DA_{item.internal_name}.uasset"
            spec_path = temp / f"item-spec-{index}.json"
            payload = item.helper_payload()
            visual_source = tools.template_path(item.visual_template.key)
            if visual_source is None or not visual_source.is_file() or not visual_source.with_suffix(".uexp").is_file():
                raise ModBuilderError(f"Selected visual template files are missing: {item.visual_template.key}.")
            if item.visual_template.key != item.template_key:
                payload["visual_source_path"] = str(visual_source)
            spec_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            _run_checked(
                [
                    str(tools.dotnet), str(tools.helper_dll), "build-item", str(source),
                    str(asset_path), str(tools.usmap), str(spec_path),
                ],
                cwd=tools.helper_dll.parent,
            )
            if not asset_path.is_file() or not asset_path.with_suffix(".uexp").is_file():
                raise ModBuilderError(
                    f"Asset helper did not produce the expected files for {item.display_name}."
                )
        _run_checked(
            [str(tools.repak), "pack", "--version", "V11", "--mount-point", "../../../", str(temp / "stage"), str(pak_path)],
            cwd=tools.repak.parent,
        )
    if not pak_path.is_file() or pak_path.stat().st_size == 0:
        raise ModBuilderError("Pak writer did not produce a non-empty patch.")
    digest = sha256_file(pak_path)
    manifest_path.write_text(
        json.dumps(_manifest_data(specs, pak_path, digest), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return BuiltItemMod(pak_path, manifest_path, digest, valid, specs)


def _read_owned_manifest(pak_path: Path, manifest_path: Path) -> dict[str, object]:
    if not pak_path.is_file() or not manifest_path.is_file():
        raise ModBuilderError("No editor-owned installed mod was found.")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModBuilderError("Installed mod manifest is unreadable; refusing to touch the pak.") from exc
    if data.get("product") != MANIFEST_PRODUCT or data.get("pak_file") != pak_path.name:
        raise ModBuilderError("Installed patch is not proven to be owned by this editor.")
    expected = str(data.get("pak_sha256", "")).upper()
    if not expected or sha256_file(pak_path) != expected:
        raise ModBuilderError("Installed patch changed after creation; refusing to replace or remove it.")
    return data


def installed_items(toolchain: ModToolchain | None = None) -> tuple[ItemModSpec, ...]:
    tools = toolchain or discover_toolchain()
    pak, manifest = tools.installed_pak, tools.installed_manifest
    if not pak or not manifest or not pak.exists() or not manifest.exists():
        return ()
    try:
        data = _read_owned_manifest(pak, manifest)
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            raw_items = [data["item"]]
        return tuple(ItemModSpec(**raw).validated() for raw in raw_items)  # type: ignore[arg-type]
    except (KeyError, TypeError, ModBuilderError):
        return ()


def installed_item(toolchain: ModToolchain | None = None) -> ItemModSpec | None:
    """Return the newest installed item for compatibility with single-item callers."""
    items = installed_items(toolchain)
    return items[-1] if items else None


def install_item_mod(built: BuiltItemMod, toolchain: ModToolchain | None = None, *, replace_owned: bool = False) -> Path:
    tools = toolchain or discover_toolchain()
    if is_game_running():
        raise ModBuilderError("Close Pokémon Gamma Emerald before installing a mod.")
    target, target_manifest = tools.installed_pak, tools.installed_manifest
    if target is None or target_manifest is None or tools.game_root is None:
        raise ModBuilderError("Pokémon Gamma Emerald installation was not found.")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target_manifest.exists():
        _read_owned_manifest(target, target_manifest)
        if not replace_owned:
            raise ModBuilderError("An editor-owned item patch is already installed; confirm replacement first.")
        backup_dir = target.parent / "GammaEditorBackups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        # Compact names keep backup writes below legacy Windows MAX_PATH even when
        # Gamma itself lives under an already deep directory.
        shutil.copy2(target, backup_dir / f"item-pack.{stamp}.pak.bak")
        shutil.copy2(target_manifest, backup_dir / f"item-pack.{stamp}.manifest.json.bak")
    data = json.loads(built.manifest_path.read_text(encoding="utf-8"))
    data["pak_file"] = target.name
    data["pak_sha256"] = sha256_file(built.pak_path)
    temp_pak = target.with_name(f".{target.name}.installing")
    temp_manifest = target_manifest.with_name(f".{target_manifest.name}.installing")
    try:
        shutil.copy2(built.pak_path, temp_pak)
        temp_manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if sha256_file(temp_pak) != data["pak_sha256"]:
            raise ModBuilderError("Temporary installed pak failed SHA-256 verification.")
        os.replace(temp_pak, target)
        os.replace(temp_manifest, target_manifest)
    finally:
        temp_pak.unlink(missing_ok=True)
        temp_manifest.unlink(missing_ok=True)
    return target


def build_and_install_item_bundle(
    items: Iterable[ItemModSpec],
    toolchain: ModToolchain | None = None,
    *,
    replace_owned: bool = False,
) -> Path:
    """Build a complete bundle in disposable staging and atomically install it.

    Installed workflows intentionally do not reuse user export folders. This keeps a
    previous ``Build .pak`` artifact from blocking an update merely because both
    bundles would have the same generated filename.
    """
    specs = _validated_specs(items)
    if not specs:
        raise ModBuilderError("The custom item bundle is empty.")
    tools = toolchain or discover_toolchain()
    with tempfile.TemporaryDirectory(prefix="gamma-editor-item-install-") as temp_name:
        built = build_item_mod(
            specs[-1],
            Path(temp_name),
            tools,
            bundled_specs=specs[:-1],
        )
        return install_item_mod(built, tools, replace_owned=replace_owned)


def uninstall_item_mod(toolchain: ModToolchain | None = None) -> None:
    tools = toolchain or discover_toolchain()
    if is_game_running():
        raise ModBuilderError("Close Pokémon Gamma Emerald before uninstalling a mod.")
    target, manifest = tools.installed_pak, tools.installed_manifest
    if target is None or manifest is None:
        raise ModBuilderError("Pokémon Gamma Emerald installation was not found.")
    _read_owned_manifest(target, manifest)
    target.unlink()
    manifest.unlink()
