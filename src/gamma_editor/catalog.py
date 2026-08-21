from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(slots=True, frozen=True)
class AssetChoice:
    name: str
    path: str
    object_name: str
    category: str


@dataclass(slots=True, frozen=True)
class ItemChoice:
    name: str
    pocket: str


def display_name(token: str) -> str:
    overrides = {
        "Gecqua": "Gecqua",
        "MissingNo": "MissingNo.",
        "Venasaur": "Venasaur",
        "Mudslap": "Mud-Slap",
        "Lightscreen": "Light Screen",
        "WillOWisp": "Will-O-Wisp",
    }
    if token in overrides:
        return overrides[token]
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", token)
    return text.replace("Pokemon", "Pokémon")


_SPECIES_MANIFEST = """
Abra|/Game/BPS/PokemonData/Pokemon/Psychic/DA_Abra
Aggron|/Game/BPS/PokemonData/Pokemon/Steel/DA_Aggron
Alakazam|/Game/BPS/PokemonData/Pokemon/Psychic/DA_Alakazam
Aron|/Game/BPS/PokemonData/Pokemon/Steel/DA_Aron
Azumarill|/Game/BPS/PokemonData/Pokemon/Water/DA_Azumarill
Azurill|/Game/BPS/PokemonData/Pokemon/Normal/DA_Azurill
Beautifly|/Game/BPS/PokemonData/Pokemon/Bug/DA_Beautifly
Beldum|/Game/BPS/PokemonData/Pokemon/Steel/DA_Beldum
Blaziken|/Game/BPS/PokemonData/Pokemon/Fire/DA_Blaziken
Breloom|/Game/BPS/PokemonData/Pokemon/Grass/DA_Breloom
Budew|/Game/BPS/PokemonData/Pokemon/Grass/DA_Budew
Cacnea|/Game/BPS/PokemonData/Pokemon/Grass/DA_Cacnea
Carvanha|/Game/BPS/PokemonData/Pokemon/Water/DA_Carvanha
Cascoon|/Game/BPS/PokemonData/Pokemon/Bug/DA_Cascoon
Charizard|/Game/BPS/PokemonData/Pokemon/Fire/DA_Charizard
Combusken|/Game/BPS/PokemonData/Pokemon/Fire/DA_Combusken
Crobat|/Game/BPS/PokemonData/Pokemon/Poison/DA_Crobat
Delcatty|/Game/BPS/PokemonData/Pokemon/Normal/DA_Delcatty
Dustox|/Game/BPS/PokemonData/Pokemon/Bug/DA_Dustox
Electrike|/Game/BPS/PokemonData/Pokemon/Electric/DA_Electrike
Electrode|/Game/BPS/PokemonData/Pokemon/Electric/DA_Electrode
Exploud|/Game/BPS/PokemonData/Pokemon/Normal/DA_Exploud
Gallade|/Game/BPS/PokemonData/Pokemon/Psychic/DA_Gallade
Gardevoir|/Game/BPS/PokemonData/Pokemon/Psychic/DA_Gardevoir
Gecqua|/Game/BPS/PokemonData/Pokemon/Water/DA_Gecqua
Geodude|/Game/BPS/PokemonData/Pokemon/Rock/DA_Geodude
Golbat|/Game/BPS/PokemonData/Pokemon/Poison/DA_Golbat
Goldeen|/Game/BPS/PokemonData/Pokemon/Water/DA_Goldeen
Golem|/Game/BPS/PokemonData/Pokemon/Rock/DA_Golem
Graveler|/Game/BPS/PokemonData/Pokemon/Rock/DA_Graveler
Grovyle|/Game/BPS/PokemonData/Pokemon/Grass/DA_Grovyle
Gulpin|/Game/BPS/PokemonData/Pokemon/Poison/DA_Gulpin
Gyarados|/Game/BPS/PokemonData/Pokemon/Water/DA_Gyarados
Hariyama|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Hariyama
Illumise|/Game/BPS/PokemonData/Pokemon/Bug/DA_Illumise
Jirachi|/Game/BPS/PokemonData/Pokemon/Steel/DA_Jirachi
Kadabra|/Game/BPS/PokemonData/Pokemon/Psychic/DA_Kadabra
Kirlia|/Game/BPS/PokemonData/Pokemon/Psychic/DA_Kirlia
Lairon|/Game/BPS/PokemonData/Pokemon/Steel/DA_Lairon
Latias|/Game/BPS/PokemonData/Pokemon/Dragon/DA_Latias
Linoone|/Game/BPS/PokemonData/Pokemon/Normal/DA_Linoone
Lombre|/Game/BPS/PokemonData/Pokemon/Water/DA_Lombre
Lotad|/Game/BPS/PokemonData/Pokemon/Water/DA_Lotad
Loudred|/Game/BPS/PokemonData/Pokemon/Normal/DA_Loudred
Lucario|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Lucario
Ludicolo|/Game/BPS/PokemonData/Pokemon/Water/DA_Ludicolo
Lunatone|/Game/BPS/PokemonData/Pokemon/Rock/DA_Lunatone
Machamp|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Machamp
Machoke|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Machoke
Machop|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Machop
Magcargo|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Magcargo
Magikarp|/Game/BPS/PokemonData/Pokemon/Water/DA_Magikarp
Magnemite|/Game/BPS/PokemonData/Pokemon/Electric/DA_Magnemite
Magneton|/Game/BPS/PokemonData/Pokemon/Electric/DA_Magneton
Magnezone|/Game/BPS/PokemonData/Pokemon/Electric/DA_Magnezone
Makuhita|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Makuhita
Manectric|/Game/BPS/PokemonData/Pokemon/Electric/DA_Manectric
Marill|/Game/BPS/PokemonData/Pokemon/Water/DA_Marill
Marshtomp|/Game/BPS/PokemonData/Pokemon/Water/DA_Marshtomp
Medicham|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Medicham
Meditite|/Game/BPS/PokemonData/Pokemon/Fighting/DA_Meditite
Metagross|/Game/BPS/PokemonData/Pokemon/Steel/DA_Metagross
Metang|/Game/BPS/PokemonData/Pokemon/Steel/DA_Metang
Mew|/Game/BPS/PokemonData/Pokemon/Psychic/DA_Mew
Mightyena|/Game/BPS/PokemonData/Pokemon/Dark/DA_Mightyena
Milotic|/Game/BPS/PokemonData/Pokemon/Water/DA_Milotic
Minun|/Game/BPS/PokemonData/Pokemon/Electric/DA_Minun
MissingNo|/Game/BPS/PokemonData/Pokemon/DA_MissingNo
Mudkip|/Game/BPS/PokemonData/Pokemon/Water/DA_Mudkip
Nincada|/Game/BPS/PokemonData/Pokemon/Bug/DA_Nincada
Ninjask|/Game/BPS/PokemonData/Pokemon/Bug/DA_Ninjask
Nosepass|/Game/BPS/PokemonData/Pokemon/Rock/DA_Nosepass
Nuzleaf|/Game/BPS/PokemonData/Pokemon/Grass/DA_Nuzleaf
Pelipper|/Game/BPS/PokemonData/Pokemon/Water/DA_Pelipper
Pikachu|/Game/BPS/PokemonData/Pokemon/Electric/DA_Pikachu
Plusle|/Game/BPS/PokemonData/Pokemon/Electric/DA_Plusle
Poochyena|/Game/BPS/PokemonData/Pokemon/Dark/DA_Poochyena
Probopass|/Game/BPS/PokemonData/Pokemon/Rock/DA_Probopass
Ralts|/Game/BPS/PokemonData/Pokemon/Psychic/DA_Ralts
Rayquaza|/Game/BPS/PokemonData/Pokemon/Dragon/DA_Rayquaza
Roselia|/Game/BPS/PokemonData/Pokemon/Grass/DA_Roselia
Roserade|/Game/BPS/PokemonData/Pokemon/Grass/DA_Roserade
Sableye|/Game/BPS/PokemonData/Pokemon/Dark/DA_Sableye
Salamence|/Game/BPS/PokemonData/Pokemon/Dragon/DA_Salamence
Sceptile|/Game/BPS/PokemonData/Pokemon/Grass/DA_Sceptile
Seaking|/Game/BPS/PokemonData/Pokemon/Water/DA_Seaking
Seedot|/Game/BPS/PokemonData/Pokemon/Grass/DA_Seedot
Sharpedo|/Game/BPS/PokemonData/Pokemon/Water/DA_Sharpedo
Shaymin|/Game/BPS/PokemonData/Pokemon/Grass/DA_Shaymin
Shedinja|/Game/BPS/PokemonData/Pokemon/Bug/DA_Shedinja
Shiftry|/Game/BPS/PokemonData/Pokemon/Grass/DA_Shiftry
Shroomish|/Game/BPS/PokemonData/Pokemon/Grass/DA_Shroomish
Silcoon|/Game/BPS/PokemonData/Pokemon/Bug/DA_Silcoon
Skarmory|/Game/BPS/PokemonData/Pokemon/Steel/DA_Skarmory
Skitty|/Game/BPS/PokemonData/Pokemon/Normal/DA_Skitty
Slaking|/Game/BPS/PokemonData/Pokemon/Normal/DA_Slaking
Slakoth|/Game/BPS/PokemonData/Pokemon/Normal/DA_Slakoth
Slugma|/Game/BPS/PokemonData/Pokemon/Fire/DA_Slugma
Swalot|/Game/BPS/PokemonData/Pokemon/Poison/DA_Swalot
Swampert|/Game/BPS/PokemonData/Pokemon/Water/DA_Swampert
Swellow|/Game/BPS/PokemonData/Pokemon/Normal/DA_Swellow
Taillow|/Game/BPS/PokemonData/Pokemon/Normal/DA_Taillow
Tentacool|/Game/BPS/PokemonData/Pokemon/Water/DA_Tentacool
Tentacruel|/Game/BPS/PokemonData/Pokemon/Water/DA_Tentacruel
Torchic|/Game/BPS/PokemonData/Pokemon/Fire/DA_Torchic
Torkoal|/Game/BPS/PokemonData/Pokemon/Fire/DA_Torkoal
Treecko|/Game/BPS/PokemonData/Pokemon/Grass/DA_Treecko
Venasaur|/Game/BPS/PokemonData/Pokemon/Grass/DA_Venasaur
Vigoroth|/Game/BPS/PokemonData/Pokemon/Normal/DA_Vigoroth
Volbeat|/Game/BPS/PokemonData/Pokemon/Bug/DA_Volbeat
Voltorb|/Game/BPS/PokemonData/Pokemon/Electric/DA_Voltorb
Wailmer|/Game/BPS/PokemonData/Pokemon/Water/DA_Wailmer
Wailord|/Game/BPS/PokemonData/Pokemon/Water/DA_Wailord
Whismur|/Game/BPS/PokemonData/Pokemon/Normal/DA_Whismur
Wingull|/Game/BPS/PokemonData/Pokemon/Water/DA_Wingull
Wurmple|/Game/BPS/PokemonData/Pokemon/Bug/DA_Wurmple
Zigzagoon|/Game/BPS/PokemonData/Pokemon/Normal/DA_Zigzagoon
Zubat|/Game/BPS/PokemonData/Pokemon/Poison/DA_Zubat
"""


