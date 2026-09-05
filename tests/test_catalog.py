from __future__ import annotations

from gamma_editor.catalog import (
    HOLDABLE_ITEM_NAMES,
    ITEMS_BY_POCKET,
    MOVE_BASE_PP,
    MOVE_LEARNSETS,
    MOVES_BY_NAME,
    RUNTIME_ABILITY_ENUMS,
    SPECIES,
    SPECIES_INFO,
    TYPE_COLORS,
    TYPE_ORDER,
    base_pp_for_move,
    calculate_pokemon_stats,
    learnset_for_species,
    legal_moves_for_species,
    max_pp_for_move,
    pp_up_limit_for_move,
    pp_ups_from_max_pp,
    type_attacks,
    type_defenses,
)
from gamma_editor.consumer_gui import (
    exact_choice,
    filter_choices,
    party_set_target_slot,
    pokemon_showdown_preset,
    validated_enum_value,
)
from gamma_editor.domain import PokemonView


STAT_NAMES = ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed")


def test_live_search_is_case_insensitive_and_prioritizes_prefixes() -> None:
    values = ("Potion", "Super Potion", "Max Potion", "Antidote")
    assert filter_choices(values, "pot") == ("Potion", "Super Potion", "Max Potion")
    assert filter_choices(values, "MAX") == ("Max Potion",)
    assert filter_choices(values, "") == values
    assert exact_choice(list(values), " max potion ") == "Max Potion"


def test_clone_clipboard_text_uses_showdown_style_set_format() -> None:
    fields = {
        "Nickname": "Buddy", "Gender": "EPokemonGender::Male", "HeldItem": "Leftovers",
        "Ability": "EPokemonAbility::Torrent", "Level": 8, "bIsShiny": True,
        "Nature": "ENature::Hardy", "MoveNames": ("Tackle", "Surf"),
    }
    for stat in STAT_NAMES:
        fields[stat + "_EV"] = 0
        fields[stat + "_IV"] = 31
    pokemon = PokemonView("Party[0]", "Party", None, 0, "Mudkip", True, fields)

    text = pokemon_showdown_preset(pokemon)

    assert text.splitlines()[0] == "Buddy (Mudkip) (M) @ Leftovers"
    assert "Ability: Torrent" in text
    assert "Level: 8" in text
    assert "Shiny: Yes" in text
    assert "31 HP / 31 Atk / 31 Def / 31 SpA / 31 SpD / 31 Spe" in text
    assert text.endswith("- Tackle\n- Surf")


def test_any_empty_party_card_redirects_to_nearest_packed_slot() -> None:
    assert party_set_target_slot(3, 3) == 3
    assert party_set_target_slot(3, 4) == 3
    assert party_set_target_slot(3, 5) == 3
    assert party_set_target_slot(3, 2) is None
    assert party_set_target_slot(6, 5) is None


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


def test_max_revive_without_concrete_asset_is_not_exposed() -> None:
    assert "Max Revive" not in {item.name for item in ITEMS_BY_POCKET["Items"]}
    assert "Max Revive" not in HOLDABLE_ITEM_NAMES
    assert sum(len(items) for items in ITEMS_BY_POCKET.values()) == 86


def test_exact_learnsets_cover_every_species_asset() -> None:
    assert len(MOVE_LEARNSETS) == len(SPECIES) == 118
    assert set(MOVE_LEARNSETS) == {species.name.casefold() for species in SPECIES}


def test_level_up_moves_are_level_and_evolution_stage_specific() -> None:
    torchic_8 = {move.name for move in legal_moves_for_species("Torchic", 8)}
    torchic_10 = {move.name for move in legal_moves_for_species("Torchic", 10)}
    combusken_16 = {move.name for move in legal_moves_for_species("Combusken", 16)}
    blaziken_36 = {move.name for move in legal_moves_for_species("Blaziken", 36)}

    assert "Ember" not in torchic_8
    assert "Ember" in torchic_10
    assert "Double Kick" not in torchic_10
    assert "Double Kick" in combusken_16
    assert "Blaze Kick" not in combusken_16
    assert "Blaze Kick" in blaziken_36


def test_machine_moves_are_split_into_tm_and_shipped_hm_sources() -> None:
    wingull = learnset_for_species("Wingull")
    assert wingull is not None
    assert "Fly" in {move.name for move in wingull.hm}
    assert "Fly" not in {move.name for move in wingull.tm}


def test_base_pp_catalog_exactly_covers_every_move() -> None:
    assert len(MOVE_BASE_PP) == 99
    assert base_pp_for_move("Scratch") == 35
    assert base_pp_for_move("Aerial Ace") == 20
    assert base_pp_for_move("Flamethrower") == 15
    assert base_pp_for_move("Rock Slide") == 10
    assert base_pp_for_move("Leaf Storm") == 5
    assert base_pp_for_move("Struggle") == 1


def test_pp_up_scaling_matches_game_formula() -> None:
    assert [max_pp_for_move("Scratch", value) for value in range(4)] == [35, 42, 49, 56]
    assert [max_pp_for_move("Flamethrower", value) for value in range(4)] == [15, 18, 21, 24]
    assert [max_pp_for_move("Leaf Storm", value) for value in range(4)] == [5, 6, 7, 8]
    assert pp_up_limit_for_move("Struggle") == 0
    assert max_pp_for_move("Struggle", 0) == 1
    assert pp_ups_from_max_pp("Scratch", 49) == 2
    assert pp_ups_from_max_pp("Scratch", 5) is None


def test_exposed_abilities_are_concrete_gamma_runtime_enums() -> None:
    assert len(RUNTIME_ABILITY_ENUMS) == 52
    assert all(
        ability.enum_name in RUNTIME_ABILITY_ENUMS
        for info in SPECIES_INFO.values()
        for ability in info.abilities
    )
    assert [ability.enum_name for ability in SPECIES_INFO["treecko"].abilities] == ["Overgrow"]
    assert [ability.enum_name for ability in SPECIES_INFO["torchic"].abilities] == ["Blaze", "SpeedBoost"]


def test_type_matchups_cover_best_stab_attack_and_combined_defense() -> None:
    mudkip_attacks = type_attacks(("Water", "Ground"))
    assert mudkip_attacks["Fire"] == 2
    assert mudkip_attacks["Electric"] == 2
    assert mudkip_attacks["Flying"] == 1
    assert mudkip_attacks["Grass"] == .5

    mudkip_defenses = type_defenses(("Water", "Ground"))
    assert mudkip_defenses["Electric"] == 0
    assert mudkip_defenses["Grass"] == 4
    assert mudkip_defenses["Fire"] == .5


def test_move_catalog_exposes_verified_attack_types_for_move_charts() -> None:
    assert MOVES_BY_NAME["tackle"].category == "Normal"
    assert MOVES_BY_NAME["rock slide"].category == "Rock"
    assert MOVES_BY_NAME["surf"].category == "Water"
    assert MOVES_BY_NAME["ice beam"].category == "Ice"


def test_species_types_support_dual_type_main_badges() -> None:
    assert SPECIES_INFO["lucario"].types == ("Fighting", "Steel")
    assert set(TYPE_COLORS) == set(TYPE_ORDER)
    assert all(
        type_name in TYPE_COLORS
        for info in SPECIES_INFO.values()
        for type_name in info.types
    )
