# Session Notes

Last updated: 2026-09-03

## Resume here

1. Story/Quest/Berry/Options all exist and validate. Private unpacked fixtures under
   `samples/private` are ignored and must never be committed.
2. Current parser baseline: 22,482 story records, no parser error; 41 automated tests.
3. Current branch is `feat/story-save-schema`; v0.6 species-aware editor source is published on
   the existing draft PR as remote commit `814bc53b4dac46a9f8be36ea5f8aa7d536b5b451`.
4. Repository `ladori08/gamma_emerald_save_editor` is public, and the user explicitly approved
   public publication on 2026-08-21.
5. Publish the initial main history, publish the feature branch, and use a draft PR unless the user
   explicitly requests otherwise.
6. Local v0.8.1 is built under `dist`; the stable root launcher was refreshed. The key-free portable
   release and packaged CLI real-story validation pass; current-context GUI smoke execution remains pending.
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
21. Sanitized v0.7 source is published on draft PR `#1` as remote commit `ae1814e`. The compare from
    the previous clean head contains exactly 11 expected source/test/docs files and no artifacts.
22. The stable user entry point is workspace-root `GammaEmeraldSaveEditor.cmd`. `scripts/build.ps1`
    refreshes it after every successful build and preserves the ignored key from the prior `dist`
    before PyInstaller replaces that folder. A root-launcher GUI smoke test passed.
23. The launcher template/build logic is backed up source-only on the draft PR as remote commit
    `9a2c9c7`; GitHub compare shows exactly the expected two files and no generated launcher/binary.
24. v0.7.1 fixes v0.7.0 searchable-enum serialization: Gender/Status/Met display values regain their
    required Gamma prefixes before comparison/write, so unrelated Stats Apply no longer fails.
25. Source GUI staged all six EVs at 252 (total 1,512) and reparsed the real story payload in memory.
    This proves editor/save acceptance only; Gamma runtime behavior above 510 remains unverified.
26. v0.7.1 hotfix source/version/test files are backed up on draft PR `#1` as remote commit
    `da585a8`; the compare contains exactly four expected files and no artifacts.
27. User live-tested an over-510 EV save after v0.7.1: Gamma loaded/saved without an immediate
    reaction or crash. Keep battle/level-up/PC-transfer recalculation as pending edge-case checks.
28. User then defeated a wild Pokémon with the over-cap Pokémon, triggering post-battle EV gain and
    recalculation, saved again and rechecked the data successfully. Over-510 EV is game-verified for
    the current Gamma build; unlike Indigo, no game-side cap patch is presently required.
29. v0.7.2 replaces native Windows searchable combobox popdowns with an Entry-backed owned popup.
    Multi-character typing and arrow-open-then-type both retain entry focus; source/full-app,
    packaged build and packaged release smoke checks pass against the current story save.
30. `scripts/build.ps1` now uses project-local test temp storage and checks every native exit code.
    The stable root launcher was refreshed and opened the new build successfully.
31. v0.7.2 source/config is backed up on draft PR `#1` as remote commit `a5abca1`. Its compare from
    the previous remote head contains exactly five expected files and no artifact or private data.
32. v0.8.0 generates exact Level-up/TM/HM/Egg learnsets from all 118 shipped Species DataAssets.
    Create/Edit move lists filter by selected species, evolution stage, current level and source;
    GUI and domain validation reject duplicates and incompatible moves.
33. The v0.8.0 source suite passes 38 tests. Packaged GUI move-filter smoke and packaged CLI
    real-story read-only validation pass. The local release ZIP is key-free and no game asset,
    extracted asset, save, backup or binary is eligible for source publication.
34. v0.8.1 extracts Base PP for all 99 shipped Move Blueprints. Moves now expose current `PP` and
    `PP Up`; Max PP is derived at 20% of Base PP per use with 0–3 uses, while one-PP moves allow zero.
    The domain layer rejects impossible Max PP/current PP combinations.
