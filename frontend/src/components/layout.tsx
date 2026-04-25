import { useState } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import {
  Activity, BarChart2, BookOpen, CheckSquare, Coins, Code2,
  CreditCard, Gift, Home, Lock, LogOut, Menu, ShieldCheck,
  ShoppingBag, Shield, ArrowLeftRight, Trophy, Vote, X,
  TrendingUp, Layers, Bell, Settings, Sun, Moon, Target,
  Sparkles, Brain,
} from "lucide-react";
import { Button } from "./ui/button";
import { NotificationBell } from "./notification-bell";

type NavItem = { name: string; href: string; icon: typeof Home };
type NavGroup = { name: string; items: NavItem[] };

const NAV_GROUPS: NavGroup[] = [
  {
    name: "Bet",
    items: [
      { name: "Dashboard",   href: "/dashboard",   icon: Home },
      { name: "Matches",     href: "/matches",     icon: Activity },
      { name: "Predictions", href: "/predictions", icon: CheckSquare },
      { name: "Accumulator", href: "/accumulator", icon: Layers },
      { name: "Odds Intel",  href: "/odds",        icon: TrendingUp },
    ],
  },
  {
    name: "Earn",
    items: [
      { name: "Wallet",      href: "/wallet",      icon: Coins },
      { name: "Tasks",       href: "/tasks",       icon: Target },
      { name: "Leaderboard", href: "/leaderboard", icon: Trophy },
      { name: "Referral",    href: "/referral",    icon: Gift },
    ],
  },
  {
    name: "Pro",
    items: [
      { name: "AI Assistant", href: "/assistant",   icon: Sparkles },
      { name: "Training",     href: "/training",    icon: BookOpen },
      { name: "Analytics",    href: "/analytics",   icon: BarChart2 },
      { name: "Marketplace",  href: "/marketplace", icon: ShoppingBag },
      { name: "Validators",   href: "/validators",  icon: ShieldCheck },
    ],
  },
  {
    name: "Network",
    items: [
      { name: "Trust & Safety", href: "/trust",      icon: Shield },
      { name: "Bridge",         href: "/bridge",     icon: ArrowLeftRight },
      { name: "Governance",     href: "/governance", icon: Vote },
      { name: "Developer",      href: "/developer",  icon: Code2 },
    ],
  },
  {
    name: "You",
    items: [
      { name: "Subscription", href: "/subscription", icon: CreditCard },
      { name: "Settings",     href: "/settings",     icon: Settings },
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

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout, hasTier } = useAuth();
  const [location] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  if (!user) return <>{children}</>;

  const isAdmin = user?.role === "admin";
  const canUploadAi = isAdmin || hasTier("analyst");

  const proGroup: NavGroup = {
    name: "Pro",
    items: [
      ...NAV_GROUPS.find(g => g.name === "Pro")!.items,
      ...(canUploadAi
        ? [{ name: "AI Sources", href: "/ai-sources", icon: Brain }]
        : []),
    ],
  };

  const allGroups: NavGroup[] = [
    ...NAV_GROUPS.map(g => (g.name === "Pro" ? proGroup : g)),
    ...(isAdmin
      ? [{ name: "Admin", items: [{ name: "Admin Panel", href: "/admin", icon: Lock }] }]
      : []),
  ];

  const NavItems = ({ onClick }: { onClick?: () => void }) => (
    <div className="space-y-4">
      {allGroups.map((group) => (
        <div key={group.name}>
          <div className="px-3 mb-1.5 text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
            {group.name}
          </div>
          <div className="space-y-0.5">
            {group.items.map((item) => {
              const isActive = location === item.href || location.startsWith(item.href + "/");
              return (
                <Link key={item.name} href={item.href}>
                  <span
                    onClick={onClick}
                    className={`group relative flex items-center gap-3 px-3 py-2 rounded-md text-sm font-mono font-medium transition-all duration-150 cursor-pointer ${
                      isActive
                        ? "bg-primary/10 text-primary border border-primary/20 shadow-sm"
                        : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground hover:translate-x-0.5 border border-transparent"
                    }`}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-primary" />
                    )}
                    <item.icon className={`w-4 h-4 flex-shrink-0 transition-transform ${isActive ? "" : "group-hover:scale-110"}`} />
                    {item.name}
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
      <div className="lg:hidden flex items-center justify-between px-4 py-3 bg-sidebar border-b border-sidebar-border sticky top-0 z-40">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-primary/10 border border-primary/30 rounded-lg flex items-center justify-center">
            <Trophy className="w-3.5 h-3.5 text-primary" />
          </div>
          <span className="font-bold font-mono text-sm tracking-tight text-foreground">
            VIT<span className="text-primary">_OS</span>
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8" aria-label="Toggle theme">
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </Button>
          <NotificationBell />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
            className="h-8 w-8"
          >
            <Menu className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* ── Mobile slide-over drawer ─────────────────────── */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute left-0 top-0 h-full w-72 bg-sidebar border-r border-sidebar-border flex flex-col shadow-2xl vit-animate-slide-down">
            <div className="flex items-center justify-between p-4 border-b border-sidebar-border">
              <div className="flex items-center gap-2">
                <Trophy className="w-5 h-5 text-primary" />
                <span className="font-bold font-mono tracking-tight">VIT Sports</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileOpen(false)}
                className="h-8 w-8"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
              <NavItems onClick={() => setMobileOpen(false)} />
            </nav>
            <div className="p-4 border-t border-sidebar-border">
              <div className="flex items-center justify-between px-2">
                <div>
                  <div className="text-sm font-mono font-medium text-foreground">{user.username}</div>
                  <div className="text-xs text-muted-foreground capitalize font-mono">{user.role}</div>
                </div>
                <Button variant="ghost" size="icon" onClick={logout} className="h-8 w-8">
                  <LogOut className="w-4 h-4 text-muted-foreground hover:text-destructive transition-colors" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Desktop sidebar ──────────────────────────────── */}
      <div className="hidden lg:flex w-64 bg-sidebar border-r border-sidebar-border flex-shrink-0 flex-col sticky top-0 h-screen">
        <div className="p-5 flex items-center gap-2.5 border-b border-sidebar-border/50">
          <div className="w-8 h-8 bg-primary/10 border border-primary/30 rounded-lg flex items-center justify-center">
            <Trophy className="w-4 h-4 text-primary" />
          </div>
          <span className="font-bold text-base font-mono tracking-tight text-foreground">
            VIT<span className="text-primary">_OS</span>
          </span>
        </div>

        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          <NavItems />
        </nav>

        <div className="p-4 border-t border-sidebar-border">
          <div className="flex items-center justify-between px-1 mb-1">
            <div className="min-w-0">
              <div className="text-sm font-mono font-medium text-foreground truncate">{user.username}</div>
              <div className="text-xs text-muted-foreground capitalize font-mono">{user.role}</div>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8" aria-label="Toggle theme">
                {theme === "dark" ? <Sun className="w-4 h-4 text-yellow-400" /> : <Moon className="w-4 h-4 text-blue-400" />}
              </Button>
              <NotificationBell />
              <Button variant="ghost" size="icon" onClick={logout} className="h-8 w-8">
                <LogOut className="w-4 h-4 text-muted-foreground hover:text-destructive transition-colors" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main content ─────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto bg-background min-h-0">
        <div className="p-4 lg:p-8 max-w-7xl mx-auto pb-24 lg:pb-8">
          {children}
        </div>
      </main>

      {/* ── Mobile Bottom Navigation ─────────────────────── */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-sidebar/95 backdrop-blur-md border-t border-sidebar-border">
        <div className="grid grid-cols-5 h-16">
          {MOBILE_BOTTOM_NAV.map((item) => {
            const isActive = location === item.href || location.startsWith(item.href + "/");
            return (
              <Link key={item.name} href={item.href}>
                <span className={`relative flex flex-col items-center justify-center h-full gap-1 transition-all cursor-pointer ${
                  isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                }`}>
                  {isActive && (
                    <span className="absolute top-0 left-1/2 -translate-x-1/2 w-10 h-0.5 bg-primary rounded-full" />
                  )}
                  <item.icon className={`w-5 h-5 transition-transform ${isActive ? "scale-110" : ""}`} />
                  <span className="text-[9px] font-mono uppercase tracking-wide">{item.name}</span>
                </span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
