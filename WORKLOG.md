# Worklog

## 2026-08-21 — Repository audit and Gamma tool bootstrap

- Audited the user's existing `tool_editor` repository, including all Markdown continuity files,
  feature tabs, backup patterns, validation behavior and development workflow.
- Confirmed the old editor targets Pokemon Essentials Ruby Marshal `.rxdata`; its codec cannot be
  reused for Gamma Emerald's Unreal saves.
- Located Gamma Emerald `GE-1.0.0`, UE `5.6.1`, its encrypted PAK and local `.ged` save directory.
- Derived known slot filename contract: MD5 of `slot|user_index|ge-vault-2f81c4`.
- Reverse engineered the outer save container from the executable and real options save:
  `GES1`, version 1, plaintext length, SHA-1, AES-256-ECB, zero padding, slot string, GVAS length.
- Verified the codec against the real `GEOptions` save. Discovered the outer slot string differs
  from standard FString by omitting its trailing NUL and corrected the implementation.
- Parsed the inner UE5.6 header: GVAS v3, UE4 package 522, UE5 package 1017, engine 5.6.1,
  86 custom versions, class `/Script/PokemonEmerald.GE_SettingsSave`.
- Implemented standalone package, safe save service, CLI and Tk GUI.
- Added repository rules, state/task/session tracking and checklist.
- Added 11 automated tests covering container integrity, known slot names, GVAS header/tag parsing,
  scalar edits, game-running/stale-source guards, backup and restore.
- Built the GUI as an `onedir` Windows application to avoid Tcl/Tk temp-directory ACL failures.
  Its packaged smoke test exits successfully. Built the CLI as a standalone executable and used it
  to validate the real options save.
- No live save was written or copied into the repository.
- Initialized a clean local `main` repository and committed the implementation as `39bbe27`.
- Connected the user's GitHub account and confirmed admin/push access to the existing
  `ladori08/tool_editor` repository. The connector exposes repository content/ref operations but no
  repository-creation operation; the separate private repository therefore awaits one user-side
  creation action.

### Release artifact hashes

- GUI executable SHA-256: `50F37FD99901747FE93FB01C11BC06F7AA12CCD401BF44A3836CDA2BBF5041A3`
- CLI executable SHA-256: `B66FB83D6ACDDB9E4C6CEBA43949CB54FDB2570ECC3F59A237AA7BC16CDFB231`
- Windows release ZIP SHA-256: `EF79DF32B3ABA3114390E477E1E5532BE97B42E21BA19FD16F01119A0235CC4F`

### Evidence commands

```powershell
python -B -m gamma_editor.cli saves
python -B -m gamma_editor.cli validate <GEOptions.dat>
python -B -m gamma_editor.cli summary <GEOptions.dat>
```

The real fixture passed container integrity and semantic encode/decode round-trip.

## 2026-08-21 — Story schema and domain editor

- User created `ladori08/gamma_emerald_save_editor` and produced an in-game story save.
- Confirmed four guarded slots: `PokemonSaveSlot`, `QuestSlot`, `GEBerrySlot`, and `GEOptions`.
- Validated the 1.4 MB story container and exported only ignored private GVAS snapshots for analysis.
- Reverse engineered UE5.6 recursive complete-type property tags, native-struct flags, fixed-array
  indices, tag-encoded booleans, arrays, sets and nested struct lists.
- Parsed more than 22,000 story records without error: Party, 14 boxes × 30 slots, Daycare, Bag,
  Seen/Caught, map/time/player data and progress values.
- Added decoded arrays for names, integer sets, PP and soft-object move paths; decoded DateTime,
  Vector, Guid and SoftObjectPath structs read-only.
- Added Trainer, Party, Storage, Bag and Progress GUI views plus CLI property-path inspection.
- Added Level/IV/EV/Friendship/AbilitySlot/HP/EXP/quantity validation and synchronized Trainer
  name/ID repair for matching owned Pokemon.
- Implemented verified variable-length FString writes with automatic size propagation through every
  enclosing struct/array.
- In-memory real-story tests changed Level, IV, shiny, quantity, PlayerName and Nickname, then
  re-encrypted/decrypted and reparsed the same record count with no structural error.
- Automated suite increased to 17 passing tests. No live save was written; the game remained open.
- Built version 0.2.0; packaged GUI opened and parsed the live story slot in its smoke test, and the
  packaged CLI validated the same encrypted story save.
- 0.2.0 GUI SHA-256: `93F2CFA4B000D0323CDD3738CC6D140539DFB30DBA084A6FF398C8A7FF65BE9F`
- 0.2.0 CLI SHA-256: `F1684D241F1E4613889188A637DD4A1839F6A7983079A8C5EBB23999CDFDDBE9`
- 0.2.0 ZIP SHA-256: `8B42D819A15ED18B09A34AB1B74546FCBB8DF43EA608B7F6FA333D092232730C`
- GitHub repository access is verified, but its visibility is public. Push is paused to avoid
  publishing the game-format implementation before the user confirms visibility.
- Committed the story-schema implementation on `feat/story-save-schema` as `bf3f172` and configured
  `origin` for `https://github.com/ladori08/gamma_emerald_save_editor.git`.

## 2026-08-21 — First controlled live-save write

- The user explicitly approved public publication of `ladori08/gamma_emerald_save_editor` and
  authorized a controlled live-save test after closing the game.
- Reconfirmed that no Pokemon Emerald process was running, all 17 tests passed, and the current
  story save passed packaged CLI GES1/AES/SHA-1/GVAS/round-trip validation.
- Located the single Potion entry at `PlayerItems[0].Items[0].Quantity` and changed its quantity
  from 2 to 3 through the same domain validation and write service used by the editor.
- The write service created timestamped backup
  `859c7fd1524eb8d6726f1233820531b8.dat.preedit-20260821-233906-624708.bak`, rejected stale/running
  game states, used temporary-file atomic replacement, and reloaded the final value as 3.
- The written live save passed the packaged CLI validation again. Pokemon Gamma Emerald then
  launched successfully; visual load and in-game resave confirmation remain pending.
- Direct Git CLI publication could not authenticate non-interactively. The authenticated GitHub
  connector initialized the public repository with only `.gitignore`, then rejected `codec.py`
  because it contains the real save-encryption key. No source branch, private fixture, live save or
  backup was published. Publication is paused pending a private repository or external-key design.
- The user visually confirmed Potion x3 in the running game, saved normally and closed the game.
  The game-produced save then passed packaged CLI integrity/round-trip validation, parsed 22,479
  records, and retained Potion quantity 3. All 17 automated tests still passed.
- After being explicitly informed that public source would expose the recovered save-encryption
  key, the user instructed work to continue. GitHub still treated the disclosure as non-overridable,
  so the codec was refactored to load the key from an environment variable or ignored local file.
- Added missing-key and local-key-file tests. The suite now passes 19 tests; a real story save also
  validated using the local-only key held in memory, and a tracked-file scan found no key literal.
  Private saves, backups, fixtures and key material remain excluded from publication.
