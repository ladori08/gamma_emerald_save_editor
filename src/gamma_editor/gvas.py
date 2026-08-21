from __future__ import annotations

from dataclasses import dataclass, field
import struct

from .errors import GvasError


@dataclass(slots=True, frozen=True)
class EngineVersion:
    major: int
    minor: int
    patch: int
    changelist: int
    branch: str


@dataclass(slots=True, frozen=True)
class CustomVersion:
    guid: str
    version: int


@dataclass(slots=True, frozen=True)
class GvasHeader:
    save_game_version: int
    package_file_version_ue4: int
    package_file_version_ue5: int | None
    engine: EngineVersion
    custom_version_format: int
    custom_versions: tuple[CustomVersion, ...]
    save_game_class: str
    body_offset: int
    header_extension: bytes = b""


@dataclass(slots=True, frozen=True)
class PropertyTypeName:
    name: str
    parameters: tuple["PropertyTypeName", ...] = ()

    def display(self) -> str:
        if not self.parameters:
            return self.name
        return f"{self.name}<{', '.join(item.display() for item in self.parameters)}>"


@dataclass(slots=True)
class PropertyRecord:
    name: str
    type_name: str
    size: int
    array_index: int
    value_offset: int
    value_size: int
    value: object = None
    header_offset: int = 0
    end_offset: int = 0
    editable: bool = False
    notes: str = ""
    bool_value_offset: int | None = None
    path: str = ""
    depth: int = 0
    type_descriptor: str = ""
    tag_flags: int = 0
    collection_values: tuple[object, ...] = ()
    size_offset: int | None = None
    size_width: int = 0
    ancestor_paths: tuple[str, ...] = ()


@dataclass(slots=True)
class GvasDocument:
    raw: bytes
    header: GvasHeader
    properties: list[PropertyRecord] = field(default_factory=list)
    property_error: str | None = None


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def take(self, size: int) -> bytes:
        if size < 0 or self.pos + size > len(self.data):
            raise GvasError(f"Unexpected end of GVAS at offset 0x{self.pos:X}.")
        value = self.data[self.pos : self.pos + size]
        self.pos += size
        return value

    def unpack(self, fmt: str):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(size))

    def u8(self) -> int:
        return self.unpack("<B")[0]

    def u16(self) -> int:
        return self.unpack("<H")[0]

    def i32(self) -> int:
        return self.unpack("<i")[0]

    def u32(self) -> int:
        return self.unpack("<I")[0]

    def i64(self) -> int:
        return self.unpack("<q")[0]

    def fstring(self, *, limit: int = 1_048_576) -> str:
        length = self.i32()
        if length == 0:
            return ""
        if abs(length) > limit:
            raise GvasError(f"Implausible FString length {length} at 0x{self.pos - 4:X}.")
        if length > 0:
            raw = self.take(length)
            if not raw.endswith(b"\0"):
                raise GvasError(f"Non-terminated FString at 0x{self.pos - length:X}.")
            return raw[:-1].decode("utf-8", errors="strict")
        raw = self.take(-length * 2)
        if not raw.endswith(b"\0\0"):
            raise GvasError(f"Non-terminated UTF-16 FString at 0x{self.pos + length * 2:X}.")
        return raw[:-2].decode("utf-16-le", errors="strict")

    def guid(self) -> str:
        a, b, c, d = self.unpack("<IIII")
        return f"{a:08x}-{b:08x}-{c:08x}-{d:08x}"


def parse_header(data: bytes) -> GvasHeader:
    r = _Reader(data)
    if r.take(4) != b"GVAS":
        raise GvasError("Inner payload does not start with GVAS.")
    save_version = r.u32()
    if not 1 <= save_version <= 3:
        raise GvasError(f"Unsupported GVAS save-game version {save_version}.")
    package_ue4 = r.u32()
    package_ue5 = r.u32() if save_version >= 3 else None
    engine = EngineVersion(r.u16(), r.u16(), r.u16(), r.u32(), r.fstring(limit=4096))
    custom_format = r.u32()
    custom_count = r.u32()
    if custom_count > 4096:
        raise GvasError(f"Implausible GVAS custom-version count {custom_count}.")
    versions = tuple(CustomVersion(r.guid(), r.i32()) for _ in range(custom_count))
    save_class = r.fstring(limit=16384)
    # GE's UE5.6 archive has a one-byte serialization marker before the first
    # property tag. Detect it structurally so older/other GVAS files still work.
    extension = b""
    if r.remaining() >= 5:
        candidate_ok = _looks_like_fstring(data, r.pos, len(data))
        shifted_ok = _looks_like_fstring(data, r.pos + 1, len(data))
        if not candidate_ok and shifted_ok and data[r.pos] in (0, 1):
            extension = r.take(1)
    return GvasHeader(
        save_game_version=save_version,
        package_file_version_ue4=package_ue4,
        package_file_version_ue5=package_ue5,
        engine=engine,
        custom_version_format=custom_format,
        custom_versions=versions,
        save_game_class=save_class,
        body_offset=r.pos,
        header_extension=extension,
    )


