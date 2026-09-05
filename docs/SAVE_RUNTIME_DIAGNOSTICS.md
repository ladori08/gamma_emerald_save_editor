# Gamma Emerald Save Runtime Diagnostics

This guide explains how to diagnose a save that passes the editor's checks but behaves incorrectly
inside Pokemon Gamma Emerald. It is based on real failures found while developing this editor:

- a structurally valid save causing an access-violation Fatal Error;
- an old Story slot loading together with a reset Quest slot, producing a New Game intro with an old Party;
- editor-created Pokemon appearing as `Unknown`;
- move names parsing correctly in the editor while every battle move button is blank;
- two byte encodings decoding to the same Python value but behaving differently in Unreal Engine.

The central lesson is simple: **container-valid, parser-valid, and runtime-valid are three different
claims**. Never treat a successful round trip as proof that the game accepts the data.

## 1. Safety rules before diagnosis

1. Do not save repeatedly after the first bad symptom. Gamma may auto-save during map or quest events.
2. Close both the game and editor before restoring or replacing anything.
3. Preserve all live slots together, not only `PokemonSaveSlot`.
4. Keep automatic `.preedit-*.bak` files. Never rename or edit the only known-good backup.
5. Make one controlled change per test. Multiple simultaneous edits destroy the useful A/B evidence.
6. Never publish `.dat`, `.bak`, decrypted `.gvas`, `save_key.hex`, or screenshots containing secrets.
7. Do not repair an unknown structure by guessing fields. Roll back and collect better evidence.

The live directory is:

```text
%LOCALAPPDATA%\PokemonEmerald\Saved\.ged
```

Gamma uses multiple cooperating slots:

| Slot | Main responsibility | Typical failure if stale/reset |
|---|---|---|
| `PokemonSaveSlot` | Trainer, Party, Storage, Bag, world position and progress fields | Missing Party, invalid Pokemon, wrong position |
| `QuestSlot` | Story/quest flags and visited locations | New Game intro mixed with an old Party |
| `GEBerrySlot` | Berry state | Berry/world-state inconsistencies |
| `GEOptions` | Settings | Usually harmless, but useful for identifying a newly generated save set |

Treat the four files as one generation when backing up or recovering them.

## 2. Run the read-only diagnostic

From the project directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnose-live-save.ps1
```

Optional arguments:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\diagnose-live-save.ps1 `
  -RecentBackups 12 `
  -RecentCrashes 5
```

The script only reads files. It reports:

- whether the game/editor is still running;
- slot name, class, size, timestamp, property count and SHA-256 for every live slot;
- recent automatic backups;
- recent crash address and stack hash;
- the tail of `GammaEmerald-Diagnostics.log`;
- warnings about structural failures or mixed slot timestamps.

It never creates, edits, restores, moves, or deletes a save.

## 3. Manual CLI checks

Use the packaged CLI so it can read the ignored key beside the executable:

```powershell
.\dist\gamma-save.exe saves
```

Do not memorize or publish hashed filenames. Let the CLI identify slot names and classes.

Validate one file:

```powershell
.\dist\gamma-save.exe validate "PATH_FROM_SAVES_OUTPUT"
.\dist\gamma-save.exe summary "PATH_FROM_SAVES_OUTPUT"
```

Inspect selected properties:

```powershell
.\dist\gamma-save.exe properties "PATH_TO_STORY_SLOT" --filter Party
.\dist\gamma-save.exe properties "PATH_TO_STORY_SLOT" --filter Moves
.\dist\gamma-save.exe properties "PATH_TO_STORY_SLOT" --filter SpeciesData
```

Record these facts for the live file and candidate backup:

- byte size;
- modification time with seconds;
- SHA-256;
- GVAS size;
- parsed property count;
- parser note/error;
- Party species, moves and PP;
- the exact point where the game fails.

SHA-256 can be calculated without opening the file:

```powershell
Get-FileHash -LiteralPath "PATH_TO_SAVE" -Algorithm SHA256
```

## 4. Understand the validation layers

### Layer A: GES1 container

Checks magic, version, bounds, AES decryption and SHA-1. A failure here means truncation, the wrong
key, a broken wrapper or corruption. Do not attempt semantic editing.

### Layer B: GVAS parser

Checks the UE header and tagged-property boundaries. A successful parse proves that byte lengths and
property framing are internally consistent. It does not prove the game can resolve referenced assets.

### Layer C: editor legality

Checks known rules such as level, IV/EV ranges, PP arrays, catalog paths, Ability enums and duplicate
IDs. Unknown fields remain outside this proof.

### Layer D: Unreal runtime

The real acceptance test is:

1. game loads the save;
2. Party names and portraits resolve;
3. menus render;
4. a battle starts and commands work;
5. the game saves normally;
6. the game exits and reloads the new save.

Only after all six steps may a feature be called runtime-verified.

## 5. Symptom-to-cause checklist

| Symptom | First checks | Likely class of problem |
|---|---|---|
| Fatal Error immediately after Continue | newest crash context, all four slot timestamps, current vs backup property count | truncated/empty slot, cross-slot mismatch, invalid runtime object |
| New Game intro but an old Party appears | Story and Quest timestamps/content | Story restored alone while Quest remained reset |
| Pokemon displays as `Unknown` | `SpeciesData`, Ability, Ability Slot, UniqueID, exact soft-object bytes | unresolved asset path or incomplete created record |
| Battle opens but all moves are blank | Moves path/object/subpath bytes plus CurrentPP/MaxPP lengths | runtime cannot resolve editor-written move assets |
| CLI says OK but game fails | compare game-authored and editor-authored bytes | semantic/runtime format not modeled by parser |
| Party count changes only on screen | check disk after closing game | scripted/in-memory starter or battle state not yet persisted |

