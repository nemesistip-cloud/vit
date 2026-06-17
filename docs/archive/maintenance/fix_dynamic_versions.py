import re

def replace_version(content, pattern, replacement):
    return re.sub(pattern, replacement, content)

files_to_fix = [
    ("frontend/src/pages/dashboard.tsx", r'ENSEMBLE v5\.5\.0 ACTIVE', 'ENSEMBLE v{config?.platform?.version || "5.5.0"} ACTIVE'),
    ("frontend/src/pages/dashboard.tsx", r'Analytics v5\.5\.0 active', 'Analytics v{config?.platform?.version || "5.5.0"} active'),
    ("frontend/src/pages/admin.tsx", r'VIT Network — v5\.5\.0', 'VIT Network — v{config?.platform?.version || "5.5.0"}'),
]

# We need to make sure usePublicConfig is imported and used in these files.
# Let's do dashboard.tsx first.

with open("frontend/src/pages/dashboard.tsx", "r") as f:
    content = f.read()

if 'usePublicConfig' not in content:
    content = re.sub(r'(import .* from "@/lib/apiClient";)', r'\1\nimport { usePublicConfig } from "@/lib/usePublicConfig";', content)
    content = re.sub(r'(export default function DashboardPage\(\) \{)', r'\1\n  const { data: config } = usePublicConfig();', content)

content = content.replace('ENSEMBLE v5.5.0 ACTIVE', 'ENSEMBLE v{config?.platform?.version || "5.5.0"} ACTIVE')
content = content.replace('Analytics v5.5.0 active', 'Analytics v{config?.platform?.version || "5.5.0"} active')

with open("frontend/src/pages/dashboard.tsx", "w") as f:
    f.write(content)

# Now admin.tsx
with open("frontend/src/pages/admin.tsx", "r") as f:
    content = f.read()

if 'usePublicConfig' not in content:
    content = re.sub(r'(import .* from "@/lib/apiClient";)', r'\1\nimport { usePublicConfig } from "@/lib/usePublicConfig";', content)
    content = re.sub(r'(export default function AdminPage\(\) \{)', r'\1\n  const { data: config } = usePublicConfig();', content)

content = content.replace('VIT Network — v5.5.0', 'VIT Network — v{config?.platform?.version || "5.5.0"}')

with open("frontend/src/pages/admin.tsx", "w") as f:
    f.write(content)