35. v0.8.1 passes 41 tests and packaged CLI real-story read-only validation. Build temp directories
    now receive a unique ID so Windows ownership from a previous run cannot break later builds.
    Local GUI/CLI hashes and the key-free portable ZIP are recorded in `WORKLOG.md`.
36. Local v0.8.0/v0.8.1 commits are `9cf5035` and `9821150`. A source-only compare against remote
    `a5abca1` contains exactly 20 expected files and no private/build artifacts. GitHub publication
    is pending because the connector hit the Codex usage limit; do not claim these commits are remote.
37. A full GE-1.0.0 packaged-content audit found 86 concrete `ItemData` assets. The editor covers
    all 86 across Items 35, Pokeballs 9, TMs 26, Berries 4 and Key Items 12.
38. The editor has one additional choice, `Max Revive`. There is no matching packaged `ItemData` or
    executable identifier, so the earlier in-memory reparse is not runtime proof. Treat it as
    unverified and do not claim the item catalog is exactly asset-backed while it remains exposed.
39. The executable's Pokeball enum contains 17 values, but only 9 have concrete `ItemData` plus
    Ball Blueprints. Dive, Dusk, Heal, Master, Nest, Net, Quick and Safari Ball are dormant enum
    support in GE-1.0.0 and must not be added merely from enum names.
40. Unreferenced item UI assets include legacy/placeholders. Alternative Amulet, Rotten Leftovers,
    Shiny Ping and Fire Stone also have Blueprints but no registered `ItemData`; require controlled
    runtime proof before exposing them in the Bag catalog. No extracted asset or key entered source.
41. User live-tested two editor-created Party Pokémon. Both displayed as `Unknown` with `?` portraits,
    and entering a wild battle produced an access-violation Fatal Error. Treat Create Pokemon as
    runtime-unsafe in v0.8.1; in-memory GVAS/GES1 validation was insufficient.
42. Read-only inspection found one duplicated GUID group among all 425 `UniqueID` properties: both
    created Party records and the original empty Box template share the same value. `PokemonID`
    generation is separate and was unique; creation must also generate a new 128-bit `UniqueID`.
43. Treecko was serialized with `EPokemonAbility::Silvano`; after Gamma loaded/resaved it, the field
    became `EPokemonAbility::EPokemonAbility_MAX`. The executable contains 52 concrete Ability enum
    values, while imported metadata uses 52 additional unsupported names. Filter/replace the source
    before allowing creation or Ability edits.
44. The newest inspected pre-edit backup containing only the original Mudkip is the backup stamped
    `20260822-144442`. Do not restore it automatically: restoration is a user-authorized live-save
    mutation and could discard later legitimate progress.
45. User approved proceeding with the source fix/build. v0.8.2 generates a random 128-bit Unreal
    Guid for each creation, rejects any collision across the whole document and reports duplicated
    occupied/empty-template identities through legality checks.
46. Writable Abilities are filtered to the 52 concrete enum values in the GE-1.0.0 executable;
    unsupported values and `*_MAX` sentinels are rejected in the domain layer. Treecko now offers
    Overgrow only. Ten species with no remaining runtime-backed mapping are fail-closed.
47. The suite passes 45 tests. A real-backup in-memory test created Torchic then Treecko, retained
    425 unique GUIDs, selected Blaze/Overgrow and passed GVAS plus GES1 round-trip. No save was written.
48. v0.8.2 GUI/CLI and a key-free portable ZIP are built. Packaged CLI real-save validation and GUI
    smoke pass. The stable root launcher points to v0.8.2; the game process was not stopped.
49. A current-save repair dry-run changes exactly four fields: the two created `UniqueID` values and
    Treecko's Ability/slot to Overgrow/0. It preserves all 22,598 parsed records and passes encrypted
    round-trip. Do not execute the live write until the user explicitly selects repair over restore.
50. The user explicitly selected repair. With game and editor closed, the guarded writer created a
    timestamped backup and applied only those four fields atomically. Post-write decode/reparse kept
    all 22,598 records, all 425 `UniqueID` values are distinct, and Treecko is Overgrow/slot 0. The
    repaired save still needs an in-game portrait, wild-battle, normal-save and reload verification.
