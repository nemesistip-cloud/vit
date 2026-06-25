import React from 'react';
import { useLocation } from 'wouter';
import { useAuth } from '@/lib/auth';
import AppShell from './layout/AppShell';
import GlobalSearch from './global-search';
import { BetSlipPanel } from './bet-slip';
import { KellyFAB } from './gamification';
import { KellyCalculatorModal } from './kelly-calculator-modal';

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { user } = useAuth();

  if (!user) return null;

  const getPageTitle = (path: string) => {
    if (path === '/' || path === '/dashboard') return 'DASHBOARD';
    if (path.startsWith('/predictions')) return 'PREDICTIONS';
    if (path.startsWith('/exchange')) return 'EXCHANGE';
    if (path.startsWith('/merit')) return 'MERIT SCORE';
    if (path.startsWith('/wallet')) return 'WALLET';
    if (path.startsWith('/matches')) return 'MATCHES';
    if (path.startsWith('/analytics')) return 'ANALYTICS';
    return 'VIT NETWORK';
  };

  return (
    <>
      <AppShell title={getPageTitle(location)}>
        {children}
      </AppShell>

      <GlobalSearch />
      <BetSlipPanel />
      <KellyFAB />
      <KellyCalculatorModal />
    </>
  );
}
