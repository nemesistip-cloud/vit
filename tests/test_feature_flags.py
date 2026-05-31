"""
Tests for the FeatureFlags system (app/core/feature_flags.py).
"""
import os
import pytest

from app.core.feature_flags import FeatureFlags


def setup_function():
    FeatureFlags.reset()


def teardown_function():
    FeatureFlags.reset()


def test_flag_defaults_to_false_when_env_not_set():
    os.environ.pop("MY_TEST_FLAG_XYZ", None)
    assert FeatureFlags.is_enabled("MY_TEST_FLAG_XYZ") is False


def test_flag_true_when_env_is_true():
    os.environ["MY_FLAG_TRUE"] = "true"
    FeatureFlags.reset()
    assert FeatureFlags.is_enabled("MY_FLAG_TRUE") is True
    del os.environ["MY_FLAG_TRUE"]


def test_flag_false_when_env_is_false():
    os.environ["MY_FLAG_FALSE"] = "false"
    FeatureFlags.reset()
    assert FeatureFlags.is_enabled("MY_FLAG_FALSE") is False
    del os.environ["MY_FLAG_FALSE"]


def test_flag_case_insensitive_true():
    os.environ["MY_FLAG_UPPER"] = "TRUE"
    FeatureFlags.reset()
    assert FeatureFlags.is_enabled("MY_FLAG_UPPER") is True
    del os.environ["MY_FLAG_UPPER"]


def test_flag_cached_after_first_read():
    os.environ["MY_CACHED_FLAG"] = "true"
    FeatureFlags.reset()
    FeatureFlags.is_enabled("MY_CACHED_FLAG")
    os.environ["MY_CACHED_FLAG"] = "false"
    assert FeatureFlags.is_enabled("MY_CACHED_FLAG") is True
    del os.environ["MY_CACHED_FLAG"]


def test_reset_clears_cache():
    os.environ["MY_RESET_FLAG"] = "true"
    FeatureFlags.reset()
    FeatureFlags.is_enabled("MY_RESET_FLAG")
    FeatureFlags.reset()
    os.environ["MY_RESET_FLAG"] = "false"
    assert FeatureFlags.is_enabled("MY_RESET_FLAG") is False
    del os.environ["MY_RESET_FLAG"]


def test_use_real_ml_models_defaults_false():
    os.environ.pop("USE_REAL_ML_MODELS", None)
    FeatureFlags.reset()
    assert FeatureFlags.is_enabled("USE_REAL_ML_MODELS") is False


def test_blockchain_enabled_defaults_false():
    os.environ.pop("BLOCKCHAIN_ENABLED", None)
    FeatureFlags.reset()
    assert FeatureFlags.is_enabled("BLOCKCHAIN_ENABLED") is False


def test_ml_cache_flag_can_be_read():
    os.environ["ML_MODEL_CACHE_ENABLED"] = "true"
    FeatureFlags.reset()
    assert FeatureFlags.is_enabled("ML_MODEL_CACHE_ENABLED") is True
    del os.environ["ML_MODEL_CACHE_ENABLED"]
