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
- [x] Create Pokémon in empty Party/Storage slots (v0.12.1 fixes duplicate identity, invalid Ability
  and noncanonical SoftObjectPath sub-paths; guarded live repair and runtime retest pass).
- [x] Merge Party and Storage into a drag/drop Pokémon card workspace.
- [~] Add right-click Copy/Set/Release for Party and Storage (Showdown-style clipboard text, disabled
  Set without preset, exact Storage target, any-empty-card Party redirect, fresh IDs, empty-payload and last-Party guards pass unit +
  real-save memory-only checks; in-game save/reload test pending).
- [x] Replace Seen/Caught progress UI with a Gamma Pokémon information Pokédex.
- [x] Add optional EV-total >510 override while keeping each EV capped at 252.
- [x] Verify EV totals above 510 through Gamma battle, post-battle EV calculation, save and recheck.
- [~] Filter Ability by Species, mark Hidden Abilities and synchronize Ability Slot (writable choices
  are runtime-filtered; exact per-species mappings remain unavailable for 12 blocked species).
- [x] Diagnose the live created-Pokémon `Unknown`/battle-crash failure from save and crash artifacts.
- [x] Generate a collision-free 128-bit `UniqueID` for every created Pokémon and reject duplicates.
- [x] Filter species Ability choices against exact GE-1.0.0 runtime enum values; reject
  sentinels such as `EPokemonAbility_MAX`.
- [x] Repair the current damaged story save through the guarded writer: replace the two duplicated
  created-Pokémon `UniqueID` values and normalize Treecko Ability/slot to Overgrow/0, with backup and
  exact post-write verification.
- [x] Repeat controlled live creation: Party species and moves render normally and the previously
  reported Fatal Error/intro mismatch no longer occurs after the v0.12.1 repair.
- [x] Annotate all Nature choices with raised/lowered stats.
- [x] Restrict Held Item choices to hold/Fling-compatible item groups.
- [x] Expand Pokédex with Abilities, base stats and incoming type defenses.
- [x] Batch Pokémon edit/create/move serialization to remove multi-reparse UI stalls.
- [x] Add catalog-validated live search to Species, Item, Nature, Ability and Move dropdowns.
- [x] Generate exact 118-species Level-up/TM/HM/Egg learnsets from shipped GE-1.0.0 DataAssets.
- [x] Filter Create/Edit moves by species, level and evolution stage; enforce domain validation.
- [x] Extract Base PP for all 99 moves and replace editable Max PP with game-valid PP Up scaling.
- [x] Add four live 18-type attack charts to Pokémon > Moves, keyed to each selected move's verified type.
- [x] Show live Base/Final stats calculated from Species, Level, Nature, IVs and EVs.
- [x] Add one-click all-252 EV fill that automatically enables the over-510 editor override.
- [x] Add resize-aware Final Stats column and 18-type Attack/Defense matchup charts to Pokémon > Stats.
- [x] Add local-runtime Pokémon portraits: large selected preview plus compact Party/Storage icons,
  with a safe initials fallback when art is unavailable.
- [x] Render exact single/dual species types in Main and Preview with standardized colors and
  contrast-aware badge text; stop treating the asset-folder category as the complete typing.
- [x] Add a responsive evolution-family chart to Pokémon > Main and verify horizontal/minimum-window
  spacing through captured 1360 × 840 and 1080 × 680 source UI runs.
- [~] Load a complete Lv. 5 base profile when creating or changing Species while preserving record
  identity/Trainer ownership (106 runtime-backed species pass; 12 remain fail-closed on Ability).
- [x] Audit every GE-1.0.0 `ItemData` against all five editor Bag pockets (86/86 covered).
- [x] Distinguish the 9 concrete shipped Pokeballs from 8 enum-only unsupported ball types.
- [x] Remove `Max Revive` from writable choices because no GE-1.0.0 `ItemData`, executable identifier
  or concrete item asset exists; explain verified catalog scope in the Bag UI.
- [ ] Runtime-verify blueprint-only item candidates before any catalog inclusion: Alternative
  Amulet, Rotten Leftovers, Shiny Ping and Fire Stone.
- [x] Determine whether asset-less items can be created by save editing alone; document why a raw
  Bag row is not a runtime item and keep arbitrary ItemName writes unavailable by default.
- [ ] On a future game update, detect new concrete ItemData assets and design a separately marked,
  evidence-backed catalog-extension import before exposing any new writer choices.
- [x] Compare Icarus mod tooling with Gamma's packaging and document a feasible Item Mod Builder
  architecture. Icarus's easy path is JSON DataTable patching; Gamma uses unversioned cooked assets.
- [x] Run a reversible external-pak container mount proof. Gamma ignored an arbitrary pak basename
  but held `PokemonEmerald-Windows_0_P.pak` open beside the base pak; probe/process were removed.
- [x] Prove cooked-asset override priority with a reversible mapped Potion price override; runtime
  loaded the patched value and all temporary loader/patch files were removed.
