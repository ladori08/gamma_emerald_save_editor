# Current State

Last updated: 2026-08-22

## Snapshot

- Project: standalone Gamma Emerald save editor; no runtime dependency on `tool_editor`.
- Target verified: Pokemon Gamma Emerald `GE-1.0.0`, Unreal Engine `5.6.1`.
- Live save folder discovered: `%LOCALAPPDATA%\PokemonEmerald\Saved\.ged`.
- Available live slots: `PokemonSaveSlot`, `QuestSlot`, `GEBerrySlot`, and `GEOptions`.
- `GES1` container reverse engineered and read-only round-trip verified against the real options save.
- Inner save identified as UE5.6 `GVAS`, class `/Script/PokemonEmerald.GE_SettingsSave`.
- GUI, CLI, guarded write/backup service, diagnostics and schema-aware editor implemented.
- Story GVAS recursively parses more than 22,000 tagged records with no parser error, including
  Party, 14 boxes, Daycare, Bag, Seen/Caught and progress fields.
- The v0.6 consumer GUI has four focused tabs: Trainer, Pokémon, Bag and Pokédex. Party and Storage
  share one workspace with six Party cards, a compact 5 × 6 Box grid and complete-payload drag/drop.
- Empty Party and Storage cards now open a Create Pokemon form. Creation activates the game's
  complete verified empty struct template, assigns a collision-free Pokemon ID and current Trainer
  ownership, and accepts the same catalog/scalar/move fields used by occupied records.
- Bag uses the five in-game pockets and supports filtered add/edit/remove, including safe insertion
  of a previously absent pocket such as TMs. Backup restore remains available from the toolbar.
- Bundled tool-only catalogs contain 118 Gamma species paths and 99 move paths. Species, nature,
  gender, status, met type, moves and PP are selected from validated controls; no game asset is
  copied into the repository or release.
- Species-aware metadata covers 116 standard Gamma species. Ability is filtered per species with
  `(H)` Hidden Ability labels and synchronized slots; Nature labels show stat effects. Gecqua and
  MissingNo. remain explicitly game-specific/unmapped rather than receiving fabricated metadata.
- Held Item choices use the verified hold/Fling item groups and exclude Poké Balls and Key Items.
- Pokédex now shows types, Abilities, height/weight, base stats and all 18 incoming type multipliers.
- Pokémon edit/create/move uses a one-pass property transaction. Real-story timings measured about
  0.78 s edit, 0.94 s Storage create, 2.49 s Party create and 1.03 s Storage-to-Party move.
- Automated suite passes: 28 tests plus real-story in-memory Bag insertion/removal, Party/Storage
  payload movement, empty-slot creation, EV-limit override and encrypt/decrypt verification.
- Packaged v0.6 GUI and CLI both pass smoke/read-only validation against the real story save.
- The ignored local v0.6 release is provisioned with `save_key.hex` beside both launchers so it runs
  directly on this machine. The key remains absent from Git tracking and GitHub publication.
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

## Safety status

- The first controlled live write and complete game round-trip passed: Potion quantity changed
  from 2 to 3 with a timestamped pre-edit backup and atomic replacement; the game displayed 3,
  resaved normally, and the resulting save revalidated with 22,479 parsed records and Potion 3.
- Real-save validation passes AES decryption, SHA-1 verification, boundary checks, GVAS marker and
  encode/decode semantic round-trip.
- Unknown GVAS data is never regenerated and remains byte-identical unless explicitly replaced.

## Current limitation

Dex/Quest set resizing, fields absent from the young save, and controlled live-game reloads for the
new Bag/Party/Storage/creation structural edits remain pending. Pokémon sprites were not bundled so
the public repository stays tool-only. Unsupported structures remain read-only.

## Next verified milestone

Live-test one newly created Pokémon with game load and normal in-game resave before tagging a release.
