# Current State

Last updated: 2026-08-21

## Snapshot

- Project: standalone Gamma Emerald save editor; no runtime dependency on `tool_editor`.
- Target verified: Pokemon Gamma Emerald `GE-1.0.0`, Unreal Engine `5.6.1`.
- Live save folder discovered: `%LOCALAPPDATA%\PokemonEmerald\Saved\.ged`.
- Available live slots: `PokemonSaveSlot`, `QuestSlot`, `GEBerrySlot`, and `GEOptions`.
- `GES1` container reverse engineered and read-only round-trip verified against the real options save.
- Inner save identified as UE5.6 `GVAS`, class `/Script/PokemonEmerald.GE_SettingsSave`.
- GUI, CLI, guarded write/backup service, diagnostics and tagged-scalar editor implemented.
- Story GVAS recursively parses more than 22,000 tagged records with no parser error, including
  Party, 14 boxes, Daycare, Bag, Seen/Caught and progress fields.
- GUI domain tabs now expose Trainer, Party, Storage, Bag and Progress. Verified scalar/bool/string
  writes include domain legality checks and automatic Trainer name/ID synchronization.
- Automated suite passes: 19 tests plus real-story in-memory edit/encrypt/decrypt verification.
- Packaged GUI smoke test passes from `dist\GammaEmeraldSaveEditor`; packaged CLI validates the
  real options save.
- Local git repository initialized on `main`; initial implementation commit is `39bbe27`.
- GitHub repository `ladori08/gamma_emerald_save_editor` exists and admin/push access is verified.
  The user explicitly approved publishing it as a public repository on 2026-08-21.
- The public source no longer embeds the recovered live save-encryption key. Runtime key loading is
  external via `GAMMA_EMERALD_SAVE_KEY_HEX` or ignored `save_key.hex`; a literal scan is clean.
  Live saves, backups and private fixtures remain excluded.
- Sanitized source is published on remote branch `feat/story-save-schema` at `47eaa3a`; draft PR
  `#1` targets `main`. The public remote history has never referenced the embedded-key local history.
- Story-schema implementation is committed locally on `feat/story-save-schema` as `bf3f172`;
  `origin` points to the new GitHub repository.

## Safety status

- The first controlled live write and complete game round-trip passed: Potion quantity changed
  from 2 to 3 with a timestamped pre-edit backup and atomic replacement; the game displayed 3,
  resaved normally, and the resulting save revalidated with 22,479 parsed records and Potion 3.
- Real-save validation passes AES decryption, SHA-1 verification, boundary checks, GVAS marker and
  encode/decode semantic round-trip.
- Unknown GVAS data is never regenerated and remains byte-identical unless explicitly replaced.

## Current limitation

Species/move/enum asset replacement, adding/removing array elements, Dex set resizing, Quest flag
resizing, money/coins/badges fields absent from the current young save, and a live game reload test
remain pending. Unsupported fields stay read-only.

## Next verified milestone

Review/merge draft PR `#1`, then tag the first verified release when release scope is confirmed.
