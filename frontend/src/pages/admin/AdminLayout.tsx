import React, { useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import {
  LayoutDashboard, Users, Wallet, Trophy, Shield, Brain,
  Store, Settings, FileText, Activity, Menu, X, LogOut, ChevronLeft, ChevronRight
} from "lucide-react";

const NAV_ITEMS = [
  { path: "/admin",             label: "Dashboard",           icon: LayoutDashboard },
  { path: "/admin/users",       label: "Users",               icon: Users },
  { path: "/admin/wallet",      label: "Wallets & Finance",   icon: Wallet },
  { path: "/admin/matches",     label: "Matches & Predictions", icon: Trophy },
  { path: "/admin/validators",  label: "Validators",          icon: Shield },
  { path: "/admin/models",      label: "AI Models",           icon: Brain },
  { path: "/admin/marketplace", label: "Marketplace",         icon: Store },
  { path: "/admin/config",      label: "Platform Config",     icon: Settings },
  { path: "/admin/audit",       label: "Audit Log",           icon: FileText },
  { path: "/admin/system",      label: "System Health",       icon: Activity },
];

interface AdminLayoutProps {
  children: React.ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const [location, navigate] = useLocation();
  const { user, logout } = useAuth() as any;
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);

  const isActive = (path: string) => {
    if (path === "/admin") return location === "/admin";
    return location.startsWith(path);
  };

  const currentLabel = NAV_ITEMS.find((i) => isActive(i.path))?.label ?? "Admin";

  return (
    <div className="flex h-screen overflow-hidden bg-[#060a0f] font-['Outfit']">

      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex flex-col border-r border-white/8 bg-[#0b1018]
          transition-all duration-200 ease-in-out
          md:relative md:z-auto
          ${sidebarOpen ? "translate-x-0 w-60" : "-translate-x-full md:translate-x-0"}
          ${desktopCollapsed ? "md:w-[52px]" : "md:w-56"}
        `}
      >
        {/* Logo row */}
        <div className="flex h-14 items-center gap-3 border-b border-white/8 px-3.5 shrink-0">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#00E676]/10 border border-[#00E676]/20">
            <span className="text-[#00E676] text-sm font-bold leading-none">⬡</span>
          </div>
          {(!desktopCollapsed || sidebarOpen) && (
            <div className="flex flex-col leading-none overflow-hidden">
              <span className="font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-[0.15em] text-white/90 truncate">
                VIT Admin
              </span>
              <span className="font-['JetBrains_Mono'] text-[9px] text-white/30 uppercase tracking-widest">
                Control Panel
              </span>
            </div>
          )}
          {/* Close on mobile */}
          <button
            className="ml-auto md:hidden text-white/40 hover:text-white/80 p-1"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={16} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2 space-y-0.5 px-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <button
                key={item.path}
                onClick={() => { navigate(item.path); setSidebarOpen(false); }}
                className={`
                  group flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-all duration-150
                  ${active
                    ? "bg-[#00E676]/10 border border-[#00E676]/20 text-[#00E676]"
                    : "border border-transparent text-white/40 hover:bg-white/5 hover:text-white/75"
                  }
                `}
              >
                <Icon size={15} className={`shrink-0 ${active ? "text-[#00E676]" : "text-white/35 group-hover:text-white/60"}`} />
                {(!desktopCollapsed || sidebarOpen) && (
                  <span className="font-['Outfit'] text-[11.5px] font-medium leading-none truncate">
                    {item.label}
                  </span>
                )}
                {active && (!desktopCollapsed || sidebarOpen) && (
                  <span className="ml-auto w-1 h-1 rounded-full bg-[#00E676] shrink-0" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom: collapse toggle (desktop) + logout */}
        <div className="border-t border-white/8 shrink-0">
          {/* Collapse toggle desktop */}
          <button
            onClick={() => setDesktopCollapsed((c) => !c)}
            className="hidden md:flex w-full items-center gap-2.5 px-3.5 py-2.5 text-xs text-white/25 hover:text-white/60 transition-colors"
          >
            {desktopCollapsed
              ? <ChevronRight size={13} />
              : <><ChevronLeft size={13} /><span className="font-['Outfit'] text-[10px]">Collapse</span></>
            }
          </button>
          {(!desktopCollapsed || sidebarOpen) && (
            <button
              onClick={logout}
              className="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-xs text-white/25 hover:text-red-400/70 transition-colors border-t border-white/5"
            >
              <LogOut size={13} />
              <span className="font-['Outfit'] text-[10px]">Sign Out</span>
            </button>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Topbar */}
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-white/8 bg-[#0b1018] px-4">
          {/* Mobile hamburger */}
          <button
            className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg bg-white/5 text-white/50 hover:text-white/80 shrink-0"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={16} />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <span className="font-['JetBrains_Mono'] text-[10px] text-white/20 uppercase tracking-widest hidden sm:block">
              vit://admin/
            </span>
            <h1 className="font-['Barlow_Condensed'] text-sm font-semibold uppercase tracking-[0.12em] text-white/70 truncate">
              {currentLabel}
            </h1>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2 shrink-0">
            <span className="hidden sm:block font-['Outfit'] text-xs text-white/30 truncate max-w-[120px]">
              {user?.username ?? user?.email}
            </span>
            <span className="rounded-md border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-2 py-0.5 font-['JetBrains_Mono'] text-[9px] font-semibold uppercase tracking-wider text-[#8B5CF6] shrink-0">
              {user?.admin_role ?? "SUPER"}
            </span>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
