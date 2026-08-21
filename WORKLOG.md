# Worklog

## 2026-08-21 — Repository audit and Gamma tool bootstrap

- Audited the user's existing `tool_editor` repository, including all Markdown continuity files,
  feature tabs, backup patterns, validation behavior and development workflow.
- Confirmed the old editor targets Pokemon Essentials Ruby Marshal `.rxdata`; its codec cannot be
  reused for Gamma Emerald's Unreal saves.
- Located Gamma Emerald `GE-1.0.0`, UE `5.6.1`, its encrypted PAK and local `.ged` save directory.
- Derived the deterministic slot filename contract; machine-specific identifiers and salts are no
  longer recorded in continuity files.
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
- The write service created a timestamped pre-edit backup, rejected stale/running game states, used
  temporary-file atomic replacement, and reloaded the final value as 3.
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
- Published a sanitized one-commit snapshot to remote branch `feat/story-save-schema` as `47eaa3a`.
  Its parent is the safe `.gitignore` initialization commit, so no earlier local key-bearing commit
  exists in public remote history. Opened draft PR `#1` against `main`.

## 2026-08-22 — Indigo-style consumer editor

- Audited the old Indigo editor workflow and mapped it to the fields actually present in Gamma's
  UE5.6 story save.
- Replaced the generic-first GUI with a save-editor workspace: Trainer, six Party slots, 14 storage
  boxes, Bag, Pokédex/Progress, Legality Check and Advanced tabs.
- Added grouped Pokemon forms for species, nickname, level/EXP/HP, nature/gender/ability, IVs, EVs,
  four moves and PP, friendship, held item, status, met data and OT identifiers.
- Derived tool-only manifests of 118 species and 99 move object paths from the local encrypted PAK.
  No PAK, sprite, game binary, save, backup, fixture or cryptographic key was copied into source.
- Added verified EnumProperty, SoftObjectProperty, integer-array and soft-object-array patching while
  preserving all unknown bytes and enclosing size fields.
- Added legality checks for catalog membership, levels, IV/EV bounds and totals, HP/friendship,
  PP alignment, duplicate Pokemon IDs and Bag quantities.
- Real-save in-memory verification changed Mudkip to Marshtomp, nature to Adamant, and expanded its
  move/PP arrays; encrypt/decrypt/reparse retained all 22,479 records. The live file was not written.
- A programmatic GUI interaction changed Party level in staged memory and confirmed the live-save
  hash remained unchanged. The real save currently produces zero legality findings.
- Automated tests increased to 23 passing tests. Packaged GUI and CLI passed smoke/integrity tests
  against the real story save, again with an unchanged live-save hash.
- Built local release `GammaEmeraldSaveEditor-0.3.0-windows.zip` (tool binaries only; no game).
  GUI SHA-256: `660F08218BC2C1C1F9F7AAFD45D23D072535FCFC6FC4E6B94C35DBE19636BEC8`.
  CLI SHA-256: `B771933BF0A1B8A231ABF9F95B023FC0C5249F184AF0DBCFB5645CC528593EF0`.
  ZIP SHA-256: `4AA0A5FD099BDFCE86A5677CA5ABDFFAF6ECA8052D1954A5D2A67431BAB9499F`.
- Published the sanitized v0.3 source as remote commit `ca26e62` and refreshed draft PR `#1`.
  GitHub's compare lists only the tool's source, tests, packaging and continuity documentation.

## 2026-08-22 — Bag and Pokémon workspace redesign

- User requested Bag pocket tabs, category-filtered item creation/editing, a unified Party/Storage
  workspace with drag/drop, optional EV-total override, removal of Legality/Advanced from primary
  navigation, and a species-information Pokédex.
- Verified that Bag pockets and rows are nested UE5 Array<Struct> payloads, Party is an Array<Struct>,
  and every Box has 30 fixed PokemonInstanceData structs compatible with Party element payloads.
- Added structured-array extraction/replacement with count, terminator, parent-size-chain and full
  reparse verification. Added fixed-struct payload replacement for Box slots.
- Added five in-game Bag pockets (Items, Poké Balls, TMs, Berries, Key Items), category-filtered
  item catalogs, Add Item dialog, edit and remove. Missing pockets are inserted in canonical order.
