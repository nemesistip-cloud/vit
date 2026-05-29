import re

path = 'app/services/ai_client.py'
with open(path, 'r') as f:
    content = f.read()

# Add import
content = content.replace('import time', 'import time\nfrom app.services.cache import cache')

# Update backoff state to be helper functions instead of dicts
content = content.replace('_backoff_until: dict[str, float] = {}', '')
content = content.replace('_provider_failures: dict[str, dict] = {}', '')

# Update reset_provider_backoff
new_reset = """async def reset_provider_backoff(name: str | None = None) -> dict:
    if name:
        await cache.delete(f"ai_backoff:{name}")
        await cache.delete(f"ai_failures:{name}")
        logger.info("[ai-client] backoff+failures reset for: %s", name)
        return {name: 0.0}
    else:
        await cache.delete_pattern("ai_backoff:*")
        await cache.delete_pattern("ai_failures:*")
        logger.info("[ai-client] backoff+failures reset for all")
        return {}"""
content = re.sub(r'def reset_provider_backoff\(name: str \| None = None\).*?return cleared', new_reset, content, flags=re.DOTALL)

# Update _provider_available
new_available = """async def _provider_available(name: str) -> bool:
    until = await cache.get(f"ai_backoff:{name}")
    if until is None:
        return True
    return time.monotonic() >= float(until)"""
content = re.sub(r'def _provider_available\(name: str\).*?return time\.monotonic\(\) >= _backoff_until\.get\(name, 0\.0\)', new_available, content, flags=re.DOTALL)

# Update _mark_provider_failed
new_mark_failed = """async def _mark_provider_failed(name: str, status_code: int) -> None:
    fail_data = {
        "status_code": status_code,
        "failed_at": time.time(),
    }
    await cache.set(f"ai_failures:{name}", fail_data, ttl=3600)
    await cache.set(f"ai_backoff:{name}", time.monotonic() + _FATAL_BACKOFF_SECONDS, ttl=_FATAL_BACKOFF_SECONDS)
    logger.warning(
        "[ai-client] %s returned HTTP %d — marked as failing, backing off for %d min",
        name, status_code, _FATAL_BACKOFF_SECONDS // 60,
    )"""
content = re.sub(r'def _mark_provider_failed\(name: str, status_code: int\).*?_FATAL_BACKOFF_SECONDS // 60,.*?\)', new_mark_failed, content, flags=re.DOTALL)

# Update _mark_rate_limited
new_mark_limited = """async def _mark_rate_limited(name: str, retry_after: Optional[str] = None) -> None:
    wait = 8.0
    if retry_after:
        try:
            wait = max(float(retry_after), 4.0)
        except ValueError:
            pass
    await cache.set(f"ai_backoff:{name}", time.monotonic() + wait, ttl=int(wait) + 1)
    logger.warning("[ai-client] %s rate-limited — cooling for %.0fs", name, wait)"""
content = re.sub(r'def _mark_rate_limited\(name: str, retry_after: Optional\[str\] = None\).*?wait, wait\)', new_mark_limited, content, flags=re.DOTALL)

# Now we need to update all calls to these functions to be awaited.
content = content.replace('if not _provider_available(name):', 'if not await _provider_available(name):')
content = content.replace('if not _provider_available("gemini"):', 'if not await _provider_available("gemini"):')
content = content.replace('if not _provider_available("claude"):', 'if not await _provider_available("claude"):')
content = content.replace('if not _provider_available("openai"):', 'if not await _provider_available("openai"):')
content = content.replace('if not _provider_available("deepseek"):', 'if not await _provider_available("deepseek"):')
content = content.replace('if not _provider_available("grok"):', 'if not await _provider_available("grok"):')
content = content.replace('if not _provider_available("puter"):', 'if not await _provider_available("puter"):')

content = content.replace('_mark_rate_limited(', 'await _mark_rate_limited(')
content = content.replace('_mark_provider_failed(', 'await _mark_provider_failed(')

# And provider_status needs to be async
content = content.replace('def provider_status() -> dict[str, dict]:', 'async def provider_status() -> dict[str, dict]:')

# Inside provider_status, we need to fetch all backoffs and failures
new_status_loop = """
    result = {}
    for name, has_key in keys.items():
        cooling_until = await cache.get(f"ai_backoff:{name}") or 0.0
        cooling = cooling_until > now
        failure = await cache.get(f"ai_failures:{name}")
"""
content = re.sub(r'result = \{\}.*?failure = _provider_failures\.get\(name\)', new_status_loop, content, flags=re.DOTALL)

with open(path, 'w') as f:
    f.write(content)
