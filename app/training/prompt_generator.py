# app/training/prompt_generator.py — Module D3
# AI Prompt Generator: generates a structured training prompt from dataset profile

from __future__ import annotations

from typing import Any, Dict, List


def generate_training_prompt(
    quality_report: Dict[str, Any],
    config: Dict[str, Any] | None = None,
    model_list: List[str] | None = None,
) -> str:
    """
    Generate a structured AI training prompt from a quality report.
    Uses column_profile, quality_score, and config to produce a prompt
    that can be used with Claude, Gemini, or GPT to guide training.
    """
    score = quality_report.get("score", 0)
    grade = quality_report.get("grade", "F")
    n = quality_report.get("record_count", 0)
    breakdown = quality_report.get("breakdown", {})
    issues = quality_report.get("issues", [])
    recommendations = quality_report.get("recommendations", [])
    outcome_dist = quality_report.get("outcome_distribution", {})
    feature_detail = quality_report.get("feature_coverage_detail", {})

    config = config or {}
    leagues = config.get("leagues", ["unknown"])
    date_from = config.get("date_from", "unknown")
    date_to = config.get("date_to", "unknown")
    validation_split = config.get("validation_split", 0.20)

    models = model_list or [
        "PoissonGoals", "EloRating", "DixonColes", "BayesianNet",
        "LSTM", "Transformer", "LogisticReg", "RandomForest",
        "XGBoost", "MarketImplied", "NeuralEnsemble", "HybridStack",
    ]

    issues_block = "\n".join(f"  - {i}" for i in issues) if issues else "  None detected"
    recommendations_block = "\n".join(f"  {idx+1}. {r}" for idx, r in enumerate(recommendations)) if recommendations else "  Dataset looks healthy — proceed with training"
    features_block = "\n".join(
        f"  - {feat}: {cov}" for feat, cov in feature_detail.items()
    )
    models_block = "\n".join(f"  - {m}" for m in models)

    prompt = f"""# VIT Sports Intelligence — AI Training Guide

## Dataset Profile
- **Records**: {n:,}
- **Leagues**: {', '.join(leagues)}
- **Date Range**: {date_from} → {date_to}
- **Validation Split**: {validation_split:.0%} held out for evaluation
- **Outcome Distribution**: Home={outcome_dist.get('home', 0)}, Draw={outcome_dist.get('draw', 0)}, Away={outcome_dist.get('away', 0)}

## Data Quality Assessment
- **Overall Score**: {score}/100 (Grade {grade})
- Completeness: {breakdown.get('completeness', 0):.1f}/100
- Sample Size: {breakdown.get('sample_size', 0):.1f}/100
- Recency: {breakdown.get('recency', 0):.1f}/100
- Feature Coverage: {breakdown.get('feature_coverage', 0):.1f}/100
- Variance: {breakdown.get('variance', 0):.1f}/100

## Feature Coverage Detail
{features_block}

## Detected Issues
{issues_block}

## Recommended Actions Before Training
{recommendations_block}

## Models To Train
{models_block}

## Training Instructions
For each model above:
1. Use vig-free market probabilities as the base signal (removes bookmaker margin)
2. Engineer features: home_advantage (+4.5%), recent_form (last 5 matches), goal_rates (Poisson lambda)
3. Train on 80% of records; validate on the held-out {validation_split:.0%}
4. Report: accuracy (1x2), log_loss, Brier score, over/under accuracy
5. Flag any model with accuracy < 50% — it is performing worse than random

## Evaluation Criteria
- **Acceptable**: accuracy ≥ 52%, Brier ≤ 0.65
- **Good**: accuracy ≥ 55%, positive CLV rate ≥ 55%
- **Excellent**: accuracy ≥ 58%, Sharpe ratio ≥ 0.5

## Context
This dataset will train the VIT 12-model ensemble for football match outcome prediction.
The ensemble uses weighted aggregation where better models receive higher weights.
Models that consistently underperform are automatically down-weighted by the accountability loop.
Focus on calibration (well-calibrated probabilities) over raw accuracy — a model that says 60%
should win 60% of the time, not 80%.
"""
    return prompt.strip()


def generate_guide_steps(quality_report: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate step-by-step guide steps for a training job based on quality report."""
    score = quality_report.get("score", 0)
    steps = [
        {"step_number": 1, "step_name": "Data Quality Check", "description": f"Dataset scored {score}/100. Grade: {quality_report.get('grade', 'F')}"},
        {"step_number": 2, "step_name": "Feature Engineering", "description": "Compute vig-free probabilities, home advantage, recent form signals"},
        {"step_number": 3, "step_name": "Train/Validation Split", "description": "Hold out 20% of records for unbiased evaluation"},
        {"step_number": 4, "step_name": "Train All 12 Models", "description": "Run each model's .train() method sequentially"},
        {"step_number": 5, "step_name": "Evaluate & Score", "description": "Compute accuracy, log_loss, Brier score per model"},
        {"step_number": 6, "step_name": "Weight Adjustment", "description": "Update model weights based on relative performance"},
        {"step_number": 7, "step_name": "Persist Weights", "description": "Save trained model artifacts to /models/*.pkl"},
        {"step_number": 8, "step_name": "Promote to Production", "description": "If avg accuracy improved, promote this version"},
    ]

    if score < 55:
        steps.insert(1, {
            "step_number": 2,
            "step_name": "Data Remediation Required",
            "description": f"Quality score {score} is below threshold. Address issues before training for reliable results.",
        })
        for i, s in enumerate(steps):
            s["step_number"] = i + 1

    return steps
