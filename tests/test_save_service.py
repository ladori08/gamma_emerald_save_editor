from __future__ import annotations

from pathlib import Path

import pytest

from gamma_editor.codec import decode_ges1, encode_ges1
from gamma_editor.errors import SafetyError
from gamma_editor.save_service import list_backups, load_save, restore_backup, write_save


def test_guarded_write_creates_valid_backup(tmp_path: Path, minimal_gvas: bytes, monkeypatch) -> None:
    target = tmp_path / "slot.dat"
    original = encode_ges1("PokemonSaveSlot", minimal_gvas)
    target.write_bytes(original)
    loaded = load_save(target)
    monkeypatch.setattr("gamma_editor.save_service.is_game_running", lambda: False)

    backup = write_save(loaded, minimal_gvas)

    assert backup.read_bytes() == original
    assert decode_ges1(target.read_bytes()).payload == minimal_gvas
    assert backup in list_backups(target)


def test_stale_source_is_rejected_before_backup(tmp_path: Path, minimal_gvas: bytes, monkeypatch) -> None:
    target = tmp_path / "slot.dat"
    target.write_bytes(encode_ges1("PokemonSaveSlot", minimal_gvas))
    loaded = load_save(target)
    target.write_bytes(target.read_bytes() + b"changed")
    monkeypatch.setattr("gamma_editor.save_service.is_game_running", lambda: False)

    with pytest.raises(SafetyError, match="changed on disk"):
        write_save(loaded, minimal_gvas)
    assert list_backups(target) == []


def test_game_running_is_rejected(tmp_path: Path, minimal_gvas: bytes, monkeypatch) -> None:
    target = tmp_path / "slot.dat"
    target.write_bytes(encode_ges1("PokemonSaveSlot", minimal_gvas))
    loaded = load_save(target)
    monkeypatch.setattr("gamma_editor.save_service.is_game_running", lambda: True)

    with pytest.raises(SafetyError, match="running"):
        write_save(loaded, minimal_gvas)


def test_restore_backup_keeps_pre_restore_copy(tmp_path: Path, minimal_gvas: bytes, monkeypatch) -> None:
    target = tmp_path / "slot.dat"
    original = encode_ges1("PokemonSaveSlot", minimal_gvas)
    target.write_bytes(original)
    loaded = load_save(target)
    monkeypatch.setattr("gamma_editor.save_service.is_game_running", lambda: False)
    backup = write_save(loaded, minimal_gvas)

    safety_copy = restore_backup(target, backup)

    assert safety_copy.exists()
    assert decode_ges1(target.read_bytes()).payload == minimal_gvas