51. v0.9.0 adds ignored local Pokémon art (117/118 icons; Gecqua fallback), compact Party/Storage
    icons, a responsive large preview and a resize-aware horizontal evolution chart. Create/species
    conversion now loads a full conservative Lv. 5 profile while preserving identity/ownership.
    A real-save memory-only conversion, 49 tests, source/packaged GUI smoke and packaged CLI
    validation pass. Twelve species remain fail-closed until exact runtime Abilities are known.
52. v0.10.0 adds a Max-all-EVs action that sets all six values to 252 and automatically enables the
    over-510 override. Pokémon > Stats now uses its lower space for a responsive six-column Final
    Stats chart and an 18-type best-STAB Attack/combined Defense chart. Full/minimum UI captures,
    50 tests, source/packaged GUI smoke and packaged CLI real-save validation pass; no save was written.
53. v0.11.0 adds four responsive attack-type charts beneath Pokémon > Moves, one per move slot. Each
    chart updates immediately from the move's verified catalog type and covers all 18 defending types.
    Full/minimum captures, 51 tests, source/packaged GUI smoke and packaged CLI real-save validation
    pass; the stable launcher was refreshed and no save was written.
54. v0.12.0 fixes Main/Preview typing to use exact mapped species types instead of only the asset
    folder category. Lucario now displays Fighting + Steel with two standardized badges, split Preview
    colors and readable contrast-aware text. Full/minimum captures, 52 tests, source/packaged GUI
    smoke and packaged CLI validation pass; no save was written.
55. On 2026-08-31 the live story slot was replaced by a nearly empty game-generated state with
    0.958 seconds of play time, no Trainer name, Party, Bag, location or progress fields, and 22,385
    parsed records; a new access-violation crash followed. On 2026-09-02 the user authorized recovery
    from the newest full pre-edit backup. Guarded restore first retained the empty target as a
    timestamped pre-restore safety copy, then restored an exact backup match with 22,598 records,
    Mudkip/Torchic/Treecko and no GUID or Ability findings. Packaged validation passes; in-game load,
    battle, normal save and reload are the next required checks.
56. The story-only restore then loaded the old three-Pokemon Party into the reset QuestSlot's intro.
    At the scripted starter battle the UI showed four Party indicators and blank move buttons. Its
    battle-start auto-save kept all three restored move arrays intact on disk, so moves were not
    deleted; progression slots were incoherent. Live Berry and Options payloads exactly match their
    known-good private captures. The private Quest payload contains the prior Birch Lab/Oldale flags
    and has been packed into a validated offline QuestSlot candidate. Once the user closes the game,
    preserve the newly auto-saved Story and Quest targets, then restore the full story backup and
    this Quest candidate together before retesting.
57. After the game fully exited, a coordinated transaction preserved both newer autosaves as
    timestamped pre-restore safety copies and atomically installed the full Story plus prior-progress
    Quest candidate. All four live slots pass packaged validation. Story reparses 22,598 records with
    Mudkip/Torchic/Treecko, all move arrays and nine Bag entries; there are no GUID/Ability findings.
    Quest contains the Birch Lab, spoke-after-save, helped-Birch and Oldale flags. Berry and Options
    remain byte-identical to known-good captures. Controlled game retesting is pending.
58. The coordinated runtime test bypassed the intro, but Party rendered Torchic and Treecko as
    `Unknown`; a normal wild battle with Mudkip showed four blank move buttons even though the live
    story still contains Mudkip's four valid move/PP arrays. This disproves runtime safety after the
    v0.8.2 GUID/Ability fix. Do not create Pokémon or keep repairing guessed fields. The verified
    pre-creation backup has one native Lv. 8 Mudkip with Growl/Tackle/Mud-Slap, zero EVs, six Bag
    entries, 22,485 records and no legality findings. Once the game exits, restore that Story while
    keeping the recovered QuestSlot; expected rollback cost is about 7 minutes 33 seconds plus the
    two invalid created Pokémon and three later Bag entries.
