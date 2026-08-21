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
- The v0.3 consumer GUI now follows the Indigo workflow: save toolbar, six Party slots, 14 storage
  boxes, grouped Pokemon forms, Bag editor, Dex/Progress browser, legality report and Advanced
  diagnostics/backups.
- Bundled tool-only catalogs contain 118 Gamma species paths and 99 move paths. Species, nature,
  gender, status, met type, moves and PP are selected from validated controls; no game asset is
  copied into the repository or release.
- Automated suite passes: 23 tests plus real-story in-memory species/nature/moves/PP
  edit/encrypt/decrypt verification.
- Packaged v0.3 GUI and CLI both pass against the real story save without modifying it.
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

## Safety status

- The first controlled live write and complete game round-trip passed: Potion quantity changed
  from 2 to 3 with a timestamped pre-edit backup and atomic replacement; the game displayed 3,
  resaved normally, and the resulting save revalidated with 22,479 parsed records and Potion 3.
- Real-save validation passes AES decryption, SHA-1 verification, boundary checks, GVAS marker and
  encode/decode semantic round-trip.
- Unknown GVAS data is never regenerated and remains byte-identical unless explicitly replaced.

## Current limitation

Adding/removing Pokemon or Bag array elements, Dex/Quest set resizing, fields absent from the young
save, and a controlled live game reload for species/move replacement remain pending. Indigo's
team-builder, damage calculator and custom-item creation are not yet Gamma-verified workflows.
Unsupported or structurally variable fields stay read-only.

## Next verified milestone

Review/merge draft PR `#1`, then live-test one species/move edit before tagging a public release.
