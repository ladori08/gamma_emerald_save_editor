from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import struct
import sys
from typing import Final

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .errors import ContainerError


MAGIC: Final[bytes] = b"GES1"
CONTAINER_VERSION: Final[int] = 1
HEADER_SIZE: Final[int] = 32
BLOCK_SIZE: Final[int] = 16
MAX_PLAINTEXT_SIZE: Final[int] = 256 * 1024 * 1024
SAVE_KEY_ENV: Final[str] = "GAMMA_EMERALD_SAVE_KEY_HEX"
SAVE_KEY_FILENAME: Final[str] = "save_key.hex"


@dataclass(slots=True, frozen=True)
class GES1Container:
    slot_name: str
    payload: bytes
    version: int = CONTAINER_VERSION
    plaintext_size: int = 0
    digest: bytes = b""


def _save_key_candidates() -> list[Path]:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().with_name(SAVE_KEY_FILENAME))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "GammaEmeraldSaveEditor" / SAVE_KEY_FILENAME)
    return candidates


def _load_save_key() -> bytes:
    raw = os.environ.get(SAVE_KEY_ENV)
    source = f"environment variable {SAVE_KEY_ENV}"
    if raw is None:
        for candidate in _save_key_candidates():
            if candidate.is_file():
                raw = candidate.read_text(encoding="ascii")
                source = str(candidate)
                break
    if raw is None:
        locations = ", ".join(str(path) for path in _save_key_candidates())
        raise ContainerError(
            f"Gamma Emerald save key is not configured. Set {SAVE_KEY_ENV} or create "
            f"{SAVE_KEY_FILENAME} in one of: {locations or 'the application directory'}."
        )
    compact = "".join(raw.split())
    try:
        key = bytes.fromhex(compact)
    except ValueError as exc:
        raise ContainerError(f"Gamma Emerald save key in {source} is not valid hexadecimal.") from exc
    if len(key) != 32:
        raise ContainerError(f"Gamma Emerald save key in {source} must be exactly 32 bytes.")
    return key


def _read_slot_string(data: bytes, offset: int) -> tuple[str, int]:
    """Read Gamma Emerald's length-prefixed slot string.

    This looks similar to an Unreal FString, but GE-1.0.0 stores the exact
    byte/code-unit count and does not append a terminator. Keeping this codec
    separate from the GVAS FString reader prevents an easy-to-miss off-by-one.
    """
    if offset + 4 > len(data):
        raise ContainerError("GES1 plaintext ended before its slot-name length.")
    (length,) = struct.unpack_from("<i", data, offset)
    offset += 4
    if length == 0:
        return "", offset
    if abs(length) > 4096:
        raise ContainerError(f"Implausible FString length in GES1 plaintext: {length}.")
    if length > 0:
        end = offset + length
        if end > len(data):
            raise ContainerError("GES1 slot name is truncated.")
        raw = data[offset:end]
        try:
            return raw.decode("utf-8"), end
        except UnicodeDecodeError as exc:
            raise ContainerError("GES1 slot name is not valid UTF-8.") from exc
    units = -length
    end = offset + units * 2
    if end > len(data):
        raise ContainerError("GES1 UTF-16 slot name is truncated.")
    raw = data[offset:end]
    try:
        return raw.decode("utf-16-le"), end
    except UnicodeDecodeError as exc:
        raise ContainerError("GES1 slot name is not valid UTF-16LE.") from exc


