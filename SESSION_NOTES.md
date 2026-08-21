# Session Notes

Last updated: 2026-08-21

## Resume here

1. Story/Quest/Berry/Options all exist and validate. Private unpacked fixtures under
   `samples/private` are ignored and must never be committed.
2. Current parser baseline: 22,479 story records, no parser error; 19 automated tests.
3. Current branch is `feat/story-save-schema`; implementation commit is `bf3f172`. Continuity-log
   updates after that commit may form a small follow-up documentation commit.
4. Repository `ladori08/gamma_emerald_save_editor` is public, and the user explicitly approved
   public publication on 2026-08-21.
5. Publish the initial main history, publish the feature branch, and use a draft PR unless the user
   explicitly requests otherwise.
6. Rebuild/package version 0.2.0 after the final test pass.
7. The first controlled live write changed Potion quantity 2 -> 3 and passed backup, atomic-write,
   visual game load, normal in-game resave, 22,479-record reparse and packaged CLI validation.
8. Public source uses external key provisioning via `GAMMA_EMERALD_SAVE_KEY_HEX` or ignored
   `save_key.hex`; the real key is not tracked. Never publish live saves, backups, keys or private
   fixtures. The current tracked-file literal scan is clean.

## Known identifiers

- Story slot: `PokemonSaveSlot`
- Story filename: `859c7fd1524eb8d6726f1233820531b8.dat`
- Options slot: `GEOptions`
- Options filename: `c4986df5d9f9ee63d369a56c49cc538f.dat`
- Filename salt: `ge-vault-2f81c4`

Sensitive cryptographic material is intentionally kept in implementation code only and must not be
duplicated into logs, issues or release notes.
