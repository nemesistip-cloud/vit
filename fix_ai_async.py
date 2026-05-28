import os
import re

def fix_file(path):
    if not os.path.exists(path): return
    with open(path, 'r') as f:
        content = f.read()

    # 1. Update provider_status calls
    # provider_status() -> await provider_status()
    # But only if it's not already awaited.
    new_content = re.sub(r'(?<!await )provider_status\(', 'await provider_status(', content)
    # Also for aliases like _ps()
    new_content = re.sub(r'(?<!await )_ps\(', 'await _ps(', new_content)

    # 2. Update reset_provider_backoff calls
    new_content = re.sub(r'(?<!await )reset_provider_backoff\(', 'await reset_provider_backoff(', new_content)

    if new_content != content:
        with open(path, 'w') as f:
            f.write(new_content)
        print(f"Fixed async calls in {path}")

# List of files to check
files = [
    'main.py',
    'app/api/routes/ai_upload.py',
    'app/api/routes/ai_support.py',
    'app/api/routes/ai_intelligence.py',
    'app/api/routes/agents.py',
    'app/api/routes/ai_assistant.py'
]

for f in files:
    fix_file(f)
