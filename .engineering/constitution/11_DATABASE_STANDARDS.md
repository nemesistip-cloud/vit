# 11 Database Standards

## 1. ORM Usage
- Use SQLAlchemy with the `asyncio` extension.
- Models MUST inherit from `Base` in `app/db/database.py`.
- **N+1 Prevention**: Explicitly use `selectinload` or `joinedload` for relationships. Lazy loading in async contexts is prohibited and will cause errors.

## 2. Migrations
- Use Alembic for all schema changes.
- Migrations live in `alembic/versions/`.
- Every PR that modifies a model MUST include a migration script.
- **Data Migrations**: Separate schema changes from data migrations into different Alembic revisions.

## 3. Connection Management
- Use `AsyncSessionLocal` for creating sessions.
- Always use `async with session.begin()` or explicit `commit()`/`rollback()` to ensure atomic transactions.
- Keep transactions short to minimize lock contention.

## 4. Performance & Design
- **Indexing**:
  - Mandatory indexes on all Foreign Keys.
  - Mandatory indexes on columns used in `WHERE` clauses for high-frequency queries (e.g., `status`, `created_at`).
- **Constraints**: Use `CheckConstraint` and `UniqueConstraint` to enforce data integrity at the database level.
- **Soft Deletes**: Use a `is_deleted` boolean or `deleted_at` timestamp instead of physical deletion for core entities.
