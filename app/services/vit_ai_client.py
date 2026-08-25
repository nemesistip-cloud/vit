"""Centralized, resilient Vit AI Client with Retries, Circuit Breaker, and Caching.
VIT Platform v6.0.0
"""
from __future__ import annotations
import logging
import asyncio
import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_env
from app.core.redis import redis_client

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    """Raised when the circuit breaker is open."""
    pass

class VitAIClient:
    _instance: Optional[VitAIClient] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # Fetch base url from config
        self.base_url = get_env("VIT_AI_URL", "https://vit-ai.onrender.com").rstrip("/")
        # Outgoing API key for vit-ai inter-service auth (X-API-KEY header)
        self._api_key = get_env("VIT_AI_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_keepalive_connections=50, max_connections=100))

        # Circuit Breaker state
        self.failure_threshold = 5
        self.recovery_timeout = 30.0 # seconds
        self.failure_count = 0
        self.state = "CLOSED" # "CLOSED", "OPEN", "HALF-OPEN"
        self.last_state_change = time.time()

        # Cache TTL
        self.cache_ttl = 300 # 5 minutes default

        self._initialized = True
        logger.info(f"[VitAIClient] Initialized on {self.base_url} with limits (100 max, 50 keepalive)")

    def _record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.critical(f"[VitAIClient] Circuit opened! Failure threshold {self.failure_threshold} reached.")
        else:
            logger.warning(f"[VitAIClient] Recorded failure ({self.failure_count}/{self.failure_threshold}).")

    def _record_success(self):
        self.failure_count = 0
        if self.state != "CLOSED":
            self.state = "CLOSED"
            self.last_state_change = time.time()
            logger.info("[VitAIClient] Circuit closed. Restored normal operations.")

    def _check_circuit(self):
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.recovery_timeout:
                self.state = "HALF-OPEN"
                self.last_state_change = time.time()
                logger.info("[VitAIClient] Circuit enters HALF-OPEN. Attempting trial request.")
            else:
                raise CircuitBreakerOpenException("Circuit Breaker is OPEN. Target is temporarily isolated.")

    def _get_cache_key(self, prompt: str, kwargs: dict) -> str:
        serialized = json.dumps({"prompt": prompt, "kwargs": kwargs}, sort_keys=True, default=str)
        h = hashlib.md5(serialized.encode()).hexdigest()
        return f"vit:ai:cache:{h}"

    async def get_cached_response(self, cache_key: str) -> Optional[str]:
        if redis_client is None:
            return None
        try:
            val = await redis_client.get(cache_key)
            if val:
                logger.debug(f"[VitAIClient] Cache hit for key {cache_key[:15]}...")
                return val
        except Exception as e:
            logger.warning(f"[VitAIClient] Redis cache read error: {e}")
        return None

    async def set_cached_response(self, cache_key: str, response: str) -> None:
        if redis_client is None:
            return
        try:
            await redis_client.setex(cache_key, self.cache_ttl, response)
        except Exception as e:
            logger.warning(f"[VitAIClient] Redis cache write error: {e}")

    def _auth_headers(self) -> dict:
        """
        Return auth headers for outgoing vit-ai requests.
        Includes HMAC service token and optional static API key.
        """
        from app.core.service_auth import make_service_headers
        headers = make_service_headers("vitnetwork")
        if self._api_key:
            headers["X-API-KEY"] = self._api_key
        return headers

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError))
    )
    async def _execute_with_retry(self, method: str, path: str, payload: Optional[dict] = None) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug(f"[VitAIClient] Executing {method} request to {url}")
        headers = self._auth_headers()

        if method.upper() == "POST":
            return await self.client.post(url, json=payload, headers=headers)
        return await self.client.get(url, headers=headers)

    async def call_ai(self, prompt: str, **kwargs) -> str:
        """Centralized call endpoint for the external AI microservice with full circuit breaker and retry logic."""
        self._check_circuit()
        cache_key = self._get_cache_key(prompt, kwargs)

        # 1. Attempt Cache Retrieval
        cached = await self.get_cached_response(cache_key)
        if cached:
            return cached

        # Dynamic model selection based on routing/intent
        intent = kwargs.pop("intent", None)
        if "model" in kwargs:
            target_model = kwargs.pop("model")
        elif intent == "prediction" or any(k in kwargs for k in ["market_odds", "features", "feature_vector"]):
            target_model = "ensemble_v1"
        else:
            target_model = "llm_consensus_v1"

        # 2. Execute Request with Retries
        try:
            body = {
                "model_id": target_model,
                "payload": {"prompt": prompt, **kwargs},
            }
            response = await self._execute_with_retry("POST", "/api/v1/chat", body)
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(f"HTTP Error {response.status_code}", request=response.request, response=response)

            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
            else:
                data = {"result": response.text}

            if isinstance(data, dict):
                completion = data.get("result")
                if completion is None:
                    completion = data.get("completion") or data.get("reply") or data.get("prediction_details")
                if completion is None:
                    completion = json.dumps(data)
                elif isinstance(completion, (dict, list)):
                    completion = json.dumps(completion)
                else:
                    completion = str(completion)
            else:
                completion = str(data)

            # Record success and cache response
            self._record_success()
            await self.set_cached_response(cache_key, completion)
            return completion

        except Exception as e:
            self._record_failure()
            logger.error(f"[VitAIClient] AI call failed: {e}")
            raise

    async def get_models(self) -> list:
        """Fetch live model definitions from the microservice."""
        self._check_circuit()
        try:
            response = await self._execute_with_retry("GET", "/api/v1/models")
            if response.status_code == 200:
                self._record_success()
                return response.json()
            raise httpx.HTTPStatusError("HTTP Error", request=response.request, response=response)
        except Exception as e:
            self._record_failure()
            logger.error(f"[VitAIClient] Fetching models failed: {e}")
            raise

    async def check_health(self) -> bool:
        """Audit real-time availability of the external microservice."""
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False

vit_ai_client = VitAIClient()
