import re

with open('frontend/src/components/layout.tsx', 'r') as f:
    content = f.read()

# Add imports for onboarding
content = content.replace("import { KellyFAB, KellyCalculatorModal } from './kelly-calculator-modal';",
                          "import { KellyFAB, KellyCalculatorModal } from './kelly-calculator-modal';\nimport { WelcomeModal } from './onboarding';")

# Add state and logic for onboarding
logic = """
  const [showOnboarding, setShowOnboarding] = React.useState(() => {
    return localStorage.getItem("vit_onboarding_completed") !== "true";
  });

  const closeOnboarding = () => {
    localStorage.setItem("vit_onboarding_completed", "true");
    setShowOnboarding(false);
  };
"""

content = content.replace('const { user } = useAuth();', 'const { user } = useAuth();' + logic)

# Add WelcomeModal to JSX
content = content.replace('<KellyCalculatorModal />',
                          '<KellyCalculatorModal />\n      {showOnboarding && user && <WelcomeModal username={user.username} onClose={closeOnboarding} onStartTour={closeOnboarding} />}')

with open('frontend/src/components/layout.tsx', 'w') as f:
    f.write(content)
