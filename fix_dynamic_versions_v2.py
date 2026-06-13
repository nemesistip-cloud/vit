import re

# assistant.tsx
with open("frontend/src/pages/assistant.tsx", "r") as f:
    content = f.read()

if 'usePublicConfig' not in content:
    content = re.sub(r'(import \{ useAssistantChat,)', r'import { usePublicConfig } from "@/lib/usePublicConfig";\n\1', content)
    content = re.sub(r'(export default function AssistantPage\(\) \{)', r'\1\n  const { data: config } = usePublicConfig();', content)

content = content.replace('Native Agentic Intelligence (v5.5.0)', 'Native Agentic Intelligence (v{config?.platform?.version || "5.5.0"})')

with open("frontend/src/pages/assistant.tsx", "w") as f:
    f.write(content)
