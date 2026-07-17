"""
Contract types and state definitions for the VIT chain smart contract layer.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ContractType(str, Enum):
    PREDICTION_ESCROW   = "prediction_escrow"   # Locks stake until match result
    PAYOUT_RULE         = "payout_rule"          # Defines reward distribution logic
    ATTESTATION         = "attestation"          # Anchors off-chain data on-chain
    GOVERNANCE_VOTE     = "governance_vote"      # DAO voting contract
    CUSTOM              = "custom"               # User-defined contract


@dataclass
class ContractState:
    """Mutable key-value store owned by one contract instance."""
    data: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def delete(self, key: str) -> None:
        self.data.pop(key, None)

    def snapshot(self) -> Dict[str, Any]:
        return dict(self.data)


@dataclass
class Contract:
    """
    A VIT chain smart contract.

    Attributes
    ----------
    contract_id : str
        Deterministic SHA-256 address derived from creator + bytecode.
    creator : str
        Wallet address or user ID of the deployer.
    contract_type : ContractType
    bytecode : dict
        Serialisable instruction set executed by SimpleVM.
    state : ContractState
        Mutable runtime state.
    deployed_at : int
        Unix timestamp of deployment.
    """
    creator: str
    contract_type: ContractType
    bytecode: Dict[str, Any]
    state: ContractState = field(default_factory=ContractState)
    deployed_at: int = field(default_factory=lambda: int(time.time()))
    contract_id: str = field(init=False)

    def __post_init__(self) -> None:
        raw = json.dumps(
            {"creator": self.creator, "bytecode": self.bytecode, "deployed_at": self.deployed_at},
            sort_keys=True,
        )
        self.contract_id = "0x" + hashlib.sha256(raw.encode()).hexdigest()[:40]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "creator": self.creator,
            "type": self.contract_type.value,
            "bytecode": self.bytecode,
            "state": self.state.snapshot(),
            "deployed_at": self.deployed_at,
        }


@dataclass
class ContractResult:
    """Return value from a contract call."""
    success: bool
    return_value: Any = None
    gas_used: int = 0
    error: Optional[str] = None
    state_changes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "return_value": self.return_value,
            "gas_used": self.gas_used,
            "error": self.error,
            "state_changes": self.state_changes,
        }
