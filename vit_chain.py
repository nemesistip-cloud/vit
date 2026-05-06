"""vit_chain.py — VIT Sovereign Ledger v6.0

Hash-linked SQLite blockchain that replaces external gas dependencies.
All VITCoin transactions are recorded on-chain with SHA-256 proof-of-work.

Tables:
  vit_blocks       — mined blocks (hash-linked, difficulty 4)
  vit_transactions — pre-mine transaction queue
  vit_balances     — running address balances

Genesis block mints 1,000,000 VIT to "genesis" address.
Mining reward: 10 VITCoin per block.
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
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

_CHAIN_DB_PATH = os.getenv("VIT_CHAIN_DB", "vit_chain_ledger.db")
_DIFFICULTY    = 4          # leading zeros required in block hash
_MINING_REWARD = Decimal("10.00000000")
_GENESIS_SUPPLY = Decimal("1000000.00000000")
_GENESIS_ADDRESS = "genesis"


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class VITTransaction:
    sender:    str
    receiver:  str
    amount:    Decimal
    memo:      str     = ""
    tx_type:   str     = "transfer"   # transfer | mint | burn | stake | reward | fee
    metadata:  dict    = field(default_factory=dict)
    timestamp: str     = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tx_id:     str     = field(default_factory=lambda: _rand_id())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["amount"] = str(self.amount)
        return d


@dataclass
class VITBlock:
    index:        int
    transactions: List[dict]
    previous_hash: str
    timestamp:    str
    nonce:        int
    miner:        str
    reward:       str
    block_hash:   str = ""

    def compute_hash(self) -> str:
        content = json.dumps({
            "index":         self.index,
            "transactions":  self.transactions,
            "previous_hash": self.previous_hash,
            "timestamp":     self.timestamp,
            "nonce":         self.nonce,
            "miner":         self.miner,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


def _rand_id() -> str:
    import uuid
    return str(uuid.uuid4())


# ── Ledger class ───────────────────────────────────────────────────────────────

class VITChainLedger:
    """Self-contained hash-linked SQLite blockchain."""

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

        # Ensure genesis block exists
        self._ensure_genesis()

    def _ensure_genesis(self) -> None:
        with self._conn() as conn:
            exists = conn.execute(
                "SELECT 1 FROM vit_blocks WHERE block_index = 0"
            ).fetchone()
            if exists:
                return

            genesis_tx = VITTransaction(
                sender=_GENESIS_ADDRESS,
                receiver=_GENESIS_ADDRESS,
                amount=_GENESIS_SUPPLY,
                memo="Genesis block — VIT Sovereign Ledger v6.0",
                tx_type="mint",
            )
            genesis_block = VITBlock(
                index=0,
                transactions=[genesis_tx.to_dict()],
                previous_hash="0" * 64,
                timestamp=datetime.now(timezone.utc).isoformat(),
                nonce=0,
                miner=_GENESIS_ADDRESS,
                reward=str(_MINING_REWARD),
            )
            genesis_block.block_hash = genesis_block.compute_hash()

            conn.execute("""
                INSERT INTO vit_blocks
                    (block_index, block_hash, previous_hash, miner, reward, nonce, timestamp, tx_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (0, genesis_block.block_hash, genesis_block.previous_hash,
                  _GENESIS_ADDRESS, str(_MINING_REWARD), 0,
                  genesis_block.timestamp, 1))

            conn.execute("""
                INSERT INTO vit_transactions
                    (tx_id, block_index, sender, receiver, amount, memo, tx_type, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (genesis_tx.tx_id, 0, _GENESIS_ADDRESS, _GENESIS_ADDRESS,
                  str(_GENESIS_SUPPLY), genesis_tx.memo, "mint", "confirmed",
                  genesis_tx.timestamp))

            conn.execute("""
                INSERT INTO vit_balances (address, balance, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(address) DO UPDATE SET
                    balance    = excluded.balance,
                    updated_at = excluded.updated_at
            """, (_GENESIS_ADDRESS, str(_GENESIS_SUPPLY)))

            conn.commit()
            logger.info("[vit-chain] genesis block created — supply=%s VIT", _GENESIS_SUPPLY)

    # ── Mining ────────────────────────────────────────────────────────────────

    def _mine(self, block: VITBlock) -> str:
        """Proof-of-work: find nonce yielding hash with `_DIFFICULTY` leading zeros."""
        target = "0" * _DIFFICULTY
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
                        (tx_id, sender, receiver, amount, memo, tx_type, metadata, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """, (tx.tx_id, tx.sender, tx.receiver, str(tx.amount),
                      tx.memo, tx.tx_type, json.dumps(tx.metadata), tx.timestamp))
                conn.commit()
        logger.debug("[vit-chain] tx queued %s %s→%s %s VIT",
                     tx.tx_id[:8], tx.sender[:12], tx.receiver[:12], tx.amount)
        return tx.tx_id

    async def mint_block(
        self,
        transactions: List[VITTransaction],
        miner: str = "system",
    ) -> VITBlock:
        """Mine a new block containing `transactions`. Returns the confirmed block."""
        async with self._lock:
            with self._conn() as conn:
                # Get last block
                row = conn.execute(
                    "SELECT block_index, block_hash FROM vit_blocks ORDER BY block_index DESC LIMIT 1"
                ).fetchone()
                prev_index = row["block_index"] if row else -1
                prev_hash  = row["block_hash"]  if row else "0" * 64
                new_index  = prev_index + 1

                tx_dicts = [tx.to_dict() for tx in transactions]
                block = VITBlock(
                    index=new_index,
                    transactions=tx_dicts,
                    previous_hash=prev_hash,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    nonce=0,
                    miner=miner,
                    reward=str(_MINING_REWARD),
                )

                # Proof-of-work (run in executor to avoid blocking event loop)
                loop = asyncio.get_event_loop()
                block.block_hash = await loop.run_in_executor(
                    None, self._mine, block
                )

                conn.execute("""
                    INSERT INTO vit_blocks
                        (block_index, block_hash, previous_hash, miner, reward, nonce, timestamp, tx_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_index, block.block_hash, block.previous_hash,
                      miner, str(_MINING_REWARD), block.nonce,
                      block.timestamp, len(transactions)))

                for tx in transactions:
                    conn.execute("""
                        INSERT OR IGNORE INTO vit_transactions
                            (tx_id, block_index, sender, receiver, amount,
                             memo, tx_type, metadata, status, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
                    """, (tx.tx_id, new_index, tx.sender, tx.receiver,
                          str(tx.amount), tx.memo, tx.tx_type,
                          json.dumps(tx.metadata), tx.timestamp))

                    # Update balances (debit sender except mint/genesis)
                    if tx.tx_type not in ("mint",) and tx.sender != _GENESIS_ADDRESS:
                        conn.execute("""
                            INSERT INTO vit_balances (address, balance, updated_at)
                            VALUES (?, ?, datetime('now'))
                            ON CONFLICT(address) DO UPDATE SET
                                balance    = CAST(CAST(balance AS REAL) - ? AS TEXT),
                                updated_at = datetime('now')
                        """, (tx.sender, str(-tx.amount), float(tx.amount)))

                    # Credit receiver
                    conn.execute("""
                        INSERT INTO vit_balances (address, balance, updated_at)
                        VALUES (?, ?, datetime('now'))
                        ON CONFLICT(address) DO UPDATE SET
                            balance    = CAST(CAST(balance AS REAL) + ? AS TEXT),
                            updated_at = datetime('now')
                    """, (tx.receiver, str(tx.amount), float(tx.amount)))

                # Mining reward for miner
                conn.execute("""
                    INSERT INTO vit_balances (address, balance, updated_at)
                    VALUES (?, ?, datetime('now'))
                    ON CONFLICT(address) DO UPDATE SET
                        balance    = CAST(CAST(balance AS REAL) + ? AS TEXT),
                        updated_at = datetime('now')
                """, (miner, str(_MINING_REWARD), float(_MINING_REWARD)))

                # Mark pending txs as confirmed
                tx_ids = [tx.tx_id for tx in transactions]
                if tx_ids:
                    conn.execute(
                        "UPDATE vit_transactions SET status='confirmed', block_index=? WHERE tx_id IN ({})".format(
                            ",".join("?" * len(tx_ids))
                        ),
                        [new_index] + tx_ids,
                    )

                conn.commit()

        logger.info("[vit-chain] block #%d mined hash=%s txs=%d miner=%s",
                    new_index, block.block_hash[:16], len(transactions), miner)
        return block

    async def verify_chain_integrity(self) -> dict:
        """Validate the entire chain's hash-link continuity."""
        with self._conn() as conn:
            blocks = conn.execute(
                "SELECT block_index, block_hash, previous_hash, nonce, timestamp, miner FROM vit_blocks ORDER BY block_index"
            ).fetchall()

        errors: List[str] = []
        for i, row in enumerate(blocks):
            idx        = row["block_index"]
            stored_hash = row["block_hash"]
            if i > 0:
                expected_prev = blocks[i - 1]["block_hash"]
                if row["previous_hash"] != expected_prev:
                    errors.append(f"Block {idx}: previous_hash mismatch")
            if not stored_hash.startswith("0" * _DIFFICULTY):
                errors.append(f"Block {idx}: hash doesn't meet difficulty")

        return {
            "valid":       len(errors) == 0,
            "block_count": len(blocks),
            "errors":      errors,
            "checked_at":  datetime.now(timezone.utc).isoformat(),
        }

    async def get_balance(self, address: str) -> Decimal:
        """Return current balance for an address."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT balance FROM vit_balances WHERE address = ?", (address,)
            ).fetchone()
        return Decimal(row["balance"]) if row else Decimal("0")

    async def get_chain_stats(self) -> dict:
        """Return high-level chain statistics."""
        with self._conn() as conn:
            block_count = conn.execute("SELECT COUNT(*) as c FROM vit_blocks").fetchone()["c"]
            tx_count    = conn.execute("SELECT COUNT(*) as c FROM vit_transactions WHERE status='confirmed'").fetchone()["c"]
            pending     = conn.execute("SELECT COUNT(*) as c FROM vit_transactions WHERE status='pending'").fetchone()["c"]
            genesis_bal = conn.execute(
                "SELECT balance FROM vit_balances WHERE address=?", (_GENESIS_ADDRESS,)
            ).fetchone()
            total_supply = float(genesis_bal["balance"]) if genesis_bal else 0.0
        return {
            "blocks":          block_count,
            "transactions":    tx_count,
            "pending_txs":     pending,
            "genesis_balance": total_supply,
            "mining_reward":   float(_MINING_REWARD),
            "difficulty":      _DIFFICULTY,
            "db_path":         self.db_path,
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
    ) -> VITBlock:
        """Transfer VITCoin between addresses."""
        balance = await self.get_balance(sender)
        if balance < amount:
            raise ValueError(f"Insufficient balance: {balance} < {amount}")
        tx = VITTransaction(
            sender=sender, receiver=receiver,
            amount=amount, memo=memo, tx_type=tx_type,
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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

chain_router = APIRouter(prefix="/api/chain", tags=["VIT Chain"])


class MintRequest(BaseModel):
    receiver:  str
    amount:    float
    memo:      str = ""


class TransferRequest(BaseModel):
    sender:   str
    receiver: str
    amount:   float
    memo:     str = ""


@chain_router.get("/stats")
async def chain_stats():
    """Public chain statistics."""
    return await get_vit_chain().get_chain_stats()


@chain_router.get("/balance/{address}")
async def chain_balance(address: str):
    """Get VITCoin balance for an address."""
    bal = await get_vit_chain().get_balance(address)
    return {"address": address, "balance": float(bal)}


@chain_router.get("/verify")
async def chain_verify():
    """Verify chain integrity (admin tool)."""
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
        )
        return {
            "block_index": block.index,
            "block_hash":  block.block_hash,
            "transferred": req.amount,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
