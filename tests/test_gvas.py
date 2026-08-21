from __future__ import annotations

import struct

from gamma_editor.gvas import parse_gvas, patch_scalar

from conftest import fstring


def _base_header() -> bytes:
    return b"".join(
        (
            b"GVAS",
            struct.pack("<III", 3, 522, 1017),
            struct.pack("<HHHI", 5, 6, 1, 44394996),
            fstring("++UE5+Release-5.6"),
            struct.pack("<II", 3, 0),
            fstring("/Script/PokemonEmerald.TestSave"),
            b"\0",
        )
    )


def test_header_extension_and_empty_properties(minimal_gvas: bytes) -> None:
    doc = parse_gvas(minimal_gvas)
    assert doc.header.package_file_version_ue5 == 1017
    assert doc.header.header_extension == b"\0"
    assert doc.properties == []
    assert doc.property_error is None


def test_parse_and_patch_fixed_size_integer() -> None:
    gvas = b"".join(
        (
            _base_header(),
            fstring("PlayerMoney"),
            fstring("IntProperty"),
            struct.pack("<IIB", 0, 4, 0),
            struct.pack("<i", 1200),
            fstring("None"),
            struct.pack("<I", 0),
        )
    )
    doc = parse_gvas(gvas)
    assert doc.property_error is None
    assert doc.properties[0].value == 1200
    patched = patch_scalar(doc, "PlayerMoney", 999999)
    reparsed = parse_gvas(patched)
    assert reparsed.properties[0].value == 999999
    assert len(patched) == len(gvas)


def test_parse_and_patch_bool_header_value() -> None:
    gvas = b"".join(
        (
            _base_header(),
            fstring("PickedStarter"),
            fstring("BoolProperty"),
            struct.pack("<IIB", 0, 0, 0),
            fstring("None"),
            struct.pack("<I", 0),
        )
    )
    doc = parse_gvas(gvas)
    assert doc.properties[0].value is False
    patched = patch_scalar(doc, "PickedStarter", True)
    assert parse_gvas(patched).properties[0].value is True


def test_parse_fixed_array_index_prefix() -> None:
    child = b"".join(
        (
            fstring("Level"),
            fstring("IntProperty"),
            struct.pack("<IIBi", 0, 4, 0, 7),
            fstring("None"),
        )
    )
    gvas = b"".join(
        (
            _base_header(),
            fstring("Pokemon"),
            fstring("StructProperty"),
            struct.pack("<I", 1),
            fstring("PokemonInstanceData"),
            struct.pack("<I", 1),
            fstring("/Script/PokemonEmerald"),
            struct.pack("<IIBI", 0, len(child), 1, 3),
            child,
            fstring("None"),
            struct.pack("<I", 0),
        )
    )
    doc = parse_gvas(gvas)
    assert doc.property_error is None
    assert doc.properties[0].array_index == 3
    assert doc.properties[0].path == "Pokemon[3]"
    assert doc.properties[1].path == "Pokemon[3].Level"


def test_resize_nested_string_updates_parent_size() -> None:
    child = b"".join(
        (
            fstring("Name"),
            fstring("StrProperty"),
            struct.pack("<IIB", 0, len(fstring("LAD")), 0),
            fstring("LAD"),
            fstring("None"),
        )
    )
    gvas = b"".join(
        (
            _base_header(),
            fstring("Trainer"),
            fstring("StructProperty"),
            struct.pack("<I", 1),
            fstring("TrainerData"),
            struct.pack("<I", 1),
            fstring("/Script/PokemonEmerald"),
            struct.pack("<IIB", 0, len(child), 0),
            child,
            fstring("None"),
            struct.pack("<I", 0),
        )
    )
    before = parse_gvas(gvas)
    old_parent_size = before.properties[0].size
    patched = patch_scalar(before, "Trainer.Name", "LADORI")
    after = parse_gvas(patched)
    assert after.property_error is None
    assert next(item.value for item in after.properties if item.path == "Trainer.Name") == "LADORI"
    assert after.properties[0].size == old_parent_size + 3
