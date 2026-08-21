from __future__ import annotations

import pytest

from gamma_editor.domain import legality_issues, validate_domain_value
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
