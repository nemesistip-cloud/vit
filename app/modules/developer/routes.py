# app/modules/developer/routes.py
"""Developer Platform REST API — Module L."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.developer import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/developer", tags=["developer"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name:       str           = Field(..., min_length=1, max_length=128)
    plan:       str           = Field(default="free")
    expires_at: Optional[datetime] = None


def _fmt_key(k, show_plain: bool = False) -> dict:
    return {
        "id":                       k.id,
        "name":                     k.name,
        "key_prefix":               k.key_prefix,
        "key":                      k.key_plain if show_plain else None,
        "plan":                     k.plan,
        "rate_limit_rpm":           k.rate_limit_rpm,
        "rate_limit_rpd":           k.rate_limit_rpd,
        "is_active":                k.is_active,
        "total_requests":           k.total_requests,
        "total_vitcoin_billed":     str(k.total_vitcoin_billed),
        "last_used_at":             k.last_used_at.isoformat() if k.last_used_at else None,
        "created_at":               k.created_at.isoformat() if k.created_at else None,
        "expires_at":               k.expires_at.isoformat() if k.expires_at else None,
    }


def _fmt_log(log) -> dict:
    return {
        "id":             log.id,
        "endpoint":       log.endpoint,
        "method":         log.method,
        "status_code":    log.status_code,
        "latency_ms":     log.latency_ms,
        "vitcoin_billed": str(log.vitcoin_billed),
        "called_at":      log.called_at.isoformat() if log.called_at else None,
    }


def _fmt_plan(p) -> dict:
    return {
        "name":                    p.name,
        "display_name":            p.display_name,
        "rate_limit_rpm":          p.rate_limit_rpm,
        "rate_limit_rpd":          p.rate_limit_rpd,
        "price_vitcoin_per_1k":    f"{float(p.price_vitcoin_per_1k):.2f}",
        "description":             p.description,
    }


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.get("/plans", summary="List available API plans")
async def list_plans(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    await svc.seed_plans(db)
    plans = await svc.list_plans(db)
    return [_fmt_plan(p) for p in plans]


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.get("/keys", summary="List my API keys")
async def list_keys(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    keys = await svc.list_keys(db, current_user.id)
    return [_fmt_key(k) for k in keys]


@router.post("/keys", summary="Create a new API key", status_code=201)
async def create_key(
    body:         CreateKeyRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    try:
        key, raw = await svc.create_key(
            db,
            user_id=current_user.id,
            name=body.name,
            plan=body.plan,
            expires_at=body.expires_at,
        )
        result = _fmt_key(key, show_plain=True)
        result["key"] = raw   # shown only once
        # Clear stored plain key
        key.key_plain = None
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/keys/{key_id}", summary="Delete an API key")
async def delete_key(
    key_id:       int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    ok = await svc.delete_key(db, key_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"deleted": True, "key_id": key_id}


@router.patch("/keys/{key_id}/revoke", summary="Revoke (disable) an API key")
async def revoke_key(
    key_id:       int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    ok = await svc.revoke_key(db, key_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"revoked": True, "key_id": key_id}


# ── Usage ─────────────────────────────────────────────────────────────────────

@router.post("/keys/{key_id}/bill", summary="Bill one API call against a key (internal use)")
async def bill_key_call(
    key_id:       int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    G09: Deduct VITCoin for a single billable API call on the given key.
    Returns {allowed, reason}. Returns 402 if insufficient balance.
    """
    key = await svc.get_key(db, key_id, current_user.id)
    if not key or not key.is_active:
        raise HTTPException(status_code=404, detail="API key not found or inactive")

    allowed, reason = await svc.bill_api_call(db, key.id, current_user.id, key.plan)
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient VITCoin balance to make API calls on the '{key.plan}' plan.",
        )
    return {"allowed": True, "reason": reason, "key_id": key_id, "plan": key.plan}


