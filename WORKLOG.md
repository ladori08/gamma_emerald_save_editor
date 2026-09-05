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

## 2026-08-22 — Species-aware editor and performance pass

- User requested Species-filtered Ability lists with Hidden Ability labels, annotated Nature
  effects, holdable-only Held Items, a detailed competitive-information Pokédex and substantially
  faster Pokémon create/edit/move interactions.
- Generated a source-only metadata module for 116 standard species already present in Gamma's
  118-asset catalog. Gecqua and MissingNo. remain explicitly unmapped; no game asset was copied.
- Ability controls now list only the selected Species' legal options, append `(H)` to Hidden
  Abilities and automatically synchronize Ability Slot. Domain validation rejects mismatched
  Ability/slot combinations.
- Nature labels now include exact effects such as `Adamant (+Atk / -SpAtk)`. Held Item excludes
  Poké Balls and Key Items and retains the Gamma item groups carrying hold/Fling semantics.
- Rebuilt Pokédex details with types, legal Abilities, height/weight, six base-stat bars, total and
  all 18 incoming type multipliers. Owned-location lookup was reduced to one property pass.
- Added a one-pass serializer that batches fixed/variable scalars, SoftObject paths, Move/PP arrays
  and complete Party/Storage payload replacements while updating every parent-size field once and
  structurally reparsing once.
- Real-story in-memory timings: edit 0.78 s, Storage create 0.94 s, Party create 2.49 s and
  Storage-to-Party move 1.03 s. All results reparsed with no property error; no live save was written.
- Automated suite passes 28 tests. Final packaged CLI validated the live story container with
  22,482 parsed properties and no parser error; packaged GUI smoke test passed.
- Built tool-only v0.6.0. GUI SHA-256:
  `EFD35AE6751765C62BB314E6EE766248F92E5FE3A16F8A1C497D3F2A36DC9DAF`.
- v0.6.0 CLI SHA-256: `0904B532CBD85CFEFEC37B87E78E2B487AEC5652B941EEAF6FEC9662BA4FD576`.
- Initial key-free v0.6.0 ZIP SHA-256:
  `9A74BEB1CA557163F2FC77B9D5B6BFEC20A00D0E1475CB98648290A17E291AC5`.
- Published sanitized v0.6 source as remote commit `814bc53b4dac46a9f8be36ea5f8aa7d536b5b451`
  and refreshed draft PR `#1`. The fast-forward compare contains exactly 16 source, test and
  continuity files; no build artifact, game, save, backup, private fixture or key was uploaded.
- User reported that the local GUI could not open a save because the runtime key had been omitted
  from the release folder. Copied the ignored local key beside the GUI and CLI, refreshed the local
  ZIP, and verified the release CLI against the real story save. No key was added to Git/GitHub.
- Runnable local v0.6.0 ZIP SHA-256:
  `A6F6814A488431F5C149E50BD5B7E59E8E45BED577A698FF563EA454D2A6ADCF`.

## 2026-08-22 — Searchable catalogs and calculated stats

- User requested case-insensitive live search in large Species/Item dropdowns, visible final stats
  driven by Species/Level/Nature/IV/EV, and the missing Max Revive item for v0.7.
- Added one reusable searchable combobox to Species, Nature, Gender, Ability, Held Item, status,
  met type, Move and Bag Item controls. Typed values still require an exact catalog match on apply.
- Added standard integer stat formulas, including Nature multipliers and Shedinja's fixed 1 HP.
  The Stats panel now shows Base/IV/EV/Final columns and updates live. Existing Pokémon do not have
  stored Max HP changed implicitly; synchronization is opt-in, while creation enables it by default.
- Added Max Revive to the Items pocket and holdable catalog. A real-story Revive-to-Max-Revive edit
  reparsed in memory successfully; the live save was not written.
- The user authorized stopping `GammaEmeraldSaveEditor` for testing. PID 14816 was stopped before
  the build; the Pokémon game process was not touched.
- Automated tests pass: 32. Packaged CLI passed real-story GES1/AES/SHA-1/GVAS round-trip validation,
  and the packaged GUI remained healthy during an 8-second hidden smoke test.
- A source-GUI real-story assertion loaded Mudkip, populated all six calculated Final stats and
  confirmed the searchable Held Item catalog contains Max Revive.
- Built runnable local v0.7.0. GUI SHA-256:
  `10F778584B1289FEC096131F41274AE335CCB1FE386676A980491781EC9978A5`.
- v0.7.0 CLI SHA-256: `BC8AAEDE87F03B828DA40DCD7904A77725838C576F4E7FE1484D86B71113CDBA`.
- Runnable local v0.7.0 ZIP SHA-256:
  `B9F7AA832E23507C65E8F94B76605157CD06BEF370C981A6C629942B328ECAF3`.
- Published sanitized v0.7 source as remote commit `ae1814e20daba03ef69dc1929cad410634f1a291`
  and refreshed draft PR `#1`. GitHub compare reports one fast-forward commit with exactly 11
  expected source/test/documentation files; no game, save, backup, key or build artifact appears.

## 2026-08-22 — Stable root launcher

- User requested one permanent file in the game root that opens the editor and remains current for
  every future build.
- Added the source-controlled `packaging/root_launcher.cmd` template. Every successful build copies
  it to workspace-root `GammaEmeraldSaveEditor.cmd`, which always launches the current `dist` GUI.
- Build now captures an existing ignored local runtime key before PyInstaller replaces `dist`, then
  restores it beside the new GUI/CLI. The key is never written into tracked source or build output
  logs.
- Rebuilt without supplying the key environment variable: 32 tests passed, the prior key hash was
  preserved exactly, and the root launcher was refreshed automatically.
- Root-launcher smoke test opened the newly built GUI as PID 27828; only that editor process was
  stopped afterward. No game process or live save was touched.
- Published only the reproducible launcher template and build logic as remote commit
  `9a2c9c77a7f977ca4b313ecc3afdd7a237015a7f`. GitHub compare confirms exactly two source files;
  the generated root launcher, runtime key and binaries remain local-only.

## 2026-08-22 — v0.7.1 Stats Apply enum hotfix

- User reported that applying Stats changes failed with `Gender is not in the verified GE-1.0.0
  enum catalog` while the form visibly contained `Male`.
- Root cause: v0.7 live-search validation canonicalized Gender/Status/Met display text but skipped
  the later generic enum-prefix branch. The serializer received `Male` instead of the unchanged
  stored `EPokemonGender::Male` and correctly rejected it.
- Added shared enum normalization for Gender, Status and Met Type plus regression coverage for all
  three required prefixes. Automated suite now passes 33 tests.
- A hidden source-GUI test loaded the real story, set all six EVs to 252, enabled the override and
  successfully staged/reparsed total EV 1,512 with valid Gender/Status enums. Live save unchanged.
