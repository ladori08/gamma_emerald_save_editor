# Current State

Last updated: 2026-09-05

## Snapshot

- Project: standalone Gamma Emerald save editor; no runtime dependency on `tool_editor`.
- Target verified: Pokemon Gamma Emerald `GE-1.0.0`, Unreal Engine `5.6.1`.
- Live save folder discovered: `%LOCALAPPDATA%\PokemonEmerald\Saved\.ged`.
- Available live slots: `PokemonSaveSlot`, `QuestSlot`, `GEBerrySlot`, and `GEOptions`.
- `GES1` container reverse engineered and read-only round-trip verified against the real options save.
- Inner save identified as UE5.6 `GVAS`, class `/Script/PokemonEmerald.GE_SettingsSave`.
- GUI, CLI, guarded write/backup service, diagnostics and schema-aware editor implemented.
- `docs/SAVE_RUNTIME_DIAGNOSTICS.md` now documents the four validation layers, multi-slot recovery,
  controlled game/editor A/B comparison, crash triage and the canonical SoftObjectPath failure.
  `scripts/diagnose-live-save.ps1` provides a read-only report of processes, live-slot summaries,
  hashes, automatic backups, crash contexts and the current game diagnostics tail.
- Story GVAS recursively parses more than 22,000 tagged records with no parser error, including
  Party, 14 boxes, Daycare, Bag, Seen/Caught and progress fields.
- The v0.16.1 consumer GUI has five focused tabs: Trainer, Pokémon, Bag, Pokédex and the experimental
  Item Mod Builder. Party and Storage share one workspace with six Party cards, a compact 5 × 6 Box
  grid and complete-payload drag/drop.
- Pokémon cards now use 32 px local runtime icons and the selected record uses a large 96/128 px
  preview portrait. The Main panel includes a responsive evolution-family chart: it prefers the
  reference-tool-style horizontal layout, recalculates spacing on resize and compacts branch nodes.
  The local ignored icon cache covers 117/118 catalog species; Gecqua uses the initials fallback.
- Main and Preview now render exact mapped species types instead of relying on the primary asset
  folder category. Dual types get two standardized color badges, a split light Preview background
  and contrast-aware badge text. Lucario therefore displays Fighting + Steel rather than Fighting only.
- Creating a Pokémon or selecting a different Species on an occupied record now loads a complete,
  conservative Lv. 5 species profile: level/EXP, Nature/Gender, runtime-backed Ability/slot,
  species-calculated HP, zero IV/EV values, exact starting moves/PP, status and met defaults.
  Conversion preserves `PokemonID`, Unreal `UniqueID` and Original/Current Trainer ownership.
- Empty Party and Storage cards now open a Create Pokemon form. Creation activates the game's
  complete verified empty struct template, assigns a collision-free Pokemon ID and current Trainer
  ownership, and accepts the same catalog/scalar/move fields used by occupied records.
- Controlled live-game testing disproved the runtime safety of Create Pokemon in v0.8.1. Two created
  Party records displayed as `Unknown`/`?`, and entering a wild battle crashed with an access
  violation because the records copied a storage-template `UniqueID` and one used an invalid Ability.
- v0.8.2 now generates a random collision-free 128-bit Unreal `UniqueID` for every creation and
  verifies that it occurs exactly once before staging. A real-save in-memory test created Torchic
  then Treecko with all 425 GUIDs unique and passed GVAS/GES1 reparse and encryption round-trip.
- Writable Ability choices are now filtered against the executable's 52 concrete
  `EPokemonAbility` values, and domain validation rejects unsupported values and `*_MAX` sentinels.
  Treecko now exposes only `Overgrow`; Torchic retains `Blaze` and `Speed Boost`. Twelve species whose
  imported mappings contain no runtime-backed choice are blocked rather than receiving fabricated data.
