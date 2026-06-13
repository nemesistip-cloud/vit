import re

with open("frontend/src/pages/landing.tsx", "r") as f:
    content = f.read()

content = content.replace("{publicCfg?.platform.version ?? 'v5.5.0'}", "{publicCfg?.platform.version || 'v5.5.0'}")
content = content.replace("<span>{publicCfg?.platform.version ?? 'v5.5.0'}</span>", "<span>{publicCfg?.platform.version || 'v5.5.0'}</span>")

with open("frontend/src/pages/landing.tsx", "w") as f:
    f.write(content)
