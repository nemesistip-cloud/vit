import React from 'react';
import { useLocation } from 'wouter';
import { useAuth } from '@/lib/auth';
import AppShell from './layout/AppShell';
import { GlobalSearch, openGlobalSearch } from './global-search';
import { BetSlipPanel } from './bet-slip';
import { KellyFAB, KellyCalculatorModal } from './kelly-calculator-modal';
import { WelcomeModal } from './onboarding';
import { Progress } from './ui/progress';

export function Layout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [showOnboarding, setShowOnboarding] = React.useState(() => {
    return localStorage.getItem("vit_onboarding_completed") !== "true";
  });

  const [navigating, setNavigating] = React.useState(false);
  const [location] = useLocation();

  React.useEffect(() => {
    setNavigating(true);
    const timer = setTimeout(() => setNavigating(false), 500);
    return () => clearTimeout(timer);
  }, [location]);

  const closeOnboarding = () => {
    localStorage.setItem("vit_onboarding_completed", "true");
    setShowOnboarding(false);
  };

  if (!user) return null;

  return (
    <>
      {navigating && (
        <div className="fixed top-0 left-0 right-0 z-[10000] h-1">
          <Progress value={80} className="h-full rounded-none bg-transparent" />
        </div>
      )}

      <AppShell onSearchOpen={openGlobalSearch}>
        {children}
      </AppShell>

      <GlobalSearch />
      <BetSlipPanel />
      <KellyFAB />
      <KellyCalculatorModal />
      {showOnboarding && user && <WelcomeModal username={user.username} onClose={closeOnboarding} onStartTour={closeOnboarding} />}
    </>
  );
}
