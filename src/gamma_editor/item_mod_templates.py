from __future__ import annotations

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
