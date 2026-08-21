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
| UX | GUI overview/properties/backups/diagnostics | Done | Packaged smoke test exit 0 |
| UX | Indigo-style Trainer/Party/Storage/Bag/Dex/Legality workspace | Done | Real-save GUI interaction + packaged smoke test |
| UX | Unified Party/Storage cards with drag/drop | Partial | Real-save in-memory payload move; live reload pending |
| UX | Focused Trainer/Pokémon/Bag/Pokédex navigation | Done | Source + packaged GUI smoke tests |
| CLI | list/summary/validate/unpack/pack/name | Done | Real options save |
| Trainer | Identity/time/location + synchronized name/ID | Partial | Real story save + in-memory write |
| Party | Pokemon/stats/IV/EV/HP/friendship | Done | Real Party record + validated writes |
| Party | Species/nature/moves/PP catalogs and writes | Partial | Real-save in-memory round-trip; live reload pending |
| Storage | 14 boxes × 30 Pokemon records | Done | 420 slots parsed |
| Storage | Complete Party/Box payload move and swap | Partial | In-memory GVAS + GES1 round-trip |
| Bag | Five pocket tabs + filtered add/edit/remove | Partial | In-memory GVAS + GES1 round-trip; live reload pending |
| Progress | Dex/flags/daycare/world state | Partial | Story + Quest decoded read-only |
| Pokédex | Gamma species information lookup | Done | 118-asset catalog + owned-location lookup |
| Build | Windows executable | Done | v0.4.0 GUI/CLI/release ZIP smoke-tested |
| Backup | Separate GitHub repository | Done | Sanitized branch + draft PR #1 published |
| Live test | Edit, game load and in-game resave | Done | Potion 2 -> 3 survived normal game resave |