- The user-authorized repair was applied to the current story save with the game and editor closed.
  It replaced only Torchic's and Treecko's duplicated `UniqueID` values and changed Treecko Ability/
  slot from `EPokemonAbility_MAX`/2 to `Overgrow`/0. A timestamped pre-edit backup was created;
  post-write decrypt/reparse retained all 22,598 records and found 425 distinct `UniqueID` values.
- On 2026-08-31 the game replaced the live story slot with a nearly empty default state: 0.958 seconds
  of play time, no Trainer name, Party, Bag, location or progress fields, and 22,385 parsed records.
  A distinct access-violation crash followed about two minutes later. On 2026-09-02 the newest full
  pre-edit backup was restored through the guarded recovery path after preserving that empty live
  state in a timestamped pre-restore copy. The restored file exactly matches the validated backup,
  reparses all 22,598 records and contains Mudkip, Torchic and Treecko with no GUID/Ability findings.
- The story-only restore exposed a cross-slot mismatch: Gamma loaded the old Party but followed the
  reset QuestSlot's new-game intro. Selecting the scripted starter showed four Party indicators and
  a blank move command panel. The game's battle-start auto-save left all three on-disk Party move
  arrays intact, proving the blank panel was not caused by deleted moves. The live Berry and Options
  payloads exactly match their known-good private captures; only QuestSlot was stale/reset. After the
  game closed, Story and Quest were restored together while timestamped safety copies preserved both
  newer autosaves. Post-restore validation confirms 22,598 story records, all three Party move arrays,
  no GUID/Ability findings and the expected Birch Lab/helped-Birch/Oldale quest flags.
- The coordinated runtime retest bypassed the intro, but Party still rendered Torchic and Treecko as
  `Unknown` and a wild battle showed blank move buttons for the otherwise valid Mudkip. This proves
  the v0.8.2 GUID/Ability repair was necessary but not sufficient and that editor-created Pokémon
  remain runtime-unsafe. The last pre-creation story backup has one native Mudkip, three base moves,
  zero EVs, 22,485 records and no legality findings; it is the selected rollback candidate.
- Comparing a game-authored move edit with the editor's immediately following Surf edit identified
  the remaining exact defect. Gamma writes an empty `FSoftObjectPath` sub-path as FString length 0;
  the editor wrote length 1 plus NUL. Both decode to an empty Python string, so structural/semantic
  checks missed the runtime-significant byte difference. The same noncanonical byte appeared in every
  editor-written move and in Torchic/Treecko `SpeciesData`, explaining both blank moves and `Unknown`.
- v0.12.1 canonicalizes empty FStrings to length 0 and adds byte-level regression coverage. The local
  build passed all 52 tests plus packaged GUI/CLI smoke. A guarded live repair canonicalized exactly
  five properties (three Moves arrays and two created SpeciesData fields), changed no decoded values,
  retained all 22,598 records and created a timestamped backup. The user's runtime retest confirmed
  that the `Unknown` species, blank move buttons, intro mismatch and Fatal Error no longer occur.
- Bag uses the five in-game pockets and supports filtered add/edit/remove, including safe insertion
  of a previously absent pocket such as TMs. Backup restore remains available from the toolbar.
- Bundled tool-only catalogs contain 118 Gamma species paths and 99 move paths. Species, nature,
  gender, status, met type, moves and PP are selected from validated controls; no game asset is
  copied into the repository or release.
- Exact Level-up, TM, HM and Egg learnsets were generated from all 118 shipped GE-1.0.0 Species
  DataAssets. Create/Edit choices are filtered by the selected species, evolution stage, current
  level and source; duplicate or incompatible moves are rejected by both GUI and domain layers.
- Exact Base PP was extracted for all 99 shipped Move Blueprints. The Moves form now edits current
  `PP` plus game-valid `PP Up` uses (0–3; zero for one-PP moves), derives serialized Max PP with the
  20%-per-use formula, and rejects impossible stored PP combinations in the domain layer.
- Pokémon > Moves now uses its lower area for four resize-aware attack-type charts. Each selected
  move is matched to its verified catalog type and displays outgoing multipliers against all 18
  defending types; the corresponding chart updates immediately when a move slot changes.
