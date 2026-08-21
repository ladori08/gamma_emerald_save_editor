from __future__ import annotations

from dataclasses import dataclass
import re

from .errors import GvasError
from .catalog import (
    AssetChoice,
    GENDERS,
    MET_TYPES,
    MOVES_BY_NAME,
    NATURES,
    SPECIES_BY_NAME,
    STATUS_CONDITIONS,
    display_name,
)
from .gvas import (
    GvasDocument,
    PropertyRecord,
    parse_gvas,
    patch_int_array,
    patch_scalar,
    patch_soft_object,
    patch_soft_object_array,
)


_PARTY_RE = re.compile(r"^Party\[(\d+)]\.(.+)$")
_BOX_RE = re.compile(r"^Boxes\[(\d+)]\.Pokemon(?:\[(\d+)])?\.(.+)$")
_ITEM_RE = re.compile(r"^PlayerItems\[(\d+)]\.Items\[(\d+)]\.(.+)$")


@dataclass(slots=True, frozen=True)
class DomainRow:
    owner: str
    field: str
    value: object
    path: str
    editable: bool
    rule: str = ""


@dataclass(slots=True, frozen=True)
class PokemonView:
    prefix: str
    source: str
    box_index: int | None
    slot_index: int
    species: str
    occupied: bool
    fields: dict[str, object]


@dataclass(slots=True, frozen=True)
class BagEntry:
    prefix: str
    category: str
    index: int
    name: str
    quantity: int


@dataclass(slots=True, frozen=True)
class LegalityIssue:
    severity: str
    owner: str
    message: str


def _species_name(value: object) -> str:
    text = str(value or "")
    match = re.search(r"DA_([A-Za-z0-9_]+)", text)
    return match.group(1) if match else "Empty"


def _move_name(value: object) -> str:
    match = re.search(r"BP_Move_([A-Za-z0-9_]+)", str(value or ""))
    return match.group(1) if match else ""


def _pokemon_view(
    document: GvasDocument,
    prefix: str,
    *,
    source: str,
    slot_index: int,
    box_index: int | None = None,
) -> PokemonView:
    fields = {
        item.path[len(prefix) + 1 :]: item.value
        for item in document.properties
        if item.path.startswith(prefix + ".") and item.type_name != "StructProperty"
    }
    species = _species_name(fields.get("SpeciesData"))
    moves = fields.get("Moves")
    if isinstance(moves, tuple):
        fields["MoveNames"] = tuple(_move_name(value) for value in moves)
    return PokemonView(
        prefix=prefix,
        source=source,
        box_index=box_index,
        slot_index=slot_index,
        species=species,
        occupied=species != "Empty",
        fields=fields,
    )


def party_pokemon(document: GvasDocument) -> list[PokemonView]:
    indices = sorted(
        {
            int(match.group(1))
            for item in document.properties
            if (match := _PARTY_RE.match(item.path)) and match.group(2) == "SpeciesData"
        }
    )
    return [
        _pokemon_view(document, f"Party[{index}]", source="Party", slot_index=index)
        for index in indices
    ]


def storage_pokemon(document: GvasDocument, box_index: int) -> list[PokemonView]:
    slots = sorted(
        {
            int(match.group(2) or 0)
            for item in document.properties
            if (match := _BOX_RE.match(item.path))
            and int(match.group(1)) == box_index
            and match.group(3) == "SpeciesData"
        }
    )
    return [
        _pokemon_view(
            document,
            f"Boxes[{box_index}].Pokemon[{slot}]",
            source="Storage",
            box_index=box_index,
            slot_index=slot,
        )
        for slot in slots
    ]


def box_names(document: GvasDocument) -> tuple[str, ...]:
    prop = next((item for item in document.properties if item.path == "BoxNames"), None)
    if prop and isinstance(prop.value, tuple):
        return tuple(str(value) for value in prop.value)
    count = 1 + max(
        (int(match.group(1)) for item in document.properties if (match := _BOX_RE.match(item.path))),
        default=-1,
    )
    return tuple(f"Box {index + 1}" for index in range(count))


def bag_entries(document: GvasDocument) -> list[BagEntry]:
    categories: dict[int, str] = {}
    values: dict[tuple[int, int], dict[str, object]] = {}
    for item in document.properties:
        category = re.match(r"^PlayerItems\[(\d+)]\.Category$", item.path)
        if category:
            categories[int(category.group(1))] = str(item.value).split("::")[-1]
        match = _ITEM_RE.match(item.path)
        if match:
            key = (int(match.group(1)), int(match.group(2)))
            values.setdefault(key, {})[match.group(3)] = item.value
    return [
        BagEntry(
            prefix=f"PlayerItems[{category}].Items[{index}]",
            category=categories.get(category, f"Pocket {category + 1}"),
            index=index,
            name=str(fields.get("ItemName", f"Item {index + 1}")),
            quantity=int(fields.get("Quantity", 0)),
        )
        for (category, index), fields in sorted(values.items())
    ]


