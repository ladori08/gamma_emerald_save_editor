# Tasks

Status legend: `[x]` verified, `[~]` implemented/awaiting final verification, `[ ]` pending/blocker.

## Core

- [x] Identify live save directory and deterministic slot filenames.
- [x] Reverse engineer `GES1` version, sizes, SHA-1, AES mode/key construction and payload layout.
- [x] Parse UE5.6 GVAS header without rejecting package version 1017.
- [x] Preserve unsupported GVAS structures as opaque bytes.
- [x] Add CLI discovery, summary, validation, unpack and non-overwriting pack commands.
- [x] Add GUI overview, properties, gameplay status, backups and diagnostics tabs.

## Save safety

- [x] Refuse writes while the game process is active.
- [x] Refuse stale writes if the source changed after load.
- [x] Create timestamped pre-edit and pre-restore backups.
- [x] Use temporary-file + atomic replacement.
- [x] Decode and compare before and after replacement.
- [x] Add backup browsing and restore flow.

## Gameplay editors

- [x] Capture and validate normal `PokemonSaveSlot`, `QuestSlot`, `GEBerrySlot`, and `GEOptions`.
- [~] Map Trainer identity, money, coins, badges, HMs and location (present fields mapped).
- [x] Map six-party Pokemon plus 14 × 30 boxed Pokemon records.
- [~] Map species, level/EXP, nature, ability, IV, EV, moves/PP, item and friendship constraints.
- [~] Map Bag pockets, item identifiers and quantities (existing quantities editable).
- [~] Map Seen/Caught Dex and progress/event flags (decoded/read-only arrays).
- [~] Add legality rules and cross-field consistency repair (core numeric rules + trainer sync done).

## Verification and delivery

- [x] Complete automated unit tests and real-options-save read-only test.
- [x] Verify story-save edit -> game load -> resave cycle.
- [x] Build Windows executable and smoke-test it.
- [x] Publish a sanitized clean history with external key provisioning and draft PR.
- [ ] Tag the first verified release.
