from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Iterable

from .mod_builder import (
    CUSTOM_ITEM_ID_BASE,
    CUSTOM_ITEM_ID_MAX_SEQUENCE,
    GAME_VERSION,
    ModBuilderError,
    ModToolchain,
    discover_toolchain,
    sha256_file,
)
from .save_service import is_game_running


RUNTIME_PRODUCT = "Gamma Emerald Save Editor Vitamin Runtime Rules"
RUNTIME_MANIFEST_NAME = "GammaVitaminRules.gamma-editor.json"
RUNTIME_MOD_NAME = "GammaVitaminRules"
RUNTIME_SCOPES = ("custom", "all")
RUNTIME_STAT_CAPS = (100, 252)
RUNTIME_TOTAL_CAPS = (510, None)
_SOURCE_DIRECTORIES = (
    "Default_UVTD_Configs",
    "MemberVarLayoutTemplates",
    "UE4SS_Signatures",
    "VTableLayoutTemplates",
)


@dataclass(frozen=True, slots=True)
class VitaminRuntimeConfig:
    stat_cap: int = 252
    total_cap: int | None = 510
    scope: str = "custom"

    def validated(self) -> "VitaminRuntimeConfig":
        if self.stat_cap not in RUNTIME_STAT_CAPS:
            raise ModBuilderError("Vitamin runtime stat cap must be 100 or 252.")
        if self.total_cap not in RUNTIME_TOTAL_CAPS:
            raise ModBuilderError("Vitamin runtime total cap must be 510 or Unlimited.")
        if self.scope not in RUNTIME_SCOPES:
            raise ModBuilderError("Vitamin runtime scope must be custom CSTM items or all Vitamins.")
        return self


@dataclass(frozen=True, slots=True)
class VitaminRuntimeEnvironment:
    game_executable: Path | None
    loader_source: Path | None
    ue4ss_source: Path | None

    @property
    def ready(self) -> bool:
        return bool(
            self.game_executable
            and self.game_executable.is_file()
            and self.loader_source
            and self.loader_source.is_file()
            and self.ue4ss_source
            and self.ue4ss_source.is_dir()
            and (self.ue4ss_source / "UE4SS.dll").is_file()
            and (self.ue4ss_source / "UE4SS-settings.ini").is_file()
            and (self.ue4ss_source / "LICENSE").is_file()
            and (self.ue4ss_source / "Mods").is_dir()
            and all((self.ue4ss_source / name).is_dir() for name in _SOURCE_DIRECTORIES)
        )

    @property
    def game_bin(self) -> Path | None:
        return self.game_executable.parent if self.game_executable else None

    @property
    def loader_target(self) -> Path | None:
        return self.game_bin / "dwmapi.dll" if self.game_bin else None

    @property
    def ue4ss_target(self) -> Path | None:
        return self.game_bin / "ue4ss" if self.game_bin else None

    @property
    def manifest_target(self) -> Path | None:
        return self.game_bin / RUNTIME_MANIFEST_NAME if self.game_bin else None


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


def discover_vitamin_runtime_environment(
    item_toolchain: ModToolchain | None = None,
) -> VitaminRuntimeEnvironment:
    tools = item_toolchain or discover_toolchain()
    candidates: list[Path] = []
    configured = os.environ.get("GAMMA_EMERALD_UE4SS_DIR")
    if configured:
        candidates.append(Path(configured))
    if tools.game_root:
        candidates.extend(
            (
                tools.game_root / "_third_party_downloads" / "ue4ss-experimental" / "prepared",
                tools.game_root / "_third_party_downloads" / "ue4ss-experimental" / "stage",
            )
        )
    for root in _unique_paths(Path(__file__).resolve().parents):
        candidates.append(root / "_third_party_downloads" / "ue4ss-experimental" / "prepared")
    source_root = next(
        (
            root
            for root in _unique_paths(candidates)
            if (root / "dwmapi.dll").is_file() and (root / "ue4ss" / "UE4SS.dll").is_file()
        ),
        None,
    )
    return VitaminRuntimeEnvironment(
        tools.game_executable,
        source_root / "dwmapi.dll" if source_root else None,
        source_root / "ue4ss" if source_root else None,
    )


