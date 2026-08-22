from __future__ import annotations

from gamma_editor.catalog import HOLDABLE_ITEM_NAMES, ITEMS_BY_POCKET, calculate_pokemon_stats
from gamma_editor.consumer_gui import exact_choice, filter_choices, validated_enum_value


STAT_NAMES = ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed")


def test_live_search_is_case_insensitive_and_prioritizes_prefixes() -> None:
    values = ("Potion", "Super Potion", "Max Potion", "Antidote")
    assert filter_choices(values, "pot") == ("Potion", "Super Potion", "Max Potion")
    assert filter_choices(values, "MAX") == ("Max Potion",)
    assert filter_choices(values, "") == values
    assert exact_choice(list(values), " max potion ") == "Max Potion"


def test_searchable_enum_choices_restore_gamma_prefixes() -> None:
    assert validated_enum_value("Gender", "male") == "EPokemonGender::Male"
    assert validated_enum_value("StatusCondition", "none") == "ESTATUSEffect::None"
    assert validated_enum_value("MetType", "gift") == "EPokemonMetType::Gift"


def test_torchic_final_stats_include_nature_iv_and_ev() -> None:
    ivs = {stat: 31 for stat in STAT_NAMES}
    evs = {stat: 0 for stat in STAT_NAMES}
    evs.update({"HP": 252, "Attack": 252})
    assert calculate_pokemon_stats("Torchic", 50, "Adamant", ivs, evs) == {
        "HP": 152,
        "Attack": 123,
        "Defense": 60,
        "SpecialAttack": 81,
        "SpecialDefense": 70,
        "Speed": 65,
    }


def test_shedinja_always_has_one_calculated_hp() -> None:
    ivs = {stat: 31 for stat in STAT_NAMES}
    evs = {stat: 252 for stat in STAT_NAMES}
    assert calculate_pokemon_stats("Shedinja", 100, "Hardy", ivs, evs)["HP"] == 1


def test_max_revive_is_an_item_and_is_holdable() -> None:
    assert "Max Revive" in {item.name for item in ITEMS_BY_POCKET["Items"]}
    assert "Max Revive" in HOLDABLE_ITEM_NAMES
