import React from 'react';
import { useLocation, useLocation as useWouterLocation } from 'wouter';
import { Home, TrendingUp, Zap, Trophy, Wallet } from 'lucide-react';
import './BottomNav.css';

const NAV_ITEMS = [
  { id: 'home',     label: 'Home',    icon: Home,        path: '/' },
  { id: 'predict',  label: 'Predict', icon: TrendingUp,  path: '/predictions' },
  { id: 'trade',    label: 'Exchange',icon: Zap,         path: '/exchange' },
  { id: 'merit',    label: 'Merit',   icon: Trophy,      path: '/merit' },
  { id: 'wallet',   label: 'Wallet',  icon: Wallet,      path: '/wallet' },
];

export default function BottomNav() {
  const [location, setLocation] = useWouterLocation();

  return (
    <nav className="bottom-nav" role="navigation" aria-label="Main navigation">
      {NAV_ITEMS.map(({ id, label, icon: Icon, path }) => {
        const isActive = location === path ||
                         (path !== '/' && location.startsWith(path));
        return (
          <button
            key={id}
            className={`bottom-nav__item ${isActive ? 'bottom-nav__item--active' : ''}`}
            onClick={() => setLocation(path)}
            aria-label={label}
            aria-current={isActive ? 'page' : undefined}
          >
            <span className="bottom-nav__icon" aria-hidden="true">
              <Icon size={22} />
            </span>
            <span className="bottom-nav__label">{label}</span>
            {isActive && <span className="bottom-nav__indicator" aria-hidden="true" />}
          </button>
        );
      })}
    </nav>
  );
}
