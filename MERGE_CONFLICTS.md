# Deferred Merge: `origin/main` (was `feat/v4.6-implementation`) → local `main`

**Status:** Not merged. Local `main` is intentionally ahead.

## Why deferred

`origin/main` was force-updated to `ae55200` (the head of `feat/v4.6-implementation`).
A merge into the working `main` (`8fa2450`) would be **deletion-heavy**:

| File | Local `main` | `origin/main` | If merged naively |
|---|---|---|---|
| `frontend/src/pages/admin.tsx` | `Textarea` import present (admin panel works) | Import missing | Admin panel breaks again |
| `main.py` | `vitcoin_pricing_loop()` defined | 3 lines removed | Startup `NameError` returns |
| `CHANGELOG_v4.6.md` | 108-line v4.6 plan | Deleted | Plan lost |
| `requirements.txt` | Full dep list | Deleted | Reproducible installs lost |
| `app/config.py` | `APP_VERSION="4.6.0"` | Older value | Version regressed |
| `.gitignore` | Excludes `vit.db` | (older form) | Risk of committing dev DB |
| `vit.db` (dev DB) | Present | Removed | Local data wiped |

`git diff --stat main origin/main` summary: **9 files changed, 2 insertions(+), 209 deletions(-).**

## Recommended path forward

The task system feature on `feat/v4.6-implementation` is the only thing local `main` *doesn't* have. Cherry-pick that work instead of merging:

```bash
git fetch origin
git log origin/main --oneline -- app/modules/tasks/   # find the task-system commit(s)
git cherry-pick <sha>                                 # apply just the task-system delta
```

If the task system is already present locally (it is — see `app/modules/tasks/`), the merge has no real benefit and should be skipped entirely.

## Branch hygiene suggestion

After the cherry-pick (or after confirming the task system is identical), the user may want to:

1. Force-push local `main` back up to `origin/main` to restore the bug-fixed history.
2. Delete `feat/v4.6-implementation` and `feat/v4.6-complete-rollout` from the remote — both are obsolete now that v4.6.0 is the active version.

These are destructive ops and require explicit user approval — they were *not* run as part of this task.
