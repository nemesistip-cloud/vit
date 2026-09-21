"""
Chain-state auto-snapshot task — Phase 1 gate.

Runs every 6 hours, dumps the Postgres chain DB via pg_dump → gzip,
and uploads to Dropbox if DROPBOX_ACCESS_TOKEN is configured.
Soft-fails on every error so the kernel is never blocked by backup failures.
"""
import asyncio
import logging
import os
import datetime

logger = logging.getLogger(__name__)

_SNAPSHOT_INTERVAL_SECONDS = 6 * 3600   # every 6 hours
_INITIAL_DELAY_SECONDS = 300            # wait 5 min for startup to settle


async def _run_snapshot() -> None:
    """Perform one pg_dump → gzip → optional Dropbox upload."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "postgres" not in db_url:
        logger.warning("[chain_snapshot] No Postgres DATABASE_URL — snapshot skipped.")
        return

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = f"/tmp/vit_chain_snapshot_{timestamp}.sql.gz"

    logger.info("[chain_snapshot] Starting DB snapshot → %s", out_path)

    proc = await asyncio.create_subprocess_shell(
        f'pg_dump "$DATABASE_URL" | gzip > {out_path}',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ.copy(),
    )
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

    if proc.returncode != 0:
        logger.error(
            "[chain_snapshot] pg_dump failed (code %s): %s",
            proc.returncode, stderr.decode().strip()[:400],
        )
        return

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    logger.info("[chain_snapshot] Snapshot ready: %s (%.2f MB)", out_path, size_mb)

    # ── Upload to Dropbox if token is available ─────────────────────────────
    token = os.environ.get("DROPBOX_ACCESS_TOKEN", "")
    if not token:
        logger.info("[chain_snapshot] DROPBOX_ACCESS_TOKEN not set — skipping upload.")
        return

    try:
        import dropbox  # type: ignore
        import dropbox.files  # type: ignore

        dbx = dropbox.Dropbox(token)
        remote_path = f"/vit-chain-snapshots/snapshot_{timestamp}.sql.gz"

        with open(out_path, "rb") as fh:
            dbx.files_upload(
                fh.read(),
                remote_path,
                mode=dropbox.files.WriteMode("overwrite"),
            )
        logger.info("[chain_snapshot] Uploaded → Dropbox%s", remote_path)

        # Prune local temp file after successful upload
        os.remove(out_path)
    except Exception as upload_exc:
        logger.error("[chain_snapshot] Dropbox upload failed: %s", upload_exc)


async def _snapshot_loop() -> None:
    """Main loop: initial delay → snapshot → repeat every 6 h."""
    logger.info(
        "[chain_snapshot] Task started — first snapshot in %ds, then every %dh.",
        _INITIAL_DELAY_SECONDS, _SNAPSHOT_INTERVAL_SECONDS // 3600,
    )
    await asyncio.sleep(_INITIAL_DELAY_SECONDS)
    while True:
        try:
            await _run_snapshot()
        except asyncio.CancelledError:
            logger.info("[chain_snapshot] Task cancelled.")
            break
        except Exception as exc:
            logger.error("[chain_snapshot] Unexpected error: %s", exc, exc_info=True)
        try:
            await asyncio.sleep(_SNAPSHOT_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            break


def start_chain_snapshot() -> None:
    """Schedule the snapshot loop as a background asyncio task."""
    asyncio.create_task(_snapshot_loop())
