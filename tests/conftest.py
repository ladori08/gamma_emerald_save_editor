from __future__ import annotations

import os
import struct

import pytest


# Synthetic tests use a non-secret deterministic key. Real saves require a separately
# provisioned key through the documented environment variable or ignored key file.
os.environ.setdefault("GAMMA_EMERALD_SAVE_KEY_HEX", "00" * 32)


def fstring(value: str) -> bytes:
    raw = value.encode("utf-8") + b"\0"
    return struct.pack("<i", len(raw)) + raw


@pytest.fixture
def minimal_gvas() -> bytes:
    return b"".join(
        (
            b"GVAS",
            struct.pack("<III", 3, 522, 1017),
            struct.pack("<HHHI", 5, 6, 1, 44394996),
            fstring("++UE5+Release-5.6"),
            struct.pack("<II", 3, 0),
            fstring("/Script/PokemonEmerald.TestSave"),
            b"\0",
            fstring("None"),
            struct.pack("<I", 0),
        )
    )
