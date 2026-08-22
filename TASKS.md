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
- [~] Map Bag pockets, item identifiers and quantities (five filtered pockets; add/edit/remove implemented, live reload pending).
- [~] Map Seen/Caught Dex and progress/event flags (decoded/read-only arrays).
- [x] Add Indigo-style Party/Storage navigation and grouped Pokemon editor forms.
- [x] Catalog the game's 118 species and 99 move object paths without copying game assets.
- [x] Add legality report and cross-field consistency repair for verified numeric/catalog rules.
- [~] Verify Bag/pocket array insertion and removal (serializer + real-save in-memory round-trip done; live reload pending).
- [~] Verify complete Pokémon moves/swaps between Party and Storage (in-memory round-trip done; live reload pending).
- [~] Create Pokémon in empty Party/Storage slots (template activation + real-save in-memory round-trip done; live reload pending).
- [x] Merge Party and Storage into a drag/drop Pokémon card workspace.
- [x] Replace Seen/Caught progress UI with a Gamma Pokémon information Pokédex.
- [x] Add optional EV-total >510 override while keeping each EV capped at 252.
- [x] Filter Ability by Species, mark Hidden Abilities and synchronize Ability Slot.
- [x] Annotate all Nature choices with raised/lowered stats.
- [x] Restrict Held Item choices to hold/Fling-compatible item groups.
- [x] Expand Pokédex with Abilities, base stats and incoming type defenses.
- [x] Batch Pokémon edit/create/move serialization to remove multi-reparse UI stalls.
- [x] Add catalog-validated live search to Species, Item, Nature, Ability and Move dropdowns.
- [x] Show live Base/Final stats calculated from Species, Level, Nature, IVs and EVs.
- [x] Add Max Revive to the Items/holdable catalogs and verify an in-memory real-story edit.
- [ ] Add Gamma-verified team-builder, damage-calculator and custom-item workflows.

## Verification and delivery

- [x] Complete automated unit tests and real-options-save read-only test.
- [x] Verify story-save edit -> game load -> resave cycle.
- [x] Build Windows executable and smoke-test it.
- [x] Package and smoke-test the tool-only v0.7.0 local release against the real story save.
- [x] Publish a sanitized clean history with external key provisioning and draft PR.
- [ ] Tag the first verified release.