- Added full Pokémon move/swap operations between Party and any current-Box slot. The complete
  serialized payload is transferred, preserving species, stats, moves, PP, identity, OT and met data.
- Replaced the 30-row Storage list with a 5 × 6 card grid, combined it with six Party cards, and
  wired mouse drag/drop to the verified payload operations.
- Added an optional toggle allowing total EV above 510 while retaining the per-stat 0–252 limit.
- Replaced Seen/Caught progress display with a searchable 118-species Gamma catalog showing Hoenn
  number, primary type, DataAsset path and owned Party/Storage locations. Legality and Advanced were
  removed from primary navigation; backup restore moved to a toolbar dialog.
- Real story payload tests added/removed Super Potion, inserted the absent TMs pocket with TM01,
  moved a complete Pokemon payload Storage → Party, allowed 1,512 total EV, then passed GVAS reparse
  and GES1 encrypt/decrypt. No live file was written.
- Automated suite now passes 24 tests. Source GUI assertions verified 4 main tabs, 5 Bag pocket tabs,
  6 Party cards and 30 Storage cards. Packaged GUI/CLI read-only smoke tests passed while the game
  was running, so structural live-game verification remains pending.
- Built local v0.4.0 release from the final sanitized source. GUI SHA-256:
  `710CE6742B3B2AEA25FC811EEEEBA2A399513183EF5EA454CC7B380C696E0196`.
  CLI SHA-256: `85E3E2B5F9430BBD73CF13006DABF4E8E68412268B734E841920F9D44DA1CD48`.
  ZIP SHA-256: `1AE4D410AA01F9363DFBA8DA30E9B20BEC4A49E9CC90B940509CEFE47FB2690C`.
- Published sanitized v0.4 source as remote commit `3e8c2b7` and refreshed draft PR `#1`.

## 2026-08-22 — Empty-slot Pokémon creation

- User reported that leaving every empty Pokémon slot read-only defeated the purpose of the editor
  and requested functional editing instead of a locked form.
- Confirmed every one of the 420 fixed Box slots contains a complete 49-field
  `PokemonInstanceData` template. Seeding its verified `SpeciesData` SoftObject makes the supported
  child fields editable without inventing or regenerating an unknown struct layout.
- Added Create Pokemon mode for empty Storage cards and empty Party cards. Storage activates the
  selected fixed struct in place; Party appends the same verified template to its structured array.
- Creation assigns a catalog Species DataAsset, collision-free positive Pokemon ID, current Trainer
  name/ID ownership and conservative defaults, then applies the regular validated level, HP,
  IV/EV, nature, gender, held-item, met, move and PP controls.
- Empty cards no longer begin drag operations. Occupied cards retain complete-payload drag/drop,
  while raw empty-slot fields stay protected from arbitrary generic-property writes.
- Added batched fixed-width scalar writes with one final structural reparse, reducing creation time
  while retaining domain validation and unknown-byte preservation.
- Automated suite passes 26 tests. A source-GUI interaction created Poochyena in an empty Box slot;
  separate real-story in-memory tests created Ralts in Party and passed full GVAS reparse and GES1
  encrypt/decrypt semantic round-trip. No live save was written.
- Built and smoke-tested tool-only v0.5.0. Packaged GUI stayed running normally and packaged CLI
  passed real-story GES1/AES/SHA-1/GVAS validation.
- v0.5.0 GUI SHA-256: `DD9EC1C34F7024D33B7587B4C39E33BB04E248FE3C3E1926C97336BBCAD4DF2C`.
- v0.5.0 CLI SHA-256: `536BFD90CCE0FEB5D2955076276915C97F4B48D64B113E79B2A297FC5026DC61`.
- v0.5.0 ZIP SHA-256: `8ABF9B4A006F83F9A59C0E270943F254260398A147FD6501863AE5E5E1AAE339`.
- Published sanitized v0.5 source as remote commit `ee750bb` and refreshed draft PR `#1`. The
  one-commit remote compare lists exactly 13 source, test and continuity files; no build artifact,
  game file, save, backup, private fixture or key was uploaded.
