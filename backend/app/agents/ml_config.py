"""app/agents/ml_config.py — Shared runtime config for ML pipeline agents.

Updated at runtime via POST /admin/ml-control/config.
Agents import get() and check values each cycle so changes take effect
without a restart.
"""

from __future__ import annotations

_config: dict = {
    "accuracy_floor":          0.45,
    "retrain_cooldown_hours":  24,
    "min_flag_cycles":         2,
    "auto_promote_threshold":  0.02,
    "auto_retrain_enabled":    True,
    "auto_promote_enabled":    True,
}


def get() -> dict:
    return _config.copy()


def update(patch: dict) -> dict:
    allowed = set(_config.keys())
    for k, v in patch.items():
        if k in allowed:
            _config[k] = v
    return _config.copy()
