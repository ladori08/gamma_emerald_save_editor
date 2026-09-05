# Project Checklist

| Area | Requirement | Status | Evidence |
|---|---|---:|---|
| Container | Validate GES1 magic/version/bounds | Done | Unit + real options save |
| Container | Verify SHA-1 before parsing | Done | Real options save |
| Container | AES decrypt/encrypt semantic round-trip | Done | Real options save |
| Secrets | External key provisioning; no tracked literal | Done | Env/file tests + literal scan |
| GVAS | Read UE5.6 header/custom versions/class | Done | Real options save |
| GVAS | Preserve unknown bytes | Done | Architecture + round-trip tests |
| Editing | Fixed-size classic scalar properties | Done | Synthetic round-trip tests |
| Safety | Game-running guard | Done | Service implementation |
| Safety | Stale-source guard | Done | Service implementation |
| Safety | Timestamped backup | Done | Service implementation |
| Safety | Atomic and verified write | Done | Service implementation |
| Recovery | Validated backup restore | Done | Service implementation |
| Recovery | Repair duplicated created-Pokémon identity/Ability | Done | Guarded live write + timestamped backup + 22,598-record post-write reparse |
| Recovery | Recover empty/default live story slot | Partial | Guarded restore + pre-restore safety copy + exact backup hash + 22,598-record reparse; game retest pending |
| Recovery | Keep Story/Quest/Berry slot generations coherent | Partial | Coordinated Story/Quest restore passes; Berry/Options match known-good captures; game retest pending |
| UX | GUI overview/properties/backups/diagnostics | Done | Packaged smoke test exit 0 |
| Diagnostics | Self-service runtime triage | Done | Detailed guide + tested read-only PowerShell report |
| UX | Indigo-style Trainer/Party/Storage/Bag/Dex/Legality workspace | Done | Real-save GUI interaction + packaged smoke test |
| UX | Unified Party/Storage cards with drag/drop | Partial | Real-save in-memory payload move; live reload pending |
| UX | Right-click Party/Storage Copy, Set and Release | Partial | Disabled Set + Showdown clipboard + exact Box/forgiving Party targeting pass; live reload pending |
| UX | Focused Trainer/Pokémon/Bag/Pokédex navigation | Done | Source + packaged GUI smoke tests |
| UX | Large Pokémon preview + compact Party/Storage icons | Done | 117 local icons + initials fallback + source UI capture |
| UX | Exact single/dual type badges + contrast colors | Done | Lucario Fighting/Steel full/minimum UI captures + GUI smoke |
| UX | Responsive Pokémon Main evolution chart | Done | Horizontal/full-size + minimum-window capture; branch compaction |
| CLI | list/summary/validate/unpack/pack/name | Done | Real options save |
| Trainer | Identity/time/location + synchronized name/ID | Partial | Real story save + in-memory write |
| Party | Pokemon/stats/IV/EV/HP/friendship | Done | Real Party record + validated writes |
| Party | Species/nature/moves/PP catalogs and writes | Partial | Real-save in-memory round-trip; live reload pending |
| Party | Exact species/stage Level-up/TM/HM/Egg move filters | Done | 118 shipped Species DataAssets + domain/UI tests |
| Party | Base PP + game-valid PP Up scaling | Done | 99 shipped Move Blueprints + formula/domain tests |
| UX | Four per-move attack type charts | Done | 99 move types + 18-type test + full/minimum UI captures |
| Party | Species-filtered Ability + Hidden Ability labels | Partial | Runtime-filtered; exact mappings remain unavailable for 12 blocked species |
| Party | Full species-profile load on create/conversion | Partial | 106 runtime-backed species; real-save memory-only conversion; 12 Ability-blocked |
| Party | Annotated Nature + holdable-item filters | Done | Unit/UI catalog checks |
| Party | Live Base/Final stat calculation | Done | Formula tests + real-save GUI load |
| Party | One-click all-252 EV fill + automatic override | Done | Source/packaged GUI smoke + 1,512 EV assertion |
| UX | Final Stats column + Attack/Defense type charts | Done | 18-type catalog test + 1360/1080 UI captures |
| Party | Searchable enum serialization | Done | Gender/Status/Met prefix regression + real-save in-memory Apply |
| Party | EV total above 510 | Done | 1,512 stored; wild battle + EV gain + save/recheck passed |
| UX | Searchable validated catalog dropdowns | Done | Multi-key/arrow focus tests + packaged GUI smoke |
| Performance | One-pass edit/move transaction | Done | Real story: ~0.78 s edit, ~1.03 s move |
| Party | Create from verified empty template | Done | v0.12.1 GUID/Ability/path fixes; guarded repair + user runtime retest passed |
| Party | Collision-free created-Pokémon UniqueID | Done | Two sequential creations left all 425 real-save GUIDs unique |
| Party | Exact runtime Ability enum validation | Done | 52-value executable whitelist + sentinel rejection + regression tests |
| Storage | 14 boxes × 30 Pokemon records | Done | 420 slots parsed |
| Storage | Complete Party/Box payload move and swap | Partial | In-memory GVAS + GES1 round-trip |
| Bag | Five pocket tabs + filtered add/edit/remove | Partial | In-memory GVAS + GES1 round-trip; live reload pending |
| Bag | Complete GE-1.0.0 concrete ItemData catalog | Done | 86/86 asset-backed items matched across all five pockets |
| Bag | Concrete Pokeball catalog | Done | Editor 9/9; 8 additional enum values have no concrete item assets |
| Progress | Dex/flags/daycare/world state | Partial | Story + Quest decoded read-only |
| Pokédex | Types/Abilities/base stats/type defenses | Done | 116 mapped species + 18-type chart |
| Bag | Hide asset-less Max Revive | Done | Removed from Bag/held-item choices; Bag Catalog Info documents scope |
| Bag | Blueprint/icon-only item candidates | Partial | Classified as unregistered; runtime verification pending |
| Bag | Template-derived custom item creation | Partial | v0.16.0 has 41 templates/11 archetypes, CSTM IDs and behavior help; per-effect user runtime acceptance pending |
| Docs | Item extension and runtime-test guide | Done | `docs/ITEM_EXTENSION_GUIDE.md`; current-build evidence + future mod/update path |
| Research | Icarus vs Gamma item-modding pipeline | Done | JSON DataTable patches vs unversioned cooked ItemData/Blueprint dependencies |
| Mod builder | V11 patch-pak construction | Done | Correct V11/mount point/internal path round-trip proven |
| Mod builder | Gamma external-pak container mount | Done | `PokemonEmerald-Windows_0_P.pak` held open beside base; arbitrary basename ignored; probe removed |
| Mod builder | Cooked-asset override priority | Done | Runtime read mapped Potion override value from patch; reversible cleanup passed |
| Mod builder | ItemData schema + new-asset discovery | Done | Build-matched usmap; 72 fields; manager auto-discovered renamed `/Game/Items/` asset |
| Mod builder | Multi-archetype item wizard | Partial | CSTM ID + Vitamin/Ball/TM discovery proofs; gameplay effects pending |
| UX | Player-facing dynamic item Effects | Done | All archetypes covered; Silk Scarf/Vitamin/TM value-following tests + GUI smoke |
| Mod builder | Runtime Vitamin cap policy | Done | Native hook return override + production-form activation + owned cleanup; user gameplay acceptance pending |
| Safety | Runtime mod ownership and conflict guards | Done | Managed hashes, unknown-loader refusal, user-mod uninstall refusal, game-running guard |
| Build | Windows executable | Done | v0.16.1 built; 70 tests + source/packaged GUI smoke + packaged live-slot validation pass |
| Build | Stable root launcher refreshed by builds | Done | Launcher opened current dist GUI; PID smoke-tested |
| Backup | Separate GitHub repository | Done | Sanitized branch + draft PR #1 published |
| Live test | Edit, game load and in-game resave | Done | Potion 2 -> 3 survived normal game resave |
