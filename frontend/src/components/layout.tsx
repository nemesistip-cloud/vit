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
import { BrandLogo } from "@/components/BrandLogo";
import { BetSlipPanel } from "./bet-slip";
import { KellyCalculatorModal, KellyFAB } from "./kelly-calculator-modal";
import { usePublicConfig } from "@/lib/usePublicConfig";

type NavItem  = { name: string; href: string; icon: any; category?: string };
type NavGroup = { name: string; items: NavItem[] };

const TIER_BADGE: Record<string, { label: string; cls: string }> = {
  elite:   { label: "Pro",       cls: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10" },
  pro:     { label: "Pro",       cls: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10" },
  analyst: { label: "Analyst",   cls: "text-blue-400 border-blue-500/40 bg-blue-500/10" },
  validator: { label: "Validator", cls: "text-amber-400 border-amber-500/40 bg-amber-500/10" },
  viewer:  { label: "Free",      cls: "text-zinc-400 border-zinc-600" },
  admin:   { label: "Admin",     cls: "bg-rose-400/10 text-rose-400 border-rose-400/25" },
};

const MOBILE_BOTTOM_NAV = [
  { name: "Home",        href: "/dashboard",   icon: Home },
  { name: "Matches",     href: "/matches",     icon: Activity },
  { name: "Predictions", href: "/predictions", icon: CheckSquare },
  { name: "Tasks",       href: "/tasks",       icon: Target },
  { name: "Wallet",      href: "/wallet",      icon: Coins },
];

function NavItems() {
  const [location] = useLocation();
  const navigation = [
    { label: "Dashboard", icon: Home, href: "/dashboard" },
    { label: "Matches", icon: Activity, href: "/matches" },
    { label: "Predictions", icon: CheckSquare, href: "/predictions" },
    { label: "Wallet", icon: Coins, href: "/wallet" },
    { label: "Leaderboard", icon: Medal, href: "/leaderboard" },
    { label: "Settings", icon: Settings, href: "/settings" },
  ];

  return (
    <div className="space-y-1">
      {navigation.map((item) => {
        const Icon = item.icon;
        const isActive = location === item.href;
        return (
          <Link key={item.href} href={item.href}>
            <a className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
              isActive ? "bg-primary/10 text-primary border border-primary/20" : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}>
              <Icon className="w-4 h-4" />
              <span className="font-medium">{item.label}</span>
            </a>
          </Link>
        );
      })}
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-auto pt-8 pb-4 border-t border-border/40">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
        <p>© 2026 VIT Network</p>
        <div className="flex gap-4">
          <Link href="/terms">Terms</Link>
          <Link href="/privacy">Privacy</Link>
        </div>
      </div>
    </footer>
  );
}

function UserInitials({ name }: { name: string }) {
  const initials = name
    .split(/[\s_-]/)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("");
  return (
    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-purple-500/20 border border-primary/20 flex items-center justify-center flex-shrink-0">
      <span className="text-xs font-bold font-mono text-primary">{initials || "V"}</span>
    </div>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { data: config } = usePublicConfig();

  if (!user) return null;

  const tier = user.tier || 'viewer';
  const tierBadge = TIER_BADGE[tier] || TIER_BADGE.viewer;

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

        <div className="flex-1 overflow-y-auto py-6 px-4 scrollbar-hide">
          <NavItems />
        </div>

        <div className="p-4 border-t border-border/40 bg-muted/20 space-y-4">
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-background/50 border border-border/40">
            <UserInitials name={user.username || user.email || 'T'} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate">{user.username || user.email}</p>
              <Badge variant="outline" className={`text-[10px] h-4 px-1 capitalize ${tierBadge.cls}`}>
                {tierBadge.label}
              </Badge>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={logout}
                  className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                  aria-label="Logout"
                >
                  <Icons.LogOut className="w-4 h-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent>Logout</TooltipContent>
            </Tooltip>
          </div>

          <div className="flex items-center justify-between px-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-8 h-8 rounded-lg"
                  onClick={toggleTheme}
                  aria-label="Toggle theme"
                >
                  {theme === 'dark' ? <Icons.Sun className="w-4 h-4" /> : <Icons.Moon className="w-4 h-4" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
              </TooltipContent>
            </Tooltip>
            <div className="text-[10px] text-muted-foreground font-mono">
              {config?.platform?.version || 'v5.5.0'}
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Nav Bar */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 h-16 bg-card/80 backdrop-blur-xl border-t border-border/40 z-50 flex items-center justify-around px-2">
        {MOBILE_BOTTOM_NAV.map((item) => {
          const isActive = location === item.href;
          return (
            <Link key={item.href} href={item.href}>
              <a className={`
                flex flex-col items-center gap-1 p-2 rounded-xl transition-all
                ${isActive ? 'text-primary scale-110' : 'text-muted-foreground'}
              `}>
                <item.icon className="w-5 h-5" />
                <span className="text-[8px] font-bold uppercase tracking-wider">{item.name}</span>
              </a>
            </Link>
          );
        })}
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
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="lg:hidden"
                  onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                  aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
                >
                  {isMobileMenuOpen ? <Icons.X className="w-5 h-5" /> : <Icons.Menu className="w-5 h-5" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {isMobileMenuOpen ? "Close menu" : "Open menu"}
              </TooltipContent>
            </Tooltip>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto scroll-smooth bg-background">
          <div className="max-w-[1600px] mx-auto p-4 lg:p-8 pb-24 lg:pb-8">
            {children}
            <Footer />
          </div>
        </div>

        {/* Global Tools */}
        <BetSlipPanel />
        <KellyFAB />
        <KellyCalculatorModal />
      </main>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 bg-background/95 backdrop-blur-md">
          <div className="p-6 flex flex-col h-full">
            <div className="flex items-center justify-between mb-8">
              <h1 className="font-display text-xl tracking-wider font-bold text-foreground">
                VIT <span className="text-primary">NETWORK</span>
              </h1>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" onClick={() => setIsMobileMenuOpen(false)} aria-label="Close menu">
                    <Icons.X className="w-6 h-6" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Close menu</TooltipContent>
              </Tooltip>
            </div>

            <div className="flex-1 overflow-y-auto">
              <NavItems />
            </div>

            <div className="mt-auto pt-6 border-t border-border/40 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <UserInitials name={user.username || user.email || 'T'} />
                  <div>
                    <p className="text-sm font-medium text-foreground">{user.username || user.email}</p>
                    <p className="text-[10px] text-primary font-bold uppercase">{tier}</p>
                  </div>
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={logout}
                      className="text-red-400 hover:text-red-500 hover:bg-red-500/10"
                      aria-label="Logout"
                    >
                      <Icons.LogOut className="w-5 h-5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Logout</TooltipContent>
                </Tooltip>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

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