_MOVE_MANIFEST = """
Absorb|/Game/BPS/ABILITIES/Moves/GRASS/BP_Move_Absorb
Acid|/Game/BPS/ABILITIES/Moves/POISON/BP_Move_Acid
AcidArmor|/Game/BPS/ABILITIES/Moves/POISON/BP_Move_AcidArmor
Acrobatics|/Game/BPS/ABILITIES/Moves/FLYING/BP_Move_Acrobatics
Acupressure|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Acupressure
AerialAce|/Game/BPS/ABILITIES/Moves/FLYING/BP_Move_AerialAce
AfterYou|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_AfterYou
Agility|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Agility
AirCutter|/Game/BPS/ABILITIES/Moves/FLYING/BP_Move_AirCutter
AirSlash|/Game/BPS/ABILITIES/Moves/FLYING/BP_Move_AirSlash
Amnesia|/Game/BPS/ABILITIES/Moves/PSYCHIC/BP_Move_Amnesia
AncientPower|/Game/BPS/ABILITIES/Moves/ROCK/BP_Move_AncientPower
AquaJet|/Game/BPS/ABILITIES/Moves/WATER/BP_Move_AquaJet
ArmThrust|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_ArmThrust
Astonish|/Game/BPS/ABILITIES/Moves/GHOST/BP_Move_Astonish
Bide|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Bide
Bite|/Game/BPS/ABILITIES/Moves/DARK/BP_Move_Bite
BlazeKick|/Game/BPS/ABILITIES/Moves/FIRE/BP_Move_BlazeKick
BrickBreak|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_BrickBreak
BulkUp|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_BulkUp
BulletSeed|/Game/BPS/ABILITIES/Moves/GRASS/BP_Move_BulletSeed
CalmMind|/Game/BPS/ABILITIES/Moves/PSYCHIC/BP_Move_CalmMind
Charge|/Game/BPS/ABILITIES/Moves/ELECTRIC/BP_Move_Charge
Confusion|/Game/BPS/ABILITIES/Moves/PSYCHIC/BP_Move_Confusion
CorruptedMissingNo|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_CorruptedMissingNo
DefenseCurl|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_DefenseCurl
DoubleKick|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_DoubleKick
DoubleTeam|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_DoubleTeam
DragonBreath|/Game/BPS/ABILITIES/Moves/DRAGON/BP_Move_DragonBreath
DragonClaw|/Game/BPS/ABILITIES/Moves/DRAGON/BP_Move_DragonClaw
Earthquake|/Game/BPS/ABILITIES/Moves/GROUND/BP_Move_Earthquake
Ember|/Game/BPS/ABILITIES/Moves/FIRE/BP_Move_Ember
FireSpin|/Game/BPS/ABILITIES/Moves/FIRE/BP_Move_FireSpin
FlameBurst|/Game/BPS/ABILITIES/Moves/FIRE/BP_Move_FlameBurst
Flamethrower|/Game/BPS/ABILITIES/Moves/FIRE/BP_Move_Flamethrower
Fly|/Game/BPS/ABILITIES/Moves/FLYING/BP_Move_Fly
FocusEnergy|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_FocusEnergy
FocusPunch|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_FocusPunch
FuryCutter|/Game/BPS/ABILITIES/Moves/BUG/BP_Move_FuryCutter
GigaDrain|/Game/BPS/ABILITIES/Moves/GRASS/BP_Move_GigaDrain
Growl|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Growl
Gust|/Game/BPS/ABILITIES/Moves/FLYING/BP_Move_Gust
Harden|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Harden
Headbutt|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Headbutt
IceBeam|/Game/BPS/ABILITIES/Moves/ICE/BP_Move_IceBeam
KarateChop|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_KarateChop
LeafBlade|/Game/BPS/ABILITIES/Moves/GRASS/BP_Move_LeafBlade
LeafStorm|/Game/BPS/ABILITIES/Moves/GRASS/BP_Move_LeafStorm
Leer|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Leer
Lightscreen|/Game/BPS/ABILITIES/Moves/PSYCHIC/BP_Move_Lightscreen
LowKick|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_LowKick
MagicalLeaf|/Game/BPS/ABILITIES/Moves/GRASS/BP_Move_MagicalLeaf
MegaDrain|/Game/BPS/ABILITIES/Moves/GRASS/BP_Move_MegaDrain
MeteorMash|/Game/BPS/ABILITIES/Moves/STEEL/BP_Move_MeteorMash
Mudslap|/Game/BPS/ABILITIES/Moves/GROUND/BP_Move_Mudslap
Peck|/Game/BPS/ABILITIES/Moves/FLYING/BP_Move_Peck
PinMissile|/Game/BPS/ABILITIES/Moves/BUG/BP_Move_PinMissile
PoisonSting|/Game/BPS/ABILITIES/Moves/POISON/BP_Move_PoisonSting
Pound|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Pound
Protect|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Protect
Psybeam|/Game/BPS/ABILITIES/Moves/PSYCHIC/BP_Move_Psybeam
Psychic|/Game/BPS/ABILITIES/Moves/PSYCHIC/BP_Move_Psychic
Pursuit|/Game/BPS/ABILITIES/Moves/DARK/BP_Move_Pursuit
QuickAttack|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_QuickAttack
Recover|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Recover
Reflect|/Game/BPS/ABILITIES/Moves/PSYCHIC/BP_Move_Reflect
Refresh|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Refresh
Revenge|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_Revenge
RockSlide|/Game/BPS/ABILITIES/Moves/ROCK/BP_Move_RockSlide
RockThrow|/Game/BPS/ABILITIES/Moves/ROCK/BP_Move_RockThrow
RockTomb|/Game/BPS/ABILITIES/Moves/ROCK/BP_Move_RockTomb
SandAttack|/Game/BPS/ABILITIES/Moves/GROUND/BP_Move_SandAttack
Scratch|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Scratch
Screech|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Screech
SeismicToss|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_SeismicToss
SelfDestruct|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_SelfDestruct
SkyUppercut|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_SkyUppercut
Slam|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Slam
SonicBoom|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_SonicBoom
Spark|/Game/BPS/ABILITIES/Moves/ELECTRIC/BP_Move_Spark
Splash|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Splash
Spore|/Game/BPS/ABILITIES/Moves/GRASS/BP_Move_Spore
SteelWing|/Game/BPS/ABILITIES/Moves/STEEL/BP_Move_SteelWing
StringShot|/Game/BPS/ABILITIES/Moves/BUG/BP_Move_StringShot
Struggle|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Struggle
Supersonic|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Supersonic
Surf|/Game/BPS/ABILITIES/Moves/WATER/BP_Move_Surf
Swagger|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Swagger
Tackle|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_Tackle
TailWhip|/Game/BPS/ABILITIES/Moves/NORMAL/BP_Move_TailWhip
Teleport|/Game/BPS/ABILITIES/Moves/PSYCHIC/BP_Move_Teleport
Thief|/Game/BPS/ABILITIES/Moves/DARK/BP_Move_Thief
Thunderbolt|/Game/BPS/ABILITIES/Moves/ELECTRIC/BP_Move_Thunderbolt
ThunderWave|/Game/BPS/ABILITIES/Moves/ELECTRIC/BP_Move_ThunderWave
Toxic|/Game/BPS/ABILITIES/Moves/POISON/BP_Move_Toxic
VitalThrow|/Game/BPS/ABILITIES/Moves/FIGHTING/BP_Move_VitalThrow
WaterGun|/Game/BPS/ABILITIES/Moves/WATER/BP_Move_WaterGun
Whirlpool|/Game/BPS/ABILITIES/Moves/WATER/BP_Move_Whirlpool
WillOWisp|/Game/BPS/ABILITIES/Moves/FIRE/BP_Move_WillOWisp
"""