- [x] Generate build-matched `.usmap/.jmap`, recover the 72-property ItemData schema and prove that
  ItemDataManager auto-discovers a renamed ItemData under `/Game/Items/` without registry edits.
- [x] Implement the v0.14.0 Potion-derived Mod Builder MVP: environment checklist, field validation,
  `.uasset/.uexp` writer, V11 build, ownership/hash guarded install/uninstall and dynamic Bag choice.
- [ ] Runtime-acceptance test a user-built HP item through Bag display/use, battle, in-game save/reload
  and editor reload before adding more templates.
- [x] Add selected Ball/TM/Berry/held-item and other shipped behavior templates with dynamic fields;
  representative Vitamin/Ball/TM assets pass writer, pak and runtime-manager discovery proofs.
- [ ] Runtime-acceptance test actual use/throw/teach/held effects and game save/reload for each new
  archetype; keep new Blueprint/native-effect authoring in a companion UE 5.6 project/future devkit.
- [ ] Add Gamma-verified team-builder, damage-calculator and custom-item workflows.

## Verification and delivery

- [x] Complete automated unit tests and real-options-save read-only test.
- [x] Add a self-service runtime diagnostics guide and read-only PowerShell triage script covering
  live slots, backup hashes, crash evidence, cross-slot mismatch and game/editor A/B testing.
- [x] Verify story-save edit -> game load -> resave cycle.
- [x] Build Windows executable and smoke-test it.
- [x] Package and smoke-test the tool-only v0.7.0 local release against the real story save.
- [x] Add a stable workspace-root launcher and regenerate it on every successful build.
- [x] Package and smoke-test v0.7.1 enum-prefix hotfix; fix Stats Apply false Gender rejection.
- [x] Package and smoke-test v0.7.2 dropdown-focus fix; keep typing active after text/arrow input.
- [x] Package and smoke-test v0.8.0 exact species/stage/level move learnsets.
- [~] Build/package v0.8.1 Base PP/PP Up editor (41 tests + packaged CLI passed; packaged GUI smoke pending).
- [x] Build/package v0.8.2 Create-Pokemon identity/Ability hotfix (45 tests + CLI/GUI smoke passed).
- [x] Build local v0.9.0 portrait/evolution/species-profile editor (49 tests, 117 packaged local
  icons, source/packaged GUI smoke and packaged CLI real-save validation passed).
- [x] Build local v0.10.0 Stats visualization update (50 tests, full/minimum UI captures,
  source/packaged GUI smoke and packaged CLI real-save validation passed).
- [x] Build local v0.11.0 per-move attack-chart update (51 tests, full/minimum UI captures,
  source/packaged GUI smoke and packaged CLI real-save validation passed).
- [x] Build local v0.12.0 exact Main/Preview type rendering (52 tests, Lucario full/minimum captures,
  source/packaged GUI smoke and packaged CLI real-save validation passed).
- [~] Recover the 2026-08-31 empty/default live story slot from the newest full pre-edit backup
  (guarded restore, safety copy, exact hash match and 22,598-record validation pass; game retest pending).
- [~] Recover the matching QuestSlot after story-only restore mixed the old Party with the new-game
  intro (coordinated Story/Quest restore and all post-write checks pass; game retest pending).
- [~] Retain the last pre-creation Mudkip-only Story as fallback if the v0.12.1 canonical-path repair
  fails runtime testing (candidate has 22,485 records and zero legality findings).
- [x] Build local v0.12.1 canonical empty-FString hotfix (52 tests, packaged GUI smoke and packaged
  CLI real-save validation passed; stable launcher refreshed).
- [x] Build local v0.13.0 Clone/Release + Bag catalog-scope update (54 tests, source/packaged GUI smoke,
  packaged CLI validation and real-story memory-only clone/release round-trip passed).
- [x] Build local v0.13.1 explicit Copy/Set workflow correction (55 tests, source GUI behavior test,
  packaged GUI smoke, four-slot packaged CLI validation and real-story memory-only Set passed).
- [x] Build local v0.13.2 forgiving Party Set targeting (56 tests, source GUI slot-6-to-next-slot
  behavior test, packaged GUI smoke and four-slot packaged CLI validation passed).
- [x] Build local v0.14.0 Potion-derived Item Mod Builder (60 tests, real asset/pak build,
  install/readback/uninstall guard cycle, source and packaged GUI smoke passed).
- [x] Build local v0.15.0 multi-archetype Item Mod Builder (63 tests, source/packaged GUI smoke,
  packaged live-slot validation and representative Vitamin/Ball/TM runtime discovery pass).
- [x] Build local v0.15.1 item-wizard UX update: persistent sequential CSTM IDs, verified Vitamin
  amount/cap controls, Held Item/Berry behavior help and explicit existing-move TM scope.
- [x] Publish a sanitized clean history with external key provisioning and draft PR.
- [ ] Tag the first verified release.