59. The user then supplied a precise game/editor comparison: three moves changed in Gamma survived,
    but adding Surf in the editor made every move disappear again. The automatic pre-edit backup
    proved Gamma encodes the empty third FString in each `FSoftObjectPath` as length 0, while the
    editor encoded length 1 plus NUL. Torchic/Treecko SpeciesData had the same bad byte and native
    Mudkip did not, exactly explaining `Unknown` plus blank moves. v0.12.1 canonicalizes empty FString
    encoding and adds byte-level regression checks. All 52 tests, build, packaged GUI smoke and CLI
    validation pass. A guarded live repair changed only the encoding of three Moves arrays and two
    SpeciesData fields (14-byte reduction), preserved all 22,598 records/decoded values and created a
    timestamped backup. All four live slots revalidate; runtime retest is pending. Keep the native
    Mudkip-only backup as fallback rather than applying further guessed repairs.
60. Added `docs/SAVE_RUNTIME_DIAGNOSTICS.md` as a detailed self-service guide and linked it from the
    README. It covers safety, Story/Quest/Berry/Options coherence, container/parser/legality/runtime
    proof levels, symptom triage, controlled A/B capture, crash correlation, the exact empty-FString
    bug, rollback criteria and a reusable incident template. Added `scripts/diagnose-live-save.ps1`,
    which is strictly read-only and reports running processes, every live slot summary/hash, recent
    backups, crash address/stack hashes and the diagnostics log tail. An end-to-end run completed
    successfully and correctly warned that the current game process was active; the new files contain
    no save-key literal or machine-specific slot filename.
61. User confirmed the v0.12.1 repaired save no longer shows the reported Fatal Error, new-game intro,
    `Unknown` Party species or blank move buttons. They then raised the deliberately limited Bag catalog
    and inability to remove added Pokémon. v0.13.0 now exposes only the 86 concrete GE-1.0.0 ItemData
    assets, removes asset-less Max Revive and explains why 8 enum-only Balls remain hidden. Occupied
    Party/Storage cards have right-click Clone/Release: clones preserve full payloads but receive fresh
    PokemonID/GUID values; releases remove Party elements or restore a fresh verified empty Box payload,
    with confirmation and a final-Party guard. All 54 tests, source/packaged GUI smoke, packaged CLI
    validation and a real-story memory-only Party/Storage clone-release encrypted round-trip pass with
    all 425 GUIDs unique. No live save was written. An old editor process locked canonical `dist`, so it
    was left untouched; versioned v0.13.0 GUI/CLI outputs were built and the root launcher points to the
    new GUI. Next test is a controlled Save + Backup, game load/resave and editor reload.
62. User clarified that Clone should behave as a reusable preset rather than immediately choosing a
    destination. v0.13.1 now makes `Clone (Copy)` read-only: it captures the complete serialized payload,
    displays the active species and copies a Showdown-style text set to the Windows clipboard. Right-click
    `Set` is visibly disabled until a preset exists, on occupied slots and on impossible Party gaps; when
    enabled it fills exactly the selected empty card with fresh PokemonID/GUID values. Release behavior is
    unchanged. The preset survives repeated Sets but clears when another save is opened/reloaded. All 55
    tests, a real-story memory-only explicit Storage Set, GUI state/clipboard behavior, packaged GUI smoke
    and packaged CLI validation of all four slots pass. No live save was written. Versioned v0.13.1 outputs
    are built and the root launcher points to the new GUI.
63. User requested forgiving Party placement so people do not need to understand packed-array slots.
    v0.13.2 enables Set on every displayed empty Party card once a preset exists, maps any such click
    to the next actual Party position and highlights that resulting card; status reports when a farther
    click was redirected. Storage remains exact-slot. All 56 tests pass. A source GUI real-save run
    verified clicking displayed slot 6 with a three-member Party created/highlighted slot 4 entirely in
    memory. Versioned packaged GUI smoke and all four packaged CLI slot validations pass; no live save
    was written and the root launcher now targets v0.13.2.