- Species-aware metadata covers 116 standard Gamma species. Ability is filtered per species with
  `(H)` Hidden Ability labels and synchronized slots; Nature labels show stat effects. Gecqua and
  MissingNo. remain explicitly game-specific/unmapped rather than receiving fabricated metadata.
- Held Item choices use the verified hold/Fling item groups and exclude Poké Balls and Key Items.
- Catalog-backed Species, Nature, Ability, Held Item, Move and Bag Item controls now support
  case-insensitive live search while retaining exact-value validation.
- Searchable controls use an owned popup instead of the native Windows ttk popdown. Typing multiple
  characters keeps focus in the entry, and opening the list with the arrow still accepts immediate
  typing without closing the popup.
- The Pokémon Stats panel shows Base and live calculated Final stats from Species, Level, Nature,
  IVs and EVs. Existing records preserve stored HP unless the Max HP sync option is enabled; new
  Pokémon enable calculated Max HP synchronization by default.
- The Stats panel now has a one-click all-252 EV action that automatically enables the over-510
  override. Its resize-aware lower pane splits into a six-column Final Stats chart and an 18-type
  matchup chart showing best STAB attack multipliers plus combined incoming defense multipliers.
- A complete GE-1.0.0 item audit found 86 concrete shipped `ItemData` assets across all five Bag
  pockets. The editor covers all 86: 35 Items, 9 Pokeballs, 26 TMs, 4 Berries and 12 Key Items.
- v0.13.0 removes `Max Revive` from writable choices because GE-1.0.0 has no matching `ItemData`,
  executable string or concrete item asset. The Bag header now opens a Catalog Info explanation with
  per-pocket counts and the boundary between concrete assets and leftover enum names.
- GE-1.0.0's Pokeball enum names 17 ball types, but only 9 have both concrete `ItemData` and Ball
  Blueprints; those same 9 are already in the editor. Dive, Dusk, Heal, Master, Nest, Net, Quick and
  Safari Ball are enum-only in this build and are not safe catalog choices.
- The packaged game also contains unused/legacy UI item icons and four blueprint-only item-like
  candidates (`Alternative Amulet`, `Rotten Leftovers`, `Shiny Ping`, `Fire Stone`). None has a
  registered `ItemData`; do not expose them as supported Bag items without runtime verification.
- A Bag record stores only `ItemName`, `ItemID` and `Quantity`. The serializer could structurally
  write an arbitrary name, but that cannot create the missing cooked ItemData, Blueprint/effect,
  icon or Asset Manager registration. Raw custom-name writing therefore remains deliberately
  unavailable: it would produce an unverified runtime reference with the same class of risk as the
  earlier parser-valid/game-invalid Pokemon records. `docs/ITEM_EXTENSION_GUIDE.md` records the
  safe boundary and the future update/mod workflow.
- v0.16.1 expands the experimental Item Mod Builder to 41 selected shipped templates across 11
  archetypes: HP/status/PP healing, Revive, Vitamin, Rare Candy, evolution/utility, held item, Berry,
  TM and Poké Ball. The form changes with the selected template and exposes only fields that are
  actually serialized there, including HP values, multipliers, boosted type/stat, any verified
  shipped move, Ball enum and catch rate. The chosen template supplies all other cooked behavior,
  icon, Blueprint, VFX and SFX dependencies. The custom item appears in its correct Bag pocket;
  held-item/Berry clones also appear in Pokémon Held Item choices. Loaded Bag, Party and every Storage
  box are checked before replacing/uninstalling a patch so a reference is not knowingly orphaned.
- Item IDs now default to a persistent numeric namespace derived from the `CSTM` FourCC and are shown
  as sequential `CSTM-######` tags. The underlying GE property is a signed `IntProperty`, so literal
  letters are not valid. The wizard retains manual numeric entry and reserves the next sequence to
  avoid reusing an identity across sessions.
