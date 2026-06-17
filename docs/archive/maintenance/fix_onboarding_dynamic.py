import re

with open("frontend/src/components/onboarding.tsx", "r") as f:
    content = f.read()

# Replace the static description in TOUR_STEPS with a function or dynamic value
# Actually, since it's a constant outside the component, let's just make it dynamic inside the component if possible,
# or just update the constant to have placeholders and replace them in the render.

content = content.replace(
    'description: "Browse live matches, tap a match card, and place your first AI-assisted prediction. Our ensemble of 13 models will show you their confidence before you commit."',
    'description: `Browse live matches, tap a match card, and place your first AI-assisted prediction. Our ensemble of ${config?.platform?.model_count || 13} models will show you their confidence before you commit.`'
)

content = content.replace(
    'description: "After selecting a match, expand the \'AI Transparency\' panel to see how each of the 13 models voted, their individual confidence, and historical accuracy."',
    'description: `After selecting a match, expand the \'AI Transparency\' panel to see how each of the ${config?.platform?.model_count || 13} models voted, their individual confidence, and historical accuracy.`'
)

# Fix the broken quote in the previous run
content = content.replace(
    'description: "Your {config?.platform?.welcome_bonus_vit || "100"} VIT welcome bonus is ready. Track your balance, view transaction history, and stake VIT on predictions to earn rewards."',
    'description: `Your ${config?.platform?.welcome_bonus_vit || 100} VIT welcome bonus is ready. Track your balance, view transaction history, and stake VIT on predictions to earn rewards.`'
)

# But wait, config is only available inside the component!
# Let's move TOUR_STEPS inside the component or use a function.

# Moving TOUR_STEPS inside OnboardingTour component
if 'const TOUR_STEPS: TourStep[] = [' in content:
    # Extract the array
    match = re.search(r'const TOUR_STEPS: TourStep\[\] = \[(.*?)\];', content, re.DOTALL)
    if match:
        steps_content = match.group(1)
        # Remove from global scope
        content = content.replace(match.group(0), '')
        # Insert into component
        content = re.sub(
            r'(export function OnboardingTour\(.*\) \{.*?const \{ data: config \} = usePublicConfig\(\);)',
            r'\1\n  const TOUR_STEPS: TourStep[] = [' + steps_content + '];',
            content,
            flags=re.DOTALL
        )

with open("frontend/src/components/onboarding.tsx", "w") as f:
    f.write(content)
