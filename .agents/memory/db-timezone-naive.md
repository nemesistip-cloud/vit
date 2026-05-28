---
name: DB timezone naive datetime mismatch
description: SQLAlchemy + asyncpg stores TIMESTAMP WITHOUT TIME ZONE as naive; Python comparisons must strip tzinfo.
---

## Rule
When comparing Python `datetime` objects against DB columns declared as `TIMESTAMP WITHOUT TIME ZONE`, use `datetime.now(timezone.utc).replace(tzinfo=None)` — NOT `datetime.now(timezone.utc)`.

**Why:** asyncpg raises `(can't subtract offset-naive and offset-aware datetimes)` when a timezone-aware Python datetime is compared to a DB column storing naive timestamps.

**How to apply:** Any time you compute a cutoff or threshold against a DB datetime column (e.g. `kickoff_time`, `created_at`), strip the tzinfo from the Python side. Affected file: `app/api/routes/admin_ai_sources.py` line 110.
