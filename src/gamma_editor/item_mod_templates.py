from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ItemModTemplate:
    key: str
    label: str
    archetype: str
    relative_path: str
    editable_fields: tuple[str, ...] = ()
    experimental: bool = False
    behavior_note: str = ""

    @property
    def object_name(self) -> str:
        return self.relative_path.rsplit("/", 1)[-1].removesuffix(".uasset")

    @property
    def package_path(self) -> str:
        path = self.relative_path.removeprefix("PokemonEmerald/Content/").removesuffix(".uasset")
        return "/Game/" + path


def _root(
    key: str,
    label: str,
    archetype: str,
    *fields: str,
    experimental: bool = False,
    behavior_note: str = "",
) -> ItemModTemplate:
    return ItemModTemplate(
        key,
        label,
        archetype,
        f"PokemonEmerald/Content/Items/{key}.uasset",
        tuple(fields),
        experimental,
        behavior_note,
    )


def _nested(
    folder: str,
    key: str,
    label: str,
    archetype: str,
    *fields: str,
    experimental: bool = False,
    behavior_note: str = "",
) -> ItemModTemplate:
    return ItemModTemplate(
        key,
        label,
        archetype,
        f"PokemonEmerald/Content/Items/{folder}/{key}.uasset",
        tuple(fields),
        experimental,
        behavior_note,
    )


_VITAMIN_NOTE = (
    "Raises the selected EV stat by EV Boost Amount. Gamma's native function caps Vitamin gains at "
    "100 EV in that stat and 510 total EV, even though a stored stat can otherwise reach 252. "
    "Choices are divisors of 252 plus Gamma's shipped default of 10; values above 100 are still "
    "clamped by the game at use time."
)