64. User asked whether missing early-access items can be added, ideally directly through the editor.
    The installed GE-1.0.0 manifest still contains exactly 86 concrete ItemData assets, all already
    covered. The executable contains eight extra Ball enum names, but no matching ItemData or concrete
    Ball Blueprints; four other candidates have Blueprints without registered ItemData. Bag rows only
    carry ItemName/ItemID/Quantity, so an arbitrary string can serialize but cannot create runtime
    content and may yield Unknown/blank/crash behavior. Arbitrary raw-name writing remains unavailable.
    Added `docs/ITEM_EXTENSION_GUIDE.md` with the game-update, mod-asset and controlled-test paths; no
    game file, live save or editor executable was changed.
65. User proposed a full in-editor item creation/packing wizard and cited Icarus modding. Research
    confirmed Icarus primarily adds/patches named rows in JSON DataTables, while its Blueprint path
    still requires the matching Unreal version, a matching project, cooking and UnrealPak. Gamma's
    embedded project descriptor reports UE 5.6 and native PokemonEmerald/Editor/GESaveGuard modules.
    Its installed item and Ball packages are unversioned cooked assets; local inspection of Potion,
    Ultra Ball and its Blueprint yields RawExport without the absent source/PDB/usmap schema, and the
    Ball depends on several visual/audio/Blueprint assets. Gamma has one encrypted V11 pak, no adjacent
    signature, and no documented Mods directory. A harmless offline V11 `_P.pak` with mount point
    `../../../` was constructed and read back, then deleted without installation. Runtime mounting and
    new-asset discovery are still hypotheses. Added `docs/ITEM_MOD_WIZARD_FEASIBILITY.md` with a phased
    design. The game was already running and was neither stopped nor modified; no live save was written.
66. User explicitly authorized the next reversible mount proof. After confirming Gamma was closed,
    built a 590-byte unencrypted V11 marker pak with mount point `../../../`, verified its single
    internal Mods path and installed it without touching the base pak. Gamma ignored the arbitrary
    `GammaEditorMountProbe_P.pak` basename: base pak was runtime-locked but probe allowed exclusive
    access. After stopping only the headless test process, renamed the same bytes to the build-matched
    `PokemonEmerald-Windows_0_P.pak` and relaunched headless. Both base and probe then rejected
    exclusive access while Shipping stayed alive, proving external patch-container mounting and the
    required naming convention. Stopped the exact test PID, removed the installed probe and all build
    temp, and verified zero Gamma processes/probe files remain. Base pak retains original byte size,
    timestamp and SHA-256 `2DB705FA9ABCB415C7D73772FF7A8584C021B703D745BDA70D209DD3ABE1CA10`.
    No asset override or live-save write occurred. Next blocker is unversioned property mapping plus
    Asset Registry/new-ItemData discovery.
67. User asked to continue implementation. Generated build-matched UE4SS USMAP/JMAP artifacts locally,
    recovered the native 72-field ItemData schema, and proved both same-path override priority and
    automatic new ItemData discovery under `/Game/Items/`. Implemented v0.14.0's experimental
    Potion-derived Item Mod Builder with environment checks, validated JSON-driven asset cloning,
    V11 packing, SHA/ownership guarded install/uninstall and dynamic Bag integration. Four new tests
    bring the suite to 60; source GUI smoke, real cooked-asset build/list and guarded local
    install/readback/uninstall all pass. All test loaders/installed patches are removed, no live save
    was written, and the base pak hash is unchanged. Runtime Bag/use/game-save acceptance is the next
    user test before adding Ball/TM/Berry/held-item/Blueprint templates. Packaged v0.14.0 GUI/CLI build
    and GUI smoke pass; stable root launcher now opens the new build.