@router.get("/usage", summary="My recent API call history")
async def my_usage(
    limit:        int = Query(default=100, ge=1, le=500),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    logs = await svc.my_usage(db, current_user.id, limit=limit)
    return [_fmt_log(log) for log in logs]


@router.get("/usage/summary", summary="My API usage summary")
async def usage_summary(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await svc.usage_summary(db, current_user.id)


# ── Docs (stub endpoint returning SDK links) ──────────────────────────────────

@router.get("/docs", summary="Developer documentation links")
async def developer_docs(
    request: Request,
    _: User = Depends(get_current_user),
):
    """Return developer reference docs.

    Endpoints are introspected from the live FastAPI app so the list always
    reflects what the server actually exposes — no hand-maintained snippets.
    """
    app = request.app
    seen: set[tuple[str, str]] = set()
    endpoints: list[dict] = []

    EXCLUDE_PREFIXES = (
        "/openapi", "/docs", "/redoc", "/static", "/assets", "/favicon",
        "/__", "/api/dev/admin",  # admin/dev internals
    )

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if not path or not methods:
            continue
        if any(path.startswith(p) for p in EXCLUDE_PREFIXES):
            continue
        # Skip websocket / mount routes
        if any(m in {"HEAD", "OPTIONS"} for m in methods):
            methods = {m for m in methods if m not in {"HEAD", "OPTIONS"}}
        if not methods:
            continue

        summary = getattr(route, "summary", None) or ""
        tags = getattr(route, "tags", None) or []
        for method in sorted(methods):
            key = (method, path)
            if key in seen:
                continue
            seen.add(key)
            endpoints.append({
                "method":      method,
                "path":        path,
                "description": summary,
                "tags":        list(tags),
            })

    endpoints.sort(key=lambda e: (e["path"], e["method"]))

    return {
        "openapi_url":         "/openapi.json",
        "redoc_url":           "/redoc",
        "swagger_url":         "/docs",
        "sdk_typescript_url":  "https://github.com/Value-intelligence-trust/vit-sdk",
        "sdk_python_url":      "https://github.com/Value-intelligence-trust/vit-sdk",
        "base_api_url":        "https://vit-897838355273.europe-west1.run.app/api",
        "cloud_run_url":       "https://vit-897838355273.europe-west1.run.app",
        "authentication":      "Include your API key in the `X-API-Key` header.",
        "rate_limiting":       "Rate limits are enforced per minute and per day per key.",
        "endpoint_count":      len(endpoints),
        "endpoints":           endpoints,
    }


# ── Platform stats (admin) ────────────────────────────────────────────────────

@router.get("/admin/stats", summary="Admin: developer platform statistics")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_admin),
):
    return await svc.platform_stats(db)


# ── Git Sync endpoints ────────────────────────────────────────────────────────
import subprocess as _subprocess
import os as _os

def _run_git(*args: str, timeout: int = 30) -> dict:
    """Run a git command and return stdout/stderr + exit code."""
    gh_token = _os.getenv("GH_TOKEN", "")
    env = {**_os.environ}
    if gh_token:
        env["GH_TOKEN"] = gh_token
    try:
        result = _subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=timeout, env=env
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode,
        }
    except _subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Command timed out", "exit_code": -1}
    except Exception as exc:
        return {"success": False, "stdout": "", "stderr": str(exc), "exit_code": -1}


@router.get("/git/status", summary="Git: current repo status and branch info")
async def git_status(_: User = Depends(get_current_admin)):
    branch_r   = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    status_r   = _run_git("status", "--short")
    remote_r   = _run_git("remote", "get-url", "origin")
    ahead_r    = _run_git("rev-list", "HEAD..@{u}", "--count")
    behind_r   = _run_git("rev-list", "@{u}..HEAD", "--count")
    log_r      = _run_git("log", "--oneline", "-5")
    return {
        "branch":        branch_r.get("stdout", "unknown"),
        "dirty_files":   status_r.get("stdout", ""),
        "remote_url":    remote_r.get("stdout", ""),
        "commits_ahead": int(ahead_r.get("stdout", "0") or 0),
        "commits_behind": int(behind_r.get("stdout", "0") or 0),
        "recent_log":    log_r.get("stdout", ""),
        "is_clean":      status_r.get("stdout", "") == "",
    }


@router.post("/git/pull", summary="Git: pull latest changes from remote")
async def git_pull(_: User = Depends(get_current_admin)):
    fetch_r  = _run_git("fetch", "origin")
    pull_r   = _run_git("pull", "--rebase", "origin",
                        _run_git("rev-parse", "--abbrev-ref", "HEAD").get("stdout", "main"))
    return {
        "success": pull_r["success"],
        "output": (fetch_r.get("stdout", "") + "\n" + pull_r.get("stdout", "")).strip(),
        "errors": (fetch_r.get("stderr", "") + "\n" + pull_r.get("stderr", "")).strip(),
    }


@router.post("/git/push", summary="Git: stage all changes and push to remote")
async def git_push(
    payload: dict = None,
    _: User = Depends(get_current_admin),
):
    msg = (payload or {}).get("message", "chore: platform update via VIT dashboard")
    add_r    = _run_git("add", "-A")
    commit_r = _run_git("commit", "-m", msg)
    push_r   = _run_git("push", "origin", "HEAD")
    output_parts = [
        add_r.get("stdout", ""),
        commit_r.get("stdout", commit_r.get("stderr", "")),
        push_r.get("stdout", ""),
    ]
    errors_parts = [push_r.get("stderr", "")]
    return {
        "success": push_r["success"] or "nothing to commit" in commit_r.get("stdout", ""),
        "output": "\n".join(p for p in output_parts if p).strip(),
        "errors": "\n".join(p for p in errors_parts if p).strip(),
        "committed": commit_r["success"],
    }


@router.get("/git/log", summary="Git: recent commit log")
async def git_log(
    n: int = 20,
    _: User = Depends(get_current_admin),
):
    log_r = _run_git("log", "--oneline", "--decorate", f"-{n}")
    diff_r = _run_git("diff", "--stat", "HEAD~1", "HEAD")
    return {
        "log":       log_r.get("stdout", ""),
        "last_diff": diff_r.get("stdout", ""),
        "success":   log_r["success"],
    }
