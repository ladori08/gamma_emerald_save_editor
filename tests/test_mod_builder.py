from __future__ import annotations

import json
from pathlib import Path

import pytest

from gamma_editor import mod_builder
from gamma_editor.item_mod_templates import ITEM_MOD_ARCHETYPES, ITEM_MOD_TEMPLATES
from gamma_editor.mod_builder import (
    BuiltItemMod,
    CUSTOM_ITEM_ID_BASE,
    ItemModSpec,
    ModBuilderError,
    ModToolchain,
    VITAMIN_EV_AMOUNTS,
    allocate_custom_item_id,
    build_item_mod,
    custom_item_id_tag,
    discover_toolchain,
    install_item_mod,
    installed_item,
    uninstall_item_mod,
)


def item_spec(**changes: object) -> ItemModSpec:
    values: dict[str, object] = {
        "internal_name": "TestPotion",
        "display_name": "Test Potion",
        "description": "Restores 75 HP.",
        "item_id": 100075,
        "buy_price": 750,
        "sell_price": 375,
        "hp_restore_amount": 75,
    }
    values.update(changes)
    return ItemModSpec(**values)  # type: ignore[arg-type]


def fake_toolchain(tmp_path: Path) -> ModToolchain:
    game = tmp_path / "game"
    tool_root = tmp_path / "tools"
    paths = {
        "game_executable": game / "PokemonEmerald" / "Binaries" / "Win64" / "PokemonEmerald-Win64-Shipping.exe",
        "base_pak": game / "PokemonEmerald" / "Content" / "Paks" / "PokemonEmerald-Windows.pak",
        "dotnet": tool_root / "dotnet-sdk" / "dotnet.exe",
        "helper_dll": tool_root / "asset-parser" / "bin" / "Release" / "net8.0" / "AssetParser.dll",
        "repak": tool_root / "repak" / "repak-local.exe",
        "usmap": tool_root / "runtime_assets" / "mappings" / "GE-1.0.0" / "game.usmap",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    template_root = tool_root / "item_template_assets"
    for template in ITEM_MOD_TEMPLATES:
        asset = template_root / template.relative_path
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"fixture")
        asset.with_suffix(".uexp").write_bytes(b"fixture")
    return ModToolchain(game, **paths, template_root=template_root)


def test_item_spec_validation_and_helper_payload() -> None:
    payload = item_spec().helper_payload()
    assert payload["object_name"] == "DA_TestPotion"
    assert payload["package_path"] == "/Game/Items/DA_TestPotion"
    assert payload["item_name"] == "Test Potion"
    with pytest.raises(ModBuilderError, match="Internal name"):
        item_spec(internal_name="not safe!").validated()
    with pytest.raises(ModBuilderError, match="100000"):
        item_spec(item_id=99).validated()
    with pytest.raises(ModBuilderError, match="Sell price"):
        item_spec(buy_price=100, sell_price=101).validated()


def test_template_catalog_covers_every_supported_item_archetype() -> None:
    assert set(ITEM_MOD_ARCHETYPES) == {
        "HP Restore",
        "Status Heal",
        "Revive",
        "PP Restore",
        "Vitamin",
        "Rare Candy",
        "Evolution / Utility",
        "Held Item",
        "Berry",
        "TM",
        "Poké Ball",
    }
    assert len(ITEM_MOD_TEMPLATES) == 41
    assert len({template.key for template in ITEM_MOD_TEMPLATES}) == len(ITEM_MOD_TEMPLATES)
    assert len([template for template in ITEM_MOD_TEMPLATES if template.archetype == "Poké Ball"]) == 9


def test_ball_template_builds_ball_pocket_payload_and_validates_enum() -> None:
    valid = item_spec(
        internal_name="QuickUltra",
        display_name="Quick Ultra",
        template_key="DA_UltraBall",
        property_overrides={"PokeballType": "QuickBall", "CatchRateModifier": 3.5},
    ).validated()
    assert valid.archetype == "Poké Ball"
    assert valid.pocket == "Pokeballs"
    payload = valid.helper_payload()
    assert payload["source_object_name"] == "DA_UltraBall"
    assert payload["source_package_path"] == "/Game/Items/DA_UltraBall"
    assert payload["property_overrides"] == {"PokeballType": "QuickBall", "CatchRateModifier": 3.5}
    with pytest.raises(ModBuilderError, match="runtime enum"):
        item_spec(
            template_key="DA_UltraBall",
            property_overrides={"PokeballType": "ImaginaryBall"},
        ).validated()