ITEM_MOD_TEMPLATES = (
    _root("DA_Potion", "Potion", "HP Restore", "HPRestoreAmount"),
    _root("DA_SuperPotion", "Super Potion", "HP Restore", "HPRestoreAmount"),
    _root("DA_FullRestore", "Full Restore", "HP Restore", "HPRestoreAmount", "HPRestorePercentage"),
    _root("DA_Antidote", "Antidote (Poison)", "Status Heal"),
    _root("DA_Awakening", "Awakening (Sleep)", "Status Heal"),
    _root("DA_BurnHeal", "Burn Heal", "Status Heal"),
    _root("DA_IceHeal", "Ice Heal (Freeze)", "Status Heal"),
    _root("DA_ParalyzeHeal", "Paralyze Heal", "Status Heal"),
    _root("DA_FullHeal", "Full Heal", "Status Heal"),
    _root("DA_Revive", "Revive", "Revive"),
    _root("DA_Ether", "Ether", "PP Restore"),
    _root("DA_HPUp", "HP Up", "Vitamin", "EVBoostAmount", behavior_note=_VITAMIN_NOTE),
    _root("DA_Protein", "Protein (Attack)", "Vitamin", "VitaminStat", "EVBoostAmount", behavior_note=_VITAMIN_NOTE),
    _root("DA_Iron", "Iron (Defense)", "Vitamin", "VitaminStat", "EVBoostAmount", behavior_note=_VITAMIN_NOTE),
    _root(
        "DA_Calcium", "Calcium (Special Attack)", "Vitamin", "VitaminStat", "EVBoostAmount",
        behavior_note=_VITAMIN_NOTE,
    ),
    _root(
        "DA_Zinc", "Zinc (Special Defense)", "Vitamin", "VitaminStat", "EVBoostAmount",
        behavior_note=_VITAMIN_NOTE,
    ),
    _root("DA_Carbos", "Carbos (Speed)", "Vitamin", "VitaminStat", "EVBoostAmount", behavior_note=_VITAMIN_NOTE),
    _root("DA_RareCandy", "Rare Candy", "Rare Candy"),
    _root("DA_WaterStone", "Water Stone", "Evolution / Utility", experimental=True),
    _root("DA_Everstone", "Everstone", "Evolution / Utility", experimental=True),
    _nested(
        "HeldItems", "DA_AmuletCoin", "Amulet Coin", "Held Item", experimental=True,
        behavior_note="Shipped behavior doubles battle money when the holder participates. The effect enum is inherited unchanged.",
    ),
    _nested(
        "HeldItems", "DA_LeftOvers", "Leftovers", "Held Item", "HPRestorePerTurn", experimental=True,
        behavior_note="Restores a percentage of the holder's maximum HP at the end of each turn (shipped value: 6.25%).",
    ),
    _nested(
        "HeldItems", "DA_LightOrb", "Light Ball", "Held Item",
        "AttackMultiplier", "SpecialAttackMultiplier", "HPRestorePerTurn", experimental=True,
        behavior_note=(
            "Shipped asset serializes 2x Attack, 2x Special Attack and 6.25% HP per turn. "
            "Its exact species restriction/effect combination still needs gameplay testing."
        ),
    ),
    _nested(
        "HeldItems", "DA_MiracleSeed", "Miracle Seed", "Held Item", "BoostedType", "TypeBoostMultiplier",
        behavior_note="Boosts moves of the selected type (shipped value: Grass at 1.2x).",
    ),
    _nested(
        "HeldItems", "DA_QuickClaw", "Quick Claw", "Held Item", experimental=True,
        behavior_note=(
            "Shipped behavior sometimes lets the holder move first. Its trigger/chance is not serialized "
            "in ItemData, so a renamed clone is high-risk and needs gameplay testing."
        ),
    ),
    _nested(
        "HeldItems", "DA_SilkScarf", "Silk Scarf", "Held Item", "BoostedType", "TypeBoostMultiplier",
        experimental=True, behavior_note="Boosts moves of the selected type (shipped value: Normal at 1.2x).",
    ),
    _nested(
        "HeldItems", "DA_SoftSand", "Soft Sand", "Held Item", "BoostedType", "TypeBoostMultiplier",
        behavior_note="Boosts moves of the selected type (shipped value: Ground at 1.2x).",
    ),
    _nested(
        "Berries", "DA_OranBerry", "Oran Berry", "Berry", "HPRestoreAmount", "BerryHPRestore",
        behavior_note="Consumable held Berry that restores a flat amount of HP when HP is low; it can also be used outside battle.",
    ),
    _nested(
        "Berries", "DA_SitrusBerry", "Sitrus Berry", "Berry", "BerryHPRestore",
        behavior_note="Consumable held Berry that restores a flat amount of HP when HP is low (shipped value: 30 HP).",
    ),
    _nested(
        "Berries", "DA_ChestoBerry", "Chesto Berry (Sleep)", "Berry", "BerryActivationThreshold",
        behavior_note="Consumable held Berry triggered by Sleep; cures Sleeping. The status trigger/list is inherited unchanged.",
    ),
    _nested(
        "Berries", "DA_PersimBerry", "Persim Berry (Confusion)", "Berry", "BerryActivationThreshold",
        behavior_note="Consumable held Berry triggered by Confusion; cures Confused. The status trigger/list is inherited unchanged.",
    ),
    _nested(
        "TMs", "DA_TM01", "TM for an existing move", "TM", "TeachableMove",
        behavior_note=(
            "Creates a new TM item that teaches one of Gamma's 99 existing move Blueprints. This is useful "
            "for moves outside the 26 shipped TMs; it does not create or edit a move's power/type/effects."
        ),
    ),
    _root("DA_Pokeball", "Poké Ball visuals", "Poké Ball", experimental=True),
    _root("DA_Greatball", "Great Ball visuals", "Poké Ball", "PokeballType", "CatchRateModifier", experimental=True),
    _root("DA_UltraBall", "Ultra Ball visuals", "Poké Ball", "PokeballType", "CatchRateModifier", experimental=True),
    _root("DA_PremierBall", "Premier Ball visuals", "Poké Ball", "PokeballType", experimental=True),
    _root("DA_LuxaryBall", "Luxury Ball visuals", "Poké Ball", "PokeballType", "CatchRateModifier", experimental=True),
    _root("DA_Repeatball", "Repeat Ball visuals", "Poké Ball", "PokeballType", experimental=True),
    _root("DA_TimerBall", "Timer Ball visuals", "Poké Ball", "PokeballType", experimental=True),
    _root("DA_CherishBall", "Cherish Ball visuals", "Poké Ball", "PokeballType", experimental=True),
    _root("DA_Shimmerball", "Shimmer Ball visuals", "Poké Ball", "PokeballType", experimental=True),
)

TEMPLATE_BY_KEY = {template.key: template for template in ITEM_MOD_TEMPLATES}
ITEM_MOD_ARCHETYPES = tuple(dict.fromkeys(template.archetype for template in ITEM_MOD_TEMPLATES))


def templates_for_archetype(archetype: str) -> tuple[ItemModTemplate, ...]:
    return tuple(template for template in ITEM_MOD_TEMPLATES if template.archetype == archetype)


def _display_number(value: str, fallback: str) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return f"{number:g}"


def _type_power_effect(item_name: str, move_type: str, multiplier: str) -> str:
    try:
        delta = (float(multiplier) - 1.0) * 100.0
    except (TypeError, ValueError):
        return f"When held, {item_name} changes the power of {move_type}-type moves."
    verb = "raises" if delta >= 0 else "lowers"
    amount = f"{abs(delta):g}%"
    return f"When held, {item_name} {verb} the power of {move_type}-type moves by {amount}."