def legality_issues(document: GvasDocument) -> list[LegalityIssue]:
    issues: list[LegalityIssue] = []
    pokemon = party_pokemon(document)
    for box_index in range(len(box_names(document))):
        pokemon.extend(item for item in storage_pokemon(document, box_index) if item.occupied)
    seen_ids: dict[int, str] = {}
    stats = ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed")
    for mon in pokemon:
        owner = f"{mon.source} {mon.slot_index + 1} / {mon.species}"
        fields = mon.fields
        if mon.species.casefold() not in SPECIES_BY_NAME:
            issues.append(LegalityIssue("Error", owner, "Species is not in the GE-1.0.0 DataAsset catalog."))
        level = _int_or(fields.get("Level"), -1)
        if not 1 <= level <= 100:
            issues.append(LegalityIssue("Error", owner, f"Level {level} is outside 1–100."))
        ev_total = 0
        for stat in stats:
            iv = _int_or(fields.get(stat + "_IV"), -1)
            ev = _int_or(fields.get(stat + "_EV"), -1)
            if not 0 <= iv <= 31:
                issues.append(LegalityIssue("Error", owner, f"{display_name(stat)} IV {iv} is outside 0–31."))
            if not 0 <= ev <= 252:
                issues.append(LegalityIssue("Error", owner, f"{display_name(stat)} EV {ev} is outside 0–252."))
            ev_total += max(ev, 0)
        if ev_total > 510:
            issues.append(LegalityIssue("Error", owner, f"EV total {ev_total} exceeds 510."))
        friendship = _int_or(fields.get("Friendship"), -1)
        if not 0 <= friendship <= 255:
            issues.append(LegalityIssue("Error", owner, f"Friendship {friendship} is outside 0–255."))
        current_hp = float(fields.get("CurrentHP", 0) or 0)
        max_hp = float(fields.get("MaxHP", 0) or 0)
        if max_hp <= 0 or current_hp < 0 or current_hp > max_hp:
            issues.append(LegalityIssue("Error", owner, f"HP {current_hp:g}/{max_hp:g} is inconsistent."))
        move_names = tuple(display_name(str(value)) for value in fields.get("MoveNames", ()))
        current_pp = tuple(_int_or(value, -1) for value in fields.get("CurrentPP", ()))
        max_pp = tuple(_int_or(value, -1) for value in fields.get("MaxPP", ()))
        if len(move_names) > 4 or len(move_names) != len(current_pp) or len(move_names) != len(max_pp):
            issues.append(LegalityIssue("Error", owner, "Move, Current PP and Max PP array lengths disagree."))
        for index, name in enumerate(move_names):
            if name.casefold() not in MOVES_BY_NAME:
                issues.append(LegalityIssue("Warning", owner, f"Move {name!r} is not in the verified catalog."))
            if index < len(current_pp) and index < len(max_pp) and not 0 <= current_pp[index] <= max_pp[index] <= 99:
                issues.append(LegalityIssue("Error", owner, f"Move {index + 1} PP is invalid."))
        pokemon_id = _int_or(fields.get("PokemonID"), 0)
        if pokemon_id and pokemon_id in seen_ids:
            issues.append(LegalityIssue("Warning", owner, f"Pokémon ID duplicates {seen_ids[pokemon_id]}."))
        elif pokemon_id:
            seen_ids[pokemon_id] = owner
    for item in bag_entries(document):
        if not 0 <= item.quantity <= 9999:
            issues.append(LegalityIssue("Error", f"Bag / {item.name}", "Quantity is outside 0–9999."))
        if not item.name.strip():
            issues.append(LegalityIssue("Error", f"Bag / {item.category}", "Item name is empty."))
    return issues


