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

Use `gamma-save saves` to identify available slots without recording machine-specific filenames.
If only the options slot exists, start or continue the game and make an in-game save before testing
gameplay fields.

For parser-valid saves that crash, enter New Game unexpectedly, show `Unknown` Pokemon, or lose move
buttons, see [the runtime diagnostics guide](docs/SAVE_RUNTIME_DIAGNOSTICS.md). The accompanying
`scripts\diagnose-live-save.ps1` command is read-only and reports live slots, backups and crash evidence.

For the difference between adding a Bag row and creating a real runtime item, including the verified
GE-1.0.0 asset counts and a safe custom-item test checklist, see
[the item extension guide](docs/ITEM_EXTENSION_GUIDE.md).
The deeper [Item Mod Wizard feasibility report](docs/ITEM_MOD_WIZARD_FEASIBILITY.md) compares the
Icarus workflow and records the completed Gamma cooked-asset proofs. The experimental
[Item Mod Builder guide](docs/ITEM_MOD_BUILDER.md) covers the v0.16.0 multi-archetype wizard,
Ball/media limitations, toolchain check, guarded install/uninstall and runtime test checklist.

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

Version 0.16.0 uses an Indigo-style consumer workspace instead of exposing raw schema rows:

- Trainer form with synchronized Trainer name/ID edits.
- One Pokémon tab combines six Party cards with a compact 5 × 6 current-Box grid. Dragging cards
  moves or swaps the complete serialized Pokémon between Party and all 14 storage boxes.
- Right-click an occupied Party or Storage card and choose `Clone (Copy)` to capture its complete
  record as an in-app clone preset; the same action also puts a readable Pokémon Showdown-style set
  on the Windows clipboard. Then right-click an empty destination and choose `Set`. `Set` is visibly
  disabled until a preset exists. Storage uses the exact selected slot; clicking any empty Party card
  automatically fills and highlights the nearest valid empty Party position because the save stores
  Party as a packed array. Every placed copy gets a fresh Pokémon ID plus 128-bit Unreal GUID.
  `Release (Delete)` asks for confirmation,
  restores a verified empty Box payload, and refuses to delete the final Party member. Copy itself
  does not dirty the save; Set and Release remain staged until `Save + Backup`.
- Party and Storage cards show compact Pokémon icons, while the selected record gets a large preview
  portrait. The Main panel also shows a responsive horizontal evolution-family chart that recomputes
  node and connector spacing as the editor window is resized.
- Main and Preview use exact mapped species types rather than the Species asset-folder category.
  Dual-type Pokémon receive two color-coded badges and a split-color Preview background; badge text
  automatically switches between black and white for readable contrast on every type color.
- Sprites are optional local runtime assets, not published source. Put icon sheets in
  `runtime_assets\pokemon_icons`, beside the packaged executable under
  `gamma_editor\assets\pokemon_icons`, or point `GAMMA_EMERALD_SPRITES_DIR` at a local directory.
  Missing art falls back to initials without changing the save.
- Selecting an empty Party or Storage card opens a Create Pokémon form. Creation activates the
  game's complete verified empty struct template, assigns a unique Pokémon ID and current Trainer
  ownership, and supports the same species/stats/IV/EV/move/PP fields as an occupied slot.
- Creation also replaces the empty template's 128-bit Unreal `UniqueID` and verifies that the new
  GUID occurs exactly once before staging, preventing the duplicate identity that GE rendered as
  `Unknown` and later crashed on during battle setup.
- v0.12.1 also emits canonical zero-length empty FString sub-paths inside every `FSoftObjectPath`.
  Older builds encoded the empty sub-path as a one-byte NUL string; it parsed successfully but Gamma
  could not resolve editor-written Species or Moves at runtime.
- Selecting a different Species for either creation or conversion loads a conservative complete
  Lv. 5 base profile: Species DataAsset, level/EXP, Nature/Gender, runtime-backed Ability/slot,
  calculated HP, zero IV/EV values, starting level-up moves with exact PP, status and met defaults.
  Existing records keep their collision-free identity and Trainer ownership fields.
- Verified GE-1.0.0 catalogs containing 118 Species DataAssets and 99 Move Blueprints.
- Species conversion/creation is currently runtime-backed for 106 species: writable Ability choices are filtered against
  the 52 concrete GE-1.0.0 runtime enum values (`(H)` marks Hidden Ability), and Nature labels show
  their raised/lowered stats. The remaining 12 catalog species whose imported mapping has no
  runtime-backed choice are blocked from creation/Ability writes instead of receiving a fabricated
  or sentinel value.
- Species, Nature, Ability, Held Item, Move and Bag Item dropdowns support case-insensitive live
  search while preserving exact catalog validation. Their custom popup keeps the text field active
  while typing, including after the arrow button opens the full list.
- The fifth `Item Mod Builder` tab exposes 41 selected templates across HP/status/PP healing,
  Revive, Vitamins, Rare Candy, evolution/utility, held items, Berries, TMs and Poké Balls. Dynamic
  fields include healing, multipliers, boosted type/stat, any verified shipped TM move, Ball enum and
  catch rate where the chosen cooked template serializes them. The installed custom item appears in
  its correct Bag pocket and custom held items/Berries appear in the Held Item selector. Unknown or
  hash-modified patch files are never overwritten; loaded Bag/Party/Storage references block patch
  replacement or uninstall.