- Vitamin templates now expose `EVBoostAmount` using every divisor of 252 plus Gamma's shipped
  default 10. Build-matched native disassembly confirms actual use is clamped to 100 EV in the chosen
  stat and 510 EV total. Held Item, Berry and TM templates show an inline inherited-behavior summary;
  TM explains that it can target any of 99 existing moves versus 26 shipped TM items, but cannot edit
  or create the move Blueprint itself.
- The Item Mod Builder now labels its primary help box `Effects` and renders a player-facing sentence
  for every supported archetype. The sentence follows the current display name and editable values;
  held-item type multipliers are converted to readable percentages. Cooked-template ownership and
  experimental-risk text remains separate in the muted secondary line.
- v0.16.0 adds an optional runtime Vitamin policy beside the item-pak builder: 100 or 252 per-stat,
  510 total or Unlimited, scoped to CSTM custom Vitamins or all Vitamins. The default is
  252/stat + 510 total + CSTM only. It changes in-game Vitamin use, not direct EV editing.
- The runtime installer owns a local build-matched UE4SS copy through a hash manifest, refuses to
  merge with an existing unknown loader/mod tree, blocks update/removal after managed files change,
  and refuses uninstall when extra user-mod files appear. Uninstall restores vanilla behavior.
- A headless GE-1.0.0 proof registered the exact native `CalculateVitaminGain` hook and changed its
  returned result from 0 to a sentinel 123 without writing a save. A production-form install also
  logged the intended 252/Unlimited/all-Vitamin configuration, then passed guarded uninstall.
- A headless read-only manager probe discovered representative custom Vitamin, Ball and TM assets and
  read their new IDs plus template-specific stat/Ball/rate/move fields. Real writer/pak builds for all
  three passed. Actual use/throw/teach/held-effect behavior and normal game save/reload remain a user
  acceptance step per archetype; Ball/evolution/held paths stay clearly experimental.
- The supplied Cobblemon archive contains 33 raw Minecraft OGG files and no license file. Its audio
  and the attached PNG require redistribution permission plus UE 5.6 import/cooking, so v0.16.0 does
  not bundle them. Ball clones reuse one of Gamma's nine complete cooked Ball visual/SFX sets; the
  eight enum-only Ball behaviors may reuse that visual but still have no unique assets in GE-1.0.0.
- UE4SS generated a matching `.usmap`/`.jmap`; the native 72-property ItemData schema was recovered.
  Runtime tests proved same-path Potion override priority and automatic discovery of a renamed ItemData
  under `/Game/Items/` without AssetRegistry edits. Every temporary loader/patch was removed, no save
  was written and the base pak remains unchanged.
- v0.13.2 gives Party/Storage cards a right-click Copy/Set/Release workflow. `Clone (Copy)` captures
  an immutable complete-payload preset without modifying the save and puts a readable Showdown-style
  set on the Windows clipboard. `Set` is disabled until a preset exists and then writes it only to the
  selected empty Storage slot, assigning fresh collision-free `PokemonID` and `UniqueID` values.
  For Party, every displayed empty card enables Set and redirects to/highlights the next packed-array
  position, so a user can click any empty card without needing to understand the serialization. Release
  removes a Party element or restores a fresh verified empty Storage payload and blocks the last member.
- Copy/Set/Release passed focused unit tests plus a real-story memory-only explicit Storage Set,
  425-GUID uniqueness check, GUI disabled-state/clipboard check and GES1 round-trip. No live save was written.
- Pokédex now shows types, Abilities, height/weight, base stats and all 18 incoming type multipliers.
- Pokémon edit/create/move uses a one-pass property transaction. Real-story timings measured about
  0.78 s edit, 0.94 s Storage create, 2.49 s Party create and 1.03 s Storage-to-Party move.
- Searchable Gender, Status and Met Type values now serialize back to their required Gamma enum
  prefixes; v0.7.0 incorrectly submitted display leaves such as `Male` during unrelated Stats edits.
- Automated suite passes: 69 tests plus real-story in-memory Bag insertion/removal, Party/Storage
  payload movement, empty-slot creation, EV-limit override and encrypt/decrypt verification.
