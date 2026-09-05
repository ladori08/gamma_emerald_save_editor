from __future__ import annotations

import struct

import pytest

from gamma_editor.domain import (
    PokemonView,
    _guid_text,
    _new_unique_id,
    copy_pokemon_preset,
    legality_issues,
    party_pokemon,
    patch_pokemon,
    pokemon_creation_defaults,
    pokemon_species_profile,
    release_pokemon,
    set_pokemon_preset,
    validate_domain_value,
    validate_move_pp_values,
    validate_species_move_choices,
)
from gamma_editor.catalog import HOLDABLE_ITEM_NAMES, MOVES_BY_NAME, NATURE_LABELS, SPECIES_INFO
from gamma_editor.errors import GvasError
from gamma_editor.gvas import GvasDocument, PropertyRecord, parse_gvas

from conftest import fstring


def _type(name: str, *parameters: bytes) -> bytes:
    return fstring(name) + struct.pack("<I", len(parameters)) + b"".join(parameters)


def _property(name: str, type_bytes: bytes, payload: bytes) -> bytes:
    return fstring(name) + type_bytes + struct.pack("<IB", len(payload), 0) + payload


def _pokemon_element(species: str, pokemon_id: int, guid_parts: tuple[int, int, int, int]) -> bytes:
    species_path = f"/Game/BPS/PokemonData/Pokemon/Water/DA_{species}"
    return b"".join(
        (
            _property(
                "SpeciesData", _type("SoftObjectProperty"),
                fstring(species_path) + fstring(f"DA_{species}") + struct.pack("<i", 0),
            ),
            _property("PokemonID", _type("IntProperty"), struct.pack("<i", pokemon_id)),
            _property(
                "UniqueID",
                _type("StructProperty", _type("Guid"), _type("/Script/CoreUObject")),
                struct.pack("<IIII", *guid_parts),
            ),
            _property("Nickname", _type("StrProperty"), fstring(species)),
            fstring("None"),
        )
    )


def _party_document(*elements: bytes) -> GvasDocument:
    header = b"".join(
        (
            b"GVAS", struct.pack("<III", 3, 522, 1017),
            struct.pack("<HHHI", 5, 6, 1, 44394996),
            fstring("++UE5+Release-5.6"), struct.pack("<II", 3, 0),
            fstring("/Script/PokemonEmerald.TestSave"), b"\0",
        )
    )
    party = _property(
        "Party",
        _type(
            "ArrayProperty",
            _type("StructProperty", _type("PokemonInstanceData"), _type("/Script/PokemonEmerald")),
        ),
        struct.pack("<I", len(elements)) + b"".join(elements),
    )
    return parse_gvas(header + party + fstring("None") + struct.pack("<I", 0))


def _prop(path: str, value: int) -> PropertyRecord:
    return PropertyRecord(
        name=path.rsplit(".", 1)[-1],
        path=path,
        type_name="IntProperty",
        size=4,
        array_index=0,
        value_offset=0,
        value_size=4,
        value=value,
        editable=True,
    )


def test_level_range() -> None:
    prop = _prop("Party[0].Level", 6)
    document = GvasDocument(raw=b"", header=None, properties=[prop])  # type: ignore[arg-type]
    validate_domain_value(document, prop, 100)
    with pytest.raises(GvasError, match="Level"):
        validate_domain_value(document, prop, 101)


def test_iv_range() -> None:
    prop = _prop("Party[0].HP_IV", 20)
    document = GvasDocument(raw=b"", header=None, properties=[prop])  # type: ignore[arg-type]
    validate_domain_value(document, prop, 31)
    with pytest.raises(GvasError, match="IV"):
        validate_domain_value(document, prop, -1)


def test_ev_total_cap() -> None:
    props = [
        _prop("Party[0].HP_EV", 252),
        _prop("Party[0].Attack_EV", 252),
        _prop("Party[0].Defense_EV", 0),
    ]
    document = GvasDocument(raw=b"", header=None, properties=props)  # type: ignore[arg-type]
    validate_domain_value(document, props[2], 6)
    with pytest.raises(GvasError, match="maximum is 510"):
        validate_domain_value(document, props[2], 7)
    validate_domain_value(document, props[2], 252, allow_ev_over_510=True)


def test_item_quantity_range() -> None:
    prop = _prop("PlayerItems[0].Items[0].Quantity", 1)
    document = GvasDocument(raw=b"", header=None, properties=[prop])  # type: ignore[arg-type]
    validate_domain_value(document, prop, 9999)
    with pytest.raises(GvasError, match="quantity"):
        validate_domain_value(document, prop, 10000)


