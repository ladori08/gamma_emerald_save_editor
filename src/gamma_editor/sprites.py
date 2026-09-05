from __future__ import annotations

import os
from pathlib import Path
import re
import sys
import tkinter as tk


_FILENAME_ALIASES = {
    "venasaur": "VENUSAUR.png",
    "missingno": "MISSINGNO.png",
}


def sprite_filename(species_name: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", species_name.casefold())
    return _FILENAME_ALIASES.get(key, re.sub(r"[^A-Z0-9]", "", species_name.upper()) + ".png")


def sprite_directories() -> tuple[Path, ...]:
    candidates: list[Path] = []
    configured = os.environ.get("GAMMA_EMERALD_SPRITES_DIR")
    if configured:
        candidates.append(Path(configured).expanduser())
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "gamma_editor" / "assets" / "pokemon_icons")
    candidates.extend(
        (
            Path(sys.executable).resolve().parent / "pokemon_icons",
            Path(__file__).resolve().parents[2] / "runtime_assets" / "pokemon_icons",
        )
    )
    result: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in result:
            result.append(resolved)
    return tuple(result)


class SpriteRepository:
    """Load optional local sprite sheets without making game art part of public source."""

    def __init__(self, master: tk.Misc) -> None:
        self.master = master
        self._source_cache: dict[str, tk.PhotoImage | None] = {}
        self._image_cache: dict[tuple[str, int], tk.PhotoImage | None] = {}

    @property
    def available_directory(self) -> Path | None:
        return next((path for path in sprite_directories() if path.is_dir()), None)

    def get(self, species_name: str, size: int) -> tk.PhotoImage | None:
        key = (species_name.casefold(), int(size))
        if key in self._image_cache:
            return self._image_cache[key]
        source = self._load_source(species_name)
        if source is None:
            self._image_cache[key] = None
            return None
        side = min(source.width(), source.height())
        if side <= 0:
            self._image_cache[key] = None
            return None
        frame = tk.PhotoImage(master=self.master, width=side, height=side)
        frame.tk.call(frame, "copy", source, "-from", 0, 0, side, side, "-to", 0, 0)
        if size == side:
            image = frame
        elif size < side and side % size == 0:
            image = frame.subsample(side // size)
        elif size > side and size % side == 0:
            image = frame.zoom(size // side)
        else:
            # Tk has nearest-neighbor integer scaling only. This ratio keeps pixel art crisp
            # while landing exactly on common UI sizes such as 48 from a 64-pixel frame.
            numerator = max(1, int(size))
            denominator = side
            image = frame.zoom(numerator).subsample(denominator)
        self._image_cache[key] = image
        return image

    def _load_source(self, species_name: str) -> tk.PhotoImage | None:
        key = species_name.casefold()
        if key in self._source_cache:
            return self._source_cache[key]
        filename = sprite_filename(species_name)
        for directory in sprite_directories():
            path = directory / filename
            if not path.is_file():
                continue
            try:
                image = tk.PhotoImage(master=self.master, file=path)
            except tk.TclError:
                continue
            self._source_cache[key] = image
            return image
        self._source_cache[key] = None
        return None
