from __future__ import annotations

from dataclasses import dataclass
import re
import struct

from .errors import GvasError
from .catalog import (
    AssetChoice,
    BAG_POCKETS,
    GENDERS,
    ITEMS_BY_POCKET,
    MET_TYPES,
    MOVES_BY_NAME,
    NATURES,
    SPECIES_INFO,
    SPECIES_BY_NAME,
    STATUS_CONDITIONS,
    display_name,
)
from .gvas import (
    GvasDocument,
    PropertyRecord,
    parse_gvas,
    patch_struct_payload,
    patch_structured_array,
    patch_property_batch,
    patch_int_array,
    patch_scalar,
    patch_fixed_scalars,
    patch_soft_object,
    patch_soft_object_array,
    struct_payload,
    structured_array_elements,
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
            storage_slot_path(box_index, slot),
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


def storage_slot_path(box_index: int, slot_index: int) -> str:
    if not 0 <= slot_index < 30:
        raise GvasError("Storage slot must be between 1 and 30.")
    base = f"Boxes[{box_index}].Pokemon"
    return base if slot_index == 0 else f"{base}[{slot_index}]"


def _storage_view(document: GvasDocument, box_index: int, slot_index: int) -> PokemonView:
    view = next(
        (item for item in storage_pokemon(document, box_index) if item.slot_index == slot_index),
        None,
    )
    if view is None:
        raise GvasError("Storage slot is missing its verified Pokémon struct.")
    return view


def _empty_storage_payload(document: GvasDocument) -> bytes:
    for box_index in range(len(box_names(document))):
        for view in storage_pokemon(document, box_index):
            if not view.occupied:
                return struct_payload(document, storage_slot_path(box_index, view.slot_index))
    raise GvasError("No empty verified storage slot is available.")


def pokemon_creation_defaults(document: GvasDocument, species_name: str | None = None) -> dict[str, object]:
    """Return conservative values for activating a verified empty Pokemon struct."""
    trainer_name = next(
        (str(item.value) for item in document.properties if item.path == "PlayerName"),
        "None",
    )
    trainer_id = next(
        (int(item.value) for item in document.properties if item.path == "PlayerId"),
        0,
    )
    # One property pass is materially faster than rebuilding every Box view merely
    # to collect IDs; retaining IDs from empty templates is conservative and safe.
    used_ids = {
        int(item.value)
        for item in document.properties
        if item.name == "PokemonID"
        and (item.path.startswith("Party[") or item.path.startswith("Boxes["))
        and int(item.value) > 0
    }
    pokemon_id = max(used_ids, default=0) + 1
    if pokemon_id > 2_147_483_647:
        pokemon_id = next(
            (candidate for candidate in range(1, 2_147_483_648) if candidate not in used_ids),
            0,
        )
    if pokemon_id <= 0:
        raise GvasError("No unused positive Pokemon ID is available.")

    defaults: dict[str, object] = {
        "Nickname": "None",
        "Level": 5,
        "CurrentEXP": 0.0,
        "CurrentHP": 1.0,
        "MaxHP": 1.0,
        "Nature": "ENature::Hardy",
        "Gender": "EPokemonGender::Genderless",
        "Ability": "EPokemonAbility::None",
        "AbilitySlot": 0,
        "HeldItem": "None",
        "Friendship": 70,
        "StatusCondition": "ESTATUSEffect::None",
        "SleepCounter": 0,
        "PokemonID": pokemon_id,
        "OriginalTrainerName": trainer_name,
        "CurrentTrainerName": trainer_name,
        "OriginalTrainerID": trainer_id,
        "CurrentTrainerID": trainer_id,
        "CaughtBallName": "Pokeball",
        "MetLocationOverride": "",
        "MetLevel": 5,
        "MetType": "EPokemonMetType::Gift",
        "MemoNote": "",
        "EggCyclesRemaining": 0,
        "EggSpeciesName": "None",
        "EggShinyRolls": 1,
        "bIsShiny": False,
        "bIsFainted": False,
        "bIsEgg": False,
        "bCannotEvolve": False,
        "bIsFollowerOut": False,
    }
    for stat in ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed"):
        defaults[stat + "_IV"] = 0
        defaults[stat + "_EV"] = 0
    info = SPECIES_INFO.get((species_name or "").casefold())
    if info and info.abilities:
        ability = info.abilities[0]
        defaults["Ability"] = f"EPokemonAbility::{ability.enum_name}"
        defaults["AbilitySlot"] = ability.slot
    return defaults


def _create_pokemon_legacy(
    document: GvasDocument,
    pokemon: PokemonView,
    *,
    species: AssetChoice,
    scalar_changes: dict[str, object] | None = None,
    moves: list[AssetChoice] | None = None,
    current_pp: list[int] | None = None,
    max_pp: list[int] | None = None,
    allow_ev_over_510: bool = False,
) -> bytes:
    """Activate an empty Box struct or append its verified template to Party."""
    if pokemon.occupied:
        raise GvasError("The selected Pokemon slot is already occupied.")
    catalog_species = SPECIES_BY_NAME.get(species.name.casefold())
    if catalog_species != species:
        raise GvasError("Species is not in the verified GE-1.0.0 catalog.")

    if pokemon.source == "Party":
        elements = list(structured_array_elements(document, "Party"))
        if 0 <= pokemon.slot_index < len(elements):
            current = next(
                (view for view in party_pokemon(document) if view.slot_index == pokemon.slot_index),
                None,
            )
            if current is None or current.occupied:
                raise GvasError("The selected Party slot is already occupied.")
            raw = document.raw
            prefix = f"Party[{pokemon.slot_index}]"
        else:
            if len(elements) >= 6:
                raise GvasError("Party is full.")
            elements.append(_empty_storage_payload(document))
            raw = patch_structured_array(document, "Party", elements)
            prefix = f"Party[{len(elements) - 1}]"
    elif pokemon.source == "Storage":
        if pokemon.box_index is None:
            raise GvasError("Storage box is required for Pokemon creation.")
        current = _storage_view(document, pokemon.box_index, pokemon.slot_index)
        if current.occupied:
            raise GvasError("The selected Storage slot is already occupied.")
        raw = document.raw
        prefix = storage_slot_path(pokemon.box_index, pokemon.slot_index)
    else:
        raise GvasError("Pokemon creation target must be Party or Storage.")

    raw = patch_soft_object(
        parse_gvas(raw),
        prefix + ".SpeciesData",
        species.path,
        species.object_name,
    )
    seeded = parse_gvas(raw)
    created = _pokemon_view(
        seeded,
        prefix,
        source=pokemon.source,
        box_index=pokemon.box_index,
        slot_index=int(prefix.rsplit("[", 1)[-1].rstrip("]")) if pokemon.source == "Party" else pokemon.slot_index,
    )
    if not created.occupied or created.species != species.name:
        raise GvasError("Pokemon SpeciesData activation failed verification.")

    requested = pokemon_creation_defaults(document)
    requested.update(scalar_changes or {})
    available = {
        item.name: item
        for item in seeded.properties
        if item.path.startswith(prefix + ".") and item.editable
    }
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise GvasError("Pokemon template is missing verified fields: " + ", ".join(unknown))
    changes = {
        field: value
        for field, value in requested.items()
        if available[field].value != value
    }
    raw = patch_pokemon(
        seeded,
        created,
        scalar_changes=changes,
        moves=moves,
        current_pp=current_pp,
        max_pp=max_pp,
        allow_ev_over_510=allow_ev_over_510,
    )
    verified = parse_gvas(raw)
    final = _pokemon_view(
        verified,
        prefix,
        source=created.source,
        box_index=created.box_index,
        slot_index=created.slot_index,
    )
    if not final.occupied or final.species != species.name:
        raise GvasError("Created Pokemon failed structural verification.")
    return raw


def create_pokemon(
    document: GvasDocument,
    pokemon: PokemonView,
    *,
    species: AssetChoice,
    scalar_changes: dict[str, object] | None = None,
    moves: list[AssetChoice] | None = None,
    current_pp: list[int] | None = None,
    max_pp: list[int] | None = None,
    allow_ev_over_510: bool = False,
) -> bytes:
    """Create a Pokémon with one batch edit (Storage) or one prepared template (Party)."""
    if pokemon.occupied:
        raise GvasError("The selected Pokemon slot is already occupied.")
    if SPECIES_BY_NAME.get(species.name.casefold()) != species:
        raise GvasError("Species is not in the verified GE-1.0.0 catalog.")
    requested = pokemon_creation_defaults(document, species.name)
    requested.update(scalar_changes or {})

    def fill_template(template: PokemonView) -> bytes:
        available = {
            item.name for item in document.properties
            if item.path.startswith(template.prefix + ".")
        }
        unknown = sorted(set(requested) - available)
        if unknown:
            raise GvasError("Pokemon template is missing verified fields: " + ", ".join(unknown))
        return patch_pokemon(
            document, template, scalar_changes=requested, species=species,
            moves=moves, current_pp=current_pp, max_pp=max_pp,
            allow_ev_over_510=allow_ev_over_510, _allow_empty_template=True,
        )

    if pokemon.source == "Storage":
        if pokemon.box_index is None:
            raise GvasError("Storage box is required for Pokemon creation.")
        current = _storage_view(document, pokemon.box_index, pokemon.slot_index)
        if current.occupied:
            raise GvasError("The selected Storage slot is already occupied.")
        return fill_template(current)
    if pokemon.source != "Party":
        raise GvasError("Pokemon creation target must be Party or Storage.")

    elements = list(structured_array_elements(document, "Party"))
    if len(elements) >= 6:
        raise GvasError("Party is full.")
    template: PokemonView | None = None
    for box_index in range(len(box_names(document))):
        template = next((view for view in storage_pokemon(document, box_index) if not view.occupied), None)
        if template is not None:
            break
    if template is None:
        raise GvasError("No empty verified storage template is available.")
    prepared = parse_gvas(fill_template(template))
    elements.append(struct_payload(prepared, template.prefix))
    encoded = struct.pack("<I", len(elements)) + b"".join(elements)
    return patch_property_batch(document, payload_changes={"Party": encoded})


def move_pokemon(
    document: GvasDocument,
    *,
    source_kind: str,
    source_slot: int,
    source_box: int | None,
    target_kind: str,
    target_slot: int,
    target_box: int | None,
) -> bytes:
    """Move or swap one complete Pokémon payload between Party and fixed Box slots."""
    if source_kind not in {"party", "storage"} or target_kind not in {"party", "storage"}:
        raise GvasError("Pokémon location must be Party or Storage.")
    if (source_kind, source_box, source_slot) == (target_kind, target_box, target_slot):
        return document.raw
    party_elements = list(structured_array_elements(document, "Party"))
    if len(party_elements) > 6:
        raise GvasError("Party contains more than six verified entries.")

    if source_kind == "party":
        if not 0 <= source_slot < len(party_elements):
            raise GvasError("Source Party slot is empty.")
        source_payload = party_elements[source_slot]
    else:
        if source_box is None:
            raise GvasError("Source Storage box is required.")
        source_view = _storage_view(document, source_box, source_slot)
        if not source_view.occupied:
            raise GvasError("Source Storage slot is empty.")
        source_payload = struct_payload(document, storage_slot_path(source_box, source_slot))

    target_occupied = False
    target_payload: bytes | None = None
    if target_kind == "party":
        target_occupied = 0 <= target_slot < len(party_elements)
        if target_occupied:
            target_payload = party_elements[target_slot]
        elif target_slot < 0 or target_slot >= 6:
            raise GvasError("Target Party slot must be between 1 and 6.")
    else:
        if target_box is None:
            raise GvasError("Target Storage box is required.")
        target_view = _storage_view(document, target_box, target_slot)
        target_occupied = target_view.occupied
        target_payload = struct_payload(document, storage_slot_path(target_box, target_slot))

    if source_kind == "party" and target_kind == "party":
        if target_occupied:
            party_elements[source_slot], party_elements[target_slot] = (
                party_elements[target_slot], party_elements[source_slot]
            )
        else:
            party_elements.append(party_elements.pop(source_slot))
        encoded = struct.pack("<I", len(party_elements)) + b"".join(party_elements)
        return patch_property_batch(document, payload_changes={"Party": encoded})

    if source_kind == "storage" and target_kind == "storage":
        assert source_box is not None and target_box is not None and target_payload is not None
        return patch_property_batch(
            document,
            payload_changes={
                storage_slot_path(target_box, target_slot): source_payload,
                storage_slot_path(source_box, source_slot): target_payload,
            },
        )

    if source_kind == "party":
        assert target_box is not None and target_payload is not None
        if target_occupied:
            party_elements[source_slot] = target_payload
        else:
            if len(party_elements) == 1:
                raise GvasError("The last Party Pokémon cannot be moved into an empty Box slot.")
            party_elements.pop(source_slot)
        encoded = struct.pack("<I", len(party_elements)) + b"".join(party_elements)
        return patch_property_batch(
            document,
            payload_changes={"Party": encoded, storage_slot_path(target_box, target_slot): source_payload},
        )

    assert source_box is not None
    if target_occupied:
        assert target_payload is not None
        party_elements[target_slot] = source_payload
        replacement = target_payload
    else:
        if len(party_elements) >= 6:
            raise GvasError("Party is full.")
        party_elements.append(source_payload)
        replacement = _empty_storage_payload(document)
    encoded = struct.pack("<I", len(party_elements)) + b"".join(party_elements)
    return patch_property_batch(
        document,
        payload_changes={"Party": encoded, storage_slot_path(source_box, source_slot): replacement},
    )


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


def bag_category_indices(document: GvasDocument) -> dict[str, int]:
    categories: dict[str, int] = {}
    for item in document.properties:
        match = re.match(r"^PlayerItems\[(\d+)]\.Category$", item.path)
        if match:
            categories[str(item.value).split("::")[-1]] = int(match.group(1))
    return categories


def _validate_bag_choice(pocket: str, item_name: str, quantity: int) -> None:
    if pocket not in BAG_POCKETS:
        raise GvasError(f"Unknown Bag pocket {pocket!r}.")
    allowed = {item.name for item in ITEMS_BY_POCKET[pocket]}
    if item_name not in allowed:
        raise GvasError(f"Item {item_name!r} is not catalogued in the {pocket} pocket.")
    if not 1 <= int(quantity) <= 9999:
        raise GvasError("Item quantity must be between 1 and 9999.")


def _first_bag_item_template(document: GvasDocument) -> bytes:
    for pocket_index in sorted(bag_category_indices(document).values()):
        path = f"PlayerItems[{pocket_index}].Items"
        elements = structured_array_elements(document, path)
        if elements:
            return elements[0]
    raise GvasError("No verified Bag item template exists in this save.")


def _ensure_bag_pocket(document: GvasDocument, pocket: str) -> tuple[bytes, int]:
    indices = bag_category_indices(document)
    if pocket in indices:
        return document.raw, indices[pocket]
    categories = list(structured_array_elements(document, "PlayerItems"))
    if not categories:
        raise GvasError("No verified Bag pocket template exists in this save.")
    order = {name: index for index, name in enumerate(BAG_POCKETS)}
    indexed_existing = sorted(
        ((index, name) for name, index in indices.items()), key=lambda item: item[0]
    )
    new_index = sum(order.get(name, len(order)) < order[pocket] for _index, name in indexed_existing)
    categories.insert(new_index, categories[0])
    raw = patch_structured_array(document, "PlayerItems", categories)
    current = parse_gvas(raw)
    raw = patch_scalar(current, f"PlayerItems[{new_index}].Category", f"EItemCategory::{pocket}")
    current = parse_gvas(raw)
    raw = patch_structured_array(current, f"PlayerItems[{new_index}].Items", [])
    return raw, new_index


def add_bag_item(document: GvasDocument, pocket: str, item_name: str, quantity: int) -> bytes:
    _validate_bag_choice(pocket, item_name, quantity)
    existing = next(
        (item for item in bag_entries(document) if item.category == pocket and item.name == item_name),
        None,
    )
    if existing:
        return patch_domain_value(document, existing.prefix + ".Quantity", int(quantity))
    template = _first_bag_item_template(document)
    raw, pocket_index = _ensure_bag_pocket(document, pocket)
    current = parse_gvas(raw)
    array_path = f"PlayerItems[{pocket_index}].Items"
    elements = list(structured_array_elements(current, array_path))
    new_index = len(elements)
    elements.append(template)
    raw = patch_structured_array(current, array_path, elements)
    current = parse_gvas(raw)
    prefix = f"{array_path}[{new_index}]"
    return patch_domain_values(
        current,
        {
            prefix + ".ItemName": item_name,
            prefix + ".ItemID": 0,
            prefix + ".Quantity": int(quantity),
        },
    )


def edit_bag_item(document: GvasDocument, entry: BagEntry, item_name: str, quantity: int) -> bytes:
    _validate_bag_choice(entry.category, item_name, quantity)
    duplicate = next(
        (
            item for item in bag_entries(document)
            if item.category == entry.category and item.name == item_name and item.prefix != entry.prefix
        ),
        None,
    )
    if duplicate:
        raise GvasError(f"{item_name} already exists in this Bag pocket; edit that row instead.")
    return patch_domain_values(
        document,
        {
            entry.prefix + ".ItemName": item_name,
            entry.prefix + ".ItemID": 0,
            entry.prefix + ".Quantity": int(quantity),
        },
    )


def remove_bag_item(document: GvasDocument, entry: BagEntry) -> bytes:
    match = _ITEM_RE.match(entry.prefix + ".ItemName")
    if not match:
        raise GvasError("Bag item path is not structurally verified.")
    pocket_index, item_index = int(match.group(1)), int(match.group(2))
    path = f"PlayerItems[{pocket_index}].Items"
    elements = list(structured_array_elements(document, path))
    if not 0 <= item_index < len(elements):
        raise GvasError("Bag item index is outside its verified array.")
    elements.pop(item_index)
    return patch_structured_array(document, path, elements)


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
    if name in {"PlayerId", "PokemonID", "PlayerMoney", "GameCornerCoins"}:
        return "0–2,147,483,647"
    return "fixed-size" if path else ""


def validate_domain_value(
    document: GvasDocument,
    prop: PropertyRecord,
    value: object,
    *,
    allow_ev_over_510: bool = False,
) -> None:
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
        if sum(ev_values) > 510 and not allow_ev_over_510:
            raise GvasError(f"Total EV would be {sum(ev_values)}; maximum is 510.")
    if name == "Friendship" and not 0 <= int(value) <= 255:
        raise GvasError("Friendship must be between 0 and 255.")
    if name == "AbilitySlot" and not 0 <= int(value) <= 2:
        raise GvasError("Ability slot must be 0, 1, or 2.")
    if name == "Quantity" and not 0 <= int(value) <= 9999:
        raise GvasError("Item quantity must be between 0 and 9999.")
    if name in {"CurrentHP", "MaxHP", "CurrentEXP"} and float(value) < 0:
        raise GvasError(f"{name} cannot be negative.")
    if name in {"PlayerId", "PokemonID", "PlayerMoney", "GameCornerCoins"} and not 0 <= int(value) <= 2_147_483_647:
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


def patch_domain_value(
    document: GvasDocument,
    path: str,
    value: object,
    *,
    allow_ev_over_510: bool = False,
) -> bytes:
    matches = [item for item in document.properties if item.path == path]
    if len(matches) != 1:
        raise GvasError(f"Expected one domain field at {path!r}, found {len(matches)}.")
    prop = matches[0]
    validate_domain_value(document, prop, value, allow_ev_over_510=allow_ev_over_510)
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


def patch_domain_values(
    document: GvasDocument,
    changes: dict[str, object],
    *,
    allow_ev_over_510: bool = False,
) -> bytes:
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
        raw = patch_domain_value(current, path, value, allow_ev_over_510=allow_ev_over_510)
    return raw


def _patch_pokemon_legacy(
    document: GvasDocument,
    pokemon: PokemonView,
    *,
    scalar_changes: dict[str, object],
    species: AssetChoice | None = None,
    moves: list[AssetChoice] | None = None,
    current_pp: list[int] | None = None,
    max_pp: list[int] | None = None,
    allow_ev_over_510: bool = False,
) -> bytes:
    if not pokemon.occupied:
        raise GvasError("Use create_pokemon() to activate a verified empty Pokemon slot.")
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
    current = parse_gvas(raw)
    by_path = {item.path: item for item in current.properties}
    ev_changes = {field: int(value) for field, value in scalar_items if field.endswith("_EV")}
    if ev_changes and not allow_ev_over_510:
        final_total = sum(
            ev_changes.get(item.name, int(item.value))
            for item in current.properties
            if item.path.startswith(pokemon.prefix + ".") and item.name.endswith("_EV")
        )
        if final_total > 510:
            raise GvasError(f"Total EV would be {final_total}; maximum is 510.")

    fixed_types = {
        "BoolProperty", "Int8Property", "ByteProperty", "UInt8Property", "Int16Property",
        "UInt16Property", "IntProperty", "Int32Property", "UInt32Property", "Int64Property",
        "UInt64Property", "FloatProperty", "DoubleProperty",
    }
    fixed_changes: dict[str, object] = {}
    variable_changes: list[tuple[str, object]] = []
    for field, value in scalar_items:
        path = pokemon.prefix + "." + field
        prop = by_path.get(path)
        if prop is None:
            raise GvasError(f"Expected one Pokemon field at {path!r}.")
        validate_domain_value(
            current,
            prop,
            value,
            allow_ev_over_510=True if field.endswith("_EV") else allow_ev_over_510,
        )
        if prop.type_name in fixed_types:
            fixed_changes[path] = value
        else:
            variable_changes.append((field, value))
    if fixed_changes:
        raw = patch_fixed_scalars(current, fixed_changes)
    for field, value in variable_changes:
        current = parse_gvas(raw)
        raw = patch_domain_value(
            current,
            pokemon.prefix + "." + field,
            value,
            allow_ev_over_510=allow_ev_over_510,
        )
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


def patch_pokemon(
    document: GvasDocument,
    pokemon: PokemonView,
    *,
    scalar_changes: dict[str, object],
    species: AssetChoice | None = None,
    moves: list[AssetChoice] | None = None,
    current_pp: list[int] | None = None,
    max_pp: list[int] | None = None,
    allow_ev_over_510: bool = False,
    _allow_empty_template: bool = False,
) -> bytes:
    """Patch one Pokémon as a single verified serialization transaction."""
    if not pokemon.occupied and not _allow_empty_template:
        raise GvasError("Use create_pokemon() to activate a verified empty Pokemon slot.")
    by_path = {item.path: item for item in document.properties}
    ev_changes = {field: int(value) for field, value in scalar_changes.items() if field.endswith("_EV")}
    if ev_changes and not allow_ev_over_510:
        final_total = sum(
            ev_changes.get(item.name, int(item.value))
            for item in document.properties
            if item.path.startswith(pokemon.prefix + ".") and item.name.endswith("_EV")
        )
        if final_total > 510:
            raise GvasError(f"Total EV would be {final_total}; maximum is 510.")

    effective_species = species.name if species is not None else pokemon.species
    info = SPECIES_INFO.get(effective_species.casefold())
    if info and (species is not None or "Ability" in scalar_changes or "AbilitySlot" in scalar_changes):
        ability_leaf = str(scalar_changes.get("Ability", pokemon.fields.get("Ability", "None"))).split("::")[-1]
        ability_slot = int(scalar_changes.get("AbilitySlot", pokemon.fields.get("AbilitySlot", 0)))
        choice = next((item for item in info.abilities if item.enum_name.casefold() == ability_leaf.casefold()), None)
        if choice is None or choice.slot != ability_slot:
            raise GvasError(f"Ability {ability_leaf!r} is not valid for {effective_species} in the selected slot.")

    scalar_paths: dict[str, object] = {}
    for field, value in scalar_changes.items():
        path = pokemon.prefix + "." + field
        prop = by_path.get(path)
        if prop is None:
            raise GvasError(f"Expected one Pokemon field at {path!r}.")
        validate_domain_value(
            document, prop, value,
            allow_ev_over_510=True if field.endswith("_EV") else allow_ev_over_510,
        )
        scalar_paths[path] = value

    move_paths: dict[str, list[tuple[str, str]]] = {}
    int_paths: dict[str, list[int]] = {}
    if moves is not None:
        if len(moves) > 4:
            raise GvasError("A Pokemon can have at most four moves.")
        move_paths[pokemon.prefix + ".Moves"] = [(move.path, move.object_name) for move in moves]
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
        int_paths[pokemon.prefix + ".CurrentPP"] = [int(value) for value in current_pp]
        int_paths[pokemon.prefix + ".MaxPP"] = [int(value) for value in max_pp]

    soft_paths = ({pokemon.prefix + ".SpeciesData": (species.path, species.object_name)} if species else {})
    allow_readonly = set()
    if _allow_empty_template:
        allow_readonly.update((*scalar_paths, *soft_paths, *move_paths, *int_paths))
    return patch_property_batch(
        document,
        scalar_changes=scalar_paths,
        soft_object_changes=soft_paths,
        soft_object_array_changes=move_paths,
        int_array_changes=int_paths,
        allow_readonly_paths=allow_readonly,
    )
