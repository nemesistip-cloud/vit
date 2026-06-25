import React from 'react';
import { useLocation } from 'wouter';
import { Search, Bell, LogOut, Settings, User, Shield, ChevronDown } from 'lucide-react';
import { BrandLogo } from '@/components/BrandLogo';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const PAGE_TITLES: Record<string, string> = {
  '/dashboard':       'Dashboard',
  '/predictions':     'Predictions',
  '/matches':         'Matches',
  '/wallet':          'Wallet',
  '/exchange':        'Exchange',
  '/merit':           'Merit Score',
  '/analytics':       'Analytics',
  '/agents':          'AI Agents',
  '/assistant':       'Assistant',
  '/governance':      'Governance',
  '/validators':      'Validators',
  '/settings':        'Settings',
  '/admin':           'Admin',
  '/leaderboard':     'Leaderboard',
  '/marketplace':     'Marketplace',
  '/training':        'Training',
  '/research':        'Research',
  '/oracle':          'Oracle',
  '/network':         'Network',
  '/treasury':        'Treasury',
  '/community':       'Community',
  '/campus':          'Academy',
  '/elections':       'Elections',
  '/policy':          'Policy',
  '/finance':         'Finance',
  '/bridge':          'Bridge',
  '/referral':        'Referral',
  '/tasks':           'Tasks',
  '/watchlist':       'Watchlist',
  '/kyc':             'KYC',
  '/identity':        'Identity',
  '/trust':           'Trust',
  '/security':        'Security',
  '/storage':         'Storage',
  '/smart-contracts': 'Contracts',
  '/roadmap':         'Roadmap',
  '/reports':         'Reports',
  '/developer':       'Developer',
  '/bankroll':        'Bankroll',
  '/backtest':        'Backtest',
  '/accumulator':     'Accumulator',
  '/odds':            'Odds',
  '/earn':            'Earn',
  '/model-performance': 'Model Performance',
  '/value-intelligence': 'Value Intelligence',
};

function getPageTitle(path: string): string {
  for (const [key, val] of Object.entries(PAGE_TITLES)) {
    if (path === key || path.startsWith(key + '/')) return val;
  }
  return 'VIT Network';
}

interface TopBarProps {
  onSearchOpen?: () => void;
}

const TIER_COLORS: Record<string, string> = {
  viewer:    'text-muted-foreground border-border',
  analyst:   'text-blue-400 border-blue-400/30',
  pro:       'text-primary border-primary/30',
  validator: 'text-secondary border-secondary/30',
  admin:     'text-rose-400 border-rose-400/30',
};

export default function TopBar({ onSearchOpen }: TopBarProps) {
  const [location, setLocation] = useLocation();
  const { user, logout } = useAuth();

  const title = getPageTitle(location);
  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : 'VT';
  const tier = user?.tier?.toLowerCase() || 'viewer';
  const tierColor = TIER_COLORS[tier] || TIER_COLORS.viewer;

  return (
    <header className="fixed top-0 inset-x-0 max-w-2xl mx-auto h-14 flex items-center gap-2 px-3 bg-background/95 backdrop-blur-md border-b border-border z-[400]">
      {/* Brand mark */}
      <button
        onClick={() => setLocation('/dashboard')}
        className="flex-shrink-0 flex items-center min-h-0 min-w-0 p-0 rounded-lg"
        aria-label="Go to dashboard"
      >
        <BrandLogo size={26} />
      </button>

      {/* Page title — hidden on very small screens */}
      <span className="hidden sm:block font-display text-sm font-bold uppercase tracking-widest text-foreground flex-shrink-0 truncate max-w-[120px]">
        {title}
      </span>

      {/* Search trigger */}
      <button
        className={cn(
          "flex-1 flex items-center gap-2 h-8 px-3 rounded-lg border transition-colors text-muted-foreground min-h-0",
          "bg-muted/40 hover:bg-muted border-border hover:border-primary/20 hover:text-foreground"
        )}
        onClick={onSearchOpen}
        aria-label="Open search"
      >
        <Search size={13} className="flex-shrink-0" />
        <span className="text-xs font-mono hidden sm:block">
          Search predictions, matches...
        </span>
        <span className="text-xs font-mono sm:hidden">Search...</span>
        <span className="ml-auto hidden sm:flex items-center gap-1 text-[10px] text-muted-foreground/60 font-mono">
          <kbd className="px-1 py-0.5 bg-muted rounded text-[9px]">⌘</kbd>
          <kbd className="px-1 py-0.5 bg-muted rounded text-[9px]">K</kbd>
        </span>
      </button>

      {/* Notifications */}
      <Button
        variant="ghost"
        size="icon"
        className="w-8 h-8 min-h-0 min-w-0 rounded-lg flex-shrink-0 text-muted-foreground hover:text-foreground"
        aria-label="Notifications"
      >
        <Bell size={16} />
      </Button>

      {/* User menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className={cn(
              "flex items-center gap-1.5 h-8 min-h-0 min-w-0 px-2 rounded-lg",
              "bg-primary/10 border border-primary/20 hover:bg-primary/15 transition-colors",
              "font-mono text-xs font-bold text-primary"
            )}
            aria-label="User menu"
          >
            {initials}
            <ChevronDown size={11} className="opacity-60" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <div className="px-3 py-2.5">
            <p className="font-mono text-sm font-bold leading-none">{user?.username || 'User'}</p>
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{user?.email || ''}</p>
            {user?.tier && (
              <Badge
                variant="outline"
                className={cn("mt-2 text-[9px] uppercase tracking-widest font-mono py-0.5", tierColor)}
              >
                {user.tier} Tier
              </Badge>
            )}
          </div>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setLocation('/settings')} className="gap-2 cursor-pointer">
            <Settings size={13} className="text-muted-foreground" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setLocation('/identity')} className="gap-2 cursor-pointer">
            <User size={13} className="text-muted-foreground" />
            Profile
          </DropdownMenuItem>
          {user?.role === 'admin' && (
            <DropdownMenuItem onClick={() => setLocation('/admin')} className="gap-2 cursor-pointer">
              <Shield size={13} className="text-muted-foreground" />
              Admin Panel
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => logout?.()}
            className="gap-2 cursor-pointer text-destructive focus:text-destructive"
          >
            <LogOut size={13} />
            Sign Out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
