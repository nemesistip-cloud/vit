#!/usr/bin/env python3
"""Run the allowlisted, read-only weekly service audit against staging only."""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from typing import Any

API_PREFIX = "/api/v1/scheduled-jobs"
MAX_HTTP_ATTEMPTS = 3
MAX_HEALTH_ATTEMPTS = 2


class ApiError(Exception):
    def __init__(self, status: str, operation: str):
        super().__init__(f"{operation} failed ({status})")
        self.status = status
        self.operation = operation


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required configuration is missing: {name}")
    return value


def _staging_base_url(name: str) -> str:
    value = _required_env(name).rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError(f"{name} must be an HTTPS URL without embedded credentials")
    if "staging" not in parsed.hostname.lower():
        raise RuntimeError(f"{name} must point to a staging hostname")
    return value


def _api_request(
    base_url: str,
    token: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    retry_safe: bool = False,
) -> dict[str, Any]:
    encoded = json.dumps(payload).encode("utf-8") if payload is not None else None
    attempts = MAX_HTTP_ATTEMPTS if retry_safe else 1
    last_status = "transport"
    for attempt in range(attempts):
        headers = {
            "Accept": "application/json",
            "X-GitHub-Scheduler-Token": token,
            "User-Agent": "VIT-staging-scheduler",
        }
        if encoded is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(base_url + API_PREFIX + path, data=encoded, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read(12_000)
                if len(body) >= 12_000:
                    raise ApiError("response_too_large", path)
                result = json.loads(body or b"{}")
                if not isinstance(result, dict):
                    raise ApiError("invalid_response", path)
                return result
        except urllib.error.HTTPError as error:
            last_status = f"http_{error.code}"
            if error.code < 500 or attempt + 1 == attempts:
                raise ApiError(last_status, path) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            last_status = "transport_or_timeout"
            if attempt + 1 == attempts:
                raise ApiError(last_status, path) from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ApiError("invalid_response", path) from None
        time.sleep(2 ** attempt)
    raise ApiError(last_status, path)


def _probe(name: str, base_url: str, path: str) -> dict[str, Any]:
    started = time.monotonic()
    status = "timeout"
    for attempt in range(MAX_HEALTH_ATTEMPTS):
        request = urllib.request.Request(
            base_url.rstrip("/") + path,
            headers={"Accept": "application/json", "User-Agent": "VIT-staging-health-audit"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                status = f"http_{response.status}"
                if response.status == 200:
                    body = response.read(4096)
                    try:
                        payload = json.loads(body) if body else {}
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        status = "invalid_health_payload"
                    else:
                        app_status = payload.get("status") if isinstance(payload, dict) else None
                        if app_status is not None and app_status not in {
                            "ok", "healthy", "operational", "quantum_stable",
                        }:
                            status = "degraded"
                        elif isinstance(payload, dict) and payload.get("database") not in {
                            None, "connected", "ok",
                        }:
                            status = "database_degraded"
                        else:
                            break
        except urllib.error.HTTPError as error:
            status = f"http_{error.code}"
        except (urllib.error.URLError, TimeoutError, OSError):
            status = "timeout"
        if attempt + 1 < MAX_HEALTH_ATTEMPTS:
            time.sleep(2 ** attempt)
    return {
        "service": name,
        "status": status,
        "latency_ms": round((time.monotonic() - started) * 1000),
    }


def _schedule_key() -> str:
    supplied = os.environ.get("SCHEDULE_KEY", "").strip()
    if supplied:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", supplied):
            raise RuntimeError("SCHEDULE_KEY must use UTC date format YYYY-MM-DD")
        try:
            date.fromisoformat(supplied)
        except ValueError as exc:
            raise RuntimeError("SCHEDULE_KEY must be a valid UTC date") from exc
        return supplied
    return datetime.now(timezone.utc).date().isoformat()


def _claim_until_ready(base_url: str, token: str, runner_id: str) -> dict[str, Any] | None:
    claim_token = secrets.token_urlsafe(32)
    for _ in range(MAX_HTTP_ATTEMPTS):
        claim = _api_request(
            base_url,
            token,
            "/runs/claim-next",
            {"runner_id": runner_id, "claim_token": claim_token},
            retry_safe=True,
        )
        if claim.get("claimed"):
            return claim
        run = claim.get("run") or {}
        if not run:
            print("No due staging health run is available; another runner may hold the lease.")
            return None
        state = run.get("status")
        if state == "completed":
            print("Weekly staging health record is already complete; no probe repeated.")
            return None
        if state == "failed":
            raise RuntimeError("scheduled health audit has exhausted its bounded attempts")
        if state == "running":
            print("Another runner holds the active lease; this invocation exits without duplicate work.")
            return None
        next_at = run.get("next_attempt_at")
        if state == "retry_wait" and next_at:
            due = datetime.fromisoformat(next_at.replace("Z", "+00:00"))
            delay = max(0, min(300, (due - datetime.now(timezone.utc)).total_seconds()))
            if delay:
                time.sleep(delay)
                continue
        if state in {"queued", "retry_wait"}:
            time.sleep(2)
            continue
        raise RuntimeError(f"scheduled run cannot be claimed (state={state or 'unknown'})")
    raise RuntimeError("scheduled run did not become claimable within the bounded poll budget")


def main() -> int:
    if os.environ.get("DRY_RUN", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("only read-only dry-run execution is enabled")

    gateway = _staging_base_url("STAGING_GATEWAY_URL")
    service_urls = {
        "gateway": (gateway, "/ping"),
        "ai": (_staging_base_url("STAGING_VIT_AI_URL"), "/health"),
        "chain": (_staging_base_url("STAGING_VIT_CHAIN_URL"), "/ping"),
        "storage": (_staging_base_url("STAGING_VIT_STORAGE_URL"), "/health"),
    }
    token = _required_env("STAGING_GITHUB_SCHEDULER_TOKEN")
    key = _schedule_key()
    runner_id = ":".join(
        filter(None, (os.environ.get("GITHUB_RUN_ID"), os.environ.get("GITHUB_RUN_ATTEMPT"), "health-audit"))
    )[:100]

    created = _api_request(
        gateway,
        token,
        "/runs",
        {"schedule_key": key, "dry_run": True},
        retry_safe=True,
    )
    run_record = created.get("run", {})
    run_id = run_record.get("id")
    if not isinstance(run_id, int):
        raise RuntimeError("scheduler API returned no run id")

    print(f"Scheduled run {run_id} ({key}); created={created.get('created', False)}; dry_run=true")
    for attempt_number in range(MAX_HTTP_ATTEMPTS):
        claim = _claim_until_ready(gateway, token, runner_id)
        if claim is None:
            return 0
        claim_token = claim.get("claim_token")
        if not isinstance(claim_token, str) or len(claim_token) < 32:
            raise RuntimeError("scheduler API returned an invalid claim")
        claimed_run_id = (claim.get("run") or {}).get("id")
        if not isinstance(claimed_run_id, int):
            raise RuntimeError("scheduler API returned a claim without a run id")

        probes = [_probe(name, base, path) for name, (base, path) in service_urls.items()]
        failures = [item for item in probes if item["status"] != "http_200"]
        result = {
            "mode": "read_only_dry_run",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "services": probes,
        }
        finish_payload = {
            "claim_token": claim_token,
            "outcome": "failed" if failures else "succeeded",
            "result": result,
            "error_code": "health_check_failed" if failures else None,
        }
        finished = _api_request(
            gateway,
            token,
            f"/runs/{claimed_run_id}/finish",
            finish_payload,
            retry_safe=True,
        )
        for item in probes:
            print(f"{item['service']}: {item['status']} ({item['latency_ms']} ms)")

        run_status = (finished.get("run") or {}).get("status")
        if run_status == "completed":
            print("Staging health audit completed.")
            return 0
        if run_status == "retry_wait" and attempt_number + 1 < MAX_HTTP_ATTEMPTS:
            delay = min(300, int(finished.get("retry_after_seconds") or 60))
            print(f"Staging probes failed; retrying after bounded delay ({delay}s).")
            time.sleep(delay)
            continue
        print("::error::Staging health audit failed; inspect this run's status and attempt history.")
        return 1

    print("::error::Staging health audit did not complete within the retry budget.")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApiError as exc:
        print(f"::error::Scheduled health audit API operation failed: {exc.operation} ({exc.status}).")
        raise SystemExit(1)
    except RuntimeError as exc:
        print(f"::error::{exc}")
        raise SystemExit(1)
