# Session Notes

Last updated: 2026-08-22

## Resume here

1. Story/Quest/Berry/Options all exist and validate. Private unpacked fixtures under
   `samples/private` are ignored and must never be committed.
2. Current parser baseline: 22,482 story records, no parser error; 32 automated tests.
3. Current branch is `feat/story-save-schema`; v0.6 species-aware editor source is published on
   the existing draft PR as remote commit `814bc53b4dac46a9f8be36ea5f8aa7d536b5b451`.
4. Repository `ladori08/gamma_emerald_save_editor` is public, and the user explicitly approved
   public publication on 2026-08-21.
5. Publish the initial main history, publish the feature branch, and use a draft PR unless the user
   explicitly requests otherwise.
6. Local v0.7.0 is built under `release`; packaged GUI/CLI pass smoke/read-only validation against
   the story save. No v0.6 structural live write was attempted.
7. The first controlled live write changed Potion quantity 2 -> 3 and passed backup, atomic-write,
   visual game load, normal in-game resave, 22,479-record reparse and packaged CLI validation.
8. Public source uses external key provisioning via `GAMMA_EMERALD_SAVE_KEY_HEX` or ignored
   `save_key.hex`; the real key is not tracked. Never publish live saves, backups, keys or private
   fixtures. The current tracked-file literal scan is clean.
9. Sanitized v0.3 snapshot `ca26e62` is on `feat/story-save-schema`; draft PR `#1` targets `main`.
   Remote public history contains only the safe initialization and sanitized feature snapshots.
10. The v0.4 GUI has Trainer/Pokémon/Bag/Pokédex tabs. Party and Storage share drag/drop cards;
    Bag has five filtered pockets with add/edit/remove; Pokédex shows species info; EV total cap can
    be toggled. Real-save in-memory mutation/encrypt/decrypt passes, but live game reload is pending.
11. Sanitized v0.4 feature source is published as `3e8c2b7` on draft PR `#1`; a documentation-only
    follow-up records final release hashes.
12. Empty Party/Storage cards now expose Create Pokemon. A verified empty Box struct is activated
    in place or appended to Party, then receives a catalog Species DataAsset, unique Pokemon ID,
    current Trainer ownership and validated form values. Source GUI creation, GVAS reparse and GES1
    encode/decode pass in memory; controlled live-game load/resave remains pending.
13. Sanitized v0.5 feature source is published as remote commit `ee750bb`. Its compare against the
    prior remote head contains exactly 13 source, test and continuity files and no artifacts.
14. v0.6 adds metadata for 116 standard Gamma species, Species-filtered Ability choices with `(H)`
    markers, annotated Nature labels, holdable-only Held Item choices, and detailed Pokédex stats/
    abilities/type defenses. Gecqua and MissingNo. are intentionally unmapped.
15. One-pass property transactions reduce real-story operations to about 0.78 s edit, 0.94 s Box
    creation, 2.49 s Party creation and 1.03 s drag/drop.
16. Sanitized v0.6 source was published as one fast-forward commit over the prior clean remote
    head. GitHub compare reports exactly 16 source/test/documentation files and no artifacts.
17. After the first local v0.6 launch reported a missing runtime key, the ignored release folder
    and local ZIP were provisioned with `save_key.hex` beside GUI/CLI. Release CLI validation then
    passed. The key remains excluded from Git and GitHub.
18. v0.7 makes all large catalog dropdowns editable with case-insensitive live filtering and exact
    catalog validation. The Stats tab calculates Base/Final stats live from Species/Level/Nature/
    IV/EV and optionally synchronizes stored Max HP. Max Revive was added to Items.
19. The v0.7 automated suite passes 32 tests; the packaged GUI smoke test and packaged CLI real-story
    validation pass. Revive-to-Max-Revive also reparses in memory with no live-save write.
20. The user explicitly authorized killing only `GammaEmeraldSaveEditor` when tests/builds need it;
    do not infer permission to stop the game process.

## Local identifiers

Do not record local save filenames, filename salts or cryptographic material in continuity files.
Discover supported slots through the CLI and keep machine-specific identifiers outside source.

Sensitive cryptographic material is externalized to an environment variable or ignored local
`save_key.hex`; it must never be committed or duplicated into logs, issues or release notes.
