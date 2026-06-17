import os
import re

files_to_fix = [
    "frontend/src/pages/info.tsx",
    "frontend/src/pages/value-intelligence.tsx",
    "frontend/src/pages/marketplace.tsx",
    "frontend/src/pages/auth.tsx",
    "frontend/src/pages/analytics.tsx",
    "frontend/src/pages/roadmap.tsx",
    "frontend/src/pages/model-performance.tsx",
    "frontend/src/pages/teams.tsx",
]

# We should ideally use a hook, but for some purely static descriptive text,
# maybe we just update it to the dynamic template where possible.

def inject_config_hook(content, component_name):
    if 'usePublicConfig' not in content:
        # Add import
        content = re.sub(r'(import .* from "@/lib/apiClient";)', r'\1\nimport { usePublicConfig } from "@/lib/usePublicConfig";', content)
        if 'usePublicConfig' not in content: # Try another common import
             content = re.sub(r'(import .* from "react";)', r'\1\nimport { usePublicConfig } from "@/lib/usePublicConfig";', content)

        # Inject hook
        content = re.sub(r'(export default function ' + component_name + r'\(.*\) \{)', r'\1\n  const { data: config } = usePublicConfig();', content)
    return content

# Special case for info.tsx
with open("frontend/src/pages/info.tsx", "r") as f:
    content = f.read()
content = inject_config_hook(content, "InfoPage")
content = content.replace("a 13-model prediction ensemble", f"a {{config?.platform?.model_count || 13}}-model prediction ensemble")
with open("frontend/src/pages/info.tsx", "w") as f:
    f.write(content)

# Value Intelligence
with open("frontend/src/pages/value-intelligence.tsx", "r") as f:
    content = f.read()
content = inject_config_hook(content, "ValueAnalyticsPage")
content = content.replace("13-model ensemble", f"{{config?.platform?.model_count || 13}}-model ensemble")
with open("frontend/src/pages/value-intelligence.tsx", "w") as f:
    f.write(content)

# Marketplace
with open("frontend/src/pages/marketplace.tsx", "r") as f:
    content = f.read()
content = inject_config_hook(content, "MarketplacePage")
content = content.replace("13 system models", f"{{config?.platform?.model_count || 13}} system models")
content = content.replace("13 VIT model families", f"{{config?.platform?.model_count || 13}} VIT model families")
with open("frontend/src/pages/marketplace.tsx", "w") as f:
    f.write(content)

# Analytics
with open("frontend/src/pages/analytics.tsx", "r") as f:
    content = f.read()
content = inject_config_hook(content, "AnalyticsPage")
content = content.replace("13-Model Ensemble Breakdown", f"{{config?.platform?.model_count || 13}}-Model Ensemble Breakdown")
with open("frontend/src/pages/analytics.tsx", "w") as f:
    f.write(content)

# Model Performance
with open("frontend/src/pages/model-performance.tsx", "r") as f:
    content = f.read()
content = inject_config_hook(content, "ModelPerformancePage")
content = content.replace("across all 13 ensemble models", f"across all {{config?.platform?.model_count || 13}} ensemble models")
with open("frontend/src/pages/model-performance.tsx", "w") as f:
    f.write(content)

# Teams
with open("frontend/src/pages/teams.tsx", "r") as f:
    content = f.read()
content = inject_config_hook(content, "TeamsPage")
content = content.replace("13-model ensemble", f"{{config?.platform?.model_count || 13}}-model ensemble")
with open("frontend/src/pages/teams.tsx", "w") as f:
    f.write(content)