## 6. Detect a Story/Quest mismatch

A strong mismatch signature is:

- Story contains Trainer name, Party, Bag and an established play time;
- Quest contains only early intro flags;
- the game asks for name/starter again;
- choosing the scripted starter temporarily adds another Party indicator.

Do not keep playing. The game may merge new quest state into old story data and auto-save it.

Recovery procedure:

1. close the game;
2. preserve current Story and Quest separately;
3. find a Story and Quest pair representing compatible progression;
4. validate both candidates before writing;
5. replace them as one coordinated operation with rollback protection;
6. leave Berry/Options alone only after confirming they match the known-good generation;
7. test Continue, Party, battle, normal save and reload.

Restoring only Story fixed the container but caused the exact mixed-intro failure in this project.

## 7. Use a controlled game/editor A/B test

This is the most useful method for a parser-valid/runtime-invalid field.

1. Start from a known-good save and preserve all slots.
2. Make one change using Gamma itself, such as replacing one move.
3. Save normally and close the game.
4. Record the file's timestamp, size and hash. This is the **game-authored** sample.
5. Open the editor and make one closely related change, such as adding one move.
6. Use `Save + Backup`. The automatic pre-edit backup now preserves the game-authored sample.
7. Do not make any other edit.
8. Compare the pre-edit backup against the editor-authored live file.
9. Compare decoded values first, then raw property payloads if the values look identical.

This procedure found the move/species bug because the logical values were equal while one byte-level
convention differed.

## 8. The SoftObjectPath bug found here

Gamma stores Species and Moves as Unreal soft-object paths. Each value contains three FStrings:

1. asset path;
2. object/class name;
3. optional sub-path.

For an empty sub-path, Gamma writes the canonical empty FString:

```text
00 00 00 00
```

The old editor wrote:

```text
01 00 00 00 00
```

Both decoded to `""`, so parser comparisons, GVAS reparsing and encrypted round trips all passed.
Gamma nevertheless failed to resolve the noncanonical soft reference.

Observed correlation:

| Data | Empty sub-path length | Runtime result |
|---|---:|---|
| Native Mudkip `SpeciesData` | 0 | Mudkip rendered correctly |
| Editor-created Torchic/Treecko `SpeciesData` | 1 | Displayed as `Unknown` |
| Moves written by Gamma | 0 | Move buttons rendered |
| Moves rewritten by old editor | 1 | All move buttons blank |

The v0.12.1 fix makes `_encode_fstring("")` emit a zero int32. Regression tests inspect the serialized
length itself rather than merely checking the decoded value.

## 9. Inspect crash evidence

Crash reports are normally under:

```text
%LOCALAPPDATA%\PokemonEmerald\Saved\Crashes
```

Useful fields in `CrashContext.runtime-xml`:

- `ErrorMessage`;
- `SecondsSinceStart`;
- `PCallStackHash`;
- `EngineVersion`;
- `GameStateName`.

Different addresses or stack hashes usually mean different failure paths. A Shipping build may have
no symbolic call stack, so correlate the crash time with slot writes and the exact player action.
Do not claim a precise C++ cause from an unsymbolized access violation alone.

## 10. Decide whether to repair or roll back

Use targeted repair only when all of these are true:

- there is a fresh backup;
- the game and editor are closed;
- the exact bytes/fields are known;
- a memory-only repair parses and round-trips;
- decoded values outside the intended fields are unchanged;
- post-write validation is available;
- a safe rollback remains available.

Roll back when any of these is true:

- the required field is guessed;
- multiple slot generations are mixed and no matching set exists;
- the game rewrites the save into an empty/default object;
- created records remain `Unknown` after known fixes;
- the candidate loses unknown bytes or parsed records unexpectedly.

For this project, the native Mudkip-only backup remains the final fallback because it has zero
legality findings and was captured before editor-created Pokemon existed.

## 11. Runtime verification checklist

After a repair or editor release:

- [ ] Continue enters the saved world, not the intro.
- [ ] Trainer name and location are correct.
- [ ] Party count is correct.
- [ ] Every species name and portrait resolves.
- [ ] Every move button has a name and usable PP.
- [ ] A normal wild battle completes.
- [ ] Party/menu navigation works afterward.
- [ ] Gamma saves normally.
- [ ] The saved file validates again.
- [ ] Relaunch + Continue works.
- [ ] Reopen in the editor and confirm values survived the game resave.

If any item fails, stop, note the exact time and action, and run the read-only diagnostic before
opening either program again.

## 12. Minimal incident report template

```text
Time:
Editor version:
Last action in editor:
Last action in game:
Did Gamma auto-save or manually save?:
Failure stage: boot / Continue / menu / battle / save / reload
Visible symptom:
Live slot timestamps:
CLI validate result:
Story property count:
Newest pre-edit backup timestamp:
Crash address and stack hash:
Screenshots attached?:
```

This information is usually enough to reproduce the failure without sharing private save contents.
