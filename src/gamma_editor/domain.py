from __future__ import annotations

from dataclasses import dataclass
import re

from .errors import GvasError
from .gvas import GvasDocument, PropertyRecord, parse_gvas, patch_scalar


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


def _species_name(value: object) -> str:
    text = str(value or "")
    match = re.search(r"DA_([A-Za-z0-9_]+)", text)
    return match.group(1) if match else "Empty"


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