- Local PAK/executable string searches and public searches found no Gamma-specific evidence proving
  whether runtime load/stat recalculation clamps totals above 510. UI now labels this override as
  editor-only and explicitly reports game-side behavior as unverified.
- Built and smoke-tested v0.7.1; the stable root launcher refreshed and opened the hotfix GUI.
- v0.7.1 GUI SHA-256: `641AA15CD454145921BDFEAB0EC27D50CCACFC3BDDDB6A38CB5040D3854D9058`.
- v0.7.1 CLI SHA-256: `BD3983C1659C02A65685A77CA09B1FCCC9B273FBE243D784967FAD905F066D1A`.
- Runnable local v0.7.1 ZIP SHA-256:
  `55167BDAF7F7CDB987719FFD5CFFBC87F0C64E36E05B0EBD17FF6A3FF9E074A5`.
- Published the source-only v0.7.1 hotfix as remote commit
  `da585a80ac48d6d3e80dd56130d302c6d5bf98ec`. Its fast-forward compare contains exactly the GUI,
  regression test and two version files; no generated build, game, save, backup or key was uploaded.
- User subsequently reported that Gamma accepted the over-510 EV edit and completed game save/load
  activity without an immediate reaction or crash. This is preliminary runtime validation; battle,
  level-up and PC deposit/withdraw remain useful recalculation checks. The user's prior Indigo
  experience crashed on entering battle with similarly excessive EVs, so the distinction is logged.
- User completed the decisive follow-up: defeated a wild Pokémon using the over-cap Pokémon, passed
  post-battle EV award/stat recalculation, saved normally and rechecked the data without a crash or
  clamp. Marked over-510 EV runtime support verified for the current Gamma build. Indigo required a
  separate game-logic patch at this exact trigger; Gamma currently does not.

## 2026-08-22 — v0.7.2 searchable-dropdown focus fix

- User demonstrated that the native Windows ttk combobox popdown stole keyboard focus after the
  first typed character. Opening the list with its arrow also required clicking back into the text
  field, which closed the list.
- Replaced the shared searchable combobox with an Entry plus owned popup Listbox. The popup keeps
  focus in the Entry, supports continuous filtering, arrow-open-then-type, keyboard navigation,
  Enter selection, mouse selection, Escape and outside-click dismissal.
- Added the multi-key and arrow-open behaviors to the executable `--smoke-test`. Source full-app,
  packaged GUI and packaged release smoke tests all passed with the real save loaded read-only.
- Automated suite passes 33 tests. Packaged CLI passed GES1/AES/SHA-1/GVAS round-trip validation;
  the live save was not modified.
- Hardened `scripts/build.ps1` after a permission-denied temp run exposed that PowerShell continued
  after a failing native command. Builds now use project-local test temp storage and stop on failed
  tests or either failed PyInstaller command.
- The stable root launcher opened the new build and only that editor process was stopped afterward.
- v0.7.2 GUI SHA-256: `C8B862223D7A79EEC01578905D96DE2D243DBC291ED2ABFAEEE1B219F2823C09`.
- v0.7.2 CLI SHA-256: `2309C3DE589BAAA1A5370F359665B539D996FC09B947053413A7E33F60C55866`.
- Runnable local v0.7.2 ZIP SHA-256:
  `82F41099F7D33187C09EBED2DC9C97CD3398CDC079C0577E3EA39689AFA59FDA`.
- Published source/config-only v0.7.2 as remote commit
  `a5abca18f74fe38f536147a226665ee841f3a1c5` and refreshed draft PR `#1`. The fast-forward compare
  contains exactly `.gitignore`, two version files, the build script and GUI source; no generated
  build, game, save, backup, runtime key or release archive was uploaded.

## 2026-08-22 — v0.8.0 exact Species move learnsets

- User requested that move choices during both creation and editing match the exact species,
  evolution stage and learn source, including Level-up, TM, HM and Egg compatibility.
- Parsed the unversioned `PokemonLevelUpMoves`, `LearnableTMMoves` and `EggMoves` fields from all 118
  shipped GE-1.0.0 Species DataAssets, then generated a compact source-only learnset module. The
  extraction workspace, game assets, encryption key and third-party analysis binaries remain local
  and ignored; none are copied into source or the distributable archive.
- The Moves panel now offers All legal, Level-up at the edited level, TM, HM and Egg filters. Each
  selected move shows its exact learn source. Changing species or level refreshes the choices live,
  so Torchic, Combusken and Blaziken retain their distinct stage-specific data.
- GUI and domain validation reject duplicate moves and species/level-incompatible edits. Existing
  unsupported save data may remain untouched during unrelated edits, while any species, level or
  move change is checked strictly against the generated GE-1.0.0 learnset.
- The shipped build exposes Fly and Surf as HM battle moves. Cut, Strength and Rock Smash are
  overworld HM features in this build rather than move Blueprint/save choices, so the editor does
  not fabricate entries for them.
- Automated suite passes 38 tests. Packaged GUI smoke verified Torchic level gating and Wingull's
  Fly HM list; packaged CLI passed real-story GES1/AES/SHA-1/GVAS read-only round-trip validation.
- Built key-free local v0.8.0 release. GUI SHA-256:
  `7A77B6BDA52BCB18DBA8E81330E09505ACED583F02F03A43CED4063F18455D9D`.
- v0.8.0 CLI SHA-256: `657CCC10B611394EBCEF234B4D5FF555774E77F01FC8AE0FA86C363DE72DFDAB`.
- Key-free v0.8.0 ZIP SHA-256:
  `410219E0648A3231607763421284424A6F39EBC10C5119DC0E598A2A8A7DBCEB`.

## 2026-08-22 — v0.8.1 Base PP and PP Up editor

- Replaced the freely editable `Current PP`/`Max PP` pair with current `PP` plus `PP Up` count.
  Selecting a move loads its verified Base PP; applying 0–3 PP Ups derives Max PP with the game's
  20%-of-Base-PP-per-use formula. One-PP moves such as Struggle disable PP Up.
- Parsed all 99 shipped GE-1.0.0 Move Blueprint defaults into a compact source-only Base PP table.
  Eighteen inherited Blueprint values are explicitly mapped by the reproducible generator. Game
  assets, extraction output and cryptographic material remain ignored and outside publication.
- The GUI preserves depleted current PP while changing PP Up, clamps it to the new maximum, and
  initializes a newly selected move at full Base PP. Existing valid Max PP values are converted
  back to PP Up counts; invalid old values are normalized on the next staged Apply.
- Added domain validation so Current PP cannot exceed derived Max PP and Max PP must correspond to
  exactly one valid PP Up level. Legality reporting now identifies impossible move-specific Max PP.
- Hardened Windows builds with a fresh pytest temp directory per run, preventing stale ownership
  from another security context from breaking a later build.
- Automated suite passes 41 tests. Packaged CLI passed real-story GES1/AES/SHA-1/GVAS read-only
  validation. GUI/CLI builds completed and the stable workspace-root launcher was refreshed; the
  current automation context could not execute the final GUI smoke, though its PP assertions are
  included in `--smoke-test`.
