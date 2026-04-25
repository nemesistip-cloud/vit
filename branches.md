# Remote Branch Inventory — origin (https://github.com/nemesistip-cloud/vit)

Snapshot taken: 2026-04-25 (during v4.6.0 prep).

| Branch | Head SHA | Subject |
|---|---|---|
| `main` | `146a7d8` | Update version information for software release (v4.5.0 baseline) |
| `feat/v4.6-complete-rollout` | `146a7d8` | Same SHA as `main` — already up to date |
| `feat/v4.6-implementation` | `ae55200` | feat(tasks): add task management system with categories, tasks, and user progress tracking |

## Local main (`8fa2450`) vs `origin/main` (`ae55200`)

Local main carries fixes that `origin/main` does not yet have:

- `frontend/src/pages/admin.tsx` — restored missing `Textarea` import (fixes blank admin panel).
- `main.py` — restored `vitcoin_pricing_loop()` definition (orphaned body had crashed startup).
- `app/config.py` — `APP_VERSION` lifted to `4.6.0` (was `4.0.0` on origin baseline, `4.5.0` mid-flight).
- `CHANGELOG_v4.6.md` — net-new file documenting the v4.6 plan and outstanding gaps.
- `requirements.txt` — present locally, deleted on `feat/v4.6-implementation`.
- `.gitignore` — adds `vit.db`.

## Merge decision

A naive merge of `origin/main` into local `main` would *delete* the items above (it's a deletion-heavy diff: `-209 / +2`). Per the task's "never silently overwrite" rule, the merge has been **deferred**. See `MERGE_CONFLICTS.md` for the per-file breakdown and the recommended path forward.
