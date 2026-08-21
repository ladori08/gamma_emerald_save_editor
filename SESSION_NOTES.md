# Session Notes

Last updated: 2026-08-22

## Resume here

1. Story/Quest/Berry/Options all exist and validate. Private unpacked fixtures under
   `samples/private` are ignored and must never be committed.
2. Current parser baseline: 22,479 story records, no parser error; 23 automated tests.
3. Current branch is `feat/story-save-schema`; implementation commit is `bf3f172`. Continuity-log
   updates after that commit may form a small follow-up documentation commit.
4. Repository `ladori08/gamma_emerald_save_editor` is public, and the user explicitly approved
   public publication on 2026-08-21.
5. Publish the initial main history, publish the feature branch, and use a draft PR unless the user
   explicitly requests otherwise.
6. Local v0.3.0 is built under `release`; packaged GUI/CLI pass against the story save without
   changing its hash.
7. The first controlled live write changed Potion quantity 2 -> 3 and passed backup, atomic-write,
   visual game load, normal in-game resave, 22,479-record reparse and packaged CLI validation.
8. Public source uses external key provisioning via `GAMMA_EMERALD_SAVE_KEY_HEX` or ignored
   `save_key.hex`; the real key is not tracked. Never publish live saves, backups, keys or private
   fixtures. The current tracked-file literal scan is clean.
9. Sanitized remote snapshot `47eaa3a` is on `feat/story-save-schema`; draft PR `#1` targets `main`.
   Remote public history contains only the safe initialization and sanitized feature snapshot.
10. The v0.3 GUI has Indigo-style Trainer/Party/Storage/Bag/Dex/Legality/Advanced tabs, plus
    tool-only catalogs for 118 species and 99 moves. Adding/removing variable-size structures and
    team-builder/damage/custom-item workflows remain deliberately disabled until Gamma-verified.

## Known identifiers

- Story slot: `PokemonSaveSlot`
- Story filename: `859c7fd1524eb8d6726f1233820531b8.dat`
- Options slot: `GEOptions`
- Options filename: `c4986df5d9f9ee63d369a56c49cc538f.dat`
- Filename salt: `ge-vault-2f81c4`

Sensitive cryptographic material is externalized to an environment variable or ignored local
`save_key.hex`; it must never be committed or duplicated into logs, issues or release notes.
