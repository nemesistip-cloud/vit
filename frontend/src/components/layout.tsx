import { useQuery } from "@tanstack/react-query";
import { TERMS } from "@/lib/terminology";
import { apiGet } from "@/lib/apiClient";
import { useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import { isTWA } from "@/lib/twa";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import {
  Activity, BarChart2, BookOpen, CheckSquare, Coins, Code2,
  CreditCard, Gift, Home, Lock, LogOut, Menu, ShieldCheck,
  ShoppingBag, Shield, ArrowLeftRight, Medal, Vote, X,
  TrendingUp, Layers, Bell, Settings, Sun, Moon, Target,
  Sparkles, Brain, Zap, Radio, Network, DatabaseZap, FlaskConical,
  Map, Fingerprint, BadgeCheck, Bot, Vault, Star, ShieldAlert, FileCode2,
  ChevronRight, Smartphone, Sword, MessageSquare, HardDrive,
  LineChart, Landmark, Eye, Mic2, Route, ListChecks, PieChart,
  Users
} from "lucide-react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "./ui/tooltip";

import { NotificationBell } from "./notification-bell";
import { EcosystemTicker } from "./ecosystem-ticker";
import { Badge } from "./ui/badge";
import { usePublicConfig } from "@/lib/usePublicConfig";

interface NavItem {
  label: string;
  icon: any;
  href: string;
  category: "signal" | "earn" | "admin" | "social";
  isNew?: boolean;
  isBeta?: boolean;
}

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { config } = usePublicConfig();

  const isAdmin = user?.role === "admin";

  const navigation: NavItem[] = [
    { label: "Dashboard", icon: Home, href: "/", category: "signal" },
    { label: "Project Teams", icon: Users, href: "/teams", category: "signal" },
    { label: "Matches", icon: Sword, href: "/matches", category: "signal" },
    { label: "Value Analytics", icon: BarChart2, href: "/analytics", category: "signal" },
    { label: "Predictions", icon: CheckSquare, href: "/predictions", category: "signal" },
    { label: "Accumulator", icon: Layers, href: "/accumulator", category: "signal" },
    { label: "Odds Intel", icon: Target, href: "/odds-intel", category: "signal" },
    { label: "Backtest", icon: Activity, href: "/backtest", category: "signal" },
    { label: "Bankroll", icon: Landmark, href: "/bankroll", category: "signal" },

    { label: "Wallet", icon: CreditCard, href: "/wallet", category: "earn" },
    { label: "Watchlist", icon: Eye, href: "/watchlist", category: "earn" },
    { label: "Tasks", icon: ListChecks, href: "/tasks", category: "earn" },
    { label: "Offers", icon: Zap, href: "/offers", category: "earn" },
    { label: "Merit", icon: Medal, href: "/merit", category: "earn" },
    { label: "Leaderboard", icon: TrophyIcon, href: "/leaderboard", category: "earn" },
    { label: "Referral", icon: ArrowLeftRight, href: "/referral", category: "earn" },
  ];

  if (isAdmin) {
    navigation.push(
      { label: "Admin", icon: Shield, href: "/admin", category: "admin" },
      { label: "Logs", icon: FileCode2, href: "/admin/logs", category: "admin" }
    );
  }

  // Common icon mapping to avoid duplicate imports
  const Icons = {
    Zap,
    X,
    ChevronRight,
    Moon,
    Sun,
    LogOut,
    Menu
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex overflow-hidden">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex w-64 flex-col border-r border-border/40 bg-card/30 backdrop-blur-xl">
        <div className="p-6 flex items-center gap-3 border-b border-border/40">
          <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center border border-primary/30">
            <DatabaseZap className="w-5 h-5 text-primary animate-pulse" />
          </div>
          <div>
            <h1 className="font-display text-lg tracking-wider font-bold text-foreground">
              VIT <span className="text-primary">NETWORK</span>
            </h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] -mt-1">
              Sports • Intelligence • Network
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-6 px-4 space-y-8 scrollbar-hide">
          {["signal", "earn", "social", "admin"].map((category) => {
            const items = navigation.filter(n => n.category === category);
            if (items.length === 0) return null;

            return (
              <div key={category} className="space-y-2">
                <h2 className="px-4 text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.2em] mb-4">
                  {category}
                </h2>
                <nav className="space-y-1">
                  {items.map((item) => (
                    <Link key={item.href} href={item.href}>
                      <a className={`
                        flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all duration-200 group
                        ${location === item.href
                          ? 'bg-primary/10 text-primary border border-primary/20'
                          : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}
                      `}>
                        <item.icon className={`w-4 h-4 ${location === item.href ? 'text-primary' : 'text-muted-foreground group-hover:text-primary transition-colors'}`} />
                        <span className="font-medium tracking-tight">{item.label}</span>
                        {item.isNew && (
                          <span className="ml-auto px-1.5 py-0.5 rounded-full bg-primary/20 text-[8px] font-bold text-primary uppercase animate-pulse">
                            New
                          </span>
                        )}
                      </a>
                    </Link>
                  ))}
                </nav>
              </div>
            );
          })}
        </div>

        <div className="p-4 border-t border-border/40 bg-muted/20 space-y-4">
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-background/50 border border-border/40">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center border border-primary/20">
              <span className="text-xs font-bold text-primary">
                {user?.email?.[0].toUpperCase() || 'T'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate">{user?.email}</p>
              <Badge variant="outline" className="text-[10px] h-4 px-1 capitalize bg-primary/5 text-primary border-primary/20">
                {user?.tier || 'Free'}
              </Badge>
            </div>
            <button
              onClick={logout}
              className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
            >
              <Icons.LogOut className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between px-2">
            <Button
              variant="ghost"
              size="icon"
              className="w-8 h-8 rounded-lg"
              onClick={toggleTheme}
            >
              {theme === 'dark' ? <Icons.Sun className="w-4 h-4" /> : <Icons.Moon className="w-4 h-4" />}
            </Button>
            <div className="text-[10px] text-muted-foreground font-mono">
              {config?.platform?.version || 'v5.5.0'}
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Nav */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 h-16 bg-card/80 backdrop-blur-xl border-t border-border/40 z-50 flex items-center justify-around px-2">
        {navigation.filter(n => ["signal", "earn"].includes(n.category)).slice(0, 5).map((item) => (
          <Link key={item.href} href={item.href}>
            <a className={`
              flex flex-col items-center gap-1 p-2 rounded-xl transition-all
              ${location === item.href ? 'text-primary scale-110' : 'text-muted-foreground'}
            `}>
              <item.icon className="w-5 h-5" />
              <span className="text-[8px] font-bold uppercase tracking-wider">{item.label}</span>
            </a>
          </Link>
        ))}
      </div>

      <main className="flex-1 flex flex-col min-w-0 h-screen">
        <header className="h-16 flex items-center justify-between px-4 lg:px-8 border-b border-border/40 bg-card/30 backdrop-blur-xl z-40 sticky top-0">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="text-[10px] font-bold text-primary tracking-widest uppercase">Live</span>
            </div>
            <div className="h-4 w-[1px] bg-border/40 mx-2" />
            <EcosystemTicker />
          </div>

          <div className="flex items-center gap-3">
            <NotificationBell />
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <Icons.X className="w-5 h-5" /> : <Icons.Menu className="w-5 h-5" />}
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto scroll-smooth">
          <div className="max-w-[1600px] mx-auto p-4 lg:p-8 pb-24 lg:pb-8">
            {children}
          </div>
        </div>
      </main>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 bg-background/95 backdrop-blur-md">
          <div className="p-6 flex flex-col h-full">
            <div className="flex items-center justify-between mb-8">
              <h1 className="font-display text-xl tracking-wider font-bold">
                VIT <span className="text-primary">NETWORK</span>
              </h1>
              <Button variant="ghost" size="icon" onClick={() => setIsMobileMenuOpen(false)}>
                <Icons.X className="w-6 h-6" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-8">
              {["signal", "earn", "social", "admin"].map((category) => {
                const items = navigation.filter(n => n.category === category);
                if (items.length === 0) return null;

                return (
                  <div key={category} className="space-y-4">
                    <h2 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-2">
                      {category}
                    </h2>
                    <div className="grid grid-cols-2 gap-2">
                      {items.map((item) => (
                        <Link key={item.href} href={item.href}>
                          <a
                            onClick={() => setIsMobileMenuOpen(false)}
                            className={`
                              flex items-center gap-3 p-3 rounded-xl border transition-all
                              ${location === item.href
                                ? 'bg-primary/10 border-primary/30 text-primary'
                                : 'bg-muted/5 border-border/40 text-muted-foreground'}
                            `}
                          >
                            <item.icon className="w-4 h-4" />
                            <span className="text-xs font-medium">{item.label}</span>
                          </a>
                        </Link>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-auto pt-6 border-t border-border/40 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30">
                    <span className="text-sm font-bold text-primary">{user?.email?.[0].toUpperCase()}</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium">{user?.email}</p>
                    <p className="text-[10px] text-primary font-bold uppercase">{user?.tier || 'Free'}</p>
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={logout} className="text-red-400 hover:text-red-500 hover:bg-red-500/10">
                  <Icons.LogOut className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Add missing Trophy icon
function TrophyIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
      <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
      <path d="M4 22h16" />
      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
      <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
    </svg>
  );
}
