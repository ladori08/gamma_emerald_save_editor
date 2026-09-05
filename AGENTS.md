# Project Rules

These rules preserve the operating contract of the original `tool_editor` project.

1. Read `CURRENT_STATE.md`, `TASKS.md`, `WORKLOG.md`, and `SESSION_NOTES.md` before changing code.
2. Record every project-related request in the continuity files during the same session.
3. Update `CURRENT_STATE.md` with the verified snapshot, `TASKS.md` with status/next actions, and
   append evidence and commands to `WORKLOG.md`.
4. Update `SESSION_NOTES.md` before stopping so another session can resume without guessing.
5. Keep `PROJECT_CHECKLIST.md` synchronized with feature and safety coverage.
6. Never commit live saves, decrypted GVAS files, backups, credentials, tokens, encryption/signing
   keys, or private test fixtures. Secrets required at runtime must use environment variables or
   ignored local files and must not be duplicated into logs.
7. Never write a live save without: game-closed check, stale-source check, timestamped backup,
   atomic replace, and post-write decode verification.
8. Unsupported or ambiguous structures remain read-only and are preserved byte-for-byte.
9. Run the complete automated test suite and a real-save read-only validation before release.
10. Keep the repository backed up to its own separate GitHub repository after verified milestones.
    Public publication requires an explicit secret scan and user approval.