- v0.8.1 GUI SHA-256: `B874C5BB1B20B487FB63E2D6671D738F1D96C70CD81A9645E508FE0F63A2732E`.
- v0.8.1 CLI SHA-256: `097A78F8C1FA63E43D40E6997B43A475090DB979C9915479010F668927DEFF57`.
- Key-free v0.8.1 portable ZIP SHA-256:
  `B6090BAAA5FCB20884B39C8E9291493D7DA649EC30E9DFCF51F9B653E02663F4`.
- Committed local v0.8.1 source as `9821150` over the local v0.8.0 learnset commit `9cf5035`.
  Audited the complete remote compare as exactly 20 source/test/documentation files with no game,
  save, key, executable or release artifact. GitHub write access then stopped at the connector's
  Codex usage limit, so remote branch `feat/story-save-schema` remains on v0.7.2 commit `a5abca1`.

## 2026-08-25 — Complete GE-1.0.0 item-catalog audit

- User requested a comparison of every game item type against the save-editor catalog after noticing
  that the Pokeball list appeared unusually short.
- Enumerated the shipped `PokemonEmerald/Content/Items` manifest and selectively inspected all 86
  cooked `ItemData` assets outside the repository. No game asset, extracted output or cryptographic
  material was copied into source or logged.
- Normalized known asset/display spelling differences (`LuxaryBall`/Luxury Ball,
  `LightOrb`/Light Ball and `WailmerPale`/Wailmer Pail) and compared all five editor pockets.
  Coverage is Items 35/35, Pokeballs 9/9, TMs 26/26, Berries 4/4 and Key Items 12/12.
- The editor has one non-asset-backed extra: `Max Revive`. A previous Revive-to-Max-Revive mutation
  reparsed in memory, but no matching GE-1.0.0 `ItemData` or executable identifier was found. This
  remains serializer-only evidence and is not treated as a game-verified item.
- Cross-checked the executable Pokeball enum against both ItemData and concrete Ball Blueprints.
  Nine values are fully shipped and already present in the editor. Dive, Dusk, Heal, Master, Nest,
  Net, Quick and Safari Ball are enum-only and lack the concrete inventory content needed for safe
  editor exposure.
- Audited all 141 packaged item UI assets. Seventy-one are referenced by concrete ItemData; the
  remainder includes generated sprites, TM-type art and 26 item-like legacy/placeholder icons.
  Alternative Amulet, Rotten Leftovers, Shiny Ping and Fire Stone also have Blueprints but no
  registered ItemData, so they are recorded as runtime-verification candidates rather than missing
  supported Bag entries.
- The `Other` item category exists in the compiled enum, but no concrete shipped ItemData was found
  for it. The five editor pockets therefore cover every currently registered GE-1.0.0 item category.
- Recounted the source catalog directly as 36 Items, 9 Pokeballs, 26 TMs, 4 Berries and 12 Key
  Items (87 total), and the unchanged automated suite passes all 41 tests.
- No live save or game file was modified during the audit.

## 2026-08-25 — Created-Pokemon Unknown portrait and battle-crash diagnosis

- User supplied screenshots showing two editor-created Party Pokémon rendered as `Unknown` with `?`
  portraits and a generic Fatal Error immediately after initiating a wild battle.
- Read the current live story save and automatic pre-edit backups without modifying them. Both
  Species DataAsset paths resolve to the expected shipped Torchic and Treecko assets, so missing
  species catalog paths are not the defect.
- Audited all 425 parsed `UniqueID` GUID fields. Exactly one GUID is duplicated: created Party slots
  2 and 3 and the still-empty Box template all share it. The Create Pokemon implementation copies
  the template GUID and generates only a new integer `PokemonID`; this invalidates its prior claim
  of complete runtime-safe identity generation.
- Compared the Treecko field before and after Gamma load/resave. The editor wrote
  `EPokemonAbility::Silvano`; Gamma persisted it as `EPokemonAbility::EPokemonAbility_MAX`.
  `Silvano` is not one of the 52 concrete Ability enum strings in the GE-1.0.0 executable.
- Cross-checked the complete generated species metadata against the executable and found 52 distinct
  metadata Ability names absent from the runtime enum. The source metadata came from external
  species/Ability tables rather than exact GE Species DataAssets, so species-aware Ability choices
  are no longer classified as verified.
- Parsed the latest crash context: `EXCEPTION_ACCESS_VIOLATION` reading address `0x30`. The stripped
  Shipping build provides no symbolic call stack, but the duplicate runtime identity and invalid
  Ability sentinel are concrete corruptions consistent with the menu failure and battle crash.
- Located the newest inspected pre-edit backup with only the original Mudkip, stamped
  `20260822-144442`. No restore was performed because it would mutate the live save and may discard
  later legitimate progress.

## 2026-08-25 — v0.8.2 Create-Pokemon identity and Ability hotfix

- User approved proceeding with the source fix and new build after the live failure diagnosis.
- Create Pokemon now replaces the empty template's `UniqueID` with a cryptographically random
  128-bit Unreal Guid, checks it against every Guid in the document and verifies the staged value
  occurs at exactly one property path. Storage activation and Party append use the same guard.
- Legality checks now include known Guid structs and report an occupied record whose identity also
  occurs on another occupied or empty-template record.
- Added the 52 concrete `EPokemonAbility` values extracted from the GE-1.0.0 Shipping executable as
  a source-only write whitelist. Unsupported imported metadata names and `*_MAX` sentinels cannot
  be selected or serialized. Ten species with no remaining safe mapping are blocked rather than
  assigned `None` or a fabricated value.
- Added four regression tests covering runtime-only Ability exposure, Treecko/Torchic choices,
  retry after a generated Guid collision, duplicate identity against an empty Box template and
  rejection of `Silvano`. The complete suite passes 45 tests.
- Ran a real-backup, memory-only integration test that created Torchic then Treecko. Party species
  resolved correctly, their Abilities were Blaze and Overgrow, all 425 parsed `UniqueID` values were
  distinct, no identity/runtime-enum legality errors remained and GES1 encode/decode round-trip passed.
- Built v0.8.2 GUI and CLI and refreshed the stable workspace-root launcher. Packaged CLI read-only
  validation passed against the current story save; packaged GUI smoke exited 0. The running game
  process was not stopped and no live save was modified.
- Built a key-free v0.8.2 portable release and confirmed it contains zero runtime keys, `.dat` saves
  or `.bak` files. Portable CLI validation and GUI smoke passed with the runtime key supplied only
  through the process environment.
- v0.8.2 GUI SHA-256: `16B08B732F3324253AB7E7CBA66169CEDEB5C75A8FB13D59E1BF32D5060A97F0`.
- v0.8.2 CLI SHA-256: `E3C9C393A05BEC63C7BC84EF892210F992F8B95DDA3B7D85AD0A3A844E937328`.
- Key-free v0.8.2 portable ZIP SHA-256:
  `885F330943D5268B292667DAB269C7A3A39993241197C5091703BBA8D98B7601`.
