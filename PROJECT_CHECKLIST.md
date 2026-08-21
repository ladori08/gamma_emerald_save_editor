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
| CLI | list/summary/validate/unpack/pack/name | Done | Real options save |
| Trainer | Identity/time/location + synchronized name/ID | Partial | Real story save + in-memory write |
| Party | Pokemon/stats/IV/EV/HP/friendship | Partial | 1 live Party record; validated writes |
| Storage | 14 boxes × 30 Pokemon records | Done | 420 slots parsed |
| Bag | Categories/items/existing quantities | Partial | Live Potion 2 -> 3 write + reload passed |
| Progress | Dex/flags/daycare/world state | Partial | Story + Quest decoded read-only |
| Build | Windows executable | Done | GUI and CLI artifacts in `dist` |
| Backup | Separate GitHub repository | Done | Sanitized branch + draft PR #1 published |
| Live test | Edit, game load and in-game resave | Done | Potion 2 -> 3 survived normal game resave |