def _int_or(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def trainer_rows(document: GvasDocument) -> list[DomainRow]:
    wanted = (
        "PlayerName",
        "PlayerId",
        "PlayerMoney",
        "GameCornerCoins",
        "TotalTimePlayed",
        "CurrentMapName",
        "PlayerLocation",
        "CurrentHours",
        "CurrentMinutes",
        "CurrentSeconds",
    )
    by_path = {item.path: item for item in document.properties}
    rows: list[DomainRow] = []
    for path in wanted:
        item = by_path.get(path)
        if item:
            rows.append(_row("Trainer", item))
    return rows


def party_rows(document: GvasDocument) -> list[DomainRow]:
    species: dict[int, str] = {}
    for item in document.properties:
        match = _PARTY_RE.match(item.path)
        if match and match.group(2) == "SpeciesData":
            species[int(match.group(1))] = _species_name(item.value)
    rows: list[DomainRow] = []
    for item in document.properties:
        match = _PARTY_RE.match(item.path)
        if not match or item.type_name == "StructProperty":
            continue
        index = int(match.group(1))
        rows.append(_row(f"#{index + 1} {species.get(index, 'Pokemon')}", item, match.group(2)))
    return rows


def storage_rows(document: GvasDocument) -> list[DomainRow]:
    occupied: dict[tuple[int, int], str] = {}
    for item in document.properties:
        match = _BOX_RE.match(item.path)
        if not match or match.group(3) != "SpeciesData":
            continue
        box = int(match.group(1))
        slot = int(match.group(2) or 0)
        species = _species_name(item.value)
        if species != "Empty":
            occupied[(box, slot)] = species
    rows: list[DomainRow] = []
    for item in document.properties:
        match = _BOX_RE.match(item.path)
        if not match or item.type_name == "StructProperty":
            continue
        box = int(match.group(1))
        slot = int(match.group(2) or 0)
        if (box, slot) not in occupied:
            continue
        owner = f"Box {box + 1} / Slot {slot + 1} / {occupied[(box, slot)]}"
        rows.append(_row(owner, item, match.group(3)))
    return rows


def bag_rows(document: GvasDocument) -> list[DomainRow]:
    category_by_index: dict[int, str] = {}
    item_by_key: dict[tuple[int, int], str] = {}
    for item in document.properties:
        category = re.match(r"^PlayerItems\[(\d+)]\.Category$", item.path)
        if category:
            category_by_index[int(category.group(1))] = str(item.value).split("::")[-1]
        match = _ITEM_RE.match(item.path)
        if match and match.group(3) == "ItemName":
            item_by_key[(int(match.group(1)), int(match.group(2)))] = str(item.value)
    rows: list[DomainRow] = []
    for item in document.properties:
        match = _ITEM_RE.match(item.path)
        if not match or match.group(3) not in {"ItemName", "ItemID", "Quantity"}:
            continue
        category = int(match.group(1))
        index = int(match.group(2))
        owner = f"{category_by_index.get(category, 'Items')} / {item_by_key.get((category, index), index)}"
        rows.append(_row(owner, item, match.group(3)))
    return rows


def progress_rows(document: GvasDocument) -> list[DomainRow]:
    wanted = {
        "PickedStarter",
        "CaughtPokemon",
        "SeenPokemon",
        "bLastBattleWon",
        "bAbilitiesRepaired",
        "SavedFlags",
    }
    return [_row("Progress", item) for item in document.properties if item.path in wanted]


def _row(owner: str, item: PropertyRecord, field: str | None = None) -> DomainRow:
    return DomainRow(
        owner=owner,
        field=field or item.name,
        value=item.value,
        path=item.path,
        editable=item.editable,
        rule=rule_for(item.path),
    )


def rule_for(path: str) -> str:
    name = path.rsplit(".", 1)[-1]
    if name == "Level":
        return "1–100"
    if name.endswith("_IV"):
        return "0–31"
    if name.endswith("_EV"):
        return "0–252; total ≤510"
    if name == "Friendship":
        return "0–255"
    if name == "AbilitySlot":
        return "0–2"
    if name == "Quantity":
        return "0–9999"
    if name in {"CurrentHP", "MaxHP", "CurrentEXP"}:
        return "≥0"
    if name in {"PlayerId", "PlayerMoney", "GameCornerCoins"}:
        return "0–2,147,483,647"
    return "fixed-size" if path else ""


def validate_domain_value(document: GvasDocument, prop: PropertyRecord, value: object) -> None:
    name = prop.path.rsplit(".", 1)[-1]
    if name == "Level" and not 1 <= int(value) <= 100:
        raise GvasError("Level must be between 1 and 100.")
    if name.endswith("_IV") and not 0 <= int(value) <= 31:
        raise GvasError("Each IV must be between 0 and 31.")
    if name.endswith("_EV"):
        if not 0 <= int(value) <= 252:
            raise GvasError("Each EV must be between 0 and 252.")
        prefix = prop.path.rsplit(".", 1)[0]
        ev_values = []
        for item in document.properties:
            if item.path.startswith(prefix + ".") and item.name.endswith("_EV"):
                ev_values.append(int(value) if item.path == prop.path else int(item.value))
        if sum(ev_values) > 510:
            raise GvasError(f"Total EV would be {sum(ev_values)}; maximum is 510.")
    if name == "Friendship" and not 0 <= int(value) <= 255:
        raise GvasError("Friendship must be between 0 and 255.")
    if name == "AbilitySlot" and not 0 <= int(value) <= 2:
        raise GvasError("Ability slot must be 0, 1, or 2.")
    if name == "Quantity" and not 0 <= int(value) <= 9999:
        raise GvasError("Item quantity must be between 0 and 9999.")
    if name in {"CurrentHP", "MaxHP", "CurrentEXP"} and float(value) < 0:
        raise GvasError(f"{name} cannot be negative.")
    if name in {"PlayerId", "PlayerMoney", "GameCornerCoins"} and not 0 <= int(value) <= 2_147_483_647:
        raise GvasError(f"{name} must fit a signed 32-bit positive integer.")
    enum_rules = {
        "Nature": ("ENature", NATURES),
        "Gender": ("EPokemonGender", GENDERS),
        "StatusCondition": ("ESTATUSEffect", STATUS_CONDITIONS),
        "MetType": ("EPokemonMetType", MET_TYPES),
    }
    if name in enum_rules:
        prefix, allowed = enum_rules[name]
        expected = {f"{prefix}::{item}" for item in allowed}
        if str(value) not in expected:
            raise GvasError(f"{name} is not in the verified GE-1.0.0 enum catalog.")


def patch_domain_value(document: GvasDocument, path: str, value: object) -> bytes:
    matches = [item for item in document.properties if item.path == path]
    if len(matches) != 1:
        raise GvasError(f"Expected one domain field at {path!r}, found {len(matches)}.")
    prop = matches[0]
    validate_domain_value(document, prop, value)
    synchronized_paths: list[str] = []
    if path == "PlayerName":
        synchronized_paths = [
            item.path
            for item in document.properties
            if item.name in {"OriginalTrainerName", "CurrentTrainerName"} and item.value == prop.value
        ]
    elif path == "PlayerId":
        synchronized_paths = [
            item.path
            for item in document.properties
            if item.name in {"OriginalTrainerID", "CurrentTrainerID"} and item.value == prop.value
        ]
    raw = patch_scalar(document, path, value)
    for synchronized_path in synchronized_paths:
        current = parse_gvas(raw)
        raw = patch_scalar(current, synchronized_path, value)
    return raw


def patch_domain_values(document: GvasDocument, changes: dict[str, object]) -> bytes:
    raw = document.raw
    by_path = {item.path: item for item in document.properties}
    ordered = list(changes.items())
    ordered.sort(
        key=lambda item: (
            0
            if item[0].endswith("_EV") and int(item[1]) <= int(by_path[item[0]].value)
            else 2
            if item[0].endswith("_EV")
            else 1
        )
    )
    for path, value in ordered:
        current = parse_gvas(raw)
        raw = patch_domain_value(current, path, value)
    return raw


def patch_pokemon(
    document: GvasDocument,
    pokemon: PokemonView,
    *,
    scalar_changes: dict[str, object],
    species: AssetChoice | None = None,
    moves: list[AssetChoice] | None = None,
    current_pp: list[int] | None = None,
    max_pp: list[int] | None = None,
) -> bytes:
    if not pokemon.occupied:
        raise GvasError("Empty Pokémon slots cannot be created until struct insertion is verified.")
    raw = document.raw
    if species is not None:
        raw = patch_soft_object(
            parse_gvas(raw),
            pokemon.prefix + ".SpeciesData",
            species.path,
            species.object_name,
        )
    ordered_scalar_changes = dict(scalar_changes)
    scalar_items = list(ordered_scalar_changes.items())
    old_fields = pokemon.fields
    scalar_items.sort(
        key=lambda item: (
            0
            if item[0].endswith("_EV") and int(item[1]) <= int(old_fields.get(item[0], 0))
            else 2
            if item[0].endswith("_EV")
            else 1
        )
    )
    for field, value in scalar_items:
        current = parse_gvas(raw)
        raw = patch_domain_value(current, pokemon.prefix + "." + field, value)
    if moves is not None:
        if len(moves) > 4:
            raise GvasError("A Pokémon can have at most four moves.")
        raw = patch_soft_object_array(
            parse_gvas(raw),
            pokemon.prefix + ".Moves",
            [(move.path, move.object_name) for move in moves],
        )
        if current_pp is None or max_pp is None:
            raise GvasError("Move edits require matching Current PP and Max PP arrays.")
    if current_pp is not None or max_pp is not None:
        if current_pp is None or max_pp is None or len(current_pp) != len(max_pp):
            raise GvasError("Current PP and Max PP must have the same length.")
        if moves is not None and len(current_pp) != len(moves):
            raise GvasError("Move and PP arrays must have the same length.")
        if not all(0 <= int(value) <= 99 for value in (*current_pp, *max_pp)):
            raise GvasError("PP values must be between 0 and 99.")
        if any(int(current) > int(maximum) for current, maximum in zip(current_pp, max_pp)):
            raise GvasError("Current PP cannot exceed Max PP.")
        raw = patch_int_array(parse_gvas(raw), pokemon.prefix + ".CurrentPP", current_pp)
        raw = patch_int_array(parse_gvas(raw), pokemon.prefix + ".MaxPP", max_pp)
    return raw
