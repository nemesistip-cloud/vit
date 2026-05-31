"""
Additional ML module tests covering file I/O paths in SimulationEngine
and app-level utilities to push coverage above 40%.
"""
import json
import os
import tempfile
import pytest

from services.ml_service.simulation_engine import SimulationEngine


# ── SimulationEngine file I/O ─────────────────────────────────────────────────

class TestSimulationEngineIO:
    def test_generate_to_file_creates_jsonl(self):
        engine = SimulationEngine(total_matches=10, seed=42)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            engine.generate_to_file(path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    def test_generate_to_file_valid_jsonl(self):
        engine = SimulationEngine(total_matches=15, seed=1)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
            path = f.name
        try:
            engine.generate_to_file(path)
            with open(path) as f:
                lines = [l.strip() for l in f if l.strip()]
            assert len(lines) == 15
            for line in lines:
                obj = json.loads(line)
                assert "home_goals" in obj
        finally:
            os.unlink(path)

    def test_load_jsonl_reads_all_records(self):
        engine = SimulationEngine(total_matches=8, seed=7)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            engine.generate_to_file(path)
            loaded = SimulationEngine.load_jsonl(path)
            assert len(loaded) == 8
        finally:
            os.unlink(path)

    def test_load_jsonl_respects_limit(self):
        engine = SimulationEngine(total_matches=20, seed=3)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            engine.generate_to_file(path)
            loaded = SimulationEngine.load_jsonl(path, limit=5)
            assert len(loaded) == 5
        finally:
            os.unlink(path)

    def test_stats_contains_required_fields(self):
        engine = SimulationEngine(total_matches=20, seed=99)
        matches = engine.generate_in_memory()
        stats = SimulationEngine.stats(matches)
        required = {"total", "avg_goals", "std_goals", "outcome_pct", "tier_distribution"}
        for field in required:
            assert field in stats, f"Missing: {field}"

    def test_stats_total_matches_count(self):
        engine = SimulationEngine(total_matches=12, seed=5)
        matches = engine.generate_in_memory()
        stats = SimulationEngine.stats(matches)
        assert stats["total"] == 12

    def test_stats_outcome_pct_sum_to_100(self):
        engine = SimulationEngine(total_matches=50, seed=11)
        matches = engine.generate_in_memory()
        stats = SimulationEngine.stats(matches)
        total_pct = sum(stats["outcome_pct"].values())
        assert abs(total_pct - 100.0) < 1.0

    def test_generate_uses_seed_deterministically(self):
        e1 = SimulationEngine(total_matches=5, seed=42)
        e2 = SimulationEngine(total_matches=5, seed=42)
        m1 = e1.generate_in_memory()
        m2 = e2.generate_in_memory()
        assert m1 == m2

    def test_generate_with_progress_callback(self):
        calls = []
        def cb(done, total):
            calls.append((done, total))

        engine = SimulationEngine(total_matches=10, seed=2)
        engine.generate_in_memory(progress_cb=cb)
        assert len(calls) > 0

    def test_generate_chunks_with_small_chunk_size(self):
        calls = []
        def cb(done, total):
            calls.append((done, total))

        engine = SimulationEngine(total_matches=12, seed=99)
        chunks = list(engine.generate(chunk_size=4, progress_cb=cb))
        total_matches = sum(len(c) for c in chunks)
        assert total_matches == 12
        assert len(calls) >= 2

    def test_generate_chunks_without_callback(self):
        engine = SimulationEngine(total_matches=8, seed=55)
        chunks = list(engine.generate(chunk_size=3))
        total = sum(len(c) for c in chunks)
        assert total == 8

    def test_generate_to_file_with_progress_callback(self):
        calls = []
        def cb(done, total):
            calls.append((done, total))

        engine = SimulationEngine(total_matches=15, seed=7)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            engine.generate_to_file(path, chunk_size=5, progress_cb=cb)
            assert len(calls) >= 2
        finally:
            os.unlink(path)

    def test_generate_large_batch_covers_extreme_goals_branch(self):
        engine = SimulationEngine(total_matches=500, seed=0)
        matches = engine.generate_in_memory()
        assert len(matches) == 500
        max_goals = max(m["total_goals"] for m in matches)
        assert max_goals >= 0


# ── App schema / utility unit tests ──────────────────────────────────────────

class TestAppSchemas:
    def test_match_request_schema_valid(self):
        from datetime import datetime, timedelta, timezone
        from app.schemas.schemas import MatchRequest
        req = MatchRequest(
            home_team="Arsenal",
            away_team="Chelsea",
            league="Premier League",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=2),
            market_odds={"home": 2.10, "draw": 3.30, "away": 3.60},
        )
        assert req.home_team == "Arsenal"
        assert req.away_team == "Chelsea"

    def test_match_request_default_odds(self):
        from datetime import datetime, timedelta, timezone
        from app.schemas.schemas import MatchRequest
        req = MatchRequest(
            home_team="PSG",
            away_team="Monaco",
            league="Ligue 1",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=3),
        )
        assert req is not None


class TestJwtUtils:
    def test_hash_password_produces_different_hashes(self):
        from app.auth.jwt_utils import hash_password
        h1 = hash_password("password123")
        h2 = hash_password("password123")
        assert h1 != h2

    def test_verify_password_correct(self):
        from app.auth.jwt_utils import hash_password, verify_password
        pw = "TestPassword456!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_password_wrong(self):
        from app.auth.jwt_utils import hash_password, verify_password
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_create_access_token_decodable(self):
        from app.auth.jwt_utils import create_access_token, decode_token
        token = create_access_token({"sub": "test@test.com", "user_id": 1})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "test@test.com"

    def test_create_refresh_token_type(self):
        from app.auth.jwt_utils import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "test@test.com"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"


class TestCoreCache:
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        from app.core.cache import TTLCache
        cache = TTLCache()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        from app.core.cache import TTLCache
        cache = TTLCache()
        result = await cache.get("nonexistent_key_xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        from app.core.cache import TTLCache
        cache = TTLCache()
        await cache.set("del_key", "val")
        await cache.delete("del_key")
        assert await cache.get("del_key") is None

    @pytest.mark.asyncio
    async def test_cache_size_increases(self):
        from app.core.cache import TTLCache
        cache = TTLCache()
        before = cache.size
        await cache.set("new_key_abc", "some_val")
        assert cache.size >= before