_SCALAR_FORMATS: dict[str, str] = {
    "Int8Property": "<b",
    "ByteProperty": "<B",
    "UInt8Property": "<B",
    "Int16Property": "<h",
    "UInt16Property": "<H",
    "IntProperty": "<i",
    "Int32Property": "<i",
    "UInt32Property": "<I",
    "Int64Property": "<q",
    "UInt64Property": "<Q",
    "FloatProperty": "<f",
    "DoubleProperty": "<d",
}


def _looks_like_fstring(data: bytes, offset: int, end: int) -> bool:
    if offset < 0 or offset + 4 > end:
        return False
    (length,) = struct.unpack_from("<i", data, offset)
    if length == 0 or abs(length) > 65536:
        return False
    byte_count = length if length > 0 else -length * 2
    value_start = offset + 4
    value_end = value_start + byte_count
    if value_end > end:
        return False
    raw = data[value_start:value_end]
    if length > 0:
        if not raw.endswith(b"\0"):
            return False
        try:
            raw[:-1].decode("utf-8")
        except UnicodeDecodeError:
            return False
    else:
        if not raw.endswith(b"\0\0"):
            return False
        try:
            raw[:-2].decode("utf-16-le")
        except UnicodeDecodeError:
            return False
    return True


def _read_complete_type(r: _Reader, *, depth: int = 0) -> PropertyTypeName:
    if depth > 16:
        raise GvasError("Property type-name nesting exceeds the safety limit.")
    name = r.fstring(limit=4096)
    count = r.u32()
    if count > 32:
        raise GvasError(f"Implausible type parameter count {count} for {name!r}.")
    return PropertyTypeName(
        name=name,
        parameters=tuple(_read_complete_type(r, depth=depth + 1) for _ in range(count)),
    )


def _decode_scalar(type_name: str, raw: bytes):
    fmt = _SCALAR_FORMATS.get(type_name)
    if fmt and len(raw) == struct.calcsize(fmt):
        return struct.unpack(fmt, raw)[0], True
    if type_name in {"StrProperty", "NameProperty", "ObjectProperty"}:
        try:
            reader = _Reader(raw)
            value = reader.fstring()
            if reader.remaining() == 0:
                return value, True
        except (GvasError, UnicodeError):
            pass
    return None, False


def _try_parse_classic_properties(data: bytes, start: int) -> tuple[list[PropertyRecord], str | None]:
    """Best-effort parser for tagged scalar properties.

    UE5.4+ can use a compact property-tag path that older public GVAS tools do
    not understand. This routine deliberately stops and preserves the complete
    opaque payload instead of guessing when it encounters an unsupported tag.
    """
    r = _Reader(data)
    r.pos = start
    records: list[PropertyRecord] = []
    try:
        while r.remaining() >= 9:
            header_offset = r.pos
            name = r.fstring(limit=65536)
            if name == "None":
                return records, None
            type_name = r.fstring(limit=256)
            size = r.i64()
            array_index = r.i32()
            if size < 0 or size > r.remaining():
                raise GvasError(f"Invalid property size {size} for {name!r}.")

            bool_value = None
            bool_value_offset = None
            if type_name == "StructProperty":
                _ = r.fstring(limit=4096)
                r.take(16)
            elif type_name in {"ByteProperty", "EnumProperty"}:
                _ = r.fstring(limit=4096)
            elif type_name == "BoolProperty":
                bool_value_offset = r.pos
                bool_value = bool(r.u8())
            elif type_name in {"ArrayProperty", "SetProperty"}:
                _ = r.fstring(limit=256)
            elif type_name == "MapProperty":
                _ = r.fstring(limit=256)
                _ = r.fstring(limit=256)

            has_guid = r.u8()
            if has_guid not in (0, 1):
                raise GvasError(
                    f"Unsupported/compact property tag at 0x{header_offset:X} ({name!r})."
                )
            if has_guid:
                r.take(16)
            value_offset = r.pos
            raw = r.take(size)
            if type_name == "BoolProperty":
                value, editable = bool_value, True
            else:
                value, editable = _decode_scalar(type_name, raw)
            records.append(
                PropertyRecord(
                    name=name,
                    type_name=type_name,
                    size=size,
                    array_index=array_index,
                    value_offset=value_offset,
                    value_size=size,
                    value=value,
                    header_offset=header_offset,
                    end_offset=r.pos,
                    editable=editable,
                    notes="" if editable else "Preserved as opaque data",
                    bool_value_offset=bool_value_offset,
                )
            )
    except (GvasError, UnicodeError, struct.error) as exc:
        return records, str(exc)
    return records, "GVAS ended without a None property terminator."


