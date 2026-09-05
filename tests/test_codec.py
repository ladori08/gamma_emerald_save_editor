from __future__ import annotations

import pytest

from gamma_editor.codec import _load_save_key, decode_ges1, encode_ges1, validate_round_trip
from gamma_editor.errors import ContainerError
from gamma_editor.save_service import slot_filename


def test_ges1_round_trip_preserves_slot_and_payload(minimal_gvas: bytes) -> None:
    blob = encode_ges1("PokemonSaveSlot", minimal_gvas)
    decoded = validate_round_trip(blob)
    assert decoded.slot_name == "PokemonSaveSlot"
    assert decoded.payload == minimal_gvas
    assert decoded.plaintext_size % 16 != 0


def test_ges1_slot_string_has_no_nul(minimal_gvas: bytes) -> None:
    blob = encode_ges1("GEOptions", minimal_gvas)
    decoded = decode_ges1(blob)
    assert decoded.slot_name == "GEOptions"


def test_corrupt_digest_is_rejected(minimal_gvas: bytes) -> None:
    blob = bytearray(encode_ges1("GEOptions", minimal_gvas))
    blob[12] ^= 0xFF
    with pytest.raises(ContainerError, match="SHA-1"):
        decode_ges1(bytes(blob))


def test_known_slot_filenames() -> None:
    assert slot_filename("PokemonSaveSlot") == "859c7fd1524eb8d6726f1233820531b8.dat"
    assert slot_filename("GEOptions") == "c4986df5d9f9ee63d369a56c49cc538f.dat"


def test_missing_external_key_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("GAMMA_EMERALD_SAVE_KEY_HEX", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    with pytest.raises(ContainerError, match="not configured"):
        _load_save_key()


def test_external_key_file_is_loaded(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("GAMMA_EMERALD_SAVE_KEY_HEX", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    key_dir = tmp_path / "GammaEmeraldSaveEditor"
    key_dir.mkdir()
    (key_dir / "save_key.hex").write_text("ab" * 32, encoding="ascii")
    assert _load_save_key() == bytes.fromhex("ab" * 32)
