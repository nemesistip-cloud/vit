"""
vit_chain.smart_contracts — Phase IV Smart Contract Layer

Provides a minimal contract execution environment for the VIT chain.
Contracts are stored as deterministic Python-dict bytecode executed by
the SimpleVM, making them auditable without a full EVM-compatible stack.
"""

from vit_chain.smart_contracts.types import (
    Contract,
    ContractState,
    ContractResult,
    ContractType,
)
from vit_chain.smart_contracts.vm import SimpleVM
from vit_chain.smart_contracts.registry import ContractRegistry

__all__ = [
    "Contract",
    "ContractState",
    "ContractResult",
    "ContractType",
    "SimpleVM",
    "ContractRegistry",
]
