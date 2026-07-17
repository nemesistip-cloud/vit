"""
SimpleVM — Minimal deterministic execution engine for VIT chain contracts.

Opcodes
-------
SET key value       — Write value to contract state
GET key             — Read key from contract state (returns value)
REQUIRE cond msg    — Halt with error if cond is falsy
EMIT event payload  — Append an event to the execution log
ADD a b             — Integer addition
SUB a b             — Integer subtraction
MUL a b             — Integer multiplication
DIV a b             — Integer division (raises on zero)
EQ  a b             — Returns True if a == b
GT  a b             — Returns True if a >  b
LT  a b             — Returns True if a <  b
RETURN value        — Set the contract return value and halt

All operands are resolved through the context dict before execution:
  - If the value is a string starting with "$", it is treated as a variable
    reference and looked up in the execution context.
  - All other values are treated as literals.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from vit_chain.smart_contracts.types import Contract, ContractResult

# Gas cost per opcode (simplified)
GAS_COSTS: Dict[str, int] = {
    "SET": 200, "GET": 50, "REQUIRE": 100, "EMIT": 150,
    "ADD": 20, "SUB": 20, "MUL": 30, "DIV": 30,
    "EQ": 20, "GT": 20, "LT": 20, "RETURN": 50,
}
GAS_LIMIT_DEFAULT = 100_000


class VMError(Exception):
    """Raised when contract execution fails."""


class SimpleVM:
    """
    Executes VIT chain contract bytecode.

    Usage
    -----
    vm = SimpleVM()
    result = vm.execute(contract, method="transfer", context={"sender": "0xabc", "amount": 100})
    """

    def __init__(self, gas_limit: int = GAS_LIMIT_DEFAULT) -> None:
        self.gas_limit = gas_limit

    def _resolve(self, value: Any, context: Dict[str, Any]) -> Any:
        """Resolve variable references ($var) from context."""
        if isinstance(value, str) and value.startswith("$"):
            key = value[1:]
            if key not in context:
                raise VMError(f"Undefined variable: {value}")
            return context[key]
        return value

    def execute(
        self,
        contract: Contract,
        method: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ContractResult:
        """
        Execute a named method from the contract bytecode.

        Parameters
        ----------
        contract : Contract
        method   : str        — Key in contract.bytecode mapping to instruction list
        context  : dict       — Caller-supplied variables ($sender, $amount, …)
        """
        ctx = dict(context or {})
        ctx.setdefault("timestamp", int(time.time()))

        instructions: List[Dict[str, Any]] = contract.bytecode.get(method, [])
        if not instructions:
            return ContractResult(
                success=False,
                error=f"Method '{method}' not found in contract {contract.contract_id}",
            )

        gas_used = 0
        events: List[Dict[str, Any]] = []
        return_value: Any = None
        state_snapshot_before = contract.state.snapshot()

        try:
            for instr in instructions:
                op: str = instr.get("op", "").upper()
                args: List[Any] = instr.get("args", [])

                cost = GAS_COSTS.get(op, 10)
                gas_used += cost
                if gas_used > self.gas_limit:
                    raise VMError(f"Gas limit exceeded ({self.gas_limit})")

                if op == "SET":
                    key   = self._resolve(args[0], ctx)
                    value = self._resolve(args[1], ctx)
                    contract.state.set(str(key), value)
                    ctx[str(key)] = value

                elif op == "GET":
                    key = self._resolve(args[0], ctx)
                    result_val = contract.state.get(str(key))
                    ctx["_last"] = result_val

                elif op == "REQUIRE":
                    cond = self._resolve(args[0], ctx)
                    msg  = self._resolve(args[1], ctx) if len(args) > 1 else "Requirement failed"
                    if not cond:
                        raise VMError(str(msg))

                elif op == "EMIT":
                    event_name = self._resolve(args[0], ctx)
                    payload    = self._resolve(args[1], ctx) if len(args) > 1 else {}
                    events.append({"event": event_name, "payload": payload, "gas": gas_used})

                elif op == "ADD":
                    a = self._resolve(args[0], ctx)
                    b = self._resolve(args[1], ctx)
                    ctx["_last"] = int(a) + int(b)

                elif op == "SUB":
                    a = self._resolve(args[0], ctx)
                    b = self._resolve(args[1], ctx)
                    ctx["_last"] = int(a) - int(b)

                elif op == "MUL":
                    a = self._resolve(args[0], ctx)
                    b = self._resolve(args[1], ctx)
                    ctx["_last"] = int(a) * int(b)

                elif op == "DIV":
                    a = self._resolve(args[0], ctx)
                    b = self._resolve(args[1], ctx)
                    if int(b) == 0:
                        raise VMError("Division by zero")
                    ctx["_last"] = int(a) // int(b)

                elif op in ("EQ", "GT", "LT"):
                    a = self._resolve(args[0], ctx)
                    b = self._resolve(args[1], ctx)
                    ctx["_last"] = (a == b if op == "EQ" else a > b if op == "GT" else a < b)

                elif op == "RETURN":
                    return_value = self._resolve(args[0], ctx) if args else ctx.get("_last")
                    break

                else:
                    raise VMError(f"Unknown opcode: {op}")

        except VMError as e:
            # Roll back state changes on failure
            contract.state.data = state_snapshot_before
            return ContractResult(
                success=False,
                error=str(e),
                gas_used=gas_used,
                state_changes={},
            )

        state_after = contract.state.snapshot()
        state_changes = {k: v for k, v in state_after.items() if state_snapshot_before.get(k) != v}

        return ContractResult(
            success=True,
            return_value=return_value,
            gas_used=gas_used,
            state_changes=state_changes,
        )