def player_effect_summary(
    template: ItemModTemplate,
    *,
    item_name: str = "",
    values: Mapping[str, str] | None = None,
) -> str:
    """Return a short player-facing description that follows the wizard's current values."""
    current = values or {}
    requested_name = item_name.strip()
    name = template.label if not requested_name or requested_name == "Custom Item" else requested_name
    key = template.key

    if template.archetype == "HP Restore":
        amount = _display_number(current.get("HPRestoreAmount", ""), "the configured amount of")
        if key == "DA_FullRestore":
            return f"When used, {name} restores HP and cures the Pokémon's status conditions."
        return f"When used, {name} restores {amount} HP to a Pokémon."

    status_effects = {
        "DA_Antidote": "poison",
        "DA_Awakening": "sleep",
        "DA_BurnHeal": "a burn",
        "DA_IceHeal": "freezing",
        "DA_ParalyzeHeal": "paralysis",
        "DA_FullHeal": "all status conditions",
    }
    if key in status_effects:
        return f"When used, {name} cures {status_effects[key]}."
    if key == "DA_Revive":
        return f"When used on a fainted Pokémon, {name} revives it and restores part of its HP."
    if key == "DA_Ether":
        return f"When used, {name} restores PP to one of a Pokémon's moves."
    if template.archetype == "Vitamin":
        stat = current.get("VitaminStat", "the selected stat")
        amount = _display_number(current.get("EVBoostAmount", ""), "the configured number of")
        return f"When used, {name} grants {amount} {stat} EVs, up to the active Vitamin caps."
    if key == "DA_RareCandy":
        return f"When used, {name} raises a Pokémon's level by one."
    if key == "DA_WaterStone":
        return f"When used on a compatible Pokémon, {name} causes it to evolve."
    if key == "DA_Everstone":
        return f"When held, {name} prevents its holder from evolving."

    if key == "DA_AmuletCoin":
        return f"When held by a Pokémon that joins the battle, {name} doubles the prize money received."
    if key == "DA_LeftOvers":
        amount = _display_number(current.get("HPRestorePerTurn", ""), "6.25")
        return f"At the end of each turn, {name} restores {amount}% of its holder's maximum HP."
    if key == "DA_LightOrb":
        attack = _display_number(current.get("AttackMultiplier", ""), "2")
        special = _display_number(current.get("SpecialAttackMultiplier", ""), "2")
        healing = _display_number(current.get("HPRestorePerTurn", ""), "6.25")
        return (
            f"When held, {name} multiplies Attack by {attack}× and Sp. Atk by {special}×, "
            f"then restores {healing}% maximum HP per turn."
        )
    if key in {"DA_MiracleSeed", "DA_SilkScarf", "DA_SoftSand"}:
        return _type_power_effect(
            name,
            current.get("BoostedType", "the selected type"),
            current.get("TypeBoostMultiplier", "1.2"),
        )
    if key == "DA_QuickClaw":
        return f"When held, {name} may let its holder move first."

    if key == "DA_OranBerry":
        held = _display_number(current.get("BerryHPRestore", ""), "the configured amount of")
        used = _display_number(current.get("HPRestoreAmount", ""), held)
        return (
            f"When its holder's HP is low, {name} is consumed to restore {held} HP. "
            f"Using it from the Bag restores {used} HP."
        )
    if key == "DA_SitrusBerry":
        amount = _display_number(current.get("BerryHPRestore", ""), "30")
        return f"When its holder's HP is low, {name} is consumed to restore {amount} HP."
    if key == "DA_ChestoBerry":
        return f"When its holder falls asleep, {name} is consumed to wake it up."
    if key == "DA_PersimBerry":
        return f"When its holder becomes confused, {name} is consumed to cure its confusion."

    if template.archetype == "TM":
        move = current.get("TeachableMove", "the selected move")
        return f"When used on a compatible Pokémon, {name} teaches it {move}."
    if template.archetype == "Poké Ball":
        ball_type = current.get("PokeballType", template.label.removesuffix(" visuals"))
        if "CatchRateModifier" in template.editable_fields:
            rate = _display_number(current.get("CatchRateModifier", ""), "the configured")
            return f"When thrown at a wild Pokémon, {name} uses {ball_type} behavior with a {rate}× catch rate."
        return f"When thrown at a wild Pokémon, {name} uses the inherited {ball_type} capture behavior."

    return template.behavior_note or "Uses the selected shipped item's effect."
