import re

path = 'app/services/ai_client.py'
with open(path, 'r') as f:
    content = f.read()

# Fix the broken "async def await _mark..." syntax
content = content.replace('async def await _mark_provider_failed', 'async def _mark_provider_failed')
content = content.replace('def await _mark_rate_limited', 'async def _mark_rate_limited')

# Correct the mark_rate_limited body to use cache
new_mark_limited = """async def _mark_rate_limited(name: str, retry_after: Optional[str] = None) -> None:
    wait = 8.0
    if retry_after:
        try:
            wait = max(float(retry_after), 4.0)
        except ValueError:
            pass
    await cache.set(f"ai_backoff:{name}", time.monotonic() + wait, ttl=int(wait) + 1)
    logger.warning("[ai-client] %s rate-limited — cooling for %.0fs", name, wait)"""

content = re.sub(r'async def _mark_rate_limited.*?wait, wait\)', new_mark_limited, content, flags=re.DOTALL)

# Fix get_provider_failures
content = content.replace('return dict(_provider_failures)', 'return {}  # Managed via cache')

with open(path, 'w') as f:
    f.write(content)
