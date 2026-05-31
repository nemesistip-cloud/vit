---
name: SQLAlchemy boolean aggregation
description: PostgreSQL with asyncpg rejects func.cast(bool_expr, Float) — use case() inside func.sum() instead.
---

## Rule
For boolean aggregation in SQLAlchemy async (asyncpg/PostgreSQL):

**Correct:**
```python
from sqlalchemy import case as sa_case, func
func.sum(sa_case((Model.bool_col == True, 1), else_=0))
```

**Wrong (raises CannotCoerceError):**
```python
func.sum(func.cast(Model.bool_col == True, Float))
```

**Why:** asyncpg does not allow coercing boolean expressions directly to float in aggregate functions. The `case()` approach is explicit and works across both SQLite (dev) and PostgreSQL (prod).

**How to apply:** Any time you compute a count/sum of rows matching a boolean condition in an async SQLAlchemy query, use the `sa_case` pattern above.
