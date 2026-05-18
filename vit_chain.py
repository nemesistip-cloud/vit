"""vit_chain.py — VIT Sovereign Ledger v7.0

Hash-linked SQLite blockchain with:
- Adaptive Difficulty Algorithm (ADDA): targets 60 s per block
- Halving schedule: reward halves every 1,000 blocks (10→5→2.5…)
- Decimal-precise balance arithmetic (no float casting)
- Rich API: mempool, rich-list, block explorer, enhanced stats

Tables:
  vit_blocks       — mined blocks (hash-linked, adaptive PoW)
  vit_transactions — pre-mine transaction queue + confirmed history
  vit_balances     — Decimal-precise running address balances

Genesis block mints 1,000,000 VIT to "genesis" address.
Initial mining reward: 10 VITCoin per block; halves every 1,000 blocks.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

_CHAIN_DB_PATH = os.getenv("VIT_CHAIN_DB", "vit_chain_ledger.db")

# ── Mining constants ──────────────────────────────────────────────────────────
_INITIAL_REWARD      = Decimal("10.00000000")   # VIT per block at genesis
_HALVING_INTERVAL    = 1_000                     # blocks between halvings
_REWARD_FLOOR        = Decimal("0.00000001")     # minimum block reward

_DEFAULT_DIFFICULTY  = 4   # leading zeros in block hash (start)
_MIN_DIFFICULTY      = 3
_MAX_DIFFICULTY      = 7
_BLOCK_TIME_TARGET_S = 60  # seconds — ADDA target inter-block time

_GENESIS_SUPPLY   = Decimal("1000000.00000000")
_GENESIS_ADDRESS  = "genesis"


# ── Helper functions ──────────────────────────────────────────────────────────

def _rand_id() -> str:
    import uuid
    return str(uuid.uuid4())


def _block_reward(block_index: int) -> Decimal:
    """Compute block mining reward with halving every _HALVING_INTERVAL blocks.

    block 0-999    → 10.00 VIT
    block 1000-1999→  5.00 VIT
    block 2000-2999→  2.50 VIT
    …floor at _REWARD_FLOOR
    """
    halvings = block_index // _HALVING_INTERVAL
    if halvings >= 30:
        return _REWARD_FLOOR
    reward = _INITIAL_REWARD / (Decimal("2") ** halvings)
    return reward.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


def _compute_next_difficulty(conn: sqlite3.Connection) -> int:
    """ADDA — Adaptive Difficulty Algorithm.

    Examines inter-block times over the last 6 blocks (5 intervals).
    If average block time < 30 s  → difficulty + 1 (too fast)
    If average block time > 120 s → difficulty − 1 (too slow)
    Otherwise keep current difficulty.
    Floor: _MIN_DIFFICULTY (3), ceiling: _MAX_DIFFICULTY (7).
    """
    rows = conn.execute(
        "SELECT timestamp, difficulty FROM vit_blocks ORDER BY block_index DESC LIMIT 6"
    ).fetchall()

    if len(rows) < 3:
        return _DEFAULT_DIFFICULTY

    # Read current difficulty from the most recent block
    current_diff = _DEFAULT_DIFFICULTY
    if rows[0]["difficulty"] is not None:
        try:
            current_diff = int(rows[0]["difficulty"])
        except (TypeError, ValueError):
            pass

    # Compute average inter-block time
    times: List[datetime] = []
    for r in rows:
        raw = r["timestamp"]
        try:
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            times.append(ts)
        except Exception:
            pass

    if len(times) < 3:
        return current_diff

    intervals = [(times[i] - times[i + 1]).total_seconds() for i in range(len(times) - 1)]
    avg_time = sum(intervals) / len(intervals)

    if avg_time < _BLOCK_TIME_TARGET_S / 2:      # < 30 s: mining too fast
        return min(_MAX_DIFFICULTY, current_diff + 1)
    elif avg_time > _BLOCK_TIME_TARGET_S * 2:     # > 120 s: mining too slow
        return max(_MIN_DIFFICULTY, current_diff - 1)
    return current_diff


def _update_balance_safe(
    conn: sqlite3.Connection,
    address: str,
    delta: Decimal,
) -> Decimal:
    """Add `delta` (positive or negative) to an address balance using Decimal
    arithmetic — never floats.  Returns the new balance."""
    row = conn.execute(
        "SELECT balance FROM vit_balances WHERE address = ?", (address,)
    ).fetchone()
    current = Decimal(row["balance"]) if row else Decimal("0")
    new_bal = max(Decimal("0"), current + delta)
    conn.execute("""
        INSERT INTO vit_balances (address, balance, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(address) DO UPDATE SET
            balance    = excluded.balance,
            updated_at = excluded.updated_at
    """, (address, str(new_bal)))
    return new_bal


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class VITTransaction:
    sender:    str
    receiver:  str
    amount:    Decimal
    memo:      str     = ""
    tx_type:   str     = "transfer"   # transfer | mint | burn | stake | reward | fee
    fee:       Decimal = Decimal("0")
    metadata:  dict    = field(default_factory=dict)
    timestamp: str     = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tx_id:     str     = field(default_factory=_rand_id)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["amount"] = str(self.amount)
        d["fee"]    = str(self.fee)
        return d


@dataclass
class VITBlock:
    index:         int
    transactions:  List[dict]
    previous_hash: str
    timestamp:     str
    nonce:         int
    miner:         str
    reward:        str
    difficulty:    int   = _DEFAULT_DIFFICULTY
    block_hash:    str   = ""

    def compute_hash(self) -> str:
        content = json.dumps({
            "index":         self.index,
            "transactions":  self.transactions,
            "previous_hash": self.previous_hash,
            "timestamp":     self.timestamp,
            "nonce":         self.nonce,
            "miner":         self.miner,
            "difficulty":    self.difficulty,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


# ── Ledger class ───────────────────────────────────────────────────────────────

class VITChainLedger:
    """Self-contained hash-linked SQLite blockchain — VIT Sovereign Ledger v7.0."""

    def __init__(self, db_path: str = _CHAIN_DB_PATH) -> None:
        self.db_path = db_path
        self._lock   = asyncio.Lock()
        self._init_db()
        logger.info("[vit-chain] ledger initialised at %s", db_path)

    # ── Schema ────────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS vit_blocks (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    block_index   INTEGER NOT NULL UNIQUE,
                    block_hash    TEXT    NOT NULL UNIQUE,
                    previous_hash TEXT    NOT NULL,
                    miner         TEXT    NOT NULL,
                    reward        TEXT    NOT NULL DEFAULT '10.00000000',
                    difficulty    INTEGER NOT NULL DEFAULT 4,
                    nonce         INTEGER NOT NULL,
                    timestamp     TEXT    NOT NULL,
                    tx_count      INTEGER NOT NULL DEFAULT 0,
                    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS vit_transactions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_id         TEXT    NOT NULL UNIQUE,
                    block_index   INTEGER REFERENCES vit_blocks(block_index),
                    sender        TEXT    NOT NULL,
                    receiver      TEXT    NOT NULL,
                    amount        TEXT    NOT NULL,
                    fee           TEXT    NOT NULL DEFAULT '0',
                    memo          TEXT    DEFAULT '',
                    tx_type       TEXT    NOT NULL DEFAULT 'transfer',
                    metadata      TEXT    NOT NULL DEFAULT '{}',
                    status        TEXT    NOT NULL DEFAULT 'pending',
                    timestamp     TEXT    NOT NULL,
                    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS vit_balances (
                    address       TEXT    PRIMARY KEY,
                    balance       TEXT    NOT NULL DEFAULT '0.00000000',
                    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_vtx_sender   ON vit_transactions(sender);
                CREATE INDEX IF NOT EXISTS idx_vtx_receiver ON vit_transactions(receiver);
                CREATE INDEX IF NOT EXISTS idx_vtx_status   ON vit_transactions(status);
                CREATE INDEX IF NOT EXISTS idx_vtx_block    ON vit_transactions(block_index);
            """)

            # Schema migration: add columns to existing tables if absent
            for migration in [
                "ALTER TABLE vit_blocks ADD COLUMN difficulty INTEGER NOT NULL DEFAULT 4",
                "ALTER TABLE vit_transactions ADD COLUMN fee TEXT NOT NULL DEFAULT '0'",
            ]:
                try:
                    conn.execute(migration)
                except sqlite3.OperationalError:
                    pass  # column already exists

        self._ensure_genesis()

    def _ensure_genesis(self) -> None:
        with self._conn() as conn:
            if conn.execute("SELECT 1 FROM vit_blocks WHERE block_index = 0").fetchone():
                return

            genesis_tx = VITTransaction(
                sender=_GENESIS_ADDRESS,
                receiver=_GENESIS_ADDRESS,
                amount=_GENESIS_SUPPLY,
                memo="Genesis block — VIT Sovereign Ledger v7.0",
                tx_type="mint",
            )
            genesis_block = VITBlock(
                index=0,
                transactions=[genesis_tx.to_dict()],
                previous_hash="0" * 64,
                timestamp=datetime.now(timezone.utc).isoformat(),
                nonce=0,
                miner=_GENESIS_ADDRESS,
                reward=str(_INITIAL_REWARD),
                difficulty=_DEFAULT_DIFFICULTY,
            )
            genesis_block.block_hash = genesis_block.compute_hash()

            conn.execute("""
                INSERT INTO vit_blocks
                    (block_index, block_hash, previous_hash, miner, reward,
                     difficulty, nonce, timestamp, tx_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (0, genesis_block.block_hash, genesis_block.previous_hash,
                  _GENESIS_ADDRESS, str(_INITIAL_REWARD), _DEFAULT_DIFFICULTY,
                  0, genesis_block.timestamp, 1))

            conn.execute("""
                INSERT INTO vit_transactions
                    (tx_id, block_index, sender, receiver, amount, fee,
                     memo, tx_type, status, timestamp)
                VALUES (?, ?, ?, ?, ?, '0', ?, ?, ?, ?)
            """, (genesis_tx.tx_id, 0, _GENESIS_ADDRESS, _GENESIS_ADDRESS,
                  str(_GENESIS_SUPPLY), genesis_tx.memo, "mint", "confirmed",
                  genesis_tx.timestamp))

            _update_balance_safe(conn, _GENESIS_ADDRESS, _GENESIS_SUPPLY)
            conn.commit()
            logger.info("[vit-chain] genesis block created — supply=%s VIT", _GENESIS_SUPPLY)

    # ── Mining ────────────────────────────────────────────────────────────────

    def _mine(self, block: VITBlock) -> str:
        """Proof-of-work: find nonce yielding hash with `block.difficulty` leading zeros."""
        target = "0" * block.difficulty
        nonce  = 0
        while True:
            block.nonce    = nonce
            candidate_hash = block.compute_hash()
            if candidate_hash.startswith(target):
                return candidate_hash
            nonce += 1

    # ── Public API ────────────────────────────────────────────────────────────

    async def log_transaction(self, tx: VITTransaction) -> str:
        """Queue a transaction for inclusion in the next block. Returns tx_id."""
        async with self._lock:
            with self._conn() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO vit_transactions
                        (tx_id, sender, receiver, amount, fee, memo,
                         tx_type, metadata, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """, (tx.tx_id, tx.sender, tx.receiver, str(tx.amount),
                      str(tx.fee), tx.memo, tx.tx_type,
                      json.dumps(tx.metadata), tx.timestamp))
                conn.commit()
        logger.debug("[vit-chain] tx queued %s %s→%s %s VIT",
                     tx.tx_id[:8], tx.sender[:12], tx.receiver[:12], tx.amount)
        return tx.tx_id

    async def mint_block(
        self,
        transactions: List[VITTransaction],
        miner: str = "system",
    ) -> VITBlock:
        """Mine a new block with ADDA difficulty + halving reward. Returns confirmed block."""
        async with self._lock:
            with self._conn() as conn:
                # Get last block for chaining
                row = conn.execute(
                    "SELECT block_index, block_hash FROM vit_blocks ORDER BY block_index DESC LIMIT 1"
                ).fetchone()
                prev_index = row["block_index"] if row else -1
                prev_hash  = row["block_hash"]  if row else "0" * 64
                new_index  = prev_index + 1

                # ADDA: compute adaptive difficulty for this block
                difficulty  = _compute_next_difficulty(conn)

                # Halving: compute block reward from index
                reward = _block_reward(new_index)

                tx_dicts = [tx.to_dict() for tx in transactions]
                block = VITBlock(
                    index=new_index,
                    transactions=tx_dicts,
                    previous_hash=prev_hash,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    nonce=0,
                    miner=miner,
                    reward=str(reward),
                    difficulty=difficulty,
                )

                # Proof-of-work (run in executor to avoid blocking event loop)
                loop = asyncio.get_event_loop()
                t0   = time.monotonic()
                block.block_hash = await loop.run_in_executor(None, self._mine, block)
                mine_ms = round((time.monotonic() - t0) * 1000, 1)

                conn.execute("""
                    INSERT INTO vit_blocks
                        (block_index, block_hash, previous_hash, miner, reward,
                         difficulty, nonce, timestamp, tx_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_index, block.block_hash, block.previous_hash,
                      miner, str(reward), difficulty, block.nonce,
                      block.timestamp, len(transactions)))

                for tx in transactions:
                    conn.execute("""
                        INSERT OR IGNORE INTO vit_transactions
                            (tx_id, block_index, sender, receiver, amount, fee,
                             memo, tx_type, metadata, status, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
                    """, (tx.tx_id, new_index, tx.sender, tx.receiver,
                          str(tx.amount), str(tx.fee), tx.memo, tx.tx_type,
                          json.dumps(tx.metadata), tx.timestamp))

                    # Decimal-precise balance updates (debit sender, credit receiver)
                    if tx.tx_type not in ("mint",) and tx.sender != _GENESIS_ADDRESS:
                        _update_balance_safe(conn, tx.sender, -tx.amount)
                        # Collect fee for miner
                        if tx.fee > Decimal("0"):
                            _update_balance_safe(conn, tx.sender, -tx.fee)

                    _update_balance_safe(conn, tx.receiver, tx.amount)

                    # Fee goes to miner
                    if tx.fee > Decimal("0") and tx.tx_type not in ("mint",):
                        _update_balance_safe(conn, miner, tx.fee)

                # Mining reward (Decimal-precise)
                _update_balance_safe(conn, miner, reward)

                # Mark any pre-queued pending txs as confirmed
                tx_ids = [tx.tx_id for tx in transactions]
                if tx_ids:
                    conn.execute(
                        "UPDATE vit_transactions SET status='confirmed', block_index=? "
                        "WHERE tx_id IN ({})".format(",".join("?" * len(tx_ids))),
                        [new_index] + tx_ids,
                    )

                conn.commit()

        logger.info(
            "[vit-chain] block #%d mined diff=%d reward=%s VIT hash=%s… txs=%d mine_ms=%s",
            new_index, difficulty, reward, block.block_hash[:16],
            len(transactions), mine_ms,
        )
        return block

    async def verify_chain_integrity(self) -> dict:
        """Validate the entire chain's hash-link continuity and PoW."""
        with self._conn() as conn:
            blocks = conn.execute(
                "SELECT block_index, block_hash, previous_hash, difficulty, "
                "nonce, timestamp, miner FROM vit_blocks ORDER BY block_index"
            ).fetchall()

        errors: List[str] = []
        for i, row in enumerate(blocks):
            idx         = row["block_index"]
            stored_hash = row["block_hash"]
            diff        = int(row["difficulty"] or _DEFAULT_DIFFICULTY)
            if i > 0:
                expected_prev = blocks[i - 1]["block_hash"]
                if row["previous_hash"] != expected_prev:
                    errors.append(f"Block {idx}: previous_hash mismatch")
            if not stored_hash.startswith("0" * diff):
                errors.append(f"Block {idx}: hash doesn't meet difficulty {diff}")

        return {
            "valid":       len(errors) == 0,
            "block_count": len(blocks),
            "errors":      errors,
            "checked_at":  datetime.now(timezone.utc).isoformat(),
        }

    async def get_balance(self, address: str) -> Decimal:
        """Return current Decimal balance for an address."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT balance FROM vit_balances WHERE address = ?", (address,)
            ).fetchone()
        return Decimal(row["balance"]) if row else Decimal("0")

    async def get_chain_stats(self) -> dict:
        """Return rich chain statistics including ADDA and halving info."""
        with self._conn() as conn:
            block_count = conn.execute(
                "SELECT COUNT(*) as c FROM vit_blocks"
            ).fetchone()["c"]
            tx_count = conn.execute(
                "SELECT COUNT(*) as c FROM vit_transactions WHERE status='confirmed'"
            ).fetchone()["c"]
            pending = conn.execute(
                "SELECT COUNT(*) as c FROM vit_transactions WHERE status='pending'"
            ).fetchone()["c"]

            # Circulating supply: sum of all balances except genesis depletion
            supply_row = conn.execute(
                "SELECT COALESCE(SUM(CAST(balance AS REAL)), 0) as s FROM vit_balances"
            ).fetchone()
            circulating = float(supply_row["s"])

            # Avg block time from last 10 blocks
            recent = conn.execute(
                "SELECT timestamp FROM vit_blocks ORDER BY block_index DESC LIMIT 11"
            ).fetchall()
            avg_block_time_s = None
            if len(recent) >= 3:
                try:
                    times = [
                        datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
                        for r in recent
                    ]
                    intervals = [(times[i] - times[i + 1]).total_seconds() for i in range(len(times) - 1)]
                    avg_block_time_s = round(sum(intervals) / len(intervals), 1)
                except Exception:
                    pass

            # Current difficulty
            current_difficulty = _compute_next_difficulty(conn)

            # Hash-rate estimate: hashes/sec ≈ 16^difficulty / avg_block_time
            hash_rate_est = None
            if avg_block_time_s and avg_block_time_s > 0:
                hash_rate_est = round((16 ** current_difficulty) / avg_block_time_s)

        next_block_index  = block_count          # next to be mined
        current_reward    = _block_reward(next_block_index)
        halvings_done     = next_block_index // _HALVING_INTERVAL
        next_halving      = (halvings_done + 1) * _HALVING_INTERVAL

        return {
            "blocks":              block_count,
            "transactions":        tx_count,
            "pending_txs":         pending,
            "circulating_supply":  round(circulating, 8),
            "genesis_supply":      float(_GENESIS_SUPPLY),
            "current_difficulty":  current_difficulty,
            "difficulty_target_s": _BLOCK_TIME_TARGET_S,
            "avg_block_time_s":    avg_block_time_s,
            "hash_rate_estimate":  hash_rate_est,
            "current_reward":      float(current_reward),
            "halvings_done":       halvings_done,
            "next_halving_block":  next_halving,
            "blocks_until_halving": max(0, next_halving - next_block_index),
            "halving_interval":    _HALVING_INTERVAL,
            "db_path":             self.db_path,
            "ledger_version":      "7.0",
        }

    async def get_mempool(self, limit: int = 50) -> dict:
        """Return pending (unconfirmed) transactions."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT tx_id, sender, receiver, amount, fee, memo, tx_type, timestamp
                FROM vit_transactions
                WHERE status = 'pending'
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) as c FROM vit_transactions WHERE status='pending'"
            ).fetchone()["c"]
        return {
            "total":        total,
            "shown":        len(rows),
            "transactions": [dict(r) for r in rows],
        }

    async def get_blocks(self, limit: int = 20, offset: int = 0) -> dict:
        """Return recent blocks in reverse order (newest first)."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT block_index, block_hash, previous_hash, miner, reward,
                       difficulty, nonce, timestamp, tx_count
                FROM vit_blocks
                ORDER BY block_index DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            total = conn.execute("SELECT COUNT(*) as c FROM vit_blocks").fetchone()["c"]
        return {
            "total":  total,
            "blocks": [dict(r) for r in rows],
        }

    async def get_block(self, index: int) -> Optional[dict]:
        """Return full block detail including its transactions."""
        with self._conn() as conn:
            blk = conn.execute("""
                SELECT block_index, block_hash, previous_hash, miner, reward,
                       difficulty, nonce, timestamp, tx_count
                FROM vit_blocks WHERE block_index = ?
            """, (index,)).fetchone()
            if not blk:
                return None
            txs = conn.execute("""
                SELECT tx_id, sender, receiver, amount, fee, memo, tx_type,
                       metadata, status, timestamp
                FROM vit_transactions WHERE block_index = ?
                ORDER BY timestamp
            """, (index,)).fetchall()
        return {
            **dict(blk),
            "transactions": [dict(t) for t in txs],
        }

    async def get_rich_list(self, limit: int = 20) -> dict:
        """Return top addresses by balance (excluding genesis)."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT address, balance, updated_at
                FROM vit_balances
                WHERE address != ?
                  AND CAST(balance AS REAL) > 0
                ORDER BY CAST(balance AS REAL) DESC
                LIMIT ?
            """, (_GENESIS_ADDRESS, limit)).fetchall()
            total_addresses = conn.execute(
                "SELECT COUNT(*) as c FROM vit_balances WHERE address != ?", (_GENESIS_ADDRESS,)
            ).fetchone()["c"]
        return {
            "total_addresses": total_addresses,
            "top_holders":     [dict(r) for r in rows],
        }

    async def mint_vitcoin(self, receiver: str, amount: Decimal, memo: str = "") -> VITBlock:
        """Convenience: mint VITCoin directly to an address."""
        tx = VITTransaction(
            sender=_GENESIS_ADDRESS,
            receiver=receiver,
            amount=amount,
            memo=memo or f"Mint {amount} VIT to {receiver}",
            tx_type="mint",
        )
        return await self.mint_block([tx], miner="treasury")

    async def transfer(
        self,
        sender: str,
        receiver: str,
        amount: Decimal,
        memo: str = "",
        tx_type: str = "transfer",
        fee: Decimal = Decimal("0"),
    ) -> VITBlock:
        """Transfer VITCoin between addresses with optional fee."""
        balance = await self.get_balance(sender)
        total_cost = amount + fee
        if balance < total_cost:
            raise ValueError(f"Insufficient balance: {balance} < {total_cost} (amount + fee)")
        tx = VITTransaction(
            sender=sender, receiver=receiver,
            amount=amount, memo=memo,
            tx_type=tx_type, fee=fee,
        )
        return await self.mint_block([tx], miner="system")


# ── Singleton ─────────────────────────────────────────────────────────────────

_GLOBAL_CHAIN: Optional[VITChainLedger] = None


def get_vit_chain() -> VITChainLedger:
    global _GLOBAL_CHAIN
    if _GLOBAL_CHAIN is None:
        _GLOBAL_CHAIN = VITChainLedger()
    return _GLOBAL_CHAIN


# ── FastAPI router ────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

chain_router = APIRouter(prefix="/api/chain", tags=["VIT Chain"])


class MintRequest(BaseModel):
    receiver: str
    amount:   float
    memo:     str = ""


class TransferRequest(BaseModel):
    sender:   str
    receiver: str
    amount:   float
    memo:     str = ""
    fee:      float = 0.0


@chain_router.get("/stats")
async def chain_stats():
    """Rich chain statistics — difficulty, halving, avg block time, hash-rate."""
    return await get_vit_chain().get_chain_stats()


@chain_router.get("/mempool")
async def chain_mempool(limit: int = Query(50, ge=1, le=200)):
    """Return pending (unconfirmed) transactions in the mempool."""
    return await get_vit_chain().get_mempool(limit=limit)


@chain_router.get("/blocks")
async def chain_blocks(
    limit:  int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Paginated block explorer — newest first."""
    return await get_vit_chain().get_blocks(limit=limit, offset=offset)


