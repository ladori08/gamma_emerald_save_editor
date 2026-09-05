from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .codec import GES1Container, decode_ges1, encode_ges1
from .errors import SafetyError
from .gvas import GvasDocument, parse_gvas


SAVE_DIR_PARTS = ("PokemonEmerald", "Saved", ".ged")
FILENAME_SALT = "ge-vault-2f81c4"
KNOWN_SLOTS = ("PokemonSaveSlot", "GEOptions")


@dataclass(slots=True)
class LoadedSave:
    path: Path
    container: GES1Container
    document: GvasDocument
    source_sha256: str


def default_save_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise SafetyError("LOCALAPPDATA is unavailable; choose the save folder manually.")
    return Path(base).joinpath(*SAVE_DIR_PARTS)


def slot_filename(slot_name: str, user_index: int = 0) -> str:
    material = f"{slot_name}|{user_index}|{FILENAME_SALT}".encode("utf-8")
    return hashlib.md5(material).hexdigest() + ".dat"  # noqa: S324 - game filename contract


def discover_saves(folder: Path | None = None) -> list[Path]:
    root = Path(folder) if folder else default_save_dir()
    if not root.is_dir():
        return []
    return sorted(
        (p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".dat"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def load_save(path: Path | str) -> LoadedSave:
    target = Path(path).resolve()
    blob = target.read_bytes()
    container = decode_ges1(blob)
    document = parse_gvas(container.payload)
    return LoadedSave(
        path=target,
        container=container,
        document=document,
        source_sha256=hashlib.sha256(blob).hexdigest(),
    )


def is_game_running() -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq PokemonEmerald-Win64-Shipping.exe", "/NH"],
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "PokemonEmerald-Win64-Shipping.exe" in result.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def _backup_path(path: Path, stamp: str | None = None) -> Path:
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return path.with_name(f"{path.name}.preedit-{stamp}.bak")


def list_backups(path: Path | str) -> list[Path]:
    target = Path(path).resolve()
    return sorted(
        target.parent.glob(f"{target.name}.preedit-*.bak"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def write_save(
    loaded: LoadedSave,
    new_gvas: bytes,
    *,
    allow_game_running: bool = False,
) -> Path:
    target = loaded.path.resolve()
    if is_game_running() and not allow_game_running:
        raise SafetyError("Pokemon Emerald is running. Close the game before writing the save.")
    current = target.read_bytes()
    current_hash = hashlib.sha256(current).hexdigest()
    if current_hash != loaded.source_sha256:
        raise SafetyError("Save changed on disk after loading. Reload it before saving.")
    if not new_gvas.startswith(b"GVAS"):
        raise SafetyError("Refusing to write a non-GVAS payload.")

    encoded = encode_ges1(loaded.container.slot_name, new_gvas)
    verified = decode_ges1(encoded)
    if verified.payload != new_gvas or verified.slot_name != loaded.container.slot_name:
        raise SafetyError("Pre-write round-trip verification failed.")

    backup = _backup_path(target)
    shutil.copy2(target, backup)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        reread = decode_ges1(temp_path.read_bytes())
        if reread.payload != new_gvas:
            raise SafetyError("Temporary save verification failed.")
        os.replace(temp_path, target)
        temp_path = None
        final = decode_ges1(target.read_bytes())
        if final.payload != new_gvas:
            raise SafetyError("Final save verification failed; restore the newest backup.")
    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    return backup


def restore_backup(save_path: Path | str, backup_path: Path | str) -> Path:
    target = Path(save_path).resolve()
    backup = Path(backup_path).resolve()
    if is_game_running():
        raise SafetyError("Pokemon Emerald is running. Close the game before restoring a backup.")
    if backup.parent != target.parent or not backup.name.startswith(f"{target.name}.preedit-"):
        raise SafetyError("Selected backup does not belong to this save.")
    decode_ges1(backup.read_bytes())
    safety_copy = _backup_path(target, datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-prerestore")
    shutil.copy2(target, safety_copy)
    temp = target.with_name(f".{target.name}.restore.tmp")
    try:
        shutil.copy2(backup, temp)
        decode_ges1(temp.read_bytes())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return safety_copy
