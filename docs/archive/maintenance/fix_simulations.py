import re

# storage.tsx
with open("frontend/src/pages/storage.tsx", "r") as f:
    content = f.read()

# Remove simulateProgress function and calls
content = re.sub(r'const simulateProgress = .*?};', '', content, flags=re.DOTALL)
content = content.replace('simulateProgress(file.size);', '')

# Ensure progress is set to something sensible or just show a spinner
content = content.replace('setUploadProgress(0);', 'setUploadProgress(10);')

with open("frontend/src/pages/storage.tsx", "w") as f:
    f.write(content)

# reports.tsx
with open("frontend/src/pages/reports.tsx", "r") as f:
    content = f.read()

# Reduce 8s delay to 500ms for query invalidation
content = content.replace('}, 8000);', '}, 500);')

with open("frontend/src/pages/reports.tsx", "w") as f:
    f.write(content)