def _parse_manifest(raw: str, *, move: bool) -> tuple[AssetChoice, ...]:
    values: list[AssetChoice] = []
    for line in raw.strip().splitlines():
        token, path = line.split("|", 1)
        object_name = path.rsplit("/", 1)[-1] + ("_C" if move else "")
        category = path.rsplit("/", 2)[-2].title()
        values.append(AssetChoice(display_name(token), path, object_name, category))
    return tuple(values)


SPECIES = _parse_manifest(_SPECIES_MANIFEST, move=False)
MOVES = _parse_manifest(_MOVE_MANIFEST, move=True)
SPECIES_BY_NAME = {item.name.casefold(): item for item in SPECIES}
MOVES_BY_NAME = {item.name.casefold(): item for item in MOVES}

NATURES = (
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
)

GENDERS = ("Male", "Female", "Genderless")
STATUS_CONDITIONS = ("None", "Sleep", "Poison", "Burn", "Paralysis", "Freeze", "BadlyPoisoned")
MET_TYPES = ("Caught", "Gift", "Egg", "Traded", "FatefulEncounter")

BAG_POCKETS = ("Items", "Pokeballs", "TMs", "Berries", "KeyItems")
BAG_POCKET_LABELS = {
    "Items": "Items",
    "Pokeballs": "Poké Balls",
    "TMs": "TMs",
    "Berries": "Berries",
    "KeyItems": "Key Items",
}

