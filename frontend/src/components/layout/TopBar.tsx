import React from 'react';
import { Search, Bell, User } from 'lucide-react';
import './TopBar.css';

interface TopBarProps {
  title?: string;
  showSearch?: boolean;
  actions?: React.ReactNode;
}

export default function TopBar({ title, showSearch, actions }: TopBarProps) {
  return (
    <header className="top-bar" role="banner">
      <div className="top-bar__brand">
        <span className="top-bar__logo" aria-label="VIT Network">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            {/* VIT diamond logo mark — replace with actual SVG */}
            <polygon points="12,2 22,12 12,22 2,12" fill="var(--vit-green)" />
          </svg>
        </span>
        {title && <span className="top-bar__title">{title}</span>}
      </div>

      {showSearch && (
        <button className="top-bar__search" aria-label="Search predictions, markets, and teams">
          <Search size={16} color="var(--vit-text-2)" aria-hidden="true" />
          <span className="top-bar__search-placeholder">Search...</span>
        </button>
      )}

      <div className="top-bar__actions">
        {actions}
        <button className="top-bar__icon-btn" aria-label="Notifications">
          <Bell size={20} aria-hidden="true" />
        </button>
        <button className="top-bar__icon-btn" aria-label="Account menu">
          <User size={20} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
