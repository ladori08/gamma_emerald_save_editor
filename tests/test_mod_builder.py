from __future__ import annotations

import json
from pathlib import Path

import pytest

from gamma_editor import mod_builder
from gamma_editor.item_mod_templates import ITEM_MOD_ARCHETYPES, ITEM_MOD_TEMPLATES, player_effect_summary
from gamma_editor.mod_builder import (
    BuiltItemMod,
    CUSTOM_ITEM_ID_BASE,
    ItemModSpec,
    ModBuilderError,
    ModToolchain,
    VITAMIN_EV_AMOUNTS,
    allocate_custom_item_id,
    build_and_install_item_bundle,
    build_item_mod,
    custom_item_id_tag,
    discover_toolchain,
    install_item_mod,
    installed_item,
    installed_items,
    remove_item_from_bundle,
    replace_item_in_bundle,
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


def test_visual_and_behavior_templates_can_differ_only_inside_one_category() -> None:
    combined = item_spec(
        template_key="DA_LeftOvers",
        visual_template_key="DA_LightOrb",
        property_overrides={
            "AttackMultiplier": 2.0,
            "DefenseMultiplier": 1.5,
            "SpecialAttackMultiplier": 2.0,
            "SpecialDefenseMultiplier": 1.25,
            "SpeedMultiplier": 1.1,
            "HPRestorePerTurn": 6.25,
        },
    ).validated()
    assert combined.visual_template_key == "DA_LightOrb"
    assert combined.template_key == "DA_LeftOvers"
    assert combined.property_overrides["DefenseMultiplier"] == 1.5
    assert combined.helper_payload()["visual_template_key"] == "DA_LightOrb"

    with pytest.raises(ModBuilderError, match="selected item category"):
        item_spec(template_key="DA_Potion", visual_template_key="DA_LightOrb").validated()


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


def test_player_effect_summary_uses_plain_dynamic_item_wording() -> None:
    by_key = {template.key: template for template in ITEM_MOD_TEMPLATES}
    assert player_effect_summary(
        by_key["DA_SilkScarf"],
        item_name="Custom Scarf",
        values={"BoostedType": "Normal", "TypeBoostMultiplier": "1.2"},
    ) == "When held, Custom Scarf raises the power of Normal-type moves by 20%."
    assert "grants 126 Speed EVs" in player_effect_summary(
        by_key["DA_Protein"],
        item_name="Speed Juice",
        values={"VitaminStat": "Speed", "EVBoostAmount": "126"},
    )
    assert "teaches it Surf" in player_effect_summary(
        by_key["DA_TM01"], item_name="Surf Disk", values={"TeachableMove": "Surf"}
    )
    combined = player_effect_summary(
        by_key["DA_LeftOvers"],
        item_name="Battle Charm",
        values={
            "AttackMultiplier": "2",
            "DefenseMultiplier": "1.5",
            "SpecialAttackMultiplier": "1",
            "SpecialDefenseMultiplier": "1",
            "SpeedMultiplier": "1",
            "HPRestorePerTurn": "6.25",
        },
    )
    assert "multiplies Attack by 2×" in combined
    assert "multiplies Defense by 1.5×" in combined
    assert "restores 6.25% maximum HP" in combined


def test_build_passes_separate_visual_asset_to_helper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tools = fake_toolchain(tmp_path)
    helper_payloads: list[dict[str, object]] = []

    def fake_run(command: list[str], *, cwd: Path) -> None:
        if "build-item" in command:
            asset = Path(command[4])
            asset.write_bytes(b"uasset")
            asset.with_suffix(".uexp").write_bytes(b"uexp")
            helper_payloads.append(json.loads(Path(command[-1]).read_text(encoding="utf-8")))
        else:
            Path(command[-1]).write_bytes(b"pak-content")

    monkeypatch.setattr(mod_builder, "_run_checked", fake_run)
    monkeypatch.setattr(mod_builder, "is_game_running", lambda: False)
    spec = item_spec(
        internal_name="VisualBehaviorSplit",
        template_key="DA_LeftOvers",
        visual_template_key="DA_LightOrb",
        property_overrides={"AttackMultiplier": 2.0, "HPRestorePerTurn": 6.25},
    )
    build_item_mod(spec, tmp_path / "output", tools)
    assert len(helper_payloads) == 1
    assert helper_payloads[0]["visual_template_key"] == "DA_LightOrb"
    assert helper_payloads[0]["visual_source_path"].endswith("DA_LightOrb.uasset")


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


def test_build_and_install_bundle_uses_disposable_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tools = fake_toolchain(tmp_path)
    staging_outputs: list[Path] = []

    def fake_run(command: list[str], *, cwd: Path) -> None:
        if "build-item" in command:
            asset = Path(command[4])
            asset.write_bytes(b"uasset")
            asset.with_suffix(".uexp").write_bytes(b"uexp")
        else:
            output = Path(command[-1])
            staging_outputs.append(output)
            output.write_bytes(b"staged-pack")

    monkeypatch.setattr(mod_builder, "_run_checked", fake_run)
    monkeypatch.setattr(mod_builder, "is_game_running", lambda: False)
    stale_export = tmp_path / "exports" / "GammaEditor-TestPotion.pak"
    stale_export.parent.mkdir()
    stale_export.write_bytes(b"older-manual-export")

    target = build_and_install_item_bundle((item_spec(),), tools)

    assert target.read_bytes() == b"staged-pack"
    assert installed_items(tools) == (item_spec().validated(),)
    assert stale_export.read_bytes() == b"older-manual-export"
    assert len(staging_outputs) == 1
    assert not staging_outputs[0].exists()


def test_building_on_an_installed_pack_preserves_every_custom_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tools = fake_toolchain(tmp_path)
    built_names: list[str] = []

    def fake_run(command: list[str], *, cwd: Path) -> None:
        if "build-item" in command:
            asset = Path(command[4])
            asset.write_bytes(b"uasset")
            asset.with_suffix(".uexp").write_bytes(b"uexp")
            payload = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
            built_names.append(payload["item_name"])
        else:
            Path(command[-1]).write_bytes("|".join(built_names).encode())

    monkeypatch.setattr(mod_builder, "_run_checked", fake_run)
    monkeypatch.setattr(mod_builder, "is_game_running", lambda: False)
    first = item_spec(
        internal_name="CustomLightBall",
        display_name="Light Ball Pro Max",
        item_id=CUSTOM_ITEM_ID_BASE + 1,
        template_key="DA_LightOrb",
    ).validated()
    second = item_spec(
        internal_name="CustomMasterBall",
        display_name="Super Ball",
        item_id=CUSTOM_ITEM_ID_BASE + 2,
        template_key="DA_Shimmerball",
        property_overrides={"PokeballType": "MasterBall"},
    ).validated()

    initial = build_item_mod(first, tmp_path / "first", tools)
    install_item_mod(initial, tools)
    legacy_manifest = json.loads(tools.installed_manifest.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    legacy_manifest["format"] = 1
    legacy_manifest.pop("items")
    tools.installed_manifest.write_text(json.dumps(legacy_manifest), encoding="utf-8")  # type: ignore[union-attr]
    assert installed_items(tools) == (first,)
    rebuilt = build_item_mod(second, tmp_path / "second", tools, bundled_specs=installed_items(tools))
    install_item_mod(rebuilt, tools, replace_owned=True)

    assert built_names == ["Light Ball Pro Max", "Light Ball Pro Max", "Super Ball"]
    assert installed_items(tools) == (first, second)
    assert installed_item(tools) == second
    manifest = json.loads(tools.installed_manifest.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert manifest["format"] == 2
    assert [item["display_name"] for item in manifest["items"]] == ["Light Ball Pro Max", "Super Ball"]


def test_custom_item_pack_rejects_identity_collisions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tools = fake_toolchain(tmp_path)
    monkeypatch.setattr(mod_builder, "is_game_running", lambda: False)
    existing = item_spec(item_id=CUSTOM_ITEM_ID_BASE + 1)
    duplicate = item_spec(internal_name="AnotherName", display_name="Another Item", item_id=CUSTOM_ITEM_ID_BASE + 1)
    with pytest.raises(ModBuilderError, match="Item ID"):
        build_item_mod(duplicate, tmp_path / "output", tools, bundled_specs=(existing,))


def test_editing_an_item_preserves_identity_category_and_pack_position() -> None:
    first = item_spec(item_id=CUSTOM_ITEM_ID_BASE + 1).validated()
    second = item_spec(
        internal_name="HeldCustom",
        display_name="Battle Charm",
        item_id=CUSTOM_ITEM_ID_BASE + 2,
        template_key="DA_LeftOvers",
        visual_template_key="DA_LightOrb",
        property_overrides={"AttackMultiplier": 2.0, "HPRestorePerTurn": 6.25},
    ).validated()
    updated = item_spec(
        internal_name=second.internal_name,
        display_name=second.display_name,
        item_id=second.item_id,
        description="Updated effect.",
        template_key="DA_AmuletCoin",
        visual_template_key="DA_SilkScarf",
        property_overrides={"DefenseMultiplier": 1.5, "HPRestorePerTurn": 3.0},
    ).validated()
    result = replace_item_in_bundle((first, second), second.item_id, updated)
    assert result == (first, updated)

    with pytest.raises(ModBuilderError, match="preserve Item ID"):
        replace_item_in_bundle((first, second), second.item_id, item_spec(
            internal_name=second.internal_name,
            display_name="Renamed Charm",
            item_id=second.item_id,
            template_key="DA_LeftOvers",
        ))
    with pytest.raises(ModBuilderError, match="preserve the item category"):
        replace_item_in_bundle((first, second), second.item_id, item_spec(
            internal_name=second.internal_name,
            display_name=second.display_name,
            item_id=second.item_id,
            template_key="DA_Potion",
        ))


def test_removing_one_item_from_bundle_is_exact_and_can_empty_pack() -> None:
    first = item_spec(item_id=CUSTOM_ITEM_ID_BASE + 1).validated()
    second = item_spec(
        internal_name="SecondItem", display_name="Second Item", item_id=CUSTOM_ITEM_ID_BASE + 2
    ).validated()
    assert remove_item_from_bundle((first, second), first.item_id) == (second,)
    assert remove_item_from_bundle((first,), first.item_id) == ()
    with pytest.raises(ModBuilderError, match="no longer exists uniquely"):
        remove_item_from_bundle((first, second), CUSTOM_ITEM_ID_BASE + 99)


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