- Prepared a memory-only repair of the current damaged save. It changes exactly four fields:
  Torchic and Treecko `UniqueID`, plus Treecko Ability and Ability Slot to Overgrow/0. All 22,598
  records remain present and encrypted round-trip passes. Live application awaits an explicit user
  choice because restoring the older clean backup would discard later progress.
- The user selected repair rather than restore. With both the game and editor closed, the guarded
  writer confirmed the current save still matched the diagnosed failure, created a timestamped
  pre-edit backup and atomically replaced the story save. No older backup or later progress was restored.
- Post-write decrypt/reparse and exact semantic comparison passed: only the four intended fields
  changed, all 22,598 property records remain, all 425 `UniqueID` values are distinct, and Treecko
  now stores `Overgrow` with Ability Slot 0. In-game portrait, battle, normal save and reload remain
  the final controlled runtime check.

## 2026-08-25 — v0.9.0 Pokémon portraits, evolution chart and species-profile conversion

- Added an optional local sprite repository. Party and Storage use compact 32 px icons, the selected
  Pokémon preview uses a responsive 96/128 px portrait, and missing art falls back to initials. The
  ignored local cache covers 117/118 catalog species; no sprite, cooked game asset or extracted data
  was added to tracked source. Gecqua currently uses the fallback.
- Added a Pokémon > Main evolution-family chart limited to the shipped GE species catalog. It favors
  the requested horizontal reference-tool layout, recomputes nodes/connectors on resize and compacts
  branched families. Captured source UI at both 1360 × 840 and the 1080 × 680 minimum; the first
  connector-label stacking defect and narrow-preview clipping found visually were corrected.
- Species selection now builds a complete conservative Lv. 5 profile instead of swapping only the
  Species DataAsset: level/EXP, Nature/Gender, runtime-backed Ability/slot, calculated HP, zero IV/EV,
  starting exact level-up moves/PP, status and met defaults. Existing conversion preserves Pokémon
  identity and Original/Current Trainer ownership.
- Corrected the serializer transaction so the catalog-validated `SpeciesData` path may pass the
  parser's generic read-only flag during an explicit conversion; unrelated read-only paths remain
  locked. A real-story, memory-only Mudkip-to-Torchic conversion retained all 22,598 records,
  preserved identity/ownership and passed GVAS/GES1 reparse. The live save was not written.
- Species profiles are available for 106 runtime-backed species. Twelve remain fail-closed because
  their imported metadata has no Ability proven in the 52-value runtime enum; no sentinel or guessed
  Ability is written.
- Added evolution, sprite-path and species-profile tests. The complete suite passes 49 tests;
  compileall, source GUI smoke, packaged GUI smoke and packaged CLI real-save read-only validation
  all pass.
- Built v0.9.0 GUI/CLI with 117 local icons embedded in the local onedir build and refreshed the
  stable workspace-root launcher. No public portable ZIP containing third-party art was produced.
- v0.9.0 GUI SHA-256: `386D687038BB4AB528A0BC812372B52E2FA9DF18369337FA5E3AC4A0C167E125`.
- v0.9.0 CLI SHA-256: `855C9255F33713BAC243F634D5CE54574B7C650A8465BC4BE3ADE8B3BD40A476`.

## 2026-08-25 — v0.10.0 Stats EV and matchup visualizations

- Added `Max all EVs (252)` to Pokémon > Stats. It sets all six EV fields to 252 and automatically
  enables the existing over-510 editor override, producing an explicit total of 1,512. The action
  remains staged and does not write until the normal Apply + Save workflow is completed.
- Split the unused lower Stats area into two resize-aware canvases. The left renders the six current
  Final stats as vertical columns; the right renders all 18 type multipliers for both best available
  same-type attacking coverage and combined incoming defense.
- Added the catalog-level best-STAB attack calculation and a regression test covering dual-type
  attack selection plus combined defense. The full suite now passes 50 tests.
- Extended GUI smoke to assert automatic EV override, all six 252 values, total 1,512 and both chart
  render paths. Visually captured the real-save Stats tab at 1360 × 840 and 1080 × 680; fixed the
  minimum-size title/bar collision and Attack/Defense section overlap found in the first capture.
- Built v0.10.0 GUI/CLI and refreshed the stable workspace-root launcher. Source and packaged GUI
  smoke plus packaged CLI real-story read-only validation pass. No live save was written.
- v0.10.0 GUI SHA-256: `992ED29C9AED752985988044238B297B5FC37D92E91A582C79C247F8771C4285`.
- v0.10.0 CLI SHA-256: `09D494387E756D0A4B4B42EF3A046C156CACA5C02EA9EC689CB42CB1BAF12818`.

## 2026-08-25 — v0.11.0 per-move attack type charts

- Added four live attack-type charts to the unused lower area of Pokémon > Moves. The charts use a
  2 × 2 responsive layout in move-slot order; each title shows slot, selected move and verified type.
- Every chart displays the selected move type's outgoing multiplier against all 18 defending types.
  Changing or clearing one move redraws its chart immediately without staging or writing by itself.
- Move types come directly from all 99 verified GE move catalog paths rather than a second inferred
  table. Added regression checks for Tackle/Normal, Rock Slide/Rock, Surf/Water and Ice Beam/Ice.
- Extended GUI smoke to load those four moves and assert all four complete chart renders. Captured
  the real-save Moves tab at 1360 × 840 and 1080 × 680; both layouts remain readable without overlap.
- Built v0.11.0 GUI/CLI and refreshed the stable workspace-root launcher. All 51 tests,
  source/packaged GUI smoke and packaged CLI real-story read-only validation pass. No save was written.
- v0.11.0 GUI SHA-256: `D93E9BE4A6F9EE271A856AA6B8809DFD3B4CEB9C56CA303520BA14CB601397C9`.
- v0.11.0 CLI SHA-256: `970D5873762B6DD9FDBCFBA583E3B243DD006456E901677CBB7417913E30A457`.

## 2026-08-25 — v0.12.0 exact Main/Preview type rendering

- User identified Lucario as an obvious Main-tab typing/color defect. The Species asset is filed under
  Fighting, while the mapped species metadata correctly defines Fighting + Steel; Preview previously
  used only the asset-folder category and therefore omitted the second type.
- Main now displays one or two exact metadata-backed type badges. Preview uses the same types, shows
  both badges and splits its light background by primary/secondary type for dual-type Pokémon.
- Replaced the older type palette with one standardized 18-type palette and added luminance-aware
  text selection. Dark badges such as Fighting, Poison, Ghost, Dragon and Dark now use white text;
  every existing Stats, Moves and Pokédex type header shares the same palette and contrast logic.