68. User requested every previously discussed item-wizard section, explicitly including Balls, and
    supplied a Poké Ball sprite sheet plus a local Cobblemon SFX ZIP. Audited all 86 shipped GE-1.0.0
    ItemData pairs and expanded v0.15.0 to 41 selected templates across 11 archetypes. The writer now
    preserves each cooked template's dependency graph while changing validated identity/text/price
    fields and serialized template-specific integers, floats, enums or TM soft-object reference. A
    headless read-only runtime probe discovered representative custom Vitamin, Ball and TM assets and
    reported their new IDs plus Speed/QuickBall/3.5/Surf overrides. Three real standalone pak builds
    also list the expected asset pairs. All temporary loader/patch files were removed; no live save was
    written and the base pak SHA-256 remains unchanged. The GUI adds archetype/template selectors,
    dynamic effect fields, correct Bag/held-item integration, and loaded Bag/Party/all-Box reference
    guards before replacement/uninstall. The supplied archive has 33 Minecraft OGG sources and no
    license file; the PNG/OGGs require redistribution permission and UE 5.6 import/cooking, so they are
    not bundled. Ball clones currently reuse Gamma's nine cooked visual/SFX sets, while eight
    enum-only Ball behaviors remain experimental. All 63 tests, source/packaged GUI smoke and
    packaged read-only live-slot validation pass; the stable launcher now targets v0.15.0. User
    gameplay-effect acceptance remains pending.

69. User requested automatic recognizable Item IDs, configurable Vitamin EV gain, inline Held
    Item/Berry behavior help and clarification of the TM builder's purpose. GE's ItemID schema is a
    signed IntProperty, so the editor now reserves sequential numeric IDs derived from the `CSTM`
    FourCC and displays them as `CSTM-######` tags. Build-matched native disassembly confirms Vitamin
    gain is `min(configured amount, 100 - stat EV, 510 - total EV)`; the wizard exposes all divisors
    of 252 plus shipped default 10 and explains runtime clamping. Held Item/Berry templates now show
    inherited-effect summaries. TM help explains that clones can target any of 99 existing moves
    versus only 26 shipped TM items, but cannot author/edit move logic. A real custom Protein runtime
    probe was discovered with the CSTM-derived ID, Speed and EVBoostAmount 84; its temporary loader and
    patch were removed, no save was written and the base pak hash remained unchanged.

70. User approved a runtime Vitamin cap feature after clarifying that it must affect item use rather
    than add a redundant direct-EV button. Before implementation, the complete v0.15.1 source snapshot
    was published as remote commit `66b32c7fd733eccaffad477922411c5d65c27982`, then work continued on
    `feat/vitamin-runtime-patch`. Implemented editor-owned build-matched UE4SS installation with
    100/252 per-stat, 510/Unlimited total and CSTM-only/all-Vitamin choices. A headless proof invoked
    the exact native `CalculateVitaminGain` function: vanilla returned 0 and the post-hook returned
    sentinel 123, proving return override rather than log-only registration. A production-form
    252/Unlimited/all install logged the active hook and was removed through its ownership guard.
    Every probe changed zero save files; the base pak remained byte-identical. Four tests bring the
    suite to 69. Source/packaged GUI smoke and packaged read-only live-slot validation pass; the
    stable root launcher now targets v0.16.0.

71. User clarified that `Behavior summary` should read like an item guide's Effects section, using
    Silk Scarf's plain held effect as the example. Renamed the box to `Effects` and added a pure
    player-facing formatter for every supported archetype. It uses the custom display name when set,
    falls back to the selected template name for the default `Custom Item`, and updates live when
    effect fields change. Silk Scarf now turns type `Normal` and multiplier `1.2` into `raises the
    power of Normal-type moves by 20%`; Vitamin and TM summaries likewise follow selected EVs/move.
    Technical clone/risk text remains in the separate muted line. Suite is now 70 tests;
    source/packaged GUI smoke and packaged read-only live-slot validation pass. The stable launcher
    now targets v0.16.1.

## Local identifiers

Do not record local save filenames, filename salts or cryptographic material in continuity files.
Discover supported slots through the CLI and keep machine-specific identifiers outside source.

Sensitive cryptographic material is externalized to an environment variable or ignored local
`save_key.hex`; it must never be committed or duplicated into logs, issues or release notes.