def _decode_extended_value(type_spec: PropertyTypeName, raw: bytes):
    type_name = type_spec.name
    value, editable = _decode_scalar(type_name, raw)
    if editable:
        return value, True
    if type_name == "BoolProperty" and len(raw) == 1:
        return bool(raw[0]), True
    if type_name == "SoftObjectProperty":
        try:
            reader = _Reader(raw)
            asset_path = reader.fstring(limit=65536)
            asset_name = reader.fstring(limit=65536) if reader.remaining() >= 4 else ""
            return asset_path if not asset_name else f"{asset_path} ({asset_name})", False
        except (GvasError, UnicodeError):
            pass
    if type_name == "EnumProperty":
        try:
            reader = _Reader(raw)
            value = reader.fstring(limit=4096)
            if reader.remaining() == 0:
                return value, True
        except (GvasError, UnicodeError):
            pass
    return None, False


def _decode_collection(type_spec: PropertyTypeName, raw: bytes) -> tuple[object, ...]:
    if len(raw) < 4 or not type_spec.parameters:
        return ()
    count_offset = 4 if type_spec.name == "SetProperty" else 0
    if len(raw) < count_offset + 4:
        return ()
    count = struct.unpack_from("<I", raw, count_offset)[0]
    if count > 100_000:
        return ()
    inner = type_spec.parameters[0]
    reader = _Reader(raw)
    reader.pos = count_offset + 4
    values: list[object] = []
    try:
        fmt = _SCALAR_FORMATS.get(inner.name)
        if fmt:
            scalar_size = struct.calcsize(fmt)
            if reader.remaining() != count * scalar_size:
                return ()
            return tuple(struct.unpack(fmt, reader.take(scalar_size))[0] for _ in range(count))
        if inner.name in {"StrProperty", "NameProperty"}:
            values = [reader.fstring(limit=65536) for _ in range(count)]
        elif inner.name == "SoftObjectProperty":
            for _ in range(count):
                asset_path = reader.fstring(limit=65536)
                asset_name = reader.fstring(limit=65536)
                # FSoftObjectPath also serializes its (usually empty) sub-path.
                _sub_path = reader.fstring(limit=65536)
                values.append(asset_path if not asset_name else f"{asset_path} ({asset_name})")
        else:
            return ()
        if reader.remaining() != 0:
            return ()
        return tuple(values)
    except (GvasError, UnicodeError, struct.error):
        return ()


def _decode_known_struct(type_spec: PropertyTypeName, raw: bytes):
    subtype = type_spec.parameters[0].name if type_spec.parameters else ""
    if subtype == "DateTime" and len(raw) == 8:
        return struct.unpack("<q", raw)[0]
    if subtype in {"Vector", "Rotator"} and len(raw) == 24:
        return tuple(round(value, 6) for value in struct.unpack("<ddd", raw))
    if subtype == "Guid" and len(raw) == 16:
        a, b, c, d = struct.unpack("<IIII", raw)
        return f"{a:08x}-{b:08x}-{c:08x}-{d:08x}"
    if subtype == "SoftObjectPath":
        try:
            reader = _Reader(raw)
            values: list[str] = []
            while reader.remaining() >= 4:
                values.append(reader.fstring(limit=65536))
            if reader.remaining() == 0:
                return " / ".join(value for value in values if value) or "None"
        except (GvasError, UnicodeError):
            pass
    return None


