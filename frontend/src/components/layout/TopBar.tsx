import React from 'react';
import { useLocation } from 'wouter';
import { GlobalSearchTrigger } from '../global-search';
import { NotificationBell } from '../notification-bell';
import { EcosystemTicker } from '../ecosystem-ticker';
import './TopBar.css';

interface TopBarProps {
  title?: string;
  showSearch?: boolean;
  actions?: React.ReactNode;
}

export default function TopBar({ title, showSearch = true, actions }: TopBarProps) {
  return (
    <header className="top-bar" role="banner">
      <div className="top-bar__brand">
        <span className="top-bar__logo" aria-label="VIT Network">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <polygon points="12,2 22,12 12,22 2,12" fill="var(--vit-green)" />
          </svg>
        </span>
        {title && <span className="top-bar__title">{title}</span>}
      </div>

      <div className="hidden sm:block flex-1">
        <EcosystemTicker />
      </div>

      <div className="top-bar__actions">
        {showSearch && <GlobalSearchTrigger />}
        {actions}
        <NotificationBell />
        <div className="w-8 h-8 rounded-full bg-vit-surface-3 border border-vit-border flex items-center justify-center text-vit-text-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
             <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
             <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </div>
      </div>
    </header>
  );
}