def _write_slot_string(value: str) -> bytes:
    if "\0" in value:
        raise ContainerError("Slot names cannot contain NUL characters.")
    try:
        raw = value.encode("ascii")
        return struct.pack("<i", len(raw)) + raw
    except UnicodeEncodeError:
        raw = value.encode("utf-16-le")
        return struct.pack("<i", -(len(raw) // 2)) + raw


def _crypt(data: bytes, *, encrypt: bool) -> bytes:
    if len(data) % BLOCK_SIZE:
        raise ContainerError("AES payload size must be a multiple of 16 bytes.")
    cipher = Cipher(algorithms.AES(_load_save_key()), modes.ECB())
    worker = cipher.encryptor() if encrypt else cipher.decryptor()
    return worker.update(data) + worker.finalize()


def decode_ges1(blob: bytes) -> GES1Container:
    if len(blob) < HEADER_SIZE + BLOCK_SIZE:
        raise ContainerError("File is too small to be a valid GES1 save.")
    if blob[:4] != MAGIC:
        raise ContainerError(f"Invalid GES1 magic: {blob[:4]!r}.")
    version, plaintext_size = struct.unpack_from("<II", blob, 4)
    if version != CONTAINER_VERSION:
        raise ContainerError(
            f"Unsupported GES1 version {version}; this build supports {CONTAINER_VERSION}."
        )
    encrypted = blob[HEADER_SIZE:]
    if len(encrypted) % BLOCK_SIZE:
        raise ContainerError("GES1 encrypted body is not aligned to 16 bytes.")
    if not 0 < plaintext_size <= len(encrypted):
        raise ContainerError(
            f"Invalid GES1 plaintext size {plaintext_size} for {len(encrypted)} encrypted bytes."
        )
    if plaintext_size > MAX_PLAINTEXT_SIZE:
        raise ContainerError("GES1 plaintext exceeds the editor safety limit.")

    expected_digest = blob[12:32]
    plaintext = _crypt(encrypted, encrypt=False)[:plaintext_size]
    actual_digest = hashlib.sha1(plaintext).digest()
    if actual_digest != expected_digest:
        raise ContainerError("GES1 SHA-1 integrity check failed (wrong build/key or corrupt save).")

    slot_name, offset = _read_slot_string(plaintext, 0)
    if offset + 4 > len(plaintext):
        raise ContainerError("GES1 plaintext ended before the GVAS payload size.")
    (payload_size,) = struct.unpack_from("<i", plaintext, offset)
    offset += 4
    if payload_size < 0 or payload_size > MAX_PLAINTEXT_SIZE:
        raise ContainerError(f"Implausible inner payload size: {payload_size}.")
    end = offset + payload_size
    if end != len(plaintext):
        raise ContainerError(
            f"GES1 inner payload boundary mismatch: declared {payload_size}, "
            f"available {len(plaintext) - offset}."
        )
    payload = plaintext[offset:end]
    if not payload.startswith(b"GVAS"):
        raise ContainerError("GES1 inner payload is not an Unreal GVAS save.")
    return GES1Container(
        slot_name=slot_name,
        payload=payload,
        version=version,
        plaintext_size=plaintext_size,
        digest=expected_digest,
    )


def encode_ges1(slot_name: str, payload: bytes) -> bytes:
    if not payload.startswith(b"GVAS"):
        raise ContainerError("Refusing to encode a non-GVAS payload.")
    plaintext = _write_slot_string(slot_name) + struct.pack("<i", len(payload)) + payload
    if len(plaintext) > MAX_PLAINTEXT_SIZE:
        raise ContainerError("GES1 plaintext exceeds the editor safety limit.")
    digest = hashlib.sha1(plaintext).digest()
    padded_size = (len(plaintext) + BLOCK_SIZE - 1) & ~(BLOCK_SIZE - 1)
    padded = plaintext.ljust(padded_size, b"\0")
    encrypted = _crypt(padded, encrypt=True)
    return MAGIC + struct.pack("<II", CONTAINER_VERSION, len(plaintext)) + digest + encrypted


def validate_round_trip(blob: bytes) -> GES1Container:
    decoded = decode_ges1(blob)
    rebuilt = encode_ges1(decoded.slot_name, decoded.payload)
    verified = decode_ges1(rebuilt)
    if verified.slot_name != decoded.slot_name or verified.payload != decoded.payload:
        raise ContainerError("GES1 encode/decode round-trip changed the payload.")
    return decoded
