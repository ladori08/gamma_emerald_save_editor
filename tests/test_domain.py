from __future__ import annotations

import pytest

from gamma_editor.domain import legality_issues, pokemon_creation_defaults, validate_domain_value
from gamma_editor.catalog import HOLDABLE_ITEM_NAMES, NATURE_LABELS, SPECIES_INFO
from gamma_editor.errors import GvasError
from gamma_editor.gvas import GvasDocument, PropertyRecord


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


def test_species_metadata_filters_abilities_natures_and_holdable_items() -> None:
    torchic = SPECIES_INFO["torchic"]
    assert [item.label for item in torchic.abilities] == ["Blaze", "Speed Boost (H)"]
    assert [item.slot for item in torchic.abilities] == [0, 2]
    assert "Adamant (+Atk / -SpAtk)" in NATURE_LABELS
    assert "Leftovers" in HOLDABLE_ITEM_NAMES
    assert "Pokeball" not in HOLDABLE_ITEM_NAMES
    assert "Bike" not in HOLDABLE_ITEM_NAMES
