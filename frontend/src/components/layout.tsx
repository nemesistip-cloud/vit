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
  Users, Zap as ZapIcon, X as XIcon, ChevronRight as ChevronRightIcon,
  Moon as MoonIcon, Sun as SunIcon, LogOut as LogOutIcon, Menu as MenuIcon
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
type NavItem  = { name: string; href: string; icon: any };
type NavGroup = { name: string; items: NavItem[] };
const NAV_GROUPS: NavGroup[] = [
  {
    name: "Signal",
    items: [
      { name: "Dashboard",      href: "/dashboard",          icon: Home },
      { name: "Project Teams",   href: "/community",          icon: Users },
      { name: "Matches",        href: "/matches",            icon: Activity },
      { name: "Value Analytics", href: "/value-analytics", icon: Shield },
      { name: "Predictions",    href: "/predictions",        icon: CheckSquare },
      { name: "Accumulator",    href: "/accumulator",        icon: Layers },
      { name: "Odds Intel",     href: "/odds",               icon: TrendingUp },
      { name: "Backtest",       href: "/backtest",           icon: LineChart },
      { name: "Bankroll",       href: "/bankroll",           icon: Landmark },
    ],
  },
  {
    name: "Earn",
    items: [
      { name: "Wallet",      href: "/wallet",      icon: Coins },
      { name: "Watchlist",   href: "/watchlist",   icon: Eye },
      { name: "Tasks",       href: "/tasks",       icon: ListChecks },
      { name: "Offers",      href: "/earn",        icon: ZapIcon },
      { name: "Merit",       href: "/merit",       icon: Star },
      { name: "Leaderboard", href: "/leaderboard", icon: Medal },
      { name: "Referral",    href: "/referral",    icon: Gift },
    ],
  },
  {
    name: "Pro",
    items: [
      { name: "AI Assistant",     href: "/assistant",          icon: Sparkles },
      { name: "Training",         href: "/training",           icon: BookOpen },
      { name: "Performance Analytics", href: "/analytics",      icon: BarChart2 },
      { name: "Model Performance",href: "/model-performance",  icon: PieChart },
      { name: "Intel Reports",    href: "/reports",            icon: Radio },
      { name: "Research",         href: "/research",           icon: FlaskConical },
      { name: "Marketplace",      href: "/marketplace",        icon: ShoppingBag },
      { name: "Validators",       href: "/validators",         icon: ShieldCheck },
    ],
  },
  {
    name: "Network",
    items: [
      { name: "VIT Analytics",      href: "/oracle",          icon: DatabaseZap },
      { name: "Node Network",    href: "/network",         icon: Network },
      { name: "Smart Contracts", href: "/smart-contracts", icon: FileCode2 },
      { name: "Treasury",        href: "/treasury",        icon: Vault },
      { name: "Trust & Safety",  href: "/trust",           icon: Lock },
      { name: "Security",        href: "/security",        icon: ShieldAlert },
      { name: "Bridge",          href: "/bridge",          icon: ArrowLeftRight },
      { name: "Governance",      href: "/governance",      icon: Vote },
      { name: "Developer",       href: "/developer",       icon: Code2 },
      { name: "Roadmap",         href: "/roadmap",         icon: Route },
    ],
  },
  {
    name: "You",
    items: [
      { name: "My Identity",      href: "/identity",        icon: Fingerprint },
      { name: "KYC Verify",       href: "/kyc",             icon: BadgeCheck },
      { name: "Subscription",     href: "/subscription",    icon: CreditCard },
      { name: "Settings",         href: "/settings",        icon: Settings },
    ],
  },
];
const MOBILE_BOTTOM_NAV = [
  { name: "Home",        href: "/dashboard",   icon: Home },
  { name: "Matches",     href: "/matches",     icon: Activity },
  { name: "Predictions", href: "/predictions", icon: CheckSquare },
  { name: "Tasks",       href: "/tasks",       icon: Target },
  { name: "Wallet",      href: "/wallet",      icon: Coins },
];
const TIER_BADGE: Record<string, { label: string; cls: string }> = {
  elite:   { label: "Pro",       cls: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10" },
  pro:     { label: "Pro",       cls: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10" },
  analyst: { label: "Analyst",   cls: "text-blue-400 border-blue-500/40 bg-blue-500/10" },
  validator: { label: "Validator", cls: "text-amber-400 border-amber-500/40 bg-amber-500/10" },
  viewer:  { label: "Free",      cls: "text-zinc-400 border-zinc-600" },
  admin:   { label: "Admin",     cls: "bg-rose-400/10 text-rose-400 border-rose-400/25" },
};
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
function Footer() {
  const { data: oracleStats } = useQuery({
    queryKey: ["/api/oracle/stats"],
    queryFn: () => apiGet<any>("/api/oracle/stats"),
    refetchInterval: 60000,
  });
  const { data: networkStats } = useQuery({
    queryKey: ["/api/network/stats"],
    queryFn: () => apiGet<any>("/api/network/stats"),
    refetchInterval: 60000,
  });
  const oracleStatus = oracleStats?.status ?? "—";
  const nodeCount = networkStats?.node_count ?? "—";
  return (
    <footer className="mt-auto py-8 px-4 border-t border-white/5 bg-card/20">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="space-y-1 text-center md:text-left">
          <div className="text-xs font-mono font-bold text-foreground">
            {TERMS.platform.name} — {TERMS.platform.version}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
            © 2026 {TERMS.platform.shortName}. {TERMS.platform.tagline}.
          </div>
        </div>
        <div className="flex flex-wrap justify-center gap-4 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/3 border border-white/5">
            Oracle Status: <span className={oracleStatus === "Live" ? "text-emerald-400" : "text-amber-400"}>{oracleStatus}</span>
            <span className={`w-1.5 h-1.5 rounded-full ${oracleStatus === "Live" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/3 border border-white/5">
            Network Nodes: <span className="text-foreground">{nodeCount}</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/3 border border-white/5">
            Engine: <span className="text-emerald-400">Active</span>
          </div>
        </div>
        <div className="flex gap-4 text-[10px] font-mono uppercase tracking-widest">
          <Link href="/terms" className="hover:text-primary transition-colors">Terms</Link>
          <Link href="/privacy" className="hover:text-primary transition-colors">Privacy</Link>
          <Link href="/developer" className="hover:text-primary transition-colors">Developer API</Link>
          <Link href="/network" className="hover:text-primary transition-colors">Network Status</Link>
        </div>
      </div>
    </footer>
  );
}
export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  if (!user) return <>{children}</>;
  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");
  const isAdmin      = user?.role === "admin";
  const tierKey      = isAdmin ? "admin" : (user?.subscription_tier ?? "viewer");
  const tierBadge    = TIER_BADGE[tierKey] ?? TIER_BADGE.viewer;
  const allGroups: NavGroup[] = [
    ...NAV_GROUPS,
    ...(isAdmin
      ? [{
          name: "Admin",
          items: [
            { name: "Admin Panel", href: "/admin",  icon: Lock },
            { name: "AI Agents",   href: "/agents", icon: Bot  },
          ],
        }]
      : []),
  ];
  const NavItems = ({ onClick }: { onClick?: () => void }) => (
    <div className="space-y-5">
      {allGroups.map((group) => (
        <div key={group.name}>
          <div className="vit-section-label px-2 mb-2">{group.name}</div>
          <div className="space-y-0.5">
            {group.items.map((item) => {
              const isActive = location === item.href || location.startsWith(item.href + "/");
              return (
                <Link key={item.name} href={item.href}>
                  <span
                    onClick={onClick}
                    className={`group relative flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-sm font-mono font-medium transition-all duration-150 cursor-pointer ${
                      isActive
                        ? "bg-primary/10 text-primary border border-primary/20  "
                        : "text-muted-foreground hover:bg-white/5 hover:text-foreground border border-transparent hover:border-white/5"
                    }`}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-2 bottom-2 w-0.5 rounded-full bg-primary " />
                    )}
                    <item.icon className={`w-3.5 h-3.5 flex-shrink-0 transition-all ${isActive ? "text-primary" : "group-hover:text-foreground group-hover:scale-105"}`} />
                    <span className="truncate text-xs">{item.name}</span>
                    {isActive && <ChevronRightIcon className="w-3 h-3 ml-auto opacity-50" />}
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
  return (
    <div className="min-h-screen bg-background flex flex-col lg:flex-row">
      {/* ── Mobile top bar ──────────────────────────────── */}
      <div className="lg:hidden flex items-center justify-between px-4 py-2.5 border-b border-border/50 sticky top-0 z-40 bg-background">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg overflow-hidden flex items-center justify-center bg-gradient-to-br from-primary/20 to-purple-500/20 border border-primary/25">
            <ZapIcon className="w-3.5 h-3.5 text-primary" />
          </div>
          <span className="font-bold font-mono text-sm tracking-tight">
            VIT
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8" aria-label="Toggle theme">
                {theme === "dark" ? <SunIcon className="w-4 h-4 text-yellow-400" /> : <MoonIcon className="w-4 h-4 text-blue-400" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            </TooltipContent>
          </Tooltip>
          <NotificationBell />
          <Button
            variant="ghost" size="icon"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
            className="h-8 w-8"
          >
            <MenuIcon className="w-4 h-4" />
          </Button>
        </div>
      </div>
      {/* ── Mobile slide-over drawer ─────────────────────── */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/75" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 h-full w-72 flex flex-col  "
            style={{ background: "var(--vit-gradient-sidebar)" }}>
            <div className="flex items-center justify-between p-4 border-b border-white/5">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary/25 to-purple-500/25 border border-primary/30 flex items-center justify-center">
                  <ZapIcon className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <div className="font-bold font-mono text-sm tracking-tight">VIT</div>
                  <div className="text-[9px] font-mono text-muted-foreground/60 tracking-widest uppercase">Analytics</div>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)} className="h-8 w-8" aria-label="Close menu">
                <XIcon className="w-4 h-4" />
              </Button>
            </div>
            <nav className="flex-1 p-3 overflow-y-auto vit-scrollbar">
              <NavItems onClick={() => setMobileOpen(false)} />
            </nav>
            <div className="p-3 border-t border-white/5">
              <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg bg-white/3">
                <UserInitials name={user.username} />
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-mono font-semibold text-foreground truncate">{user.username}</div>
                  <div className={`inline-flex items-center rounded px-1 py-0 text-[9px] font-mono border mt-0.5 ${tierBadge.cls}`}>{tierBadge.label}</div>
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" onClick={logout} className="h-7 w-7 flex-shrink-0" aria-label="Logout">
                      <LogOutIcon className="w-3.5 h-3.5 text-muted-foreground" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Logout</TooltipContent>
                </Tooltip>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* ── Desktop sidebar ──────────────────────────────── */}
      <div className="hidden lg:flex w-60 flex-shrink-0 flex-col sticky top-0 h-screen border-r border-white/5"
        style={{ background: "var(--vit-gradient-sidebar)" }}>
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-4 py-4 border-b border-white/5">
          <BrandLogo size={32} withWordmark />
          <div className="flex items-center gap-0.5 flex-shrink-0 ml-auto">
            <span className="vit-live-dot" style={{ width: 5, height: 5 }} />
          </div>
        </div>
        {/* Nav */}
        <nav className="flex-1 px-2.5 py-3 overflow-y-auto vit-scrollbar">
          <NavItems />
        </nav>
        {/* User footer */}
        <div className="p-3 border-t border-white/5">
          <div className="flex items-center gap-2 rounded-lg p-2 bg-white/3 hover:bg-white/5 transition-colors">
            <UserInitials name={user.username} />
            <div className="min-w-0 flex-1">
              <div className="text-xs font-mono font-semibold text-foreground truncate">{user.username}</div>
              <span className={`inline-flex items-center rounded px-1 py-0 text-[9px] font-mono border mt-0.5 ${tierBadge.cls}`}>{tierBadge.label}</span>
            </div>
            <div className="flex items-center gap-0.5 flex-shrink-0">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-7 w-7" aria-label="Toggle theme">
                    {theme === "dark" ? <SunIcon className="w-3.5 h-3.5 text-yellow-400/70" /> : <MoonIcon className="w-3.5 h-3.5 text-blue-400/70" />}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
                </TooltipContent>
              </Tooltip>
              <NotificationBell />
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" onClick={logout} className="h-7 w-7" aria-label="Logout">
                    <LogOutIcon className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive transition-colors" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Logout</TooltipContent>
              </Tooltip>
            </div>
          </div>
        </div>
      </div>
      {/* ── Main content + ecosystem ticker ──────────────── */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <EcosystemTicker />
        <main className="flex-1 overflow-y-auto bg-background vit-scrollbar">
          <div className="p-4 lg:p-6 max-w-7xl mx-auto pb-24 lg:pb-8">
            {children}
            <Footer />
          </div>
        </main>

        {/* Global Tools */}
        <BetSlipPanel />
        <KellyFAB />
        <KellyCalculatorModal />
      </div>
      {/* ── Mobile Bottom Navigation ─────────────────────── */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border/40"
        style={{ background: "rgba(8,8,18,0.98)" }}>
        <div className="flex justify-around items-center h-[60px] max-w-lg mx-auto">
          {MOBILE_BOTTOM_NAV.map((item) => {
            const isActive = location === item.href || location.startsWith(item.href + "/");
            return (
              <Link key={item.name} href={item.href} className="flex-1">
                <span className={`relative flex flex-col items-center justify-center h-full gap-1 transition-all cursor-pointer ${
                  isActive ? "text-primary" : "text-muted-foreground/60 hover:text-muted-foreground"
                }`}>
                  {isActive && (
                    <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-primary rounded-full " />
                  )}
                  <item.icon className={`w-4.5 h-4.5 transition-transform ${isActive ? "scale-110" : ""}`} style={{ width: 18, height: 18 }} />
                  <span className="text-[9px] font-mono uppercase tracking-wide text-center">{item.name}</span>
                </span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