- Added regression coverage that Lucario is Fighting/Steel and that every mapped species type exists
  in the complete color table. Extended GUI smoke to verify both Lucario badges and Fighting contrast.
- Captured Lucario Main at 1360 × 840 and 1080 × 680. Both exact dual-type badges, split Preview and
  evolution layout remain readable. All 52 tests, source/packaged GUI smoke and packaged CLI
  real-story read-only validation pass; no save was written.
- Built v0.12.0 GUI/CLI and refreshed the stable workspace-root launcher.
- v0.12.0 GUI SHA-256: `CF11751650011FD2F711EFF970241C3C43109BB535A843ECAAEEF10E8080FFFF`.
- v0.12.0 CLI SHA-256: `5EB8229D8FC6FC06484EEE9019F3DEBD5CDAF48BC641A39DBEB713DBC65E52D4`.

## 2026-09-02 — Recover empty/default live story slot

- User reported that selecting the existing save now ended in a Fatal Error. Read-only inspection
  found a new crash about two minutes after the live slots were written on 2026-08-31. It is a
  different access-violation address and stack hash from the earlier created-Pokemon battle crash.
- Packaged `gamma-save validate` confirmed that all four live GES1 containers still passed AES,
  SHA-1, GVAS marker and round-trip checks. Structural validity therefore did not explain the crash.
- A semantic comparison against the newest pre-edit backup showed that the live story slot was a
  nearly empty default state: 0.958 seconds of play time, no Trainer name, Party, Bag, location,
  money or progress fields, and 22,385 parsed records instead of 22,598. All 420 empty Box template
  IDs had also been regenerated, consistent with game-side default-object construction rather than
  a normal editor property patch.
- The newest full pre-edit backup retained the Trainer, Mudkip/Torchic/Treecko Party, Bag, world
  location and progress. Read-only legality inspection found no duplicate GUID or invalid Ability;
  its only findings were the three explicitly over-cap 1,512 EV totals.
- User explicitly authorized recovery. With the game and editor closed, the guarded restore path
  first preserved the empty live target as a timestamped pre-restore safety copy, validated the
  source backup, atomically replaced the live slot and reloaded it for verification.
- Post-restore SHA-256 comparison showed an exact match with the selected backup. Packaged GES1/AES/
  SHA-1/GVAS validation passed; source reparse returned all 22,598 records, three expected Party
  Pokemon, nine Bag entries and no GUID/Ability findings. No game process was launched or stopped.
- Controlled in-game load, menu, battle, normal save and reload remain pending user verification.

## 2026-09-03 — Diagnose story/quest generation mismatch

- User tested the restored story and Gamma entered the opening sequence instead of continuing at
  the stored world position. At the scripted starter battle the UI showed four Party indicators
  while the move command panel was blank.
- The game remained open and was not stopped. Read-only inspection found that battle start had
  auto-saved Story, Quest and Berry. The story now reparses 22,601 records and still contains exactly
  the restored Mudkip, Torchic and Treecko with all four move paths and PP arrays intact; the apparent
  fourth starter existed only in the scripted in-memory battle state at capture time.
- The Quest payload grew from the empty/default capture and now contains intro flags only through
  seeing Birch in danger. This confirms that story-only restore mixed the old Party with a reset
  progression slot and explains both the new-game flow and inconsistent battle UI.
- The ignored private Quest capture contains the later Birch Lab, helped-Birch and Oldale flags.
  Live Berry and Options payloads are byte-identical to their corresponding known-good private
  captures, narrowing coordinated recovery to Story plus Quest.
- Packed the prior-progress Quest GVAS into an offline QuestSlot candidate and verified its slot name,
  GES1/AES/SHA-1/GVAS boundaries, class and exact encrypted round-trip. No live file was changed.
- Next action: after the user closes the game, preserve both current auto-saved targets and atomically
  restore the newest full story backup plus the validated Quest candidate as one coherent set.
- The first coordinated-restore attempt was safely rejected because the Shipping process had not
  fully exited; it created no temporary file or backup. After process exit was confirmed, the retry
  preserved both current auto-saved targets under one timestamp and installed Story plus Quest with
  rollback protection across the two replacements.
- All four final live containers pass packaged validation. Story matches its source backup, reparses
  22,598 records and retains three Party members, all move arrays and nine Bag entries with no GUID/
  Ability finding. Quest exactly matches the offline candidate and contains the Birch Lab,
  spoke-after-save, helped-Birch and Oldale flags. Berry and Options remain byte-identical to the
  known-good private captures. No game process was launched or stopped.
- Coordinated recovery is complete; controlled in-game testing remains pending.

## 2026-09-03 — Created-Pokémon runtime retest failure

- User supplied Party and wild-battle screenshots after the coordinated Story/Quest recovery. Quest
  recovery worked: Gamma no longer entered the new-game intro. Party still rendered the native
  Mudkip correctly but displayed both editor-created records as `Unknown`.
- The wild battle showed Mudkip with correct level and HP but four blank move buttons. Read-only live
  inspection confirmed Mudkip still stores Tackle, Rock Slide, Surf and Ice Beam with valid PP arrays,
  so the UI failure is runtime state contamination rather than deleted move data.
- The story file was unchanged during this battle because Gamma disables auto-save at battle start.
  No live file was modified during diagnosis and the running game process was not stopped.
- The result disproves the remaining v0.8.2 runtime-safety assumption: unique GUIDs and executable-
  backed Abilities fix two concrete corruptions but do not initialize every field Gamma requires for
  a runtime-valid created record. Further guessed repairs are unsafe.
- Validated the last pre-creation story backup. It contains one native Lv. 8 Mudkip with Growl,
  Tackle and Mud-Slap, zero EVs, six Bag entries, no occupied Storage, 22,485 parsed records and no
  legality findings. It passes packaged GES1/AES/SHA-1/GVAS validation.
- Selected recovery plan: after game exit, retain the recovered QuestSlot and restore only this
  Mudkip-only Story. The rollback removes the two invalid created records, about 7 minutes 33 seconds
  of later story time and three later Bag entries. Runtime retest remains pending.

## 2026-09-03 — v0.12.1 canonical SoftObjectPath hotfix

- User reported that three move edits made through Gamma appeared in-game, but adding Surf through
  the editor made all four Mudkip move buttons blank after reload. The immediate automatic pre-edit
  backup preserved the game-authored representation for exact comparison.
- Byte-level inspection identified the remaining common cause. Gamma serializes the empty third
  FString (sub-path) of `FSoftObjectPath` as a zero int32 with no terminator. The editor serialized
  the same decoded empty value as length 1 plus NUL. Its parser accepted both forms, but Gamma did
  not resolve the noncanonical form at runtime.
- All three game-authored Mudkip moves used the canonical zero-length form. The editor-authored move
  and every move rewritten by the editor used length 1. Native Mudkip SpeciesData used length 0,
  while editor-created Torchic and Treecko SpeciesData used length 1. This exactly correlates with
  working/missing moves and native/`Unknown` species rendering.
