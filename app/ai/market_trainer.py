"""
app/ai/market_trainer.py — Phase 2: Specialized Market Model Training Pipeline

Trains BTTSModel, OverUnderModel, and CorrectScoreModel on settled match
prediction history pulled from the database.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from app.ai.market_models import (
    BTTSModel,
    OverUnderModel,
    CorrectScoreModel,
    _BTTS_FEATURE_KEYS,
    _OU_FEATURE_KEYS,
    _CS_FEATURE_KEYS,
    build_feature_vector,
)

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "models")
)


# ---------------------------------------------------------------------------
# Label builders
# ---------------------------------------------------------------------------

def _btts_label(home_goals: int, away_goals: int) -> int:
    return 1 if (home_goals > 0 and away_goals > 0) else 0


def _ou_label(home_goals: int, away_goals: int) -> int:
    total = home_goals + away_goals
    if total <= 1:   return 0
    elif total == 2: return 1
    elif total == 3: return 2
    elif total <= 5: return 3
    else:            return 4


def _cs_label(home_goals: int, away_goals: int) -> int:
    if home_goals <= 4 and away_goals <= 4:
        return home_goals * 5 + away_goals
    return 25   # "other"


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------

async def _load_training_data(db) -> List[Dict]:
    """Pull settled matches with features from the DB."""
    from sqlalchemy import select, and_
    from app.db.models import Match, Prediction
    from app.data.feature_engineering import engineer_features

    rows = (await db.execute(
        select(
            Match.id,
            Match.home_goals,
            Match.away_goals,
            Match.opening_odds_home, Match.opening_odds_draw, Match.opening_odds_away,
            Match.closing_odds_home, Match.closing_odds_draw, Match.closing_odds_away,
            Prediction.home_prob, Prediction.draw_prob, Prediction.away_prob,
            Prediction.over_25_prob, Prediction.btts_prob,
            Prediction.model_insights,
        ).join(Prediction, Prediction.match_id == Match.id).where(
            and_(
                Match.home_goals.isnot(None),
                Match.away_goals.isnot(None),
                Match.closing_odds_home.isnot(None),
            )
        ).limit(5000)
    )).fetchall()

    cols = [
        "match_id", "home_goals", "away_goals",
        "open_home", "open_draw", "open_away",
        "close_home", "close_draw", "close_away",
        "home_prob", "draw_prob", "away_prob",
        "over_25_prob", "btts_prob",
        "model_insights",
    ]

    records = []
    for r in rows:
        d = dict(zip(cols, r))
        # Build a minimal feature dict from available columns
        insights = d.get("model_insights") or {}
        feat = {
            "market_home_prob_vf":   d.get("home_prob"),
            "market_draw_prob_vf":   d.get("draw_prob"),
            "market_away_prob_vf":   d.get("away_prob"),
            "market_over25_prob_vf": d.get("over_25_prob"),
            "market_btts_prob_vf":   d.get("btts_prob"),
            "lambda_home":           d.get("home_prob", 0.33) * 2.5,
            "lambda_away":           d.get("away_prob", 0.33) * 2.0,
        }
        # Merge any cached feature insights
        if isinstance(insights, dict):
            feat.update(insights.get("features", {}))
        d["features"] = feat
        records.append(d)

    return records


def _build_tensors(
    records: List[Dict],
    feature_keys: List[str],
    label_fn,
) -> Optional[TensorDataset]:
    if not records:
        return None
    X, y = [], []
    for r in records:
        hg = int(r.get("home_goals") or 0)
        ag = int(r.get("away_goals") or 0)
        vec = build_feature_vector(r["features"], feature_keys).squeeze(0)
        lbl = label_fn(hg, ag)
        X.append(vec)
        y.append(lbl)
    return TensorDataset(
        torch.stack(X),
        torch.tensor(y, dtype=torch.long),
    )


# ---------------------------------------------------------------------------
# Generic training loop
# ---------------------------------------------------------------------------

def _train_model(
    model: nn.Module,
    dataset: TensorDataset,
    epochs: int = 60,
    batch_size: int = 64,
    lr: float = 3e-4,
    weight_decay: float = 1e-4,
) -> Dict[str, Any]:
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss()

    model.train()
    history = []
    for epoch in range(epochs):
        total_loss = 0.0
        correct = 0
        total = 0
        for X_batch, y_batch in loader:
            optimizer.zero_grad()
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item() * len(y_batch)
            correct += (logits.argmax(dim=1) == y_batch).sum().item()
            total += len(y_batch)
        scheduler.step()
        if (epoch + 1) % 10 == 0:
            acc = correct / total if total else 0.0
            history.append({"epoch": epoch + 1, "loss": round(total_loss / total, 5), "acc": round(acc, 4)})
            logger.info(
                "[market-trainer] epoch %d/%d  loss=%.5f  acc=%.3f",
                epoch + 1, epochs, total_loss / total, acc,
            )

    model.eval()
    return {"epochs": epochs, "history": history, "samples": len(dataset)}


# ---------------------------------------------------------------------------
# Save / load helpers
# ---------------------------------------------------------------------------

def _save(model: nn.Module, model_key: str) -> str:
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, f"{model_key}.pth")
    torch.save({"state_dict": model.state_dict(), "model_key": model_key}, path)
    logger.info("[market-trainer] saved %s → %s", model_key, path)
    return path


def load_market_model(model_cls, model_key: str, **kwargs):
    """Load a saved market model, returning None if not found."""
    path = os.path.join(MODELS_DIR, f"{model_key}.pth")
    if not os.path.isfile(path):
        return None
    try:
        model = model_cls(**kwargs)
        ckpt = torch.load(path, map_location="cpu")
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        logger.info("[market-trainer] loaded %s from %s", model_key, path)
        return model
    except Exception as exc:
        logger.warning("[market-trainer] failed to load %s: %s", model_key, exc)
        return None


# ---------------------------------------------------------------------------
# Public training entry points
# ---------------------------------------------------------------------------

async def train_btts_model(db, epochs: int = 60) -> Dict[str, Any]:
    records = await _load_training_data(db)
    dataset = _build_tensors(records, _BTTS_FEATURE_KEYS, _btts_label)
    if dataset is None or len(dataset) < 20:
        return {"error": "Insufficient data", "samples": len(records)}

    model = BTTSModel(input_size=len(_BTTS_FEATURE_KEYS))
    stats = _train_model(model, dataset, epochs=epochs)
    path  = _save(model, BTTSModel.MODEL_KEY)
    return {**stats, "model_key": BTTSModel.MODEL_KEY, "saved_to": path}


async def train_over_under_model(db, epochs: int = 60) -> Dict[str, Any]:
    records = await _load_training_data(db)
    dataset = _build_tensors(records, _OU_FEATURE_KEYS, _ou_label)
    if dataset is None or len(dataset) < 20:
        return {"error": "Insufficient data", "samples": len(records)}

    model = OverUnderModel(input_size=len(_OU_FEATURE_KEYS))
    stats = _train_model(model, dataset, epochs=epochs)
    path  = _save(model, OverUnderModel.MODEL_KEY)
    return {**stats, "model_key": OverUnderModel.MODEL_KEY, "saved_to": path}


async def train_correct_score_model(db, epochs: int = 80) -> Dict[str, Any]:
    records = await _load_training_data(db)
    dataset = _build_tensors(records, _CS_FEATURE_KEYS, _cs_label)
    if dataset is None or len(dataset) < 30:
        return {"error": "Insufficient data", "samples": len(records)}

    model = CorrectScoreModel(input_size=len(_CS_FEATURE_KEYS))
    stats = _train_model(model, dataset, epochs=epochs)
    path  = _save(model, CorrectScoreModel.MODEL_KEY)
    return {**stats, "model_key": CorrectScoreModel.MODEL_KEY, "saved_to": path}


async def train_all_market_models(db, epochs: int = 60) -> Dict[str, Any]:
    """Train all three specialized market models and return a combined report."""
    results: Dict[str, Any] = {}
    for key, fn in [
        ("btts",          lambda: train_btts_model(db, epochs)),
        ("over_under",    lambda: train_over_under_model(db, epochs)),
        ("correct_score", lambda: train_correct_score_model(db, max(epochs, 80))),
    ]:
        try:
            results[key] = await fn()
        except Exception as exc:
            logger.error("[market-trainer] %s training failed: %s", key, exc)
            results[key] = {"error": str(exc)}
    return results