_ITEMS_BY_POCKET: dict[str, tuple[str, ...]] = {
    "Items": (
        "Potion", "Super Potion", "Revive", "Antidote", "Awakening", "Burn Heal",
        "Calcium", "Carbos", "Escape Rope", "Ether", "Everstone", "Full Heal",
        "Full Restore", "Hard Stone", "Heart Scale", "HP Up", "Ice Heal", "Iron",
        "Paralyze Heal", "Protein", "Rare Candy", "Repel", "Sea Incense", "Soothe Bell",
        "Stardust", "Tiny Mushroom", "Water Stone", "Zinc", "Amulet Coin", "Leftovers",
        "Light Ball", "Miracle Seed", "Quick Claw", "Silk Scarf", "Soft Sand",
    ),
    "Pokeballs": (
        "Pokeball", "Great Ball", "Ultra Ball", "Premier Ball", "Luxury Ball",
        "Repeat Ball", "Timer Ball", "Cherish Ball", "Shimmer Ball",
    ),
    "TMs": tuple(f"TM{number:02d}" for number in (
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 16, 17, 19, 24, 26, 29,
        31, 33, 34, 35, 39, 46, 51, 52,
    )),
    "Berries": ("Chesto Berry", "Oran Berry", "Persim Berry", "Sitrus Berry"),
    "KeyItems": (
        "Bike", "Coin Case", "DEVON Dividend", "Devon Goods", "Harbor Mail",
        "Item Finder", "Letter", "Mysterious Flower", "Old Rod", "Powder Jar",
        "Ticket", "Wailmer Pail",
    ),
}