@chain_router.get("/block/{index}")
async def chain_block_detail(index: int):
    """Full block detail including all transactions."""
    block = await get_vit_chain().get_block(index)
    if block is None:
        raise HTTPException(status_code=404, detail=f"Block {index} not found")
    return block


@chain_router.get("/rich-list")
async def chain_rich_list(limit: int = Query(20, ge=1, le=100)):
    """Top VITCoin holders by balance."""
    return await get_vit_chain().get_rich_list(limit=limit)


@chain_router.get("/balance/{address}")
async def chain_balance(address: str):
    """Get Decimal-precise VITCoin balance for an address."""
    bal = await get_vit_chain().get_balance(address)
    return {"address": address, "balance": str(bal), "balance_float": float(bal)}


@chain_router.get("/verify")
async def chain_verify():
    """Verify chain integrity — hash-link continuity and PoW for every block."""
    return await get_vit_chain().verify_chain_integrity()


@chain_router.post("/mint")
async def chain_mint(req: MintRequest):
    """Mint VITCoin to an address (treasury operation)."""
    block = await get_vit_chain().mint_vitcoin(
        receiver=req.receiver,
        amount=Decimal(str(req.amount)),
        memo=req.memo,
    )
    return {
        "block_index": block.index,
        "block_hash":  block.block_hash,
        "difficulty":  block.difficulty,
        "reward":      block.reward,
        "minted":      req.amount,
        "receiver":    req.receiver,
    }


@chain_router.post("/transfer")
async def chain_transfer(req: TransferRequest):
    """Transfer VITCoin between addresses."""
    try:
        block = await get_vit_chain().transfer(
            sender=req.sender,
            receiver=req.receiver,
            amount=Decimal(str(req.amount)),
            memo=req.memo,
            fee=Decimal(str(req.fee)),
        )
        return {
            "block_index": block.index,
            "block_hash":  block.block_hash,
            "difficulty":  block.difficulty,
            "transferred": req.amount,
            "fee":         req.fee,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