- Changed `_encode_fstring("")` to emit Unreal's canonical zero length and added byte-level regression
  assertions for both standalone soft objects and soft-object arrays. The complete suite passes all
  52 tests.
- Bumped the local build to v0.12.1. GUI/CLI PyInstaller builds completed, the stable root launcher
  was refreshed, packaged GUI smoke passed and packaged CLI validated the real story save.
- Ran a memory-only five-property repair first. It canonicalized the Moves arrays for all three Party
  records and SpeciesData for Torchic/Treecko, reduced GVAS by exactly 14 bytes, retained every one of
  22,598 parsed records and left all decoded species, moves, PP and other values unchanged.
- With game/editor closed, the guarded writer created a timestamped backup and applied that exact
  repair atomically. All four live slots pass packaged validation; every repaired sub-path now has
  length 0, all three Party move sets remain present and no GUID/Ability finding exists.
- v0.12.1 GUI SHA-256: `F1F352BF6499B166D9D8A78816B0212ACD9677AF4954940CB5337E1C08E65487`.
- v0.12.1 CLI SHA-256: `D39F74FB358F82396CA0C55BE1E26213F85D985206E6734D71116625BD394832`.
- Runtime verification of Party species, move buttons, battle, normal save and reload remains pending.

## 2026-09-03 — Self-service runtime diagnostics documentation

- User requested a detailed method for independently detecting and diagnosing failures like the
  recent Fatal Error, mixed New Game/old Party state, `Unknown` species and blank move buttons.
- Added `docs/SAVE_RUNTIME_DIAGNOSTICS.md`. It separates GES1 integrity, GVAS structural parsing,
  known-field legality and actual runtime acceptance; documents coherent four-slot handling; and
  provides symptom mapping, controlled game/editor A/B capture, crash triage, safe repair/rollback
  criteria, a runtime test checklist and an incident-report template.
- Documented the exact SoftObjectPath evidence: canonical empty FString length 0 versus the old
  editor's parser-equivalent but runtime-invalid length 1 plus NUL representation.
- Added `scripts/diagnose-live-save.ps1`. The script performs no filesystem writes and reports game/
  editor processes, live-slot validation/metadata/hashes, recent automatic backups, recent crash
  addresses/stack hashes and the latest Gamma diagnostics log entries.
- Ran the script end to end with reduced history limits. It exited 0, summarized all four live slots,
  parsed both recorded crash contexts and correctly warned that Gamma was currently running.
- Linked the guide and script from README. A targeted literal scan found no key, 64-hex secret or
  machine-specific slot filename in either new file; `git diff --check` reports no whitespace error.

## 2026-09-03 — v0.13.0 item scope and Pokémon Clone/Release

- User reported that the Bag dropdown contains fewer familiar franchise items, especially Balls,
  and requested right-click `Clone (Copy)` / `Release (Delete)` actions for Party and Box cards.
- Rechecked the completed GE-1.0.0 asset audit. The writable catalog is intentionally build-specific:
  86 concrete `ItemData` entries, including 9 Balls with matching item and Ball assets. Eight other
  Ball enum names have no concrete runtime assets and remain unavailable.
- Removed `Max Revive` from Bag and held-item choices because it has no concrete GE-1.0.0 asset.
  Added a Bag `Catalog Info` dialog that shows the 86-item pocket counts and names the unsupported
  enum-only Balls so a deliberately safe list is not mistaken for a loading failure.
- Added domain-level clone/release transactions. Clone preserves the entire source struct but creates
  a new positive `PokemonID` and random collision-free 128-bit `UniqueID`. Release removes Party array
  elements, blocks the final Party member, or fills a Box slot with a verified empty-template payload
  carrying fresh identities.
- Added the requested right-click menu to all Party and current-Box cards. Party clones prefer the next
  Party slot; Storage clones prefer the source/current Box, then other boxes, with Party as fallback.
  Release requires confirmation. All results stay staged until `Save + Backup`.
- `python -m pytest -q`: 54 passed. Python compile and `git diff --check` passed.
- Source GUI smoke passed. A real story save was exercised read-only/in-memory through Party clone +
  release, Storage clone + release, 22,598-record reparse, 425-UniqueID uniqueness and GES1 encrypted
  round-trip. No live save write occurred; Gamma was running throughout this validation.
- The normal build passed tests but could not replace the canonical onedir because an already-running
  old editor process held its native cryptography module open. The process was deliberately not stopped.
  Built GUI/CLI v0.13.0 into separate versioned outputs, copied only the existing ignored local runtime
  key into those outputs, passed packaged GUI smoke and packaged CLI read-only validation, and pointed
  the workspace-root launcher at the versioned GUI.
- v0.13.0 GUI SHA-256: `AB6973DD25893EC953D7B618DEB3CCB15E95D7BD18F68D214A83CD1F47BD06A1`.
- v0.13.0 CLI SHA-256: `C6ACA05C4B566C6C1B070EF3E6C9E11126BC29B6634CE09B433F7D33EBBFC6AC`.
- Runtime verification still needed: stage a clone and a release, save with the game closed, load the
  game, inspect Party/Box, save normally, then reload the editor. Automatic backup/guarded write remains
  the only supported live mutation path.

## 2026-09-03 — v0.13.1 explicit clone-preset Set workflow

- User clarified that Clone must not auto-select a destination. The desired flow matches Pokémon
  Showdown sets: copy one occupied record as a preset, choose an exact empty card, then invoke Set;
  Set must appear disabled before any preset has been copied.
- Replaced the GUI auto-destination behavior with an in-app immutable full-payload preset. `Clone (Copy)`
  does not dirty or modify the document, updates a visible preset indicator, and also writes a readable
  Showdown-style text set (species/nickname, item, gender, Ability, level, shiny, EVs, Nature, IVs and
  moves) to the Windows clipboard.
- Added `Set` to the card context menu. It is disabled without a preset, on occupied targets and on
  non-contiguous empty Party positions. Once enabled it writes only to the card the user chose and
  assigns new collision-free PokemonID/GUID values. The preset remains available for multiple Sets.
- Split domain behavior into `copy_pokemon_preset()` and `set_pokemon_preset()` while retaining the
  earlier combined helper as a compatibility wrapper. Opening/reloading a save clears the in-app preset.
- All 55 tests pass, including preset immutability, fresh identities and Showdown-style text coverage.
  A real story memory-only explicit Storage Set retained 22,598 records, all 425 GUIDs unique and a
  valid encrypted round-trip. A source GUI behavior run verified initially disabled Set state,
  non-contiguous Party disabling, clipboard text and exact Storage placement. No live write occurred.
- Built versioned v0.13.1 GUI/CLI outputs. Packaged GUI smoke and packaged CLI read-only validation of
  all four live slots pass. The workspace-root launcher now targets v0.13.1.