def test_verified_enum_catalog() -> None:
    prop = _prop("Party[0].Nature", 0)
    prop.type_name = "EnumProperty"
    document = GvasDocument(raw=b"", header=None, properties=[prop])  # type: ignore[arg-type]
    validate_domain_value(document, prop, "ENature::Adamant")
    with pytest.raises(GvasError, match="enum catalog"):
        validate_domain_value(document, prop, "ENature::DefinitelyNotReal")


def test_legality_report_flags_invalid_level() -> None:
    species = _prop("Party[0].SpeciesData", 0)
    species.type_name = "SoftObjectProperty"
    species.value = "/Game/BPS/PokemonData/Pokemon/Water/DA_Mudkip (DA_Mudkip)"
    level = _prop("Party[0].Level", 101)
    document = GvasDocument(raw=b"", header=None, properties=[species, level])  # type: ignore[arg-type]
    issues = legality_issues(document)
    assert any("Level 101" in issue.message for issue in issues)


def test_creation_defaults_use_trainer_and_unique_pokemon_id() -> None:
    player_name = _prop("PlayerName", 0)
    player_name.type_name = "StrProperty"
    player_name.value = "MAY"
    player_id = _prop("PlayerId", 12345)
    species = _prop("Party[0].SpeciesData", 0)
    species.type_name = "SoftObjectProperty"
    species.value = "/Game/BPS/PokemonData/Pokemon/Water/DA_Mudkip (DA_Mudkip)"
    pokemon_id = _prop("Party[0].PokemonID", 800)
    document = GvasDocument(
        raw=b"",
        header=None,  # type: ignore[arg-type]
        properties=[player_name, player_id, species, pokemon_id],
    )

    defaults = pokemon_creation_defaults(document)

    assert defaults["OriginalTrainerName"] == "MAY"
    assert defaults["CurrentTrainerName"] == "MAY"
    assert defaults["OriginalTrainerID"] == 12345
    assert defaults["PokemonID"] == 801
    assert defaults["Level"] == 5
    assert defaults["MaxHP"] == 1.0


def test_species_profile_loads_complete_torchic_basics() -> None:
    player_name = _prop("PlayerName", 0)
    player_name.type_name = "StrProperty"
    player_name.value = "MAY"
    player_id = _prop("PlayerId", 12345)
    document = GvasDocument(
        raw=b"", header=None, properties=[player_name, player_id]  # type: ignore[arg-type]
    )

    profile = pokemon_species_profile(document, "Torchic", level=5)

    assert profile.scalar_defaults["Ability"] == "EPokemonAbility::Blaze"
    assert profile.scalar_defaults["AbilitySlot"] == 0
    assert profile.scalar_defaults["Gender"] == "EPokemonGender::Male"
    assert profile.scalar_defaults["CurrentHP"] == profile.scalar_defaults["MaxHP"] == 19.0
    assert [move.name for move in profile.moves] == ["Growl", "Scratch"]
    assert profile.current_pp == profile.max_pp == (30, 35)


def test_species_metadata_filters_abilities_natures_and_holdable_items() -> None:
    torchic = SPECIES_INFO["torchic"]
    assert [item.label for item in torchic.abilities] == ["Blaze", "Speed Boost (H)"]
    assert [item.slot for item in torchic.abilities] == [0, 2]
    assert "Adamant (+Atk / -SpAtk)" in NATURE_LABELS
    assert "Leftovers" in HOLDABLE_ITEM_NAMES
    assert "Pokeball" not in HOLDABLE_ITEM_NAMES
    assert "Bike" not in HOLDABLE_ITEM_NAMES


def test_species_move_validation_accepts_exact_tm_egg_and_level_sources() -> None:
    validate_species_move_choices(
        "Torchic",
        8,
        [MOVES_BY_NAME["scratch"], MOVES_BY_NAME["aerial ace"], MOVES_BY_NAME["low kick"]],
    )


def test_species_move_validation_rejects_future_stage_and_duplicate_moves() -> None:
    with pytest.raises(GvasError, match="not legal for Torchic at Lv. 8"):
        validate_species_move_choices("Torchic", 8, [MOVES_BY_NAME["ember"]])
    with pytest.raises(GvasError, match="same move"):
        validate_species_move_choices(
            "Torchic", 50, [MOVES_BY_NAME["scratch"], MOVES_BY_NAME["scratch"]]
        )


def test_move_pp_validation_accepts_pp_ups_and_rejects_impossible_maximum() -> None:
    moves = [MOVES_BY_NAME["scratch"], MOVES_BY_NAME["flamethrower"]]
    validate_move_pp_values(moves, [40, 24], [42, 24])
    with pytest.raises(GvasError, match="Scratch Max PP 40"):
        validate_move_pp_values(moves, [35, 15], [40, 15])
    with pytest.raises(GvasError, match="Current PP"):
        validate_move_pp_values(moves, [43, 15], [42, 15])


