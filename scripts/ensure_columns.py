#!/usr/bin/env python3
"""
Pre-flight schema guard — runs before Alembic on every deploy.

Adds any User (and related) columns that the ORM model defines but that
may be absent from the production DB because of divergent migration heads,
a failed alembic upgrade, or columns added to models without a migration.

All statements use  ADD COLUMN IF NOT EXISTS  so this script is fully
idempotent and safe to run on every startup.  Exits 0 on success, 1 on
connection failure (non-fatal: the start script logs a warning and
continues).
"""
import os
import sys

DATABASE_URL = os.getenv("DATABASE_URL", "")

if "postgres" not in DATABASE_URL:
    print("[ensure_columns] Not a Postgres DB — skipping.", flush=True)
    sys.exit(0)

# Normalise the URL so psycopg2 can connect.
# Render may supply  postgres://  or  postgresql+asyncpg://  or  postgresql://
sync_url = DATABASE_URL
for old, new in [
    ("postgresql+asyncpg://", "postgresql://"),
    ("postgres+asyncpg://",   "postgresql://"),
    ("postgres://",            "postgresql://"),   # Render shorthand → psycopg2 form
]:
    if sync_url.startswith(old):
        sync_url = new + sync_url[len(old):]
        break

COLUMNS = [
    # (table, column, DDL)
    # ── Prediction lifecycle/provenance ────────────────────────────────────
    # Older Render databases may have the original predictions table without
    # the columns added by later ORM revisions. Keep the pre-flight guard
    # idempotent so read queries cannot fail before Alembic catches up.
    ("predictions", "status",              "VARCHAR(32) NOT NULL DEFAULT 'READY'"),
    ("predictions", "source",              "VARCHAR(32) NOT NULL DEFAULT 'live_generated'"),
    ("predictions", "is_seed",             "BOOLEAN NOT NULL DEFAULT false"),
    ("predictions", "provenance",          "JSONB"),
    ("predictions", "job_id",              "VARCHAR(64)"),
    ("predictions", "error_message",       "TEXT"),
    ("predictions", "model_insights",      "JSONB"),
    ("predictions", "model_weights",       "JSONB"),
    ("predictions", "submitted_market_id", "VARCHAR"),
    ("predictions", "submitted_market_side", "VARCHAR"),
    ("predictions", "submitted_stake",     "DOUBLE PRECISION"),
    ("predictions", "normalized_edge",     "DOUBLE PRECISION"),
    ("predictions", "raw_edge",            "DOUBLE PRECISION"),
    ("predictions", "vig_free_edge",       "DOUBLE PRECISION"),
    ("predictions", "recommended_stake",   "DOUBLE PRECISION"),
    ("predictions", "was_correct",         "BOOLEAN"),
    ("predictions", "settled_profit",      "DOUBLE PRECISION"),
    # ── Core user flags ────────────────────────────────────────────────────
    ("users", "is_active",              "BOOLEAN NOT NULL DEFAULT true"),
    ("users", "is_verified",            "BOOLEAN NOT NULL DEFAULT false"),
    ("users", "is_banned",              "BOOLEAN NOT NULL DEFAULT false"),
    ("users", "withdrawals_frozen",     "BOOLEAN NOT NULL DEFAULT false"),
    ("users", "is_flagged",             "BOOLEAN NOT NULL DEFAULT false"),
    # ── Profile extras ────────────────────────────────────────────────────
    ("users", "company_name",           "VARCHAR(255)"),
    ("users", "phone",                  "VARCHAR(50)"),
    ("users", "wallet_address",         "VARCHAR(42)"),
    ("users", "google_id",              "VARCHAR(255)"),
    ("users", "telegram_id",            "VARCHAR(255)"),
    ("users", "telegram_username",      "VARCHAR(255)"),
    ("users", "last_login",             "TIMESTAMPTZ"),
    ("users", "updated_at",             "TIMESTAMPTZ"),
    # ── RBAC ─────────────────────────────────────────────────────────────
    ("users", "admin_role",             "VARCHAR(20)"),
    ("users", "subscription_tier",      "VARCHAR(20) DEFAULT 'viewer'"),
    # ── KYC ──────────────────────────────────────────────────────────────
    ("users", "kyc_status",             "VARCHAR(20) DEFAULT 'none'"),
    ("users", "kyc_submitted_at",       "TIMESTAMPTZ"),
    ("users", "kyc_data",               "JSONB"),
    # ── 2FA / TOTP ───────────────────────────────────────────────────────
    ("users", "totp_secret",            "VARCHAR(64)"),
    ("users", "totp_secret_pending",    "VARCHAR(64)"),
    ("users", "totp_enabled",           "BOOLEAN NOT NULL DEFAULT false"),
    # ── Brute-force protection (SEC-10) ───────────────────────────────────
    ("users", "failed_login_count",     "INTEGER NOT NULL DEFAULT 0"),
    ("users", "locked_until",           "TIMESTAMPTZ"),
    # ── Gamification ─────────────────────────────────────────────────────
    ("users", "current_streak",         "INTEGER NOT NULL DEFAULT 0"),
    ("users", "best_streak",            "INTEGER NOT NULL DEFAULT 0"),
    ("users", "total_xp",               "INTEGER NOT NULL DEFAULT 0"),
    # ── Academic / Student Identity ───────────────────────────────────────
    ("users", "university",             "VARCHAR(255)"),
    ("users", "faculty",                "VARCHAR(255)"),
    ("users", "department",             "VARCHAR(255)"),
    ("users", "study_level",            "VARCHAR(20)"),
    ("users", "matric_number",          "VARCHAR(50)"),
    ("users", "student_skills",         "JSONB DEFAULT '[]'::jsonb"),
    ("users", "student_interests",      "JSONB DEFAULT '[]'::jsonb"),
    ("users", "student_country",        "VARCHAR(100)"),
    ("users", "is_student_verified",    "BOOLEAN NOT NULL DEFAULT false"),
    ("users", "student_profile_completed", "BOOLEAN NOT NULL DEFAULT false"),
]

INDEXES = [
    # (index_name, table, column)
    ("ix_users_university",  "users", "university"),
    ("ix_users_faculty",     "users", "faculty"),
    ("ix_users_department",  "users", "department"),
    ("ix_users_google_id",   "users", "google_id"),
    ("ix_users_telegram_id", "users", "telegram_id"),
]

try:
    import psycopg2
except ImportError:
    print("[ensure_columns] psycopg2 not available — skipping.", flush=True)
    sys.exit(0)

try:
    conn = psycopg2.connect(sync_url)
    conn.autocommit = True
    cur = conn.cursor()
    print("[ensure_columns] Connected. Adding missing columns…", flush=True)

    added = 0
    for table, col, ddl in COLUMNS:
        sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl};"
        try:
            cur.execute(sql)
            added += 1
        except Exception as e:
            print(f"[ensure_columns]   WARN {table}.{col}: {e}", flush=True)

    for idx, table, col in INDEXES:
        try:
            cur.execute(
                "SELECT 1 FROM pg_indexes WHERE indexname = %s", (idx,)
            )
            if not cur.fetchone():
                cur.execute(f"CREATE INDEX {idx} ON {table} ({col});")
        except Exception as e:
            print(f"[ensure_columns]   WARN index {idx}: {e}", flush=True)

    cur.close()
    conn.close()
    print(f"[ensure_columns] Done — processed {added}/{len(COLUMNS)} column statements.", flush=True)
    sys.exit(0)

except Exception as e:
    print(f"[ensure_columns] ERROR: {e}", flush=True)
    sys.exit(1)
