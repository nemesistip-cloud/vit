import React, { useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/lib/auth";

const NAV_ITEMS = [
  { path: "/admin",            label: "Dashboard",        icon: "⬛" },
  { path: "/admin/users",      label: "Users",            icon: "👥" },
  { path: "/admin/wallet",     label: "Wallets & Finance",icon: "💰" },
  { path: "/admin/matches",    label: "Matches & Predictions", icon: "⚽" },
  { path: "/admin/validators", label: "Validators",       icon: "🛡" },
  { path: "/admin/models",     label: "AI Models",        icon: "🤖" },
  { path: "/admin/marketplace",label: "Marketplace",      icon: "🏪" },
  { path: "/admin/config",     label: "Platform Config",  icon: "⚙️" },
  { path: "/admin/audit",      label: "Audit Log",        icon: "📋" },
  { path: "/admin/system",     label: "System Health",    icon: "💚" },
];

interface AdminLayoutProps {
  children: React.ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const [location, navigate] = useLocation();
  const { user, logout } = useAuth() as any;
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const isActive = (path: string) => {
    if (path === "/admin") return location === "/admin";
    return location.startsWith(path);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#080c12] font-['Outfit']">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r border-white/10 bg-[#0d1117] transition-all duration-200 ${
          sidebarOpen ? "w-56" : "w-14"
        } shrink-0`}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-3 border-b border-white/10 px-4">
          <span className="text-[#00E676] text-lg font-bold shrink-0">⬡</span>
          {sidebarOpen && (
            <span className="font-['Barlow_Condensed'] text-sm font-semibold uppercase tracking-widest text-white/70">
              VIT Admin
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-3">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                isActive(item.path)
                  ? "bg-[#00E676]/10 text-[#00E676]"
                  : "text-white/50 hover:bg-white/5 hover:text-white/80"
              }`}
            >
              <span className="shrink-0 text-base leading-none">{item.icon}</span>
              {sidebarOpen && (
                <span className="truncate font-['Outfit'] text-xs">{item.label}</span>
              )}
            </button>
          ))}
        </nav>

        {/* Toggle */}
        <button
          onClick={() => setSidebarOpen((s) => !s)}
          className="border-t border-white/10 px-4 py-3 text-left text-xs text-white/30 hover:text-white/60"
        >
          {sidebarOpen ? "← Collapse" : "→"}
        </button>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex h-14 items-center justify-between border-b border-white/10 bg-[#0d1117] px-6">
          <h1 className="font-['Barlow_Condensed'] text-base font-semibold uppercase tracking-widest text-white/60">
            {NAV_ITEMS.find((i) => isActive(i.path))?.label ?? "Admin"}
          </h1>
          <div className="flex items-center gap-4">
            <span className="font-['Outfit'] text-xs text-white/40">
              {user?.username ?? user?.email}
            </span>
            <span className="rounded-full border border-[#8B5CF6]/40 bg-[#8B5CF6]/10 px-2.5 py-0.5 font-['JetBrains_Mono'] text-[10px] font-semibold uppercase tracking-wider text-[#8B5CF6]">
              {user?.admin_role ?? "admin"}
            </span>
            <button
              onClick={logout}
              className="rounded-lg px-3 py-1.5 font-['Outfit'] text-xs text-white/40 hover:bg-white/10 hover:text-white/80"
            >
              Logout
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