def render_vitamin_runtime_lua(config: VitaminRuntimeConfig) -> str:
    valid = config.validated()
    total_cap = "nil" if valid.total_cap is None else str(valid.total_cap)
    scope_all = "true" if valid.scope == "all" else "false"
    return f'''local FUNCTION_PATH = "/Script/PokemonEmerald.PokemonManagerSubsystem:CalculateVitaminGain"
local STAT_CAP = {valid.stat_cap}
local TOTAL_CAP = {total_cap}
local APPLY_TO_ALL_VITAMINS = {scope_all}
local CUSTOM_ID_MIN = {CUSTOM_ITEM_ID_BASE + 1}
local CUSTOM_ID_MAX = {CUSTOM_ITEM_ID_BASE + CUSTOM_ITEM_ID_MAX_SEQUENCE}

local EV_FIELDS = {{
    [0] = "HP_EV",
    [1] = "Attack_EV",
    [2] = "Defense_EV",
    [3] = "SpecialAttack_EV",
    [4] = "SpecialDefense_EV",
    [5] = "Speed_EV",
}}

local function integer(value)
    return math.floor(tonumber(tostring(value)) or 0)
end

local function patched_gain(item, pokemon)
    if not item or not item:IsValid() or integer(item.ItemType) ~= 11 then
        return nil
    end
    local item_id = integer(item.ItemID)
    if not APPLY_TO_ALL_VITAMINS and (item_id < CUSTOM_ID_MIN or item_id > CUSTOM_ID_MAX) then
        return nil
    end
    local field = EV_FIELDS[integer(item.VitaminStat)]
    if not field then
        return nil
    end
    local current = integer(pokemon[field])
    local gain = math.min(math.max(0, integer(item.EVBoostAmount)), math.max(0, STAT_CAP - current))
    if TOTAL_CAP then
        local total = 0
        for _, ev_field in pairs(EV_FIELDS) do
            total = total + integer(pokemon[ev_field])
        end
        gain = math.min(gain, math.max(0, TOTAL_CAP - total))
    end
    return math.max(0, gain)
end

local installed = false
local function install_hook()
    if installed then
        return
    end
    local ok, pre_id, post_id = pcall(
        RegisterHook,
        FUNCTION_PATH,
        function()
        end,
        function(_context, return_param, item_param, pokemon_param)
            local gain = patched_gain(item_param:get(), pokemon_param:get())
            if gain ~= nil then
                return_param:set(gain)
                return gain
            end
        end
    )
    if ok then
        installed = true
        print(string.format(
            "[GammaVitaminRules] ACTIVE=1 STAT_CAP=%d TOTAL_CAP=%s SCOPE=%s PRE=%s POST=%s\\n",
            STAT_CAP,
            TOTAL_CAP and tostring(TOTAL_CAP) or "UNLIMITED",
            APPLY_TO_ALL_VITAMINS and "ALL" or "CSTM",
            tostring(pre_id),
            tostring(post_id)
        ))
    else
        print(string.format("[GammaVitaminRules] hook pending: %s\\n", tostring(pre_id)))
        ExecuteWithDelay(2000, install_hook)
    end
end

install_hook()
'''


def _managed_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith("UE4SS.log"):
            continue
        result[relative] = sha256_file(path)
    return result


