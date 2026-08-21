# Gamma Emerald Save Editor

Windows save inspector/editor for Pokemon Gamma Emerald `GE-1.0.0` (Unreal Engine 5.6).

The tool validates and round-trips the game's encrypted `GES1` wrapper, reads the inner `GVAS`
header, exposes only verified scalar properties, and preserves unknown data byte-for-byte. Every
live write is guarded by a timestamped backup, stale-file detection, game-running detection,
atomic replacement, and a final decode/integrity check.

## Quick start

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
$env:GAMMA_EMERALD_SAVE_KEY_HEX = "YOUR_64_HEX_CHARACTER_KEY"
.\.venv\Scripts\python.exe -m gamma_editor.gui
```

The real save-encryption key is deliberately not published. Supply its 64 hexadecimal characters
through `GAMMA_EMERALD_SAVE_KEY_HEX`. Packaged builds may instead place an ignored `save_key.hex`
beside the executable or at `%LOCALAPPDATA%\GammaEmeraldSaveEditor\save_key.hex`.

The default save folder is:

```text
%LOCALAPPDATA%\PokemonEmerald\Saved\.ged
```

Known slot filenames for user index `0`:

- Story: `859c7fd1524eb8d6726f1233820531b8.dat`
- Options: `c4986df5d9f9ee63d369a56c49cc538f.dat`

If only the options file exists, start or continue the game and make an in-game save before
testing gameplay fields.

## CLI

```powershell
gamma-save saves
gamma-save summary PATH_TO_SAVE
gamma-save validate PATH_TO_SAVE
gamma-save properties PATH_TO_SAVE --top-level
gamma-save properties PATH_TO_SAVE --filter Party --editable
gamma-save unpack PATH_TO_SAVE exported.gvas
gamma-save pack exported.gvas wrapped.dat --slot PokemonSaveSlot
gamma-save slot-filename PokemonSaveSlot
```

`pack` never overwrites an existing file. The GUI is the supported route for guarded live writes.

## Editor workspace

Version 0.3 uses an Indigo-style consumer workspace instead of exposing only raw schema rows:

- Trainer form with synchronized Trainer name/ID edits.
- Party and 14-box Storage navigation with grouped Main, Stats, Moves, Met and OT/Misc forms.
- Verified GE-1.0.0 catalogs containing 118 Species DataAssets and 99 Move Blueprints.
- Pokémon preview cards, HP bar, IV/EV helpers, four move/PP rows and staged-change workflow.
- Bag editor for existing item names and quantities, searchable raw properties, backup restore,
  Pokédex/Progress browser and a legality report covering every verified numeric relationship.

## Editing status

- Complete and tested on real `PokemonSaveSlot`, `QuestSlot`, `GEBerrySlot`, and `GEOptions`
  saves: AES-256 wrapper, SHA-1 integrity, UE5.6 recursive complete-type property tags, discovery,
  diagnostics, export/import staging, backups, restore, CLI, and GUI.
- Story parser currently maps more than 22,000 records across Trainer, Party, 14 storage boxes,
  Daycare, Bag, Seen/Caught and progress fields without a parser error.
- Verified writes: numeric/float/bool fields, variable-length Trainer/Pokemon/item strings with
  parent-size propagation, synchronized trainer name/ID, and domain checks for Level, IV, EV total,
  Friendship, Ability Slot, HP/EXP and Bag quantity.
- Verified staged serializers now cover Species DataAssets, Nature/Gender/status/met enums, up to
  four Move Blueprint paths, Current/Max PP arrays, and the existing scalar/string fields.
- Read-only until struct insertion/removal is game-verified: adding/removing Pokémon or Bag rows,
  resizing Dex sets, and editing Quest flag arrays.

No user save, decrypted payload, encryption key, or backup is committed to source control.

## Development

```powershell
.\scripts\test.ps1
.\scripts\build.ps1
```

The GUI is built as `dist\GammaEmeraldSaveEditor\GammaEmeraldSaveEditor.exe` with its runtime
folder beside it. The CLI is built as the standalone `dist\gamma-save.exe`.

Project continuity files are maintained in `CURRENT_STATE.md`, `TASKS.md`, `WORKLOG.md`,
`SESSION_NOTES.md`, and `PROJECT_CHECKLIST.md`. See `AGENTS.md` for the mandatory workflow.