- A real-story, memory-only Mudkip-to-Torchic conversion passed with all identity/ownership fields
  preserved, 22,598 property records retained and a successful GVAS/GES1 round-trip. The live save
  was not written during this verification.
- v0.8.2 GUI/CLI builds completed, the stable launcher was refreshed, and packaged CLI read-only
  validation plus packaged GUI smoke pass against the real story save. The key-free portable ZIP
  contains no runtime key, save or backup.
- v0.9.0 local GUI/CLI builds completed with 117 optional local icons embedded in the onedir GUI.
  Source and packaged GUI smoke, packaged CLI real-story read-only validation and all 49 tests pass;
  the stable launcher was refreshed. No public ZIP containing the local art cache was produced.
- v0.10.0 local GUI/CLI builds completed with the Stats EV/type-chart additions. Source UI captures
  at 1360 × 840 and 1080 × 680, all 50 tests, source/packaged GUI smoke and packaged CLI real-story
  read-only validation pass; the stable launcher now opens this build.
- v0.11.0 local GUI/CLI builds completed with four per-move attack charts. Full/minimum Moves-tab
  captures, all 51 tests, source/packaged GUI smoke and packaged CLI real-story read-only validation
  pass; the stable launcher now opens v0.11.0.
- v0.12.0 local GUI/CLI builds completed with exact dual-type Main/Preview rendering. Lucario
  full/minimum captures, all 52 tests, source/packaged GUI smoke and packaged CLI real-story read-only
  validation pass; the stable launcher now opens v0.12.0.
- v0.12.1 local GUI/CLI builds completed with canonical Unreal empty-FString serialization. All 52
  tests, packaged GUI smoke and packaged CLI real-save validation pass; the stable launcher was refreshed.
- A packaged v0.13.2 GUI/CLI build completed in versioned output because an already-running v0.12.1
  process held the canonical `dist` directory open. Packaged GUI smoke and CLI live-slot validation
  pass; the workspace-root launcher now targets the versioned v0.13.2 GUI without stopping the old process.
- The stable local `dist` launcher remains provisioned with the ignored `save_key.hex` so it runs
  directly on this machine. The distributable v0.8.1 portable ZIP is deliberately key-free; the key remains
  absent from Git tracking and GitHub publication.
- Build tests use a project-local temporary directory and every native test/PyInstaller exit code is
  checked, so a failed test can no longer be followed by a misleading successful build.
- `D:\Games\gamma-emerald-ea-windows\GammaEmeraldSaveEditor.cmd` is the stable user launcher. Each
  successful build refreshes it to open the current GUI under repository `dist`, while preserving
  the ignored local runtime key across replacement of that build folder.
- Local git repository initialized on `main`; initial implementation commit is `39bbe27`.
- GitHub repository `ladori08/gamma_emerald_save_editor` exists and admin/push access is verified.
  The user explicitly approved publishing it as a public repository on 2026-08-21.
- The public source no longer embeds the recovered live save-encryption key. Runtime key loading is
  external via `GAMMA_EMERALD_SAVE_KEY_HEX` or ignored `save_key.hex`; a literal scan is clean.
  Live saves, backups and private fixtures remain excluded.
- Sanitized v0.3 source was published on remote branch `feat/story-save-schema` as `ca26e62`;
  draft PR `#1` targets `main`. The public remote history has never referenced the embedded-key
  local history.
- The Indigo-style implementation is committed locally on `feat/story-save-schema` as `8f0d7bf`;
  `origin` points to the dedicated GitHub repository.
- Sanitized v0.4 feature source is published on the same draft PR as remote commit `3e8c2b7`.
- Sanitized v0.6 source is published on draft PR `#1` as remote commit
  `814bc53b4dac46a9f8be36ea5f8aa7d536b5b451`. Its one-commit compare contains exactly 16
  source/test/documentation files and no build artifact, game file, save, fixture or key.