- Custom Item IDs are generated from a persistent numeric `CSTM` namespace and shown as sequential
  tags such as `CSTM-000001`. Gamma's underlying `ItemID` is an `int32`, so letters cannot be stored
  in the game field itself. Vitamin templates expose EV gain choices based on divisors of 252 plus
  the shipped default 10; Gamma clamps Vitamin use to 100 EV in the selected stat and 510 total.
  Held Item, Berry and TM selections show an inline behavior summary. TM clones can point at any of
  Gamma's 99 existing moves, including moves outside its 26 shipped TM items, but cannot author or
  modify a move's power, type or effects.
- The Item Mod Builder can separately install editor-owned runtime Vitamin rules for GE-1.0.0.
  Options are a 100 or 252 per-stat cap, a 510 total cap or no total cap, and either custom CSTM
  Vitamins only or every Vitamin. The conservative default is 252/stat, 510 total, CSTM only.
  Installation uses a build-matched local UE4SS loader, refuses to merge with unknown UE4SS files,
  records hashes in an ownership manifest, and provides a guarded uninstall that restores vanilla
  100/stat and 510-total behavior. This runtime hook is independent from the custom-item `.pak`.
- Move choices are generated from the shipped GE-1.0.0 Species DataAssets for all 118 species. The
  Moves panel filters exact Level-up (capped at the edited level), TM, HM and Egg sources, shows the
  source beside every selected move, and rejects species/stage-incompatible or duplicate moves.
- The Moves panel reads Base PP for all 99 shipped Move Blueprints. `PP` is the current usable PP;
  `PP Up` is limited to the game's 0–3 range (or zero for one-PP moves), and serialized Max PP is
  calculated automatically with the game's 20%-per-use scaling instead of being freely editable.
- The lower Moves panel renders four live attack-type charts, one for each selected move slot. Every
  chart uses the move's verified catalog type and shows its multiplier against all 18 defending types;
  changing or clearing a move redraws the corresponding chart immediately.
- The Stats panel shows Base and calculated Final HP/Attack/Defense/Sp. Atk/Sp. Def/Speed live from
  Species, Level, Nature, IVs and EVs. Calculated Max HP synchronization is opt-in for existing
  Pokémon and enabled by default only while creating one.
- Stats also includes `Max all EVs (252)`, which sets all six EV fields to 252 and automatically
  enables the over-510 editor override. The lower panel renders a resize-aware Final Stats column
  chart and all 18 type matchups for both best same-type attacking coverage and incoming defense.
- Held Item choices are restricted to the Gamma items that carry hold/Fling semantics; Poké Balls
  and Key Items are excluded.
- Pokémon preview cards, HP bar, IV/EV helpers, optional EV-total limit override, four move/PP rows
  and staged-change workflow.
- The EV-total override disables the editor's 510-total validation while keeping each stat capped at
  252. The current Gamma build has passed a wild battle, post-battle EV gain and save/reload with an
  over-510 total; other game builds may behave differently.
- Bag pocket tabs for Items, Poké Balls, TMs, Berries and Key Items, with filtered add/edit/remove
  controls. Missing pockets and item rows are inserted through verified structured-array resizing.
  `Catalog Info` explains that the 86 writable entries are the concrete GE-1.0.0 asset pool, not the
  full franchise pool. Only 9 Balls have both `ItemData` and Ball Blueprints in this build; 8 additional
  enum-only Ball names and the asset-less `Max Revive` stay hidden to avoid runtime-invalid saves.
- Pokédex species lookup shows Gamma catalog identity, types, legal Abilities, height/weight,
  six base stats, all 18 incoming type multipliers, DataAsset and owned Party/Storage locations;
  it is independent from Seen/Caught save progress.
- Pokémon edits and Party/Storage moves use a one-pass property transaction. On the 22,000-property
  real story fixture, an edit measures about 0.8 s, Storage creation about 0.9 s, and drag/drop about
  1.0 s on the development machine (previous creation path was roughly 15–18 s).
- Timestamped backups remain automatic, and the toolbar exposes validated backup restore.

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
  four Move Blueprint paths, Current/Max PP arrays, complete Party/Storage Pokémon payload moves,
  verified empty-slot Pokémon creation, Bag pocket/item insertion/removal, and existing
  scalar/string fields.
- Read-only until independently game-verified: resizing Seen/Caught sets and editing Quest flag
  arrays. Newly created Pokémon still require a controlled live-game load/resave verification.

No user save, decrypted payload, encryption key, or backup is committed to source control.

## Development

```powershell
.\scripts\test.ps1
.\scripts\build.ps1
```

The GUI is built as `dist\GammaEmeraldSaveEditor\GammaEmeraldSaveEditor.exe` with its runtime
folder beside it. The CLI is built as the standalone `dist\gamma-save.exe`.
Every successful build also refreshes the stable launcher one directory above the repository as
`GammaEmeraldSaveEditor.cmd`. That launcher always opens the current `dist` GUI, so its path does
not change between releases. Repeat local builds preserve an existing ignored runtime key before
PyInstaller replaces `dist`, then restore it only to the new local build.

Project continuity files are maintained in `CURRENT_STATE.md`, `TASKS.md`, `WORKLOG.md`,
`SESSION_NOTES.md`, and `PROJECT_CHECKLIST.md`. See `AGENTS.md` for the mandatory workflow.