- v0.13.1 GUI SHA-256: `E1F677860757BA8EC08274EBF6133B4BFDD5A87AAA1B283F20838C4F7E1A5F89`.
- v0.13.1 CLI SHA-256: `34A14D7E7CAD0CB98C3CDC1D04FB872D595662B47E9A5B4D2CE914E1B8697825`.

## 2026-09-04 — v0.13.2 forgiving empty-Party Set target

- User confirmed the copy-preset workflow works but noted that users may not understand why only the
  next Party card is valid. Requested accepting Set from any displayed empty Party card and placing
  the clone in the closest valid empty position beside the current packed Party.
- Added a deterministic Party-target normalizer. With three current members, right-click Set on slot
  4, 5 or 6 now targets serialized slot 4. Occupied cards remain invalid targets; full Party remains
  unavailable. Storage continues to honor the exact selected slot.
- After Set, the actual filled Party card is selected/highlighted. If the clicked and actual positions
  differ, status text explicitly reports the redirect rather than implying the impossible gap was kept.
- Added unit coverage for all empty/occupied/full Party boundaries. All 56 tests and Python compile pass.
- A source GUI run against the real story save copied Party slot 1, invoked Set on displayed Party slot
  6, verified creation in/highlight of the actual next slot and confirmed redirect status. The operation
  remained in memory and the live save was not written.
- Built versioned v0.13.2 GUI/CLI outputs. Packaged GUI smoke and packaged CLI read-only validation of
  all four live slots pass; the root launcher now targets v0.13.2.
- v0.13.2 GUI SHA-256: `2F0F37DB5D3AD52A1EA1C9979050050938F9C2C40F66240D35FBDE60A2578B4E`.
- v0.13.2 CLI SHA-256: `AE950B77D9413FFDC2D1B54DC69E190772514E6F674CCB7C5B084F6079A7A6B3`.

## 2026-09-05 - Custom-item feasibility audit

- User asked whether items missing from the early-access release can be added, preferably from the
  save editor.
- Recounted the installed `Manifest_UFSFiles_Win64.txt`: it still lists exactly 86 concrete
  `PokemonEmerald/Content/Items/**/DA_*.uasset` files. The editor already covers all 86.
- Rechecked the shipping executable and found the eight known extra Ball enum identifiers (Dive,
  Dusk, Heal, Master, Nest, Net, Quick and Safari), while the content manifest has no matching
  ItemData or concrete Ball Blueprint. The only shipped concrete Ball implementations remain the
  nine already catalogued choices.
- Confirmed from the verified Bag schema and writer that a save row contains ItemName, ItemID and
  Quantity. Bypassing catalog validation could serialize any string, but it cannot provide cooked
  ItemData, behavior Blueprint/effect, UI asset or runtime registration. This is serializer-only,
  not a usable custom item, and remains intentionally unavailable in the GUI.
- `repak info` confirmed the original game pak is encrypted when no external key is supplied. No pak,
  asset, executable or save was modified, and no cryptographic material was recorded.
- Added `docs/ITEM_EXTENSION_GUIDE.md` and linked it from README. It explains the boundary between
  save editing and game modding, the future-update catalog path, and a controlled runtime checklist.

## 2026-09-05 - Item Mod Wizard / Icarus comparison

- User asked whether the editor can expose all required item fields, create cooked content and pack
  it into Gamma, citing Icarus mod tools as precedent.
- Reviewed both active Icarus Mod Manager implementations and their authoring guide. Their resilient
  path patches/adds named rows in JSON DataTables from `Data.pak`; new Blueprint assets still require
  the exact Unreal version, a correctly named C++ project, cooking and UnrealPak packaging.
- Inspected Gamma locally. Its embedded project descriptor reports EngineAssociation 5.6 and modules
  PokemonEmerald (Runtime), PokemonEmeraldEditor (Editor) and GESaveGuard (Runtime). The installed
  build has no Unreal Editor/UnrealPak, source headers, `.usmap` or Shipping PDB.
- Selectively extracted and inspected DA_Potion, DA_UltraBall and BP_Pokeball_UltraBall outside the
  repository without printing or recording cryptographic material. All are unversioned cooked
  packages and UAssetAPI exposes RawExport without a build-matched mapping. Ultra Ball's imports
  confirm dependencies on its Ball Blueprint, UI icon, world sprite/flipbooks, particle and sound.
- The game directory contains one encrypted V11 base pak and no adjacent `.sig`, `.utoc` or `.ucas`.
  This makes standard patch mounting plausible but does not prove the Shipping build accepts it.
- Built a harmless offline V11 `GammaEditorProbe_P.pak` with mount point `../../../`, verified its
  internal `PokemonEmerald/Content/Mods/...` entry and deleted all probe/extracted temp files. It was
  never copied into the game, and the already-running game process was neither stopped nor launched.
- Added `docs/ITEM_MOD_WIZARD_FEASIBILITY.md`. Proposed phases are environment detector, controlled
  mount proof, schema/registry proof, existing-item override MVP, template-based new items reusing
  existing behavior, and only then save integration. Arbitrary Blueprint/native behavior remains an
  external UE 5.6/devkit problem rather than a Python form field.

## 2026-09-05 - Reversible Gamma patch-container mount proof

- User explicitly authorized the controlled mount probe described in the feasibility report.
- Confirmed no Gamma process was running. Built a 590-byte unencrypted V11 pak with mount point
  `../../../` and one marker text entry under `PokemonEmerald/Content/Mods/GammaEditorProbe`.
  Verified version, mount point, file list and install-copy SHA-256 before launching anything.
- Installed as `GammaEditorMountProbe_P.pak` first. A headless Shipping process locked the encrypted
  base pak but not the probe, proving that arbitrary patch basenames are not scanned by this build.
- Stopped only the headless process created for the test, renamed the exact same probe bytes to
  `PokemonEmerald-Windows_0_P.pak`, and relaunched. Exclusive-open checks then failed for both the
  base pak and probe while Shipping remained alive. This proves external V11 patch-container mounting
  and the required project/platform patch naming convention without relying on Shipping log output.
- Stopped the exact second headless PID and removed the installed probe plus ignored build temp after
  validating every cleanup target. Final state: zero Gamma processes, no probe pak, unchanged base
  pak size/timestamp and SHA-256
  `2DB705FA9ABCB415C7D73772FF7A8584C021B703D745BDA70D209DD3ABE1CA10`.
- The probe contained no cooked asset override and never accessed a save. Asset priority/discovery is
  still unproven; the next technical gate is a build-matched `.usmap`/SDK or equivalent safe schema.

## 2026-09-05 - v0.14.0 Item Mod Builder implementation

- User asked to continue from the approved modding research into implementation.
- Used the official UE4SS experimental developer build to generate a build-matched `.usmap` and
  `.jmap`. The USMAP parsed Potion/Ultra Ball as structured exports; JMAP recovered the native
  72-property ItemData layout, enum domains/defaults and ItemDataManager `/Game/Items/` scan path.
