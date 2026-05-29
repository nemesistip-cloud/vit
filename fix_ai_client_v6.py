import re

path = 'app/services/ai_client.py'
with open(path, 'r') as f:
    content = f.read()

# Fix the broken mark_rate_limited body AGAIN. _backoff_until[name] is wrong, should be cache.set
pattern = r'async def _mark_rate_limited\(name: str, retry_after: Optional\[str\] = None\) -> None:.*?wait, wait\)'
replacement = """async def _mark_rate_limited(name: str, retry_after: Optional[str] = None) -> None:
    wait = 8.0
    if retry_after:
        try:
            wait = max(float(retry_after), 4.0)
        except ValueError:
            pass
    await cache.set(f"ai_backoff:{name}", time.monotonic() + wait, ttl=int(wait) + 1)
    logger.warning("[ai-client] %s rate-limited — cooling for %.0fs", name, wait)"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(path, 'w') as f:
    f.write(content)