- Sanitized v0.7 source is published on the same draft PR as remote commit
  `ae1814e20daba03ef69dc1929cad410634f1a291`. Its fast-forward compare contains exactly 11
  expected source/test/documentation files and no build artifact, game, save, backup or key.
- The stable-launcher template and repeat-build key-preservation logic are published source-only as
  remote commit `9a2c9c77a7f977ca4b313ecc3afdd7a237015a7f`; its compare contains exactly those two files.
- The v0.7.1 enum-prefix hotfix and regression test are published source-only as remote commit
  `da585a80ac48d6d3e80dd56130d302c6d5bf98ec`; its compare contains exactly four expected files.
- The v0.7.2 dropdown-focus/build-guard source is published as remote commit
  `a5abca18f74fe38f536147a226665ee841f3a1c5`; its one-commit compare contains exactly five
  expected source/config files and no game, save, key, binary or release artifact.
- Local v0.8.0 exact-learnset commit `9cf5035` and v0.8.1 PP Up commit `9821150` are not yet on
  GitHub. The source-only 20-file remote compare was audited clean, but publication was blocked by
  the GitHub connector's Codex usage limit; remote `feat/story-save-schema` remains at `a5abca1`.

## Safety status

- The first controlled live write and complete game round-trip passed: Potion quantity changed
  from 2 to 3 with a timestamped pre-edit backup and atomic replacement; the game displayed 3,
  resaved normally, and the resulting save revalidated with 22,479 parsed records and Potion 3.
- The current created-Pokémon damage was repaired through the guarded writer after exact four-field
  semantic-diff validation. Timestamped backup, stale-source guard, atomic replace and post-write
  payload verification all passed, but the first runtime retest still rendered both created records
  as `Unknown` and broke the battle move panel. The remaining cause was then proven as noncanonical
  empty FString encoding in `FSoftObjectPath`; v0.12.1 and the five-property live repair pass all
  offline checks, and the user confirmed the repaired Party, moves and game flow now work in Gamma.
- The later empty/default live-slot incident was recovered from the newest full pre-edit backup.
  The prior empty live file was retained as a timestamped pre-restore safety copy; source and
  packaged validation, exact backup hash comparison and 22,598-record reparse all passed.
- Story-only recovery was not sufficient because the reset QuestSlot drove the intro independently.
  The coherent Story/Quest recovery passes structural/semantic checks and the user confirmed Gamma
  resumes the intended progression instead of reopening the intro.
- Real-save validation passes AES decryption, SHA-1 verification, boundary checks, GVAS marker and
  encode/decode semantic round-trip.
- Unknown GVAS data is never regenerated and remains byte-identical unless explicitly replaced.

## Current limitation

Dex/Quest set resizing and fields absent from the young save remain pending. Create Pokemon was
runtime-unsafe through v0.12.0 because `FSoftObjectPath` empty sub-paths were noncanonical in addition
to the earlier GUID/Ability defects. v0.12.1 fixes all three known causes; the live save was repaired
and the user confirmed the reported runtime failures are gone. The Mudkip-only backup remains the fallback.
Pokémon sprites remain ignored local runtime assets so the public repository stays tool-only; Gecqua
currently uses an initials fallback. Twelve species remain fail-closed because no exact runtime-backed
Ability mapping is available. EV totals above 510 are accepted by the editor/save serializer
and have passed a controlled Gamma wild battle, post-battle EV calculation, save and data recheck
without a crash or clamp. `Max Revive` is hidden; blueprint/icon/enum-only item candidates are not
proven runtime inventory entries and remain unavailable. Unsupported structures remain read-only.

## Next verified milestone

Use v0.16.1 to build/install one disposable item per intended archetype, add it to the correct Bag
pocket, then verify display and actual use/throw/teach/held effect plus normal in-game save/reload and
editor reload. For a custom Vitamin above the vanilla cap, install the separate runtime rules with
the desired scope/caps before launching Gamma, then uninstall them after the test. Remove all Bag and
held references before replacing/uninstalling an item patch. Keep the verified Mudkip-only backup as
a fallback.