ITEMS_BY_POCKET = {key: tuple(ItemChoice(name, key) for name in values) for key, values in _ITEMS_BY_POCKET.items()}
ITEM_CHOICES = tuple(item for pocket in BAG_POCKETS for item in ITEMS_BY_POCKET[pocket])
ITEM_BY_NAME = {item.name.casefold(): item for item in ITEM_CHOICES}
ITEM_NAMES = ("None",) + tuple(item.name for item in ITEM_CHOICES)

# GE-1.0.0 uses the classic Hoenn regional number for its Seen/Caught integer sets.
# Only entries that also have a verified Species DataAsset in this build are named here.
HOENN_DEX = {
    1: "Treecko", 2: "Grovyle", 3: "Sceptile", 4: "Torchic", 5: "Combusken",
    6: "Blaziken", 7: "Mudkip", 8: "Marshtomp", 9: "Swampert", 10: "Poochyena",
    11: "Mightyena", 12: "Zigzagoon", 13: "Linoone", 14: "Wurmple", 15: "Silcoon",
    16: "Beautifly", 17: "Cascoon", 18: "Dustox", 19: "Lotad", 20: "Lombre",
    21: "Ludicolo", 22: "Seedot", 23: "Nuzleaf", 24: "Shiftry", 25: "Taillow",
    26: "Swellow", 27: "Wingull", 28: "Pelipper", 29: "Ralts", 30: "Kirlia",
    31: "Gardevoir", 34: "Shroomish", 35: "Breloom", 36: "Slakoth", 37: "Vigoroth",
    38: "Slaking", 39: "Nincada", 40: "Ninjask", 41: "Shedinja", 42: "Whismur",
    43: "Loudred", 44: "Exploud", 45: "Makuhita", 46: "Hariyama", 47: "Azurill",
    48: "Nosepass", 49: "Skitty", 50: "Delcatty", 51: "Sableye", 53: "Aron",
    54: "Lairon", 55: "Aggron", 56: "Meditite", 57: "Medicham", 58: "Electrike",
    59: "Manectric", 60: "Plusle", 61: "Minun", 62: "Volbeat", 63: "Illumise",
    64: "Roselia", 65: "Gulpin", 66: "Swalot", 67: "Carvanha", 68: "Sharpedo",
    69: "Wailmer", 70: "Wailord", 73: "Torkoal", 80: "Cacnea", 86: "Lunatone",
    99: "Milotic", 122: "Salamence", 123: "Beldum", 124: "Metang", 125: "Metagross",
    129: "Latias", 133: "Rayquaza", 134: "Jirachi",
}
