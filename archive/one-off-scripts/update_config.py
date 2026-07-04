import os

filepath = 'app/config.py'
with open(filepath, 'r') as f:
    content = f.read()

new_config = """
# ── Semantic Search / Embedding Config ───────────────────────────────────────
EMBEDDING_MODEL: str = get_env("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM: int = get_int_env("EMBEDDING_DIM", "384")
EMBEDDING_CACHE_TTL: int = get_int_env("EMBEDDING_CACHE_TTL", "3600")
"""

insertion_point = '# ── Memory budget (controls lazy model loading in ModelRegistry) ──────────────'
if insertion_point in content:
    content = content.replace(insertion_point, new_config + "\n" + insertion_point)
else:
    content += "\n" + new_config

with open(filepath, 'w') as f:
    f.write(content)
