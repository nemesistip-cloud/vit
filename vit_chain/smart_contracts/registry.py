"""
ContractRegistry — In-memory contract store for the VIT chain node.

In production this will be backed by the chain state DB. For Phase IV this
provides a working in-process registry suitable for single-node deployments.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from vit_chain.smart_contracts.types import Contract, ContractType


class ContractRegistry:
    """Singleton registry of deployed contracts."""

    _instance: Optional["ContractRegistry"] = None
    _contracts: Dict[str, Contract]

    def __new__(cls) -> "ContractRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._contracts = {}
        return cls._instance

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def deploy(self, contract: Contract) -> Contract:
        """Register a new contract. Raises ValueError if address already taken."""
        if contract.contract_id in self._contracts:
            raise ValueError(f"Contract {contract.contract_id} already deployed")
        self._contracts[contract.contract_id] = contract
        return contract

    def get(self, contract_id: str) -> Optional[Contract]:
        return self._contracts.get(contract_id)

    def list_by_type(self, contract_type: ContractType) -> List[Contract]:
        return [c for c in self._contracts.values() if c.contract_type == contract_type]

    def list_by_creator(self, creator: str) -> List[Contract]:
        return [c for c in self._contracts.values() if c.creator == creator]

    def all(self) -> List[Contract]:
        return list(self._contracts.values())

    def count(self) -> int:
        return len(self._contracts)

    # ── Built-in contract templates ───────────────────────────────────────────

    @staticmethod
    def prediction_escrow_template(
        creator: str,
        match_id: int,
        stake_amount: int,
        bet_side: str,
    ) -> Contract:
        """
        Template: lock stake until match result, pay out on win.
        """
        return Contract(
            creator=creator,
            contract_type=ContractType.PREDICTION_ESCROW,
            bytecode={
                "lock": [
                    {"op": "REQUIRE", "args": ["$sender_is_creator", "Only creator can lock"]},
                    {"op": "SET",  "args": ["locked", True]},
                    {"op": "SET",  "args": ["stake",  stake_amount]},
                    {"op": "SET",  "args": ["bet_side", bet_side]},
                    {"op": "SET",  "args": ["match_id", match_id]},
                    {"op": "EMIT", "args": ["Locked", {"match_id": match_id, "stake": stake_amount}]},
                    {"op": "RETURN", "args": [True]},
                ],
                "settle": [
                    {"op": "REQUIRE", "args": ["$locked",  "Contract not locked"]},
                    {"op": "REQUIRE", "args": ["$result_available", "Result not finalised"]},
                    {"op": "SET",  "args": ["settled", True]},
                    {"op": "EQ",   "args": ["$actual_outcome", "$bet_side"]},
                    {"op": "SET",  "args": ["won", "$_last"]},
                    {"op": "EMIT", "args": ["Settled", {"won": "$_last"}]},
                    {"op": "RETURN", "args": ["$_last"]},
                ],
            },
        )

    @staticmethod
    def attestation_template(creator: str, attestation_hash: str) -> Contract:
        """Template: immutably record an attestation hash on chain."""
        return Contract(
            creator=creator,
            contract_type=ContractType.ATTESTATION,
            bytecode={
                "record": [
                    {"op": "SET",  "args": ["hash",      attestation_hash]},
                    {"op": "SET",  "args": ["recorded",  True]},
                    {"op": "EMIT", "args": ["Attested",  {"hash": attestation_hash}]},
                    {"op": "RETURN", "args": [attestation_hash]},
                ],
                "verify": [
                    {"op": "GET",  "args": ["hash"]},
                    {"op": "EQ",   "args": ["$_last", "$check_hash"]},
                    {"op": "RETURN", "args": ["$_last"]},
                ],
            },
        )