def _try_parse_extended_properties(
    data: bytes,
    start: int,
    end: int,
    *,
    prefix: str = "",
    depth: int = 0,
    record_budget: int = 100_000,
    ancestor_paths: tuple[str, ...] = (),
) -> tuple[list[PropertyRecord], int, str | None]:
    """Parse UE5.6 complete-type property tags used by Gamma Emerald.

    Tag layout verified against GE-1.0.0 is FString name, recursive complete
    type name, uint32 payload size, uint8 extension flags, then payload. Nested
    structs retain ordinary None-terminated property lists.
    """
    if depth > 32:
        return [], start, "Nested property depth exceeds the safety limit."
    r = _Reader(data)
    r.pos = start
    records: list[PropertyRecord] = []
    try:
        while r.pos < end:
            if len(records) >= record_budget:
                raise GvasError("Property record count exceeds the safety limit.")
            header_offset = r.pos
            if not _looks_like_fstring(data, r.pos, end):
                raise GvasError(f"Invalid property name at 0x{r.pos:X}.")
            name = r.fstring(limit=65536)
            if name == "None":
                return records, r.pos, None
            type_spec = _read_complete_type(r)
            size_offset = r.pos
            size = r.u32()
            tag_flags_offset = r.pos
            tag_flags = r.u8()
            serialized_value_offset = r.pos
            array_index = 0
            value_offset = serialized_value_offset
            if tag_flags & 0x01:
                if value_offset + 4 > end:
                    raise GvasError(f"Array-indexed property {name!r} has a truncated index.")
                array_index = struct.unpack_from("<I", data, value_offset)[0]
                value_offset += 4
            value_end = value_offset + size
            if value_end > end:
                raise GvasError(
                    f"Property {name!r} payload exceeds its container: "
                    f"{size} bytes at 0x{value_offset:X}."
                )
            raw = data[value_offset:value_end]
            value, editable = _decode_extended_value(type_spec, raw)
            if type_spec.name == "BoolProperty" and size == 0:
                value = bool(tag_flags & 0x10)
                editable = True
            path = f"{prefix}.{name}" if prefix else name
            if array_index:
                path += f"[{array_index}]"
            record = PropertyRecord(
                name=name,
                type_name=type_spec.name,
                type_descriptor=type_spec.display(),
                size=size,
                array_index=array_index,
                value_offset=value_offset,
                value_size=value_end - value_offset,
                value=value,
                header_offset=header_offset,
                end_offset=value_end,
                editable=editable,
                notes="" if editable else "Preserved as opaque data",
                bool_value_offset=(
                    value_offset
                    if type_spec.name == "BoolProperty" and size == 1
                    else tag_flags_offset
                    if type_spec.name == "BoolProperty" and size == 0
                    else None
                ),
                path=path,
                depth=depth,
                tag_flags=tag_flags,
                size_offset=size_offset,
                size_width=4,
                ancestor_paths=ancestor_paths,
            )
            records.append(record)

            nested_error: str | None = None
            if type_spec.name == "StructProperty" and _looks_like_fstring(data, value_offset, value_end):
                children, child_end, nested_error = _try_parse_extended_properties(
                    data,
                    value_offset,
                    value_end,
                    prefix=path,
                    depth=depth + 1,
                    record_budget=record_budget - len(records),
                    ancestor_paths=ancestor_paths + (path,),
                )
                if nested_error is None and child_end == value_end:
                    records.extend(children)
                    record.value = f"{len(children)} fields"
                    record.notes = "Structured, child fields shown below"
                elif nested_error:
                    record.notes = f"Opaque struct: {nested_error}"
            elif type_spec.name == "StructProperty":
                known_value = _decode_known_struct(type_spec, raw)
                if known_value is not None:
                    record.value = known_value
                    record.notes = "Decoded fixed-size struct (read-only)"
            elif type_spec.name == "ArrayProperty" and size >= 4:
                count = struct.unpack_from("<I", raw, 0)[0]
                collection = _decode_collection(type_spec, raw)
                record.collection_values = collection
                record.value = collection if collection or count == 0 else f"{count} item(s)"
                inner = type_spec.parameters[0] if type_spec.parameters else None
                if inner and inner.name == "StructProperty":
                    child_pos = value_offset + 4
                    all_children: list[PropertyRecord] = []
                    for index in range(count):
                        element_path = f"{path}[{index}]"
                        children, child_pos, nested_error = _try_parse_extended_properties(
                            data,
                            child_pos,
                            value_end,
                            prefix=element_path,
                            depth=depth + 1,
                            record_budget=record_budget - len(records) - len(all_children),
                            ancestor_paths=ancestor_paths + (path,),
                        )
                        all_children.extend(children)
                        if nested_error:
                            break
                    if nested_error is None and child_pos == value_end:
                        records.extend(all_children)
                        record.notes = "Structured array, child fields shown below"
                    elif nested_error:
                        record.notes = f"Opaque array tail: {nested_error}"
            elif type_spec.name == "SetProperty" and size >= 4:
                collection = _decode_collection(type_spec, raw)
                record.collection_values = collection
                if collection:
                    record.value = collection
            r.pos = value_end
    except (GvasError, UnicodeError, struct.error) as exc:
        return records, r.pos, str(exc)
    return records, r.pos, "Property list ended without a None terminator."


def parse_gvas(data: bytes) -> GvasDocument:
    header = parse_header(data)
    if header.header_extension:
        properties, _end, error = _try_parse_extended_properties(
            data, header.body_offset, len(data)
        )
    else:
        properties, error = _try_parse_classic_properties(data, header.body_offset)
    document = GvasDocument(raw=data, header=header, properties=properties, property_error=error)
    _apply_semantic_safety(document)
    return document


def _apply_semantic_safety(document: GvasDocument) -> None:
    """Disable writes into structurally present but semantically empty slots."""
    empty_prefixes: list[str] = []
    for item in document.properties:
        if item.path.startswith("Boxes[") and item.path.endswith(".SpeciesData"):
            value = str(item.value or "")
            if "DA_" not in value:
                empty_prefixes.append(item.path.rsplit(".", 1)[0] + ".")
        if item.path.startswith("Daycare.Slots[") and item.path.endswith(".bOccupied") and item.value is False:
            empty_prefixes.append(item.path.rsplit(".", 1)[0] + ".Mon.")
    if not empty_prefixes:
        return
    for item in document.properties:
        if item.editable and any(item.path.startswith(prefix) for prefix in empty_prefixes):
            item.editable = False
            item.notes = "Read-only: field belongs to an empty Pokemon slot"