def test_new_unique_id_retries_a_template_collision(monkeypatch) -> None:
    existing = struct.pack("<IIII", 1, 2, 3, 4)
    replacement = struct.pack("<IIII", 5, 6, 7, 8)
    prop = _prop("Boxes[0].Pokemon.UniqueID", 0)
    prop.type_name = "StructProperty"
    prop.type_descriptor = "StructProperty<Guid</Script/CoreUObject>>"
    prop.value = _guid_text(existing)
    document = GvasDocument(raw=b"", header=None, properties=[prop])  # type: ignore[arg-type]
    candidates = iter((existing, replacement))
    monkeypatch.setattr("gamma_editor.domain.secrets.token_bytes", lambda size: next(candidates))

    text, payload = _new_unique_id(document)

    assert payload == replacement
    assert text == "00000005-00000006-00000007-00000008"


def test_legality_report_flags_unique_id_shared_with_empty_box() -> None:
    species = _prop("Party[0].SpeciesData", 0)
    species.type_name = "SoftObjectProperty"
    species.value = "/Game/BPS/PokemonData/Pokemon/Water/DA_Mudkip (DA_Mudkip)"
    party_guid = _prop("Party[0].UniqueID", 0)
    party_guid.type_name = "StructProperty"
    party_guid.value = "00000001-00000002-00000003-00000004"
    empty_species = _prop("Boxes[0].Pokemon.SpeciesData", 0)
    empty_species.type_name = "SoftObjectProperty"
    empty_species.value = "None (None)"
    empty_guid = _prop("Boxes[0].Pokemon.UniqueID", 0)
    empty_guid.type_name = "StructProperty"
    empty_guid.value = party_guid.value
    document = GvasDocument(
        raw=b"", header=None,  # type: ignore[arg-type]
        properties=[species, party_guid, empty_species, empty_guid],
    )

    issues = legality_issues(document)

    assert any("UniqueID duplicates Boxes[0].Pokemon.UniqueID" in issue.message for issue in issues)


def test_patch_pokemon_rejects_non_runtime_ability_before_serialization() -> None:
    ability = _prop("Party[0].Ability", 0)
    ability.type_name = "EnumProperty"
    ability.value = "EPokemonAbility::Overgrow"
    slot = _prop("Party[0].AbilitySlot", 0)
    pokemon = PokemonView(
        prefix="Party[0]", source="Party", box_index=None, slot_index=0,
        species="Treecko", occupied=True,
        fields={"Ability": ability.value, "AbilitySlot": 0},
    )
    document = GvasDocument(raw=b"", header=None, properties=[ability, slot])  # type: ignore[arg-type]

    with pytest.raises(GvasError, match="not a GE-1.0.0 runtime enum"):
        patch_pokemon(
            document,
            pokemon,
            scalar_changes={"Ability": "EPokemonAbility::Silvano", "AbilitySlot": 2},
        )


def test_copy_then_set_party_preset_preserves_payload_but_assigns_fresh_ids(monkeypatch) -> None:
    original = _pokemon_element("Mudkip", 40, (1, 2, 3, 4))
    document = _party_document(original)
    source = party_pokemon(document)[0]
    target = PokemonView(
        prefix="Party[1]", source="Party", box_index=None, slot_index=1,
        species="Empty", occupied=False, fields={},
    )
    fresh_guid = struct.pack("<IIII", 5, 6, 7, 8)
    monkeypatch.setattr("gamma_editor.domain.secrets.token_bytes", lambda size: fresh_guid)

    preset = copy_pokemon_preset(document, source)
    assert document.raw == _party_document(original).raw
    assert preset.species == "Mudkip"
    after = parse_gvas(set_pokemon_preset(document, preset, target))
    pokemon = party_pokemon(after)

    assert [item.species for item in pokemon] == ["Mudkip", "Mudkip"]
    assert pokemon[0].fields["PokemonID"] == 40
    assert pokemon[1].fields["PokemonID"] == 41
    assert pokemon[0].fields["UniqueID"] != pokemon[1].fields["UniqueID"]
    assert pokemon[1].fields["Nickname"] == "Mudkip"


def test_release_party_pokemon_removes_payload_and_blocks_last_member() -> None:
    mudkip = _pokemon_element("Mudkip", 40, (1, 2, 3, 4))
    torchic = _pokemon_element("Torchic", 41, (5, 6, 7, 8))
    document = _party_document(mudkip, torchic)

    after = parse_gvas(release_pokemon(document, party_pokemon(document)[0]))

    assert [item.species for item in party_pokemon(after)] == ["Torchic"]
    with pytest.raises(GvasError, match="last Party"):
        release_pokemon(after, party_pokemon(after)[0])
