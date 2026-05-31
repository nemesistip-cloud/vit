"""Smart Contract Executor — deterministic rule-based contract evaluation engine."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

GAS_TABLE = {
    "transfer": 21_000,
    "mint": 55_000,
    "burn": 35_000,
    "stake": 85_000,
    "unstake": 75_000,
    "slash": 60_000,
    "vote": 45_000,
    "propose": 90_000,
    "execute": 120_000,
    "allocate": 70_000,
    "register": 100_000,
    "update_state": 25_000,
    "query": 5_000,
    "default": 30_000,
}

BUILTIN_ABIS: dict[str, list[dict]] = {
    "VITToken": [
        {"name": "transfer", "inputs": ["to", "amount"], "outputs": ["success"]},
        {"name": "mint", "inputs": ["to", "amount"], "outputs": ["new_supply"]},
        {"name": "burn", "inputs": ["from", "amount"], "outputs": ["new_supply"]},
        {"name": "balance_of", "inputs": ["address"], "outputs": ["balance"]},
        {"name": "total_supply", "inputs": [], "outputs": ["supply"]},
    ],
    "Staking": [
        {"name": "stake", "inputs": ["validator", "amount", "lock_days"], "outputs": ["stake_id"]},
        {"name": "unstake", "inputs": ["stake_id"], "outputs": ["returned"]},
        {"name": "slash", "inputs": ["validator", "pct"], "outputs": ["slashed_amount"]},
        {"name": "claim_rewards", "inputs": ["validator"], "outputs": ["rewards"]},
        {"name": "get_stake", "inputs": ["stake_id"], "outputs": ["stake_info"]},
    ],
    "Prediction": [
        {"name": "create_market", "inputs": ["match_id", "market_type", "odds"], "outputs": ["market_id"]},
        {"name": "place_bet", "inputs": ["market_id", "outcome", "amount"], "outputs": ["bet_id"]},
        {"name": "settle_market", "inputs": ["market_id", "result"], "outputs": ["payouts"]},
        {"name": "dispute_result", "inputs": ["market_id", "evidence"], "outputs": ["dispute_id"]},
    ],
    "Governance": [
        {"name": "propose", "inputs": ["title", "description", "call_data"], "outputs": ["proposal_id"]},
        {"name": "vote", "inputs": ["proposal_id", "support", "weight"], "outputs": ["vote_id"]},
        {"name": "execute", "inputs": ["proposal_id"], "outputs": ["execution_hash"]},
        {"name": "cancel", "inputs": ["proposal_id"], "outputs": ["success"]},
        {"name": "queue", "inputs": ["proposal_id"], "outputs": ["eta"]},
    ],
    "Treasury": [
        {"name": "allocate", "inputs": ["pool", "recipient", "amount", "reason"], "outputs": ["allocation_id"]},
        {"name": "deposit", "inputs": ["pool", "amount", "source"], "outputs": ["balance"]},
        {"name": "withdraw", "inputs": ["pool", "amount", "to"], "outputs": ["tx_hash"]},
        {"name": "pool_balance", "inputs": ["pool"], "outputs": ["balance"]},
    ],
}

BUILTIN_RULES: dict[str, dict] = {
    "VITToken": {
        "max_supply": 1_000_000_000,
        "min_transfer": Decimal("0.000001"),
        "burn_rate_pct": Decimal("0"),
        "pause_on_anomaly": True,
    },
    "Staking": {
        "min_stake": Decimal("100"),
        "max_stake": Decimal("10_000_000"),
        "min_lock_days": 7,
        "max_lock_days": 365,
        "base_apy": Decimal("0.08"),
        "slash_max_pct": Decimal("0.50"),
    },
    "Prediction": {
        "min_bet": Decimal("1"),
        "max_bet": Decimal("100_000"),
        "house_edge_pct": Decimal("0.02"),
        "dispute_window_hours": 24,
        "oracle_required": True,
    },
    "Governance": {
        "quorum_pct": Decimal("0.04"),
        "pass_threshold": Decimal("0.51"),
        "voting_period_days": 7,
        "timelock_days": 2,
        "min_proposal_stake": Decimal("1000"),
    },
    "Treasury": {
        "max_single_alloc_pct": Decimal("0.10"),
        "multisig_threshold": 3,
        "governance_required_above": Decimal("50000"),
        "auto_distribute_rewards": True,
    },
}


def _compute_tx_hash(contract_address: str, method: str, params: dict, nonce: int) -> str:
    raw = json.dumps({
        "contract": contract_address,
        "method": method,
        "params": params,
        "nonce": nonce,
        "ts": datetime.now(timezone.utc).isoformat(),
        "salt": secrets.token_hex(8),
    }, sort_keys=True, default=str)
    return "0x" + hashlib.sha3_256(raw.encode()).hexdigest()


def _compute_event_topic(event_name: str, contract_address: str) -> str:
    raw = f"{contract_address}:{event_name}".encode()
    return "0x" + hashlib.sha3_256(raw).hexdigest()


def _gas_for_method(method: str) -> int:
    return GAS_TABLE.get(method, GAS_TABLE["default"])


def _validate_params(method: str, params: dict, rules: dict) -> tuple[bool, str]:
    """Rule-based parameter validation."""
    if method == "transfer":
        amount = Decimal(str(params.get("amount", 0)))
        if amount <= 0:
            return False, "Transfer amount must be positive"
        if "min_transfer" in rules and amount < rules["min_transfer"]:
            return False, f"Below minimum transfer {rules['min_transfer']}"

    elif method == "stake":
        amount = Decimal(str(params.get("amount", 0)))
        min_s = Decimal(str(rules.get("min_stake", 0)))
        max_s = Decimal(str(rules.get("max_stake", 10**9)))
        if amount < min_s:
            return False, f"Below minimum stake {min_s}"
        if amount > max_s:
            return False, f"Exceeds maximum stake {max_s}"

    elif method == "slash":
        pct = Decimal(str(params.get("pct", 0)))
        max_slash = Decimal(str(rules.get("slash_max_pct", Decimal("0.5"))))
        if pct <= 0 or pct > max_slash:
            return False, f"Slash percent must be 0–{max_slash}"

    elif method == "vote":
        if "support" not in params:
            return False, "Vote requires 'support' parameter"

    elif method == "allocate":
        if not params.get("recipient"):
            return False, "Allocation requires recipient"

    return True, ""


def execute_contract_call(
    contract_address: str,
    contract_name: str,
    method: str,
    params: dict,
    state: dict,
    rules: dict,
    caller: str | None = None,
    block_number: int = 0,
) -> dict[str, Any]:
    """
    Deterministic contract execution engine.
    Returns: {success, result, new_state, events, gas_used, error, tx_hash}
    """
    tx_hash = _compute_tx_hash(contract_address, method, params, block_number)
    gas_used = _gas_for_method(method)
    events: list[dict] = []
    new_state = dict(state)

    valid, err = _validate_params(method, params, rules)
    if not valid:
        return {
            "success": False,
            "result": None,
            "new_state": state,
            "events": [],
            "gas_used": gas_used // 5,
            "error": err,
            "tx_hash": tx_hash,
        }

    result: Any = None

    try:
        if contract_name == "VITToken":
            result, new_state, events = _exec_token(method, params, new_state, rules, contract_address)

        elif contract_name == "Staking":
            result, new_state, events = _exec_staking(method, params, new_state, rules, contract_address)

        elif contract_name == "Prediction":
            result, new_state, events = _exec_prediction(method, params, new_state, rules, contract_address)

        elif contract_name == "Governance":
            result, new_state, events = _exec_governance(method, params, new_state, rules, contract_address, caller)

        elif contract_name == "Treasury":
            result, new_state, events = _exec_treasury(method, params, new_state, rules, contract_address)

        else:
            result, new_state, events = _exec_generic(method, params, new_state, contract_address)

        return {
            "success": True,
            "result": result,
            "new_state": new_state,
            "events": events,
            "gas_used": gas_used,
            "error": None,
            "tx_hash": tx_hash,
        }

    except Exception as exc:
        logger.exception("[executor] Contract call failed: %s.%s", contract_name, method)
        return {
            "success": False,
            "result": None,
            "new_state": state,
            "events": [],
            "gas_used": gas_used // 2,
            "error": str(exc),
            "tx_hash": tx_hash,
        }


def _exec_token(method: str, params: dict, state: dict, rules: dict, addr: str):
    events = []
    balances: dict = state.get("balances", {})
    supply = Decimal(str(state.get("total_supply", "0")))
    result = None

    if method == "transfer":
        frm = str(params.get("from", "system"))
        to = str(params["to"])
        amount = Decimal(str(params["amount"]))
        bal_from = Decimal(str(balances.get(frm, "0")))
        if bal_from < amount:
            raise ValueError(f"Insufficient balance: have {bal_from}, need {amount}")
        balances[frm] = str(bal_from - amount)
        balances[to] = str(Decimal(str(balances.get(to, "0"))) + amount)
        events.append({"name": "Transfer", "topic": _compute_event_topic("Transfer", addr),
                       "data": {"from": frm, "to": to, "amount": str(amount)}})
        result = {"success": True}

    elif method == "mint":
        to = str(params["to"])
        amount = Decimal(str(params["amount"]))
        max_supply = Decimal(str(rules.get("max_supply", 10**9)))
        if supply + amount > max_supply:
            raise ValueError("Exceeds maximum supply")
        balances[to] = str(Decimal(str(balances.get(to, "0"))) + amount)
        supply += amount
        events.append({"name": "Mint", "topic": _compute_event_topic("Mint", addr),
                       "data": {"to": to, "amount": str(amount), "new_supply": str(supply)}})
        result = {"new_supply": str(supply)}

    elif method == "burn":
        frm = str(params.get("from", "system"))
        amount = Decimal(str(params["amount"]))
        bal = Decimal(str(balances.get(frm, "0")))
        if bal < amount:
            raise ValueError("Insufficient balance to burn")
        balances[frm] = str(bal - amount)
        supply -= amount
        events.append({"name": "Burn", "topic": _compute_event_topic("Burn", addr),
                       "data": {"from": frm, "amount": str(amount), "new_supply": str(supply)}})
        result = {"new_supply": str(supply)}

    elif method in ("balance_of", "total_supply"):
        if method == "balance_of":
            addr_q = str(params.get("address", ""))
            result = {"balance": str(balances.get(addr_q, "0"))}
        else:
            result = {"supply": str(supply)}

    state["balances"] = balances
    state["total_supply"] = str(supply)
    return result, state, events


def _exec_staking(method: str, params: dict, state: dict, rules: dict, addr: str):
    events = []
    stakes: dict = state.get("stakes", {})
    result = None

    if method == "stake":
        stake_id = secrets.token_hex(8)
        amount = Decimal(str(params["amount"]))
        validator = str(params.get("validator", "default"))
        lock_days = int(params.get("lock_days", 30))
        apy = Decimal(str(rules.get("base_apy", "0.08")))
        stakes[stake_id] = {
            "validator": validator, "amount": str(amount),
            "lock_days": lock_days, "apy": str(apy), "active": True,
            "staked_at": datetime.now(timezone.utc).isoformat(),
        }
        events.append({"name": "Staked", "topic": _compute_event_topic("Staked", addr),
                       "data": {"stake_id": stake_id, "amount": str(amount), "validator": validator}})
        result = {"stake_id": stake_id}

    elif method == "unstake":
        stake_id = str(params["stake_id"])
        if stake_id not in stakes:
            raise ValueError("Stake not found")
        stake = stakes[stake_id]
        stake["active"] = False
        amount = Decimal(str(stake["amount"]))
        events.append({"name": "Unstaked", "topic": _compute_event_topic("Unstaked", addr),
                       "data": {"stake_id": stake_id, "returned": str(amount)}})
        result = {"returned": str(amount)}

    elif method == "slash":
        validator = str(params.get("validator", ""))
        pct = Decimal(str(params["pct"]))
        slashed = Decimal("0")
        for sid, s in stakes.items():
            if s.get("validator") == validator and s.get("active"):
                amt = Decimal(str(s["amount"]))
                cut = amt * pct
                s["amount"] = str(amt - cut)
                slashed += cut
        events.append({"name": "Slashed", "topic": _compute_event_topic("Slashed", addr),
                       "data": {"validator": validator, "pct": str(pct), "total_slashed": str(slashed)}})
        result = {"slashed_amount": str(slashed)}

    elif method == "get_stake":
        stake_id = str(params.get("stake_id", ""))
        result = {"stake_info": stakes.get(stake_id, {})}

    state["stakes"] = stakes
    return result, state, events


def _exec_prediction(method: str, params: dict, state: dict, rules: dict, addr: str):
    events = []
    markets: dict = state.get("markets", {})
    result = None

    if method == "create_market":
        market_id = secrets.token_hex(8)
        markets[market_id] = {
            "match_id": params.get("match_id"),
            "market_type": params.get("market_type", "1X2"),
            "odds": params.get("odds", {}),
            "bets": {},
            "settled": False,
            "result": None,
        }
        events.append({"name": "MarketCreated", "topic": _compute_event_topic("MarketCreated", addr),
                       "data": {"market_id": market_id, "match_id": params.get("match_id")}})
        result = {"market_id": market_id}

    elif method == "place_bet":
        market_id = str(params["market_id"])
        if market_id not in markets:
            raise ValueError("Market not found")
        if markets[market_id]["settled"]:
            raise ValueError("Market already settled")
        bet_id = secrets.token_hex(8)
        markets[market_id]["bets"][bet_id] = {
            "outcome": params.get("outcome"),
            "amount": str(params.get("amount", 0)),
            "bettor": params.get("bettor", ""),
        }
        result = {"bet_id": bet_id}

    elif method == "settle_market":
        market_id = str(params["market_id"])
        if market_id not in markets:
            raise ValueError("Market not found")
        market = markets[market_id]
        market["settled"] = True
        market["result"] = params.get("result")
        payouts = {}
        for bid, bet in market["bets"].items():
            if bet["outcome"] == params.get("result"):
                odds = Decimal(str(market["odds"].get(bet["outcome"], "2")))
                payout = Decimal(str(bet["amount"])) * odds
                payouts[bid] = str(payout)
        events.append({"name": "MarketSettled", "topic": _compute_event_topic("MarketSettled", addr),
                       "data": {"market_id": market_id, "result": params.get("result"), "payouts": payouts}})
        result = {"payouts": payouts}

    state["markets"] = markets
    return result, state, events


def _exec_governance(method: str, params: dict, state: dict, rules: dict, addr: str, caller: str | None):
    events = []
    proposals: dict = state.get("proposals", {})
    result = None

    if method == "propose":
        prop_id = secrets.token_hex(8)
        proposals[prop_id] = {
            "title": params.get("title"),
            "description": params.get("description"),
            "call_data": params.get("call_data", {}),
            "proposer": caller,
            "votes_for": 0, "votes_against": 0,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        events.append({"name": "Proposed", "topic": _compute_event_topic("Proposed", addr),
                       "data": {"proposal_id": prop_id, "title": params.get("title")}})
        result = {"proposal_id": prop_id}

    elif method == "vote":
        prop_id = str(params["proposal_id"])
        if prop_id not in proposals:
            raise ValueError("Proposal not found")
        support = bool(params.get("support", True))
        weight = int(params.get("weight", 1))
        if support:
            proposals[prop_id]["votes_for"] += weight
        else:
            proposals[prop_id]["votes_against"] += weight
        result = {"vote_id": secrets.token_hex(4)}

    elif method == "execute":
        prop_id = str(params["proposal_id"])
        if prop_id not in proposals:
            raise ValueError("Proposal not found")
        p = proposals[prop_id]
        total = p["votes_for"] + p["votes_against"]
        if total == 0:
            raise ValueError("No votes cast")
        pass_thr = Decimal(str(rules.get("pass_threshold", "0.51")))
        if Decimal(str(p["votes_for"])) / Decimal(str(total)) < pass_thr:
            raise ValueError("Did not reach passing threshold")
        p["status"] = "executed"
        exec_hash = _compute_tx_hash(addr, "execute", params, 0)
        events.append({"name": "ProposalExecuted", "topic": _compute_event_topic("ProposalExecuted", addr),
                       "data": {"proposal_id": prop_id, "exec_hash": exec_hash}})
        result = {"execution_hash": exec_hash}

    state["proposals"] = proposals
    return result, state, events


def _exec_treasury(method: str, params: dict, state: dict, rules: dict, addr: str):
    events = []
    pools: dict = state.get("pools", {})
    result = None

    if method == "deposit":
        pool = str(params["pool"])
        amount = Decimal(str(params["amount"]))
        pools[pool] = str(Decimal(str(pools.get(pool, "0"))) + amount)
        events.append({"name": "Deposited", "topic": _compute_event_topic("Deposited", addr),
                       "data": {"pool": pool, "amount": str(amount)}})
        result = {"balance": pools[pool]}

    elif method == "allocate":
        pool = str(params["pool"])
        amount = Decimal(str(params["amount"]))
        bal = Decimal(str(pools.get(pool, "0")))
        if bal < amount:
            raise ValueError(f"Insufficient pool balance: {bal}")
        pools[pool] = str(bal - amount)
        alloc_id = secrets.token_hex(8)
        events.append({"name": "Allocated", "topic": _compute_event_topic("Allocated", addr),
                       "data": {"pool": pool, "amount": str(amount), "recipient": params.get("recipient"), "allocation_id": alloc_id}})
        result = {"allocation_id": alloc_id}

    elif method == "pool_balance":
        pool = str(params["pool"])
        result = {"balance": pools.get(pool, "0")}

    state["pools"] = pools
    return result, state, events


def _exec_generic(method: str, params: dict, state: dict, addr: str):
    key = str(params.get("key", method))
    state[key] = params.get("value", True)
    events = [{"name": "StateUpdated", "topic": _compute_event_topic("StateUpdated", addr),
               "data": {"key": key, "method": method}}]
    return {"updated": key}, state, events