def test_tm_and_vitamin_template_specific_fields() -> None:
    tm = item_spec(
        template_key="DA_TM01",
        property_overrides={
            "TeachableMove": {
                "package": "/Game/Pokemon/Moves/Water/BP_Surf",
                "asset": "BP_Surf_C",
            }
        },
    ).validated()
    assert tm.pocket == "TMs"
    assert tm.helper_payload()["source_package_path"] == "/Game/Items/TMs/DA_TM01"
    vitamin = item_spec(
        template_key="DA_Protein",
        property_overrides={"VitaminStat": "Speed", "EVBoostAmount": 84},
    ).validated()
    assert vitamin.archetype == "Vitamin"
    assert vitamin.property_overrides["EVBoostAmount"] == 84
    assert 10 in VITAMIN_EV_AMOUNTS and 252 in VITAMIN_EV_AMOUNTS
    with pytest.raises(ModBuilderError, match="dropdown"):
        item_spec(
            template_key="DA_Protein",
            property_overrides={"VitaminStat": "Speed", "EVBoostAmount": 11},
        ).validated()
    with pytest.raises(ModBuilderError, match="cannot safely edit"):
        item_spec(template_key="DA_Protein", property_overrides={"PokeballType": "PokeBall"}).validated()


def test_custom_item_ids_use_persistent_sequential_cstm_namespace(tmp_path: Path) -> None:
    state = tmp_path / "item-id-sequence.json"
    first = allocate_custom_item_id(state)
    second = allocate_custom_item_id(state)
    skipped = allocate_custom_item_id(state, used_ids=(CUSTOM_ITEM_ID_BASE + 3,))
    assert first == CUSTOM_ITEM_ID_BASE + 1
    assert second == CUSTOM_ITEM_ID_BASE + 2
    assert skipped == CUSTOM_ITEM_ID_BASE + 4
    assert custom_item_id_tag(first) == "CSTM-000001"
    assert custom_item_id_tag(100_000) is None
    persisted = json.loads(state.read_text(encoding="utf-8"))
    assert persisted == {"format": 1, "namespace": "CSTM", "next_sequence": 5}


def test_behavior_notes_explain_held_berry_and_tm_scope() -> None:
    by_key = {template.key: template for template in ITEM_MOD_TEMPLATES}
    assert "doubles battle money" in by_key["DA_AmuletCoin"].behavior_note
    assert "cures Sleeping" in by_key["DA_ChestoBerry"].behavior_note
    assert "does not create or edit a move" in by_key["DA_TM01"].behavior_note


def test_discover_toolchain_from_explicit_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tools = fake_toolchain(tmp_path)
    assert tools.game_root is not None
    (tools.game_root / "PokemonEmerald.exe").write_bytes(b"launcher")
    monkeypatch.setenv("GAMMA_EMERALD_GAME_DIR", str(tools.game_root))
    monkeypatch.setenv("GAMMA_EMERALD_MOD_TOOLS", str(tmp_path / "tools"))
    discovered = discover_toolchain()
    assert discovered.ready
    assert discovered.game_root == tools.game_root.resolve()


def test_build_install_and_owned_uninstall_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tools = fake_toolchain(tmp_path)
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path) -> None:
        calls.append(command)
        if "build-item" in command:
            asset = Path(command[4])
            asset.write_bytes(b"uasset")
            asset.with_suffix(".uexp").write_bytes(b"uexp")
            payload = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
            assert payload["item_name"] == "Test Potion"
        else:
            Path(command[-1]).write_bytes(b"pak-content")

    monkeypatch.setattr(mod_builder, "_run_checked", fake_run)
    monkeypatch.setattr(mod_builder, "is_game_running", lambda: False)
    built = build_item_mod(item_spec(), tmp_path / "output", tools)
    assert built.pak_path.read_bytes() == b"pak-content"
    assert len(calls) == 2
    assert "--version" in calls[1] and "V11" in calls[1]
    assert "--mount-point" in calls[1] and "../../../" in calls[1]

    target = install_item_mod(built, tools)
    assert target.name == "PokemonEmerald-Windows_0_P.pak"
    assert installed_item(tools) == item_spec().validated()
    with pytest.raises(ModBuilderError, match="confirm replacement"):
        install_item_mod(built, tools)
    uninstall_item_mod(tools)
    assert not target.exists()
    assert installed_item(tools) is None

    target.write_bytes(b"foreign")
    with pytest.raises(ModBuilderError, match="editor-owned"):
        uninstall_item_mod(tools)
    assert target.read_bytes() == b"foreign"


def test_install_refuses_game_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tools = fake_toolchain(tmp_path)
    pak = tmp_path / "built.pak"
    pak.write_bytes(b"pak")
    manifest = Path(str(pak) + ".gamma-editor.json")
    manifest.write_text("{}", encoding="utf-8")
    built = BuiltItemMod(pak, manifest, mod_builder.sha256_file(pak), item_spec())
    monkeypatch.setattr(mod_builder, "is_game_running", lambda: True)
    with pytest.raises(ModBuilderError, match="Close"):
        install_item_mod(built, tools)
