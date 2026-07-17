"""AI Prompt Generator — Module D3.

Wraps the existing prompt_generator with the Module D TrainingJob interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.training.prompt_generator import generate_training_prompt as _generate
from app.training.prompt_generator import generate_guide_steps


def generate_training_prompt(
    quality_report: Dict[str, Any],
    league: str = "unknown",
    row_count: int = 0,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    model_list: Optional[List[str]] = None,
) -> str:
    """
    Generate a structured natural-language training prompt.

    Parameters
    ----------
    quality_report  : output of score_dataset()
    league          : league name
    row_count       : total records in dataset
    date_from       : ISO date string
    date_to         : ISO date string
    model_list      : list of model names to train

    Returns
    -------
    str — the full training prompt ready for an LLM
    """
    config = {
        "leagues": [league],
        "date_from": date_from or "unknown",
        "date_to": date_to or "unknown",
        "validation_split": 0.20,
    }

    quality_report.setdefault("record_count", row_count)

    return _generate(quality_report=quality_report, config=config, model_list=model_list)


def build_guide_steps(quality_report: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return ordered guide steps for a training job."""
    return generate_guide_steps(quality_report)
