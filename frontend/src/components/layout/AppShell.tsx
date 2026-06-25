import React from 'react';
import TopBar from './TopBar';
import BottomNav from './BottomNav';

interface AppShellProps {
  children: React.ReactNode;
  onSearchOpen?: () => void;
}

export default function AppShell({ children, onSearchOpen }: AppShellProps) {
  return (
    <div className="flex flex-col min-h-dvh max-w-2xl mx-auto relative bg-background">
      <TopBar onSearchOpen={onSearchOpen} />
      <main
        id="main-content"
        className="flex-1 overflow-y-auto overflow-x-hidden pt-14 pb-16 scroll-smooth"
        style={{ WebkitOverflowScrolling: 'touch' as any }}
      >
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