- A reversible same-path Potion patch reported the changed BuyPrice through runtime reflection,
  proving asset override priority. A second renamed `DA_GammaEditorProbe` patch was automatically
  discovered by ItemDataManager with its new ID/price before explicit LoadAsset, proving that a new
  ItemData under `/Game/Items/` does not require an AssetRegistry patch in this build.
- Generalized the local UAssetAPI helper to accept a validated JSON spec and rewrite object/package
  identity, ItemName, independent FText keys/source strings, ItemID, prices and HPRestoreAmount. A
  real helper smoke produced a renamed `.uasset/.uexp` pair and a V11 pak with the expected paths.
- Added `mod_builder.py`: game/toolchain discovery, conservative field validation, SHA-256 manifests,
  build-only output, game-running guards, atomic install, backup-before-owned-replacement, and
  ownership/hash-checked uninstall. The base pak is never a write target.
- Added the fifth GUI tab `Item Mod Builder`. The MVP exposes only the Potion-derived HP-consumable
  fields that have runtime evidence. When a valid editor-owned patch is installed, its display/runtime
  name appears in Bag Items and domain validation permits it; uninstall is blocked while that loaded
  Bag still contains the item.
- Added four backend tests for validation, discovery, command construction, build/install/uninstall
  ownership guards and game-running refusal. Full suite passes at 60 tests; source GUI smoke also
  selects and validates the new tab.
- Ran a real local build, listed both cooked files from its pak, then performed a real guarded
  install/readback/uninstall cycle. The installed test patch is gone, zero live saves were accessed,
  and base pak SHA-256 remains
  `2DB705FA9ABCB415C7D73772FF7A8584C021B703D745BDA70D209DD3ABE1CA10`.
- Added `docs/ITEM_MOD_BUILDER.md` and updated the feasibility report/README. Ball, TM, Berry, held-item,
  custom icon, Blueprint and native-behavior authoring remain blocked pending template-specific proofs.
- Built the packaged v0.14.0 GUI/CLI after all 60 tests passed and refreshed the stable workspace
  launcher. Packaged GUI smoke, including the Item Mod Builder environment/form checks, passed.
  GUI SHA-256: `2071CE1E564F6508952225759459A51D352779009E1B8E8A7842BFE4549CF833`.
  CLI SHA-256: `7DDA51225F51AADF0D9EE2CF4D2F936825F9CC91C741D8BE1721EBD91BAB70F2`.

## 2026-09-05 - v0.15.0 multi-archetype Item Mod Builder

- User requested the rest of the item wizard, explicitly including Poké Balls, and supplied a
  Poké Ball icon sheet plus a local Cobblemon SFX archive for evaluation.
- Extracted only the 172 whitelisted `.uasset/.uexp` ItemData files from the encrypted base pak into
  the ignored local tool workspace without printing or persisting the decryption key. Parsed all 86
  assets with the build-matched mapping and classified their concrete serialized fields/dependencies.
- Expanded the builder to 41 selected behavior/visual templates across HP/status/PP healing, Revive,
  Vitamins, Rare Candy, evolution/utility, held items, Berries, TMs and all nine complete shipped Ball
  visual sets. Template-specific fields include healing values, stat/type/move/Ball enums and scalar
  multipliers only when the selected asset serializes that property.
- Generalized the local UAssetAPI helper to clone any selected source package, synthesize missing
  integer identity/price properties safely, edit mapped int/float/bool/enum/soft-object properties,
  and re-open the written output for identity verification.
- Built real Protein, Ultra Ball and TM assets/paks. A temporary read-only runtime manager probe found
  all three custom assets and read the intended ID plus Speed, QuickBall/3.5 and Surf fields. Stopped
  the exact test process and removed the temporary loader and required-name patch; the base pak still
  hashes to `2DB705FA9ABCB415C7D73772FF7A8584C021B703D745BDA70D209DD3ABE1CA10`.
- Added dynamic GUI archetype/template controls, correct Bag-pocket routing, custom held-item/Berry
  choices, and replacement/uninstall guards that scan the loaded Bag, Party and all Storage boxes.
- Audited the supplied ZIP: 33 Minecraft OGG sources plus pack metadata/image, SHA-256
  `5A1C4FDFEC5F1CD5E2C0F8E00956203F57A6AF47F1897D76A52C36387BA4721A`, no license file. Raw PNG/OGG
  files are not UE cooked assets and are not bundled; current Ball mods reuse Gamma's cooked art/SFX.
- Added multi-archetype validation tests and documentation. Full source suite passes 63 tests.
  Built v0.15.0 GUI/CLI, refreshed the stable root launcher, and passed source/packaged GUI smoke plus
  packaged read-only validation of every currently detected live slot. Actual per-effect gameplay
  remains the user acceptance step. GUI SHA-256:
  `DE7F6AD8B6E436AFCA7845D4C83B0DABA3FA4E0DC9F01894DBA3C32E7724CFFF`.
  CLI SHA-256: `FBAE869F30190DC0E9296BDA5B85ED9E0EA1804FBC31F041541B775695825FC0`.

## 2026-09-05 - v0.15.1 custom-ID and item-behavior UX

- Confirmed from the build-matched ItemData mapping that `ItemID` is a signed `IntProperty`; literal
  text IDs are impossible. Added a persistent numeric namespace derived from the `CSTM` FourCC,
  sequential `CSTM-######` display tags, exact numeric readout, collision skipping and a manual
  `Next CSTM ID` action. GUI smoke mode does not consume the real persistent counter.
- Disassembled Gamma's native `CalculateVitaminGain` function and confirmed the result is clamped by
  the configured `EVBoostAmount`, 100 EV in the selected stat and 510 total EV. Added a read-only
  dropdown containing every divisor of 252 plus the shipped default 10 and extended the local writer
  to synthesize the otherwise inherited `EVBoostAmount` property.
- Added inline behavior summaries for the supported Held Item and Berry templates. Clarified in both
  UI and docs that the TM clone can target any of 99 existing move Blueprints, including moves beyond
  the 26 shipped TM items, but cannot create or edit move power/type/effects.
- Built and runtime-discovered a temporary custom Protein with a CSTM-derived numeric ID, Speed and
  EVBoostAmount 84. Removed the loader and patch afterward, wrote no live save, and confirmed the base
  pak SHA-256 remains `2DB705FA9ABCB415C7D73772FF7A8584C021B703D745BDA70D209DD3ABE1CA10`.
- All 65 tests and source GUI smoke pass. Built v0.15.1, refreshed the stable root launcher, passed
  packaged GUI smoke and read-only packaged CLI validation of the currently detected live slot.
  GUI SHA-256: `FA8D312FE73B822BA0B2A98712F8BEDE2D2A37D963570D791E04D7B3D844FB5C`.
  CLI SHA-256: `9A2F2D9FF127ABD83099843744759C7B5D6FD8799121DF4E64AC12C3EA9323A0`.
