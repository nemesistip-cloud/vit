"""
vit_chain/core/genesis.py
─────────────────────────
Idempotent genesis seeding for VIT Chain (Chain ID 7764).

Rules (per Phase 1 gate):
  - Checks for an existing genesis block before any insert.
  - Never crashes or double-seeds on cold boot.
  - All writes are wrapped in a single async transaction.
  - Uses get_env() / get_int_env() from app.config — never os.getenv() directly.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_env, get_int_env
from app.core.errors import AppError

logger = logging.getLogger(__name__)

CHAIN_ID: int = 7764


# ── Types ──────────────────────────────────────────────────────────────────────

class GenesisValidator:
    """Minimal descriptor for a bootstrap validator."""
    def __init__(self, address: str, stake: int, name: str = "") -> None:
        self.address = address
        self.stake = stake
        self.name = name


# ── Entry point ────────────────────────────────────────────────────────────────

async def seed_genesis(db: AsyncSession) -> bool:
    """
    Idempotently seed the genesis block and initial validator set.

    Returns:
        True  — genesis was seeded this call (first boot).
        False — genesis already present; nothing was written.

    Raises:
        AppError — on unrecoverable database failure.
    """
    try:
        from app.db.models import Block, ValidatorStake
        from vit_chain.genesis import ensure_genesis

        result = await db.execute(
            select(func.count()).select_from(Block).where(Block.height == 0)
        )
        count = result.scalar_one()
        if count > 0:
            logger.info("[genesis] Genesis block already present — skipping seed.")
            return False

        logger.info("[genesis] Seeding genesis block & initial validators (chain_id=%d)...", CHAIN_ID)
        await ensure_genesis(db)

        # ── Initial validator set ──────────────────────────────────────
        validators = _load_genesis_validators()
        for v in validators:
            res = await db.execute(
                select(ValidatorStake).where(ValidatorStake.address == v.address)
            )
            if not res.scalar_one_or_none():
                stake = ValidatorStake(
                    address=v.address,
                    stake_amount=v.stake,
                    label=v.name,
                    active=True,
                )
                db.add(stake)

        logger.info(
            "[genesis] Seeded genesis block + %d bootstrap validators.", len(validators)
        )

        return True

    except Exception as exc:
        logger.error("[genesis] Genesis seeding failed: %s", exc, exc_info=True)
        raise AppError(
            code="GENESIS_SEED_FAILED",
            message=f"Genesis seeding failed: {exc}",
        ) from exc


# ── Helpers ────────────────────────────────────────────────────────────────────

def _genesis_hash() -> str:
    """Deterministic genesis block hash derived from chain constants."""
    import hashlib
    payload = f"vitchain:genesis:{CHAIN_ID}".encode()
    return "0x" + hashlib.sha256(payload).hexdigest()


def _load_genesis_validators() -> List[GenesisValidator]:
    """
    Load bootstrap validator set from environment.

    Expects comma-separated address:stake:name triples in GENESIS_VALIDATORS:
        GENESIS_VALIDATORS=0xABC:1000000:node1,0xDEF:1000000:node2

    Falls back to an empty list — the chain can run validatorless in dev,
    but production deployments MUST set GENESIS_VALIDATORS.
    """
    raw = get_env("GENESIS_VALIDATORS", "")
    if not raw.strip():
        logger.warning(
            "[genesis] GENESIS_VALIDATORS is not set — starting with no bootstrap validators. "
            "This is only acceptable in development."
        )
        return []

    validators: List[GenesisValidator] = []
    for entry in raw.split(","):
        parts = entry.strip().split(":")
        if len(parts) < 2:
            logger.warning("[genesis] Skipping malformed GENESIS_VALIDATORS entry: %r", entry)
            continue
        address, stake_str = parts[0], parts[1]
        name = parts[2] if len(parts) > 2 else ""
        try:
            validators.append(GenesisValidator(address=address, stake=int(stake_str), name=name))
        except ValueError:
            logger.warning("[genesis] Invalid stake value in GENESIS_VALIDATORS entry: %r", entry)

    return validators
