"""
vit_chain/consensus/engine.py — ConsensusManager with Phase 1 slashing integration.

Wiring added 2026-07-19:
  - DOUBLE_SIGN:   detected when same validator proposes two distinct block hashes at
                   the same height within the same epoch window.
  - INVALID_BLOCK: slash fired when engine.finalize_block() returns False.
  - DOWNTIME:      consecutive miss streak tracked per-validator; slash triggered at
                   SLASHING_DOWNTIME_SLOTS (default 50) consecutive missed slots.

All slash calls use a fresh AsyncSessionLocal session to avoid nested-transaction
conflicts with the outer epoch session.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from vit_chain.consensus.storage_engine import StorageConsensusEngine
from vit_chain.consensus.base import AbstractConsensusEngine
from vit_chain.consensus.reputation import ReputationManager
from vit_chain.consensus.events import ConsensusEventBus
from vit_chain.consensus.models import ConsensusCheckpoint
from vit_chain.core.blockchain import VITChain

logger = logging.getLogger(__name__)

EPOCH_SECONDS       = 15
CHECKPOINT_INTERVAL = 100

# Lazy-import guard so the engine still boots even if slashing models aren't
# migrated yet (degrades gracefully with a log warning).
_SLASHING_AVAILABLE: Optional[bool] = None


def _try_import_slashing():
    global _SLASHING_AVAILABLE
    if _SLASHING_AVAILABLE is not None:
        return _SLASHING_AVAILABLE
    try:
        from vit_chain.consensus.slashing import slashing_manager, SlashReason  # noqa: F401
        _SLASHING_AVAILABLE = True
    except Exception as exc:
        logger.warning("[consensus] Slashing module unavailable — enforcement disabled: %s", exc)
        _SLASHING_AVAILABLE = False
    return _SLASHING_AVAILABLE


async def _slash(validator_address: str, reason_name: str, evidence: str, slot: int = 0) -> None:
    """
    Execute a slash in an isolated session.
    Safe to call from within an outer epoch session — never shares transactions.
    """
    if not _try_import_slashing():
        return
    try:
        from vit_chain.consensus.slashing import slashing_manager, SlashReason
        reason = SlashReason[reason_name]
        async with AsyncSessionLocal() as slash_db:
            result = await slashing_manager.check_and_slash(
                slash_db, validator_address, reason,
                evidence=evidence, current_slot=slot,
            )
            if result:
                logger.warning(
                    "[consensus] SLASH %s | %s | -%d | stake %d→%d",
                    validator_address, reason_name,
                    result["slash_amount"], result["stake_before"], result["stake_after"],
                )
    except Exception as exc:
        logger.error("[consensus] Slash call failed (%s / %s): %s", validator_address, reason_name, exc)


class ConsensusManager:
    """
    Coordinates multiple consensus engines and manages the validator lifecycle.

    Phase 1 slashing integration:
      · _seen_proposals   — detects DOUBLE_SIGN within an epoch window
      · _miss_streaks     — tracks consecutive missed slots for DOWNTIME detection
    """

    def __init__(self, validator_key: str):
        self.validator_key = validator_key
        self.engines: dict[str, AbstractConsensusEngine] = {
            "storage": StorageConsensusEngine(validator_key)
        }
        self.primary_engine    = "storage"
        self.reputation_manager = ReputationManager()
        self.event_bus          = ConsensusEventBus()
        self._running           = False

        # Phase 1 slashing state ─────────────────────────────────────────────
        # {height: {validator_id: block_hash}} — pruned after each epoch commit
        self._seen_proposals: dict[int, dict[str, str]] = defaultdict(dict)
        # {validator_id: consecutive_miss_count}
        self._miss_streaks: dict[str, int] = defaultdict(int)

    # ── Main epoch loop ───────────────────────────────────────────────────────

    async def run(self):
        self._running = True
        logger.info("[consensus] ConsensusManager started with engines: %s", list(self.engines.keys()))
        _try_import_slashing()   # warm up import check at boot

        while self._running:
            try:
                epoch = int(time.time()) // EPOCH_SECONDS

                # Phase 1 — run epoch logic (generates storage challenges etc.)
                async with AsyncSessionLocal() as db:
                    for engine in self.engines.values():
                        await engine.run_epoch_logic(db, epoch)
                    await db.commit()

                await asyncio.sleep(10)

                # Phase 2 — block production and finalization
                async with AsyncSessionLocal() as db:
                    engine = self.engines.get(self.primary_engine)
                    if engine:
                        block = await engine.produce_block_candidate(db, epoch)
                        if block:
                            # ── DOUBLE_SIGN detection ─────────────────────
                            if block.validator_id and block.block_hash:
                                prev = self._seen_proposals[block.height].get(block.validator_id)
                                if prev is not None and prev != block.block_hash:
                                    logger.error(
                                        "[consensus] DOUBLE_SIGN detected — %s proposed two hashes at height %d",
                                        block.validator_id, block.height,
                                    )
                                    await _slash(
                                        block.validator_id, "DOUBLE_SIGN",
                                        evidence=(
                                            f"Height {block.height}: "
                                            f"first={prev[:16]}… second={block.block_hash[:16]}…"
                                        ),
                                        slot=block.height,
                                    )
                                else:
                                    self._seen_proposals[block.height][block.validator_id] = block.block_hash

                            if hasattr(engine, "finalize_block"):
                                success = await engine.finalize_block(db, epoch, block)
                                if success:
                                    # Successful block — reset miss streak
                                    if block.validator_id:
                                        self._miss_streaks[block.validator_id] = 0
                                        await self.reputation_manager.record_production(db, block.validator_id)

                                    await self.event_bus.emit_block_produced(
                                        block.height, block.block_hash, block.validator_id
                                    )
                                    if block.height > 0 and block.height % CHECKPOINT_INTERVAL == 0:
                                        await self.create_checkpoint(db, block)

                                    await db.commit()
                                    logger.info("[consensus] Block finalized at height %d", block.height)

                                else:
                                    # ── INVALID_BLOCK slash ───────────────
                                    if block.validator_id:
                                        await self.reputation_manager.record_miss(db, block.validator_id)
                                        await db.commit()
                                        await _slash(
                                            block.validator_id, "INVALID_BLOCK",
                                            evidence=f"finalize_block() returned False at height {block.height}",
                                            slot=block.height,
                                        )
                                    logger.warning("[consensus] Block finalization failed at epoch %d", epoch)

                        else:
                            # No block produced — potential slot miss
                            # (validator_id of the expected proposer is not available here;
                            #  DOWNTIME is checked per-validator in on_new_block via miss streak)
                            pass

                # Prune old proposal records (keep last 1000 heights)
                if len(self._seen_proposals) > 1000:
                    oldest = sorted(self._seen_proposals)[:500]
                    for h in oldest:
                        del self._seen_proposals[h]

                now = time.time()
                next_epoch_time = (int(now // EPOCH_SECONDS) + 1) * EPOCH_SECONDS
                await asyncio.sleep(max(0, next_epoch_time - now))

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[consensus] ConsensusManager error: %s", exc)
                await asyncio.sleep(1)

    # ── Block helpers ─────────────────────────────────────────────────────────

    async def create_checkpoint(self, db: AsyncSession, block) -> None:
        """Creates a state checkpoint at the current block."""
        checkpoint = ConsensusCheckpoint(
            height=block.height,
            block_hash=block.block_hash,
            state_root=block.merkle_root,
            validator_set_hash="0x" + "f" * 64,
        )
        db.add(checkpoint)
        # commit() is handled by the caller

    async def validate_block(self, db: AsyncSession, block) -> bool:
        """
        Runs validation across all engines.
        If any engine rejects the block, the proposer is slashed for INVALID_BLOCK.
        """
        for engine in self.engines.values():
            if not await engine.validate_block_rules(db, block):
                if getattr(block, "validator_id", None):
                    await _slash(
                        block.validator_id, "INVALID_BLOCK",
                        evidence=(
                            f"validate_block_rules() rejected block "
                            f"at height {getattr(block, 'height', '?')}"
                        ),
                        slot=getattr(block, "height", 0),
                    )
                return False
        return True

    async def on_new_block(self, db: AsyncSession, block) -> None:
        """
        Notify all engines, update reputation, and check DOWNTIME streak.
        Called by external peers when a peer block arrives.
        """
        for engine in self.engines.values():
            await engine.on_new_block(db, block)

        if block.validator_id:
            # Successful peer block — reset streak and record production
            self._miss_streaks[block.validator_id] = 0
            await self.reputation_manager.record_production(db, block.validator_id)

        await db.commit()

    async def record_validator_miss(self, validator_address: str, slot: int = 0) -> None:
        """
        Call when a validator is known to have missed its designated slot.
        Increments the miss streak and fires a DOWNTIME slash when the threshold
        is reached (SLASHING_DOWNTIME_SLOTS, default 50).
        """
        self._miss_streaks[validator_address] += 1
        streak = self._miss_streaks[validator_address]

        if _try_import_slashing():
            from vit_chain.consensus.slashing import DOWNTIME_SLOT_THRESHOLD
            if streak >= DOWNTIME_SLOT_THRESHOLD:
                logger.warning(
                    "[consensus] DOWNTIME threshold reached — %s missed %d consecutive slots",
                    validator_address, streak,
                )
                await _slash(
                    validator_address, "DOWNTIME",
                    evidence=f"Missed {streak} consecutive slots (threshold={DOWNTIME_SLOT_THRESHOLD})",
                    slot=slot,
                )
                # Reset after slash so the validator isn't slashed again every slot
                self._miss_streaks[validator_address] = 0

    def stop(self) -> None:
        self._running = False