def _manifest_payload(
    config: VitaminRuntimeConfig,
    loader: Path,
    ue4ss_root: Path,
) -> dict[str, object]:
    return {
        "product": RUNTIME_PRODUCT,
        "format": 1,
        "target_game_version": GAME_VERSION,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config.validated()),
        "loader_sha256": sha256_file(loader),
        "managed_files": _managed_hashes(ue4ss_root),
    }


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_owned_manifest(environment: VitaminRuntimeEnvironment) -> dict[str, object]:
    loader = environment.loader_target
    ue4ss_root = environment.ue4ss_target
    manifest = environment.manifest_target
    if not loader or not ue4ss_root or not manifest or not manifest.is_file():
        raise ModBuilderError("No editor-owned Vitamin runtime patch was found.")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModBuilderError("Vitamin runtime manifest is unreadable; refusing to touch the loader.") from exc
    if data.get("product") != RUNTIME_PRODUCT or data.get("format") != 1:
        raise ModBuilderError("The installed Vitamin runtime patch is not proven to be editor-owned.")
    if not loader.is_file() or sha256_file(loader) != data.get("loader_sha256"):
        raise ModBuilderError("The installed runtime loader changed; refusing to replace or remove it.")
    managed = data.get("managed_files")
    if not isinstance(managed, dict) or not ue4ss_root.is_dir():
        raise ModBuilderError("The installed Vitamin runtime file inventory is invalid.")
    for relative, expected in managed.items():
        path = ue4ss_root / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            raise ModBuilderError(f"Runtime file changed: {relative}. Refusing destructive cleanup.")
    return data


def installed_vitamin_runtime_config(
    environment: VitaminRuntimeEnvironment | None = None,
) -> VitaminRuntimeConfig | None:
    runtime = environment or discover_vitamin_runtime_environment()
    manifest = runtime.manifest_target
    if not manifest or not manifest.exists():
        return None
    try:
        data = _read_owned_manifest(runtime)
        raw = data["config"]
        return VitaminRuntimeConfig(**raw).validated()  # type: ignore[arg-type]
    except (KeyError, TypeError, OSError, ModBuilderError):
        return None


def _prepare_runtime_root(source: Path, target: Path, config: VitaminRuntimeConfig) -> None:
    source_root = source.resolve()
    source_mods = (source / "Mods").resolve()

    def runtime_only(directory: str, names: list[str]) -> set[str]:
        current = Path(directory).resolve()
        if current == source_root:
            return {name for name in names if name in {"UE4SS.pdb", "Docs", "Changelog.md", "README.md"}}
        if current == source_mods:
            return {name for name in names if name != "shared"}
        return set()

    shutil.copytree(
        source,
        target,
        ignore=runtime_only,
    )
    settings_path = target / "UE4SS-settings.ini"
    settings = settings_path.read_text(encoding="utf-8")
    settings = settings.replace("UseCache = 1", "UseCache = 0")
    settings_path.write_text(settings, encoding="utf-8")
    mods = target / "Mods"
    for child in mods.iterdir():
        if child.is_dir() and child.name != "shared":
            shutil.rmtree(child)
    scripts = mods / RUNTIME_MOD_NAME / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "main.lua").write_text(render_vitamin_runtime_lua(config), encoding="utf-8")
    (mods / "mods.txt").write_text(f"{RUNTIME_MOD_NAME} : 1\n", encoding="utf-8")


