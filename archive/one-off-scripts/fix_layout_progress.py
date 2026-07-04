import re

with open('frontend/src/components/layout.tsx', 'r') as f:
    content = f.read()

# Add progress import
content = content.replace("import { WelcomeModal } from './onboarding';",
                          "import { WelcomeModal } from './onboarding';\nimport { Progress } from './ui/progress';")

# Add navigation progress state
logic = """
  const [navigating, setNavigating] = React.useState(false);
  const [location] = useLocation();

  React.useEffect(() => {
    setNavigating(true);
    const timer = setTimeout(() => setNavigating(false), 500);
    return () => clearTimeout(timer);
  }, [location]);
"""

content = content.replace('const closeOnboarding = () => {', 'const closeOnboarding = () => {' + logic)

# Add progress bar to JSX (fixed at top)
progress_bar = """
      {navigating && (
        <div className="fixed top-0 left-0 right-0 z-[10000] h-1">
          <Progress value={80} className="h-full rounded-none bg-transparent" />
        </div>
      )}
"""

content = content.replace('<AppShell onSearchOpen={openGlobalSearch}>', progress_bar + '\n      <AppShell onSearchOpen={openGlobalSearch}>')

with open('frontend/src/components/layout.tsx', 'w') as f:
    f.write(content)
