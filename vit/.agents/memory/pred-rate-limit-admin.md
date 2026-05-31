---
name: Prediction rate limit admin bypass
description: Admin users must be exempted from per-user daily prediction limits in predict.py
---

## Rule
In `app/api/routes/predict.py`, check `current_user.role in ("admin", "super_admin")` and skip the `MAX_PREDICTIONS_PER_DAY` guard for those users.

**Why:** Admins generate bulk predictions for seeding/testing and should never hit the rate cap. Without this, admin users exhaust their 20-prediction daily quota during batch operations.

**How to apply:** Gate the entire rate-limit block with `if user_id is not None and not _is_admin:` where `_is_admin = getattr(current_user, "role", None) in ("admin", "super_admin")`.