def install_vitamin_runtime(
    config: VitaminRuntimeConfig,
    environment: VitaminRuntimeEnvironment | None = None,
) -> Path:
    valid = config.validated()
    runtime = environment or discover_vitamin_runtime_environment()
    if is_game_running():
        raise ModBuilderError("Close Pokémon Gamma Emerald before installing runtime rules.")
    if not runtime.ready:
        raise ModBuilderError("The local UE4SS runtime source for GE-1.0.0 is incomplete.")
    assert runtime.loader_source and runtime.ue4ss_source
    assert runtime.loader_target and runtime.ue4ss_target and runtime.manifest_target and runtime.game_bin
    loader = runtime.loader_target
    ue4ss_root = runtime.ue4ss_target
    manifest = runtime.manifest_target

    if manifest.exists():
        data = _read_owned_manifest(runtime)
        main_lua = ue4ss_root / "Mods" / RUNTIME_MOD_NAME / "Scripts" / "main.lua"
        temporary = main_lua.with_name(".main.lua.updating")
        previous = main_lua.read_bytes()
        try:
            temporary.write_text(render_vitamin_runtime_lua(valid), encoding="utf-8")
            os.replace(temporary, main_lua)
            data.update(_manifest_payload(valid, loader, ue4ss_root))
            _write_manifest(manifest, data)
        except OSError as exc:
            main_lua.write_bytes(previous)
            raise ModBuilderError(f"Could not update Vitamin runtime rules: {exc}") from exc
        finally:
            temporary.unlink(missing_ok=True)
        return main_lua

    if loader.exists() or ue4ss_root.exists():
        raise ModBuilderError(
            "An unmanaged UE4SS/dwmapi installation already exists. The editor will not overwrite or merge it."
        )
    stage = Path(tempfile.mkdtemp(prefix=".gvr-", dir=runtime.game_bin))
    staged_root = stage / "ue4ss"
    staged_loader = stage / "dwmapi.dll"
    try:
        _prepare_runtime_root(runtime.ue4ss_source, staged_root, valid)
        shutil.copy2(runtime.loader_source, staged_loader)
        os.replace(staged_root, ue4ss_root)
        os.replace(staged_loader, loader)
        _write_manifest(manifest, _manifest_payload(valid, loader, ue4ss_root))
    except Exception as exc:
        if manifest.exists():
            manifest.unlink()
        if loader.exists():
            loader.unlink()
        if ue4ss_root.exists():
            shutil.rmtree(ue4ss_root)
        if isinstance(exc, ModBuilderError):
            raise
        raise ModBuilderError(f"Could not install Vitamin runtime rules: {exc}") from exc
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return ue4ss_root / "Mods" / RUNTIME_MOD_NAME / "Scripts" / "main.lua"


def uninstall_vitamin_runtime(
    environment: VitaminRuntimeEnvironment | None = None,
) -> None:
    runtime = environment or discover_vitamin_runtime_environment()
    if is_game_running():
        raise ModBuilderError("Close Pokémon Gamma Emerald before uninstalling runtime rules.")
    data = _read_owned_manifest(runtime)
    assert runtime.loader_target and runtime.ue4ss_target and runtime.manifest_target
    managed = {str(relative) for relative in data["managed_files"]}  # type: ignore[index]
    current = {
        path.relative_to(runtime.ue4ss_target).as_posix()
        for path in runtime.ue4ss_target.rglob("*")
        if path.is_file()
    }
    unexpected = sorted(path for path in current - managed if not path.startswith("UE4SS.log"))
    if unexpected:
        raise ModBuilderError(
            f"Unmanaged file exists inside UE4SS ({unexpected[0]}); refusing to delete possible user mods."
        )
    suffix = f".gamma-editor-removing-{os.getpid()}"
    loader_quarantine = runtime.loader_target.with_name(runtime.loader_target.name + suffix)
    root_quarantine = runtime.ue4ss_target.with_name(runtime.ue4ss_target.name + suffix)
    loader_moved = False
    root_moved = False
    try:
        os.replace(runtime.loader_target, loader_quarantine)
        loader_moved = True
        os.replace(runtime.ue4ss_target, root_quarantine)
        root_moved = True
    except OSError as exc:
        try:
            if root_moved and root_quarantine.exists():
                os.replace(root_quarantine, runtime.ue4ss_target)
            if loader_moved and loader_quarantine.exists():
                os.replace(loader_quarantine, runtime.loader_target)
        except OSError:
            pass
        raise ModBuilderError(f"Could not safely stage Vitamin runtime removal: {exc}") from exc

    try:
        runtime.manifest_target.unlink()
    except OSError as exc:
        try:
            os.replace(root_quarantine, runtime.ue4ss_target)
            os.replace(loader_quarantine, runtime.loader_target)
        except OSError:
            pass
        raise ModBuilderError(f"Could not finalize Vitamin runtime removal: {exc}") from exc

    try:
        loader_quarantine.unlink()
        shutil.rmtree(root_quarantine)
    except OSError as exc:
        raise ModBuilderError(
            "Vitamin runtime was deactivated, but an editor-owned quarantined file could not be cleaned up: "
            f"{exc}"
        ) from exc
