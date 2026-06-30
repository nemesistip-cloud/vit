# 11 Database Standards

## 1. ORM Usage
- Use SQLAlchemy with the `asyncio` extension.
- Models must inherit from `Base` in `app/db/database.py`.

## 2. Migrations
- Use Alembic for all schema changes.
- Migrations live in `alembic/versions/`.
- Every PR that modifies a model MUST include a migration script.

## 3. Connection Management
- Use `AsyncSessionLocal` for creating sessions.
- Always use `async with session.begin()` or explicit `commit()`/`rollback()` to ensure atomic transactions.
- Keep transactions short to minimize lock contention.

## 4. Performance
- Use indexes on frequently queried columns (e.g., `user_id`, `match_id`).
- Avoid N+1 queries by using `selectinload` or `joinedload`.
