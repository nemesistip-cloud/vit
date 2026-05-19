"""
ModelLoader — loads trained .pkl files from /models/ directory.

Looks in (in order of priority):
  1. MODELS_DIR env var (if set)
  2. <workspace_root>/models/  (default — where pkl files are committed)
  3. <workspace_root>/models/trained/  (legacy location)
  4. services/ml_service/models/  (old layout)

Caches models in memory so they are only read from disk once.
Returns None if the file is missing or fails to load, allowing
the orchestrator to fall back to its algorithmic models.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MODEL_CACHE: Dict[str, Any] = {}

# Root of the workspace (two levels up from this file: services/ml_service/ -> services/ -> workspace/)
_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

def _candidate_dirs() -> List[Path]:
    """Return ordered list of directories to search for pkl files."""
    env_dir = os.environ.get("MODELS_DIR", "")
    candidates = []
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.extend([
        _WORKSPACE_ROOT / "models",
        _WORKSPACE_ROOT / "models" / "trained",
        _WORKSPACE_ROOT / "backend" / "models" / "trained",
        Path(__file__).parent / "models",
    ])
    return candidates


def _find_pkl(model_key: str) -> Optional[Path]:
    """Search all candidate directories for <model_key>.pkl."""
    for d in _candidate_dirs():
        p = d / f"{model_key}.pkl"
        if p.exists():
            return p
    return None


def load_model(model_key: str, cache_enabled: bool = True) -> Optional[Dict[str, Any]]:
    """
    Load a trained model payload from the models directory.

    Payload must be a dict with at least a 'model' key.
    Raw sklearn estimators are wrapped automatically so the rest of the
    codebase can always call payload['model'].predict_proba(X).
    """
    if cache_enabled and model_key in _MODEL_CACHE:
        return _MODEL_CACHE[model_key]

    pkl_path = _find_pkl(model_key)
    if pkl_path is None:
        logger.debug(f"No trained pkl found for '{model_key}' in {[str(d) for d in _candidate_dirs()]}")
        return None

    try:
        import joblib
        raw = joblib.load(pkl_path)

        if isinstance(raw, dict) and "model" in raw:
            payload = raw
        else:
            payload = {
                "model": raw,
                "scaler": None,
                "metrics": {},
                "training_samples": None,
                "version": 1,
                "loaded_from": str(pkl_path),
            }
            logger.info(f"ModelLoader: wrapped raw estimator from {pkl_path.name}")

        if cache_enabled:
            _MODEL_CACHE[model_key] = payload

        acc = payload.get("metrics", {}).get("accuracy", "?")
        samples = payload.get("training_samples", "?")
        logger.info(f"✅ ModelLoader: loaded '{model_key}' from {pkl_path} (acc={acc}, samples={samples})")
        return payload

    except Exception as exc:
        logger.warning(f"ModelLoader: failed to load '{model_key}.pkl' from {pkl_path}: {exc}")
        return None


def clear_cache() -> None:
    """Clear the in-memory model cache (e.g. after uploading new weights)."""
    _MODEL_CACHE.clear()
    logger.info("ModelLoader cache cleared")


def list_available_models() -> List[str]:
    """Return all model keys that have a trained pkl file available."""
    seen: set = set()
    found: List[str] = []
    for d in _candidate_dirs():
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.suffix == ".pkl" and f.stem not in seen:
                seen.add(f.stem)
                found.append(f.stem)
    return sorted(found)
