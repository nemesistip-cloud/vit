import React from 'react';
import { useLocation } from 'wouter';
import { useAuth } from '@/lib/auth';
import AppShell from './layout/AppShell';
import { GlobalSearch, openGlobalSearch } from './global-search';
import { BetSlipPanel } from './bet-slip';
import { KellyFAB, KellyCalculatorModal } from './kelly-calculator-modal';

export function Layout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <>
      <AppShell onSearchOpen={openGlobalSearch}>
        {children}
      </AppShell>

      <GlobalSearch />
      <BetSlipPanel />
      <KellyFAB />
      <KellyCalculatorModal />
    </>
  );
}
