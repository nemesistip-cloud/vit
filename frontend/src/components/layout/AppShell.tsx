import React from 'react';
import TopBar from './TopBar';
import BottomNav from './BottomNav';
import './AppShell.css';

interface AppShellProps {
  children: React.ReactNode;
  title?: string;
  showSearch?: boolean;
  actions?: React.ReactNode;
}

export default function AppShell({ children, title, showSearch = true, actions }: AppShellProps) {
  return (
    <div className="app-shell" role="main">
      <TopBar title={title} showSearch={showSearch} actions={actions} />
      <div className="app-content" id="main-content">
        {children}
      </div>
      <BottomNav />
    </div>
  );
}
