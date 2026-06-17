import re

# elections.tsx
with open("frontend/src/pages/elections.tsx", "r") as f:
    content = f.read()

if 'usePublicConfig' not in content:
    content = re.sub(r'(import .* from "@/lib/apiClient";)', r'\1\nimport { usePublicConfig } from "@/lib/usePublicConfig";', content)
    content = re.sub(r'(export default function ElectionsPage\(\) \{)', r'\1\n  const { data: config } = usePublicConfig();', content)

content = content.replace('{ label: "Intelligence Engine Ready", value: "22",', '{ label: "Intelligence Engine Ready", value: String(config?.platform?.model_count || "22"),')

with open("frontend/src/pages/elections.tsx", "w") as f:
    f.write(content)

# onboarding.tsx
with open("frontend/src/components/onboarding.tsx", "r") as f:
    content = f.read()

if 'usePublicConfig' not in content:
    content = re.sub(r'(import \{ useState,)', r'import { usePublicConfig } from "@/lib/usePublicConfig";\n\1', content)

# Update Tour steps - need to find where they are
content = content.replace('Your 100 VIT welcome bonus is ready.', 'Your {config?.platform?.welcome_bonus_vit || "100"} VIT welcome bonus is ready.')

# Also need to inject usePublicConfig into the component that uses TOUR_STEPS
# OnboardingTour uses TOUR_STEPS
content = re.sub(r'(export function OnboardingTour\(.*\) \{)', r'\1\n  const { data: config } = usePublicConfig();', content)

with open("frontend/src/components/onboarding.tsx", "w") as f:
    f.write(content)