def _encode_fstring(value: str) -> bytes:
    if "\0" in value:
        raise GvasError("Unreal strings cannot contain NUL characters.")
    try:
        raw = value.encode("ascii") + b"\0"
        return struct.pack("<i", len(raw)) + raw
    except UnicodeEncodeError:
        raw = value.encode("utf-16-le") + b"\0\0"
        return struct.pack("<i", -(len(raw) // 2)) + raw


def _replace_property_payload(
    document: GvasDocument,
    prop: PropertyRecord,
    encoded: bytes,
) -> bytes:
    data = bytearray(document.raw)
    delta = len(encoded) - prop.value_size
    if delta:
        if not document.header.header_extension or prop.size_offset is None or prop.size_width != 4:
            raise GvasError("Variable-size edits require a verified UE5.6 property-size chain.")
        targets = [prop]
        for ancestor_path in prop.ancestor_paths:
            matches = [item for item in document.properties if item.path == ancestor_path]
            if len(matches) != 1 or matches[0].size_offset is None or matches[0].size_width != 4:
                raise GvasError(f"Cannot verify parent size field for {ancestor_path!r}.")
            targets.append(matches[0])
        for target in targets:
            assert target.size_offset is not None
            new_size = target.size + delta
            if not 0 <= new_size <= 0xFFFFFFFF:
                raise GvasError(f"Resized property {target.path!r} exceeds uint32 limits.")
            struct.pack_into("<I", data, target.size_offset, new_size)
    data[prop.value_offset : prop.end_offset] = encoded
    rebuilt = bytes(data)
    verified = parse_gvas(rebuilt)
    if verified.property_error:
        raise GvasError(f"Resized GVAS failed structural verification: {verified.property_error}")
    if not any(item.path == prop.path for item in verified.properties):
        raise GvasError("Resized GVAS lost the edited property path.")
    return rebuilt


def patch_property_batch(
    document: GvasDocument,
    *,
    scalar_changes: dict[str, object] | None = None,
    soft_object_changes: dict[str, tuple[str, str]] | None = None,
    int_array_changes: dict[str, list[int] | tuple[int, ...]] | None = None,
    soft_object_array_changes: dict[str, list[tuple[str, str]] | tuple[tuple[str, str], ...]] | None = None,
    payload_changes: dict[str, bytes] | None = None,
    allow_readonly_paths: set[str] | None = None,
) -> bytes:
    """Apply independent verified property edits with one resize pass and one reparse."""
    scalar_changes = scalar_changes or {}
    soft_object_changes = soft_object_changes or {}
    int_array_changes = int_array_changes or {}
    soft_object_array_changes = soft_object_array_changes or {}
    payload_changes = payload_changes or {}
    allow_readonly_paths = allow_readonly_paths or set()
    all_paths = [
        *scalar_changes, *soft_object_changes, *int_array_changes,
        *soft_object_array_changes, *payload_changes,
    ]
    if len(all_paths) != len(set(all_paths)):
        raise GvasError("A property cannot be edited twice in the same transaction.")
    for path in all_paths:
        if any(other != path and other.startswith(path + ".") for other in all_paths):
            raise GvasError("A transaction cannot replace both a property and one of its children.")

    by_path: dict[str, PropertyRecord] = {}
    for item in document.properties:
        if item.path in all_paths:
            if item.path in by_path:
                raise GvasError(f"Expected one property at {item.path!r}.")
            by_path[item.path] = item
    missing = sorted(set(all_paths) - set(by_path))
    if missing:
        raise GvasError("Missing property path(s): " + ", ".join(missing))

    replacements: list[tuple[PropertyRecord, bytes]] = []
    bool_changes: list[tuple[PropertyRecord, bool]] = []

    for path, value in scalar_changes.items():
        prop = by_path[path]
        if not prop.editable and path not in allow_readonly_paths:
            raise GvasError(f"Property {path!r} is not safely editable.")
        if prop.type_name == "BoolProperty":
            if prop.bool_value_offset is None:
                raise GvasError(f"Bool property {path!r} is missing its verified header offset.")
            bool_changes.append((prop, bool(value)))
            continue
        fmt = _SCALAR_FORMATS.get(prop.type_name)
        if fmt is not None:
            try:
                encoded = struct.pack(fmt, value)
            except (struct.error, TypeError, ValueError) as exc:
                raise GvasError(f"Invalid value for {prop.type_name}: {value!r}.") from exc
            if len(encoded) != prop.value_size:
                raise GvasError(f"Scalar encoded size changed unexpectedly for {path!r}.")
        elif prop.type_name in {"StrProperty", "NameProperty", "ObjectProperty", "EnumProperty"}:
            if not isinstance(value, str):
                raise GvasError(f"String property {path!r} requires a string value.")
            encoded = _encode_fstring(value)
        else:
            raise GvasError(f"Unsupported scalar type {prop.type_name} at {path!r}.")
        replacements.append((prop, encoded))

    for path, (asset_path, object_name) in soft_object_changes.items():
        prop = by_path[path]
        if prop.type_name != "SoftObjectProperty":
            raise GvasError(f"Property {path!r} is not a SoftObjectProperty.")
        if not prop.editable and path not in allow_readonly_paths:
            raise GvasError(f"Property {path!r} is not safely editable.")
        reader = _Reader(document.raw[prop.value_offset : prop.end_offset])
        try:
            reader.fstring(limit=65536)
            reader.fstring(limit=65536)
            trailing: list[str] = []
            while reader.remaining():
                trailing.append(reader.fstring(limit=65536))
        except (GvasError, UnicodeError) as exc:
            raise GvasError(f"Soft object at {path!r} has an unverified payload.") from exc
        encoded = _encode_fstring(asset_path) + _encode_fstring(object_name)
        encoded += b"".join(_encode_fstring(item) for item in trailing)
        replacements.append((prop, encoded))

    for path, values in int_array_changes.items():
        prop = by_path[path]
        if prop.type_name != "ArrayProperty" or "IntProperty" not in prop.type_descriptor:
            raise GvasError(f"Array at {path!r} is not an integer array.")
        if len(values) > 100_000:
            raise GvasError("Integer array exceeds the safety limit.")
        encoded = struct.pack("<I", len(values)) + b"".join(struct.pack("<i", int(item)) for item in values)
        replacements.append((prop, encoded))

    for path, values in soft_object_array_changes.items():
        prop = by_path[path]
        if prop.type_name != "ArrayProperty" or "SoftObjectProperty" not in prop.type_descriptor:
            raise GvasError(f"Array at {path!r} is not a soft-object array.")
        if len(values) > 1024:
            raise GvasError("Soft-object array exceeds the safety limit.")
        encoded = bytearray(struct.pack("<I", len(values)))
        for asset_path, object_name in values:
            encoded.extend(_encode_fstring(asset_path))
            encoded.extend(_encode_fstring(object_name))
            encoded.extend(_encode_fstring(""))
        replacements.append((prop, bytes(encoded)))

    for path, encoded in payload_changes.items():
        prop = by_path[path]
        if prop.type_name not in {"ArrayProperty", "StructProperty"}:
            raise GvasError(f"Raw payload replacement is not allowed for {prop.type_name}.")
        replacements.append((prop, encoded))

    data = bytearray(document.raw)
    size_deltas: dict[int, tuple[PropertyRecord, int]] = {}
    for prop, encoded in replacements:
        delta = len(encoded) - prop.value_size
        if not delta:
            continue
        if not document.header.header_extension or prop.size_offset is None or prop.size_width != 4:
            raise GvasError("Variable-size edits require a verified UE5.6 property-size chain.")
        for target_path in (prop.path, *prop.ancestor_paths):
            target = by_path.get(target_path)
            if target is None:
                matches = [item for item in document.properties if item.path == target_path]
                if len(matches) != 1:
                    raise GvasError(f"Cannot verify parent size field for {target_path!r}.")
                target = matches[0]
            if target.size_offset is None or target.size_width != 4:
                raise GvasError(f"Cannot verify parent size field for {target_path!r}.")
            old = size_deltas.get(target.size_offset, (target, 0))
            size_deltas[target.size_offset] = (target, old[1] + delta)
    for size_offset, (target, delta) in size_deltas.items():
        new_size = target.size + delta
        if not 0 <= new_size <= 0xFFFFFFFF:
            raise GvasError(f"Resized property {target.path!r} exceeds uint32 limits.")
        struct.pack_into("<I", data, size_offset, new_size)
    for prop, value in bool_changes:
        assert prop.bool_value_offset is not None
        if prop.size == 0:
            if value:
                data[prop.bool_value_offset] |= 0x10
            else:
                data[prop.bool_value_offset] &= ~0x10
        else:
            data[prop.bool_value_offset] = 1 if value else 0
    for prop, encoded in sorted(replacements, key=lambda item: item[0].value_offset, reverse=True):
        data[prop.value_offset : prop.end_offset] = encoded

    rebuilt = bytes(data)
    verified = parse_gvas(rebuilt)
    if verified.property_error:
        raise GvasError(f"Batch edit failed structural verification: {verified.property_error}")
    verified_paths = {item.path for item in verified.properties}
    lost = sorted(set(all_paths) - verified_paths)
    if lost:
        raise GvasError("Batch edit lost property path(s): " + ", ".join(lost))
    return rebuilt


def patch_scalar(document: GvasDocument, property_name: str, value: object) -> bytes:
    matches = [p for p in document.properties if p.path == property_name]
    if not matches:
        matches = [p for p in document.properties if p.name == property_name]
    if len(matches) != 1:
        raise GvasError(f"Expected exactly one property named {property_name!r}, found {len(matches)}.")
    prop = matches[0]
    if not prop.editable:
        raise GvasError(f"Property {property_name!r} is not safely editable.")
    data = bytearray(document.raw)
    if prop.type_name == "BoolProperty":
        if prop.bool_value_offset is None:
            raise GvasError("Bool property is missing its verified header offset.")
        if prop.size == 0:
            if bool(value):
                data[prop.bool_value_offset] |= 0x10
            else:
                data[prop.bool_value_offset] &= ~0x10
        else:
            data[prop.bool_value_offset] = 1 if bool(value) else 0
        return bytes(data)
    fmt = _SCALAR_FORMATS.get(prop.type_name)
    if fmt:
        try:
            encoded = struct.pack(fmt, value)
        except (struct.error, TypeError, ValueError) as exc:
            raise GvasError(f"Invalid value for {prop.type_name}: {value!r}.") from exc
        if len(encoded) != prop.value_size:
            raise GvasError("Scalar encoded size changed unexpectedly.")
        data[prop.value_offset : prop.end_offset] = encoded
        return bytes(data)
    if prop.type_name in {"StrProperty", "NameProperty", "ObjectProperty", "EnumProperty"}:
        if not isinstance(value, str):
            raise GvasError("String properties require a string value.")
        return _replace_property_payload(document, prop, _encode_fstring(value))
    raise GvasError(f"Unsupported editable property type {prop.type_name}.")


def patch_fixed_scalars(document: GvasDocument, changes: dict[str, object]) -> bytes:
    """Patch multiple verified fixed-width scalar fields with one structural reparse."""
    data = bytearray(document.raw)
    for path, value in changes.items():
        matches = [item for item in document.properties if item.path == path]
        if len(matches) != 1:
            raise GvasError(f"Expected one property at {path!r}, found {len(matches)}.")
        prop = matches[0]
        if not prop.editable:
            raise GvasError(f"Property {path!r} is not safely editable.")
        if prop.type_name == "BoolProperty":
            if prop.bool_value_offset is None:
                raise GvasError(f"Bool property {path!r} is missing its verified header offset.")
            if prop.size == 0:
                if bool(value):
                    data[prop.bool_value_offset] |= 0x10
                else:
                    data[prop.bool_value_offset] &= ~0x10
            else:
                data[prop.bool_value_offset] = 1 if bool(value) else 0
            continue
        fmt = _SCALAR_FORMATS.get(prop.type_name)
        if fmt is None:
            raise GvasError(f"Property {path!r} is not a fixed-width scalar.")
        try:
            encoded = struct.pack(fmt, value)
        except (struct.error, TypeError, ValueError) as exc:
            raise GvasError(f"Invalid value for {prop.type_name}: {value!r}.") from exc
        if len(encoded) != prop.value_size:
            raise GvasError(f"Scalar encoded size changed unexpectedly for {path!r}.")
        data[prop.value_offset : prop.end_offset] = encoded
    rebuilt = bytes(data)
    verified = parse_gvas(rebuilt)
    if verified.property_error:
        raise GvasError(f"Fixed-scalar batch failed structural verification: {verified.property_error}")
    return rebuilt


def _property_at(document: GvasDocument, path: str, expected_type: str) -> PropertyRecord:
    matches = [item for item in document.properties if item.path == path]
    if len(matches) != 1:
        raise GvasError(f"Expected one property at {path!r}, found {len(matches)}.")
    prop = matches[0]
    if prop.type_name != expected_type:
        raise GvasError(f"Property {path!r} is {prop.type_name}, expected {expected_type}.")
    return prop


def patch_soft_object(
    document: GvasDocument,
    path: str,
    asset_path: str,
    object_name: str,
) -> bytes:
    """Replace a verified UE5 FSoftObjectPtr payload while preserving any sub-path."""
    prop = _property_at(document, path, "SoftObjectProperty")
    reader = _Reader(document.raw[prop.value_offset : prop.end_offset])
    try:
        _old_asset_path = reader.fstring(limit=65536)
        _old_object_name = reader.fstring(limit=65536)
        trailing: list[str] = []
        while reader.remaining():
            trailing.append(reader.fstring(limit=65536))
    except (GvasError, UnicodeError) as exc:
        raise GvasError(f"Soft object at {path!r} has an unverified payload.") from exc
    encoded = _encode_fstring(asset_path) + _encode_fstring(object_name)
    encoded += b"".join(_encode_fstring(item) for item in trailing)
    return _replace_property_payload(document, prop, encoded)


def patch_int_array(document: GvasDocument, path: str, values: list[int] | tuple[int, ...]) -> bytes:
    prop = _property_at(document, path, "ArrayProperty")
    if "IntProperty" not in prop.type_descriptor:
        raise GvasError(f"Array at {path!r} is not an integer array.")
    if len(values) > 100_000:
        raise GvasError("Integer array exceeds the safety limit.")
    try:
        encoded = struct.pack("<I", len(values)) + b"".join(struct.pack("<i", int(item)) for item in values)
    except (struct.error, TypeError, ValueError) as exc:
        raise GvasError("Integer array contains an invalid value.") from exc
    return _replace_property_payload(document, prop, encoded)


def patch_soft_object_array(
    document: GvasDocument,
    path: str,
    values: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> bytes:
    prop = _property_at(document, path, "ArrayProperty")
    if "SoftObjectProperty" not in prop.type_descriptor:
        raise GvasError(f"Array at {path!r} is not a soft-object array.")
    if len(values) > 1024:
        raise GvasError("Soft-object array exceeds the safety limit.")
    encoded = bytearray(struct.pack("<I", len(values)))
    for asset_path, object_name in values:
        encoded.extend(_encode_fstring(asset_path))
        encoded.extend(_encode_fstring(object_name))
        encoded.extend(_encode_fstring(""))
    return _replace_property_payload(document, prop, bytes(encoded))


def structured_array_elements(document: GvasDocument, path: str) -> tuple[bytes, ...]:
    """Return complete serialized elements from a verified Array<Struct> property."""
    prop = _property_at(document, path, "ArrayProperty")
    if "StructProperty" not in prop.type_descriptor or prop.value_size < 4:
        raise GvasError(f"Array at {path!r} is not a structured array.")
    count = struct.unpack_from("<I", document.raw, prop.value_offset)[0]
    if count > 100_000:
        raise GvasError(f"Structured array at {path!r} exceeds the safety limit.")
    if count == 0:
        if prop.value_size != 4:
            raise GvasError(f"Empty structured array at {path!r} has an unexpected payload.")
        return ()
    starts: list[int] = []
    for index in range(count):
        prefix = f"{path}[{index}]."
        offsets = [
            item.header_offset
            for item in document.properties
            if item.path.startswith(prefix)
            and prop.value_offset + 4 <= item.header_offset < prop.end_offset
        ]
        if not offsets:
            raise GvasError(f"Cannot verify element {index} boundaries for {path!r}.")
        starts.append(min(offsets))
    if starts[0] != prop.value_offset + 4 or starts != sorted(set(starts)):
        raise GvasError(f"Structured array at {path!r} has ambiguous element boundaries.")
    ends = starts[1:] + [prop.end_offset]
    elements = tuple(document.raw[start:end] for start, end in zip(starts, ends))
    if any(not element.endswith(_encode_fstring("None")) for element in elements):
        raise GvasError(f"Structured array at {path!r} has an unverified element terminator.")
    return elements


def patch_structured_array(
    document: GvasDocument,
    path: str,
    elements: list[bytes] | tuple[bytes, ...],
) -> bytes:
    """Replace a verified Array<Struct>, including its count and parent size chain."""
    prop = _property_at(document, path, "ArrayProperty")
    if "StructProperty" not in prop.type_descriptor:
        raise GvasError(f"Array at {path!r} is not a structured array.")
    if len(elements) > 100_000:
        raise GvasError("Structured array exceeds the safety limit.")
    terminator = _encode_fstring("None")
    if any(not isinstance(item, bytes) or not item.endswith(terminator) for item in elements):
        raise GvasError("Structured array element is missing its verified None terminator.")
    encoded = struct.pack("<I", len(elements)) + b"".join(elements)
    rebuilt = _replace_property_payload(document, prop, encoded)
    reparsed = parse_gvas(rebuilt)
    if len(structured_array_elements(reparsed, path)) != len(elements):
        raise GvasError(f"Structured array at {path!r} failed count verification.")
    return rebuilt


def struct_payload(document: GvasDocument, path: str) -> bytes:
    prop = _property_at(document, path, "StructProperty")
    payload = document.raw[prop.value_offset : prop.end_offset]
    if not payload.endswith(_encode_fstring("None")):
        raise GvasError(f"Struct at {path!r} has an unverified terminator.")
    return payload


def patch_struct_payload(document: GvasDocument, path: str, payload: bytes) -> bytes:
    prop = _property_at(document, path, "StructProperty")
    if not payload.endswith(_encode_fstring("None")):
        raise GvasError("Replacement struct is missing its verified None terminator.")
    return _replace_property_payload(document, prop, payload)
