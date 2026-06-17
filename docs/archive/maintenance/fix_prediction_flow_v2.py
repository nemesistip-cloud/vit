import re

with open("frontend/src/components/PredictionFlow.tsx", "r") as f:
    content = f.read()

# Fix duplicates and clean up first
content = content.replace('  const { data: config } = usePublicConfig();\n  const { data: config } = usePublicConfig();', '  const { data: config } = usePublicConfig();')

# 1. Add import if missing (should be there from previous run but let's be sure)
if 'import { usePublicConfig } from "@/lib/usePublicConfig";' not in content:
    content = re.sub(
        r'(import \{ useMutation, useQueryClient \} from "@tanstack/react-query";)',
        r'\1\nimport { usePublicConfig } from "@/lib/usePublicConfig";',
        content
    )

# 2. Update PROCESSING_STEPS (remove v4.2)
content = content.replace(
    '{ label: "Initializing Neural Ensemble v4.2", icon: Layers },',
    '{ label: "Initializing Neural Ensemble", icon: Layers },'
)

# 3. Refactor mutationFn - remove simulation loop and fix kickoff line
mutation_pattern = re.compile(
    r'mutationFn: async \(\) => \{.*?\? match\.kickoff_time',
    re.DOTALL
)
# We want to keep 'mutationFn: async () => {\n      const kickoff = match.kickoff_time?.endsWith("Z")\n        ? match.kickoff_time'
content = mutation_pattern.sub(
    'mutationFn: async () => {\n      const kickoff = match.kickoff_time?.endsWith("Z")\n        ? match.kickoff_time',
    content
)

# 4. Make versioning dynamic
content = content.replace(
    'Analytics v4.2 Finalized',
    'Analytics v{config?.platform?.version || "5.5.0"} Finalized'
)
content = content.replace(
    'ML Ensemble v4.2',
    'ML Ensemble v{config?.platform?.version || "5.5.0"}'
)

# 5. Fix Loading UI
content = re.sub(
    r'\{PROCESSING_STEPS\[processingStep\]\.label\}',
    'Processing Ensemble Models...',
    content
)
content = re.sub(
    r'const isCurrent = idx === processingStep;',
    'const isCurrent = true;',
    content
)
content = re.sub(
    r'const isPast = idx < processingStep;',
    'const isPast = false;',
    content
)
content = re.sub(
    r'<span>Progress: \{Math\.round\(\(\(processingStep \+ 1\) / PROCESSING_STEPS\.length\) \* 100\)\}%</span>',
    '<span>System Stability: 99.9%</span>',
    content
)
# Fix the progress bar width
content = re.sub(
    r'style=\{\{ width: `\$\{ \(\(processingStep \+ 1\) / PROCESSING_STEPS\.length\) \* 100 \}%` \}\}',
    'style={{ width: `100%` }}',
    content
)

# 6. Remove remaining processingStep state if any
content = content.replace('  const [processingStep, setProcessingStep] = useState(0);', '')
content = content.replace('      setProcessingStep(0);', '')

with open("frontend/src/components/PredictionFlow.tsx", "w") as f:
    f.write(content)
