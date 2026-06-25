import React from 'react';
import { useLocation } from 'wouter';
import { LayoutDashboard, TrendingUp, Zap, Trophy, Wallet } from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { id: 'home',    label: 'Home',    icon: LayoutDashboard, path: '/dashboard'   },
  { id: 'signals', label: 'Signals', icon: TrendingUp,      path: '/predictions' },
  { id: 'trade',   label: 'Trade',   icon: Zap,             path: '/exchange'    },
  { id: 'merit',   label: 'Merit',   icon: Trophy,          path: '/merit'       },
  { id: 'wallet',  label: 'Wallet',  icon: Wallet,          path: '/wallet'      },
] as const;

export default function BottomNav() {
  const [location, setLocation] = useLocation();

  return (
    <nav
      className="fixed bottom-0 inset-x-0 max-w-2xl mx-auto flex items-stretch justify-around bg-background/95 backdrop-blur-md border-t border-border z-[400]"
      style={{ height: 60, paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      role="navigation"
      aria-label="Main navigation"
    >
      {NAV_ITEMS.map(({ id, label, icon: Icon, path }) => {
        const isActive =
          location === path ||
          (path !== '/dashboard' && location.startsWith(path));

        return (
          <button
            key={id}
            className={cn(
              "relative flex flex-col items-center justify-center gap-0.5 flex-1 h-full px-1",
              "min-h-0 min-w-0 transition-colors duration-150",
              isActive
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
            onClick={() => setLocation(path)}
            aria-label={label}
            aria-current={isActive ? 'page' : undefined}
          >
            {/* Active indicator pill at top */}
            {isActive && (
              <span className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-[2px] bg-primary rounded-b-full" />
            )}

            <Icon
              size={19}
              strokeWidth={isActive ? 2.5 : 2}
              className={cn(
                "transition-transform duration-150",
                isActive && "scale-110"
              )}
            />
            <span
              className={cn(
                "text-[9px] tracking-wide font-mono leading-none",
                isActive ? "font-bold" : "font-medium"
              )}
            >
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
