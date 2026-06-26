import React, { useEffect, useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminTable } from "@/components/admin/AdminTable";
import { useAdminData, apiFetch } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";
import {
  Users, Cpu, DollarSign, AlertCircle, BarChart2,
  Activity, Gauge, Clock, RefreshCw, Trash2, Download,
  RotateCcw, Zap
} from "lucide-react";

interface KPIProps {
  label: string;
  value: string | number;
  icon: React.ElementType;
  accent: "green" | "purple" | "red" | "yellow" | "blue";
  loading?: boolean;
  delta?: string;
  deltaPositive?: boolean;
}

const ACCENT = {
  green:  { border: "border-[#00E676]/15", bg: "bg-[#00E676]/5",  text: "text-[#00E676]",  icon: "bg-[#00E676]/10 text-[#00E676]"  },
  purple: { border: "border-[#8B5CF6]/15", bg: "bg-[#8B5CF6]/5",  text: "text-[#8B5CF6]",  icon: "bg-[#8B5CF6]/10 text-[#8B5CF6]"  },
  red:    { border: "border-red-500/15",   bg: "bg-red-500/5",    text: "text-red-400",    icon: "bg-red-500/10 text-red-400"    },
  yellow: { border: "border-yellow-400/15",bg: "bg-yellow-400/5", text: "text-yellow-400", icon: "bg-yellow-400/10 text-yellow-400" },
  blue:   { border: "border-blue-400/15",  bg: "bg-blue-400/5",   text: "text-blue-400",   icon: "bg-blue-400/10 text-blue-400"   },
};

function KPICard({ label, value, icon: Icon, accent, loading, delta, deltaPositive }: KPIProps) {
  const c = ACCENT[accent];
  return (
    <div className={`rounded-xl border ${c.border} ${c.bg} p-4 flex flex-col gap-3`}>
      <div className="flex items-center justify-between">
        <p className="font-['Outfit'] text-[10px] font-semibold uppercase tracking-[0.15em] text-white/40 leading-none">{label}</p>
        <div className={`rounded-lg p-1.5 ${c.icon}`}>
          <Icon size={12} />
        </div>
      </div>
      {loading ? (
        <div className="h-8 w-20 animate-pulse rounded-lg bg-white/8" />
      ) : (
        <p className={`font-['JetBrains_Mono'] text-2xl font-bold leading-none ${c.text} tabular-nums`}>
          {value}
        </p>
      )}
      {delta && !loading && (
        <p className={`font-['JetBrains_Mono'] text-[10px] leading-none ${deltaPositive ? "text-[#00E676]" : "text-red-400"}`}>
          {delta}
        </p>
      )}
    </div>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="h-px flex-1 bg-white/6" />
      <p className="font-['Barlow_Condensed'] text-[10px] font-semibold uppercase tracking-[0.2em] text-white/30 px-2">{children}</p>
      <div className="h-px flex-1 bg-white/6" />
    </div>
  );
}

export default function AdminDashboard() {
  const { data: health,      loading: healthLoading, refetch } = useAdminData<any>("/api/admin/system/health");
  const { data: metrics,     loading: metricsLoading }          = useAdminData<any>("/api/admin/system/metrics");
  const { data: auditData,   loading: auditLoading }            = useAdminData<any>("/api/admin/audit-log", { limit: 10, page: 1 });
  const { data: usersData }   = useAdminData<any>("/api/admin/users", { limit: 1 });
  const { data: withdrawalData } = useAdminData<any>("/api/admin/wallet/withdrawal-queue");
  const { data: vitPrice }    = useAdminData<any>("/api/admin/wallet/vitcoin-price");
  const [flushLoading, setFlushLoading] = useState(false);

  useEffect(() => {
    const id = setInterval(refetch, 30_000);
    return () => clearInterval(id);
  }, [refetch]);

  const handleFlushCache = async () => {
    setFlushLoading(true);
    try {
      await adminApi.flushCache();
      toast.success("Cache flushed");
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setFlushLoading(false);
    }
  };

  const handleRetrainAll = async () => {
    try {
      await adminApi.retrainAll();
      toast.success("Full retrain queued");
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleExportUsers = async () => {
    try {
      const blob = await adminApi.exportUsers();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "vit_users.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const auditLogs = auditData?.logs ?? [];

  const statusItems = [
    { label: "Database",   status: health?.database?.status ?? "unknown" },
    { label: "Redis",      status: health?.redis?.status ?? "unknown" },
    { label: "AI Engine",  status: (health?.models_ready ?? 0) > 0 ? "active" : "degraded" },
    { label: "Tachyon",    status: (health?.tachyon_nodes ?? 0) > 0 ? "active" : "degraded" },
  ];

  const quickActions = [
    { label: "Retrain All",   icon: Zap,        color: "border-[#8B5CF6]/25 bg-[#8B5CF6]/8 text-[#8B5CF6] hover:bg-[#8B5CF6]/15", onClick: handleRetrainAll, disabled: false },
    { label: flushLoading ? "Flushing…" : "Flush Cache", icon: Trash2, color: "border-red-500/25 bg-red-500/8 text-red-400 hover:bg-red-500/15 disabled:opacity-40", onClick: handleFlushCache, disabled: flushLoading },
    { label: "Export Users",  icon: Download,   color: "border-[#00E676]/25 bg-[#00E676]/8 text-[#00E676] hover:bg-[#00E676]/15", onClick: handleExportUsers, disabled: false },
    { label: "Refresh",       icon: RefreshCw,  color: "border-white/10 bg-white/4 text-white/40 hover:bg-white/8", onClick: refetch, disabled: false },
  ];

  return (
    <AdminLayout>
      <div className="flex flex-col gap-5 max-w-6xl">

        {/* ── KPI Grid ── */}
        <div>
          <SectionHeader>System Overview</SectionHeader>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KPICard label="Total Users"       value={usersData?.total ?? "—"}     icon={Users}      accent="green"  loading={!usersData} />
            <KPICard label="Models Ready"      value={health?.models_ready ?? "—"} icon={Cpu}        accent="purple" loading={healthLoading} />
            <KPICard label="VIT Price"         value={vitPrice ? `$${Number(vitPrice.current_price_usd).toFixed(4)}` : "—"} icon={DollarSign} accent="yellow" loading={!vitPrice} />
            <KPICard label="Open Withdrawals"  value={withdrawalData?.length ?? "—"} icon={AlertCircle} accent="red" loading={!withdrawalData} />
            <KPICard label="Total Predictions" value={health?.total_predictions?.toLocaleString() ?? "—"} icon={BarChart2} accent="blue" loading={healthLoading} />
            <KPICard label="24h Requests"      value={metrics?.requests_24h?.toLocaleString() ?? "—"} icon={Activity} accent="green" loading={metricsLoading} />
            <KPICard label="Error Rate"        value={metrics ? `${metrics.error_rate_pct}%` : "—"} icon={Gauge} accent={metrics?.error_rate_pct > 5 ? "red" : "green"} loading={metricsLoading} />
            <KPICard label="Avg Response"      value={metrics ? `${Math.round(metrics.avg_response_ms)}ms` : "—"} icon={Clock} accent="purple" loading={metricsLoading} />
          </div>
        </div>

        {/* ── Status + Actions ── */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* System Status */}
          <div className="rounded-xl border border-white/8 bg-[#0b1018] p-5">
            <SectionHeader>System Status</SectionHeader>
            {healthLoading ? (
              <div className="space-y-2">
                {[0,1,2,3].map(i => <div key={i} className="h-10 animate-pulse rounded-lg bg-white/5" />)}
              </div>
            ) : (
              <div className="space-y-2">
                {statusItems.map((s) => (
                  <div key={s.label} className="flex items-center justify-between rounded-lg bg-white/4 border border-white/5 px-3.5 py-2.5">
                    <span className="font-['Outfit'] text-xs text-white/55">{s.label}</span>
                    <AdminStatusPill status={s.status} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="rounded-xl border border-white/8 bg-[#0b1018] p-5">
            <SectionHeader>Quick Actions</SectionHeader>
            <div className="grid grid-cols-2 gap-2.5">
              {quickActions.map((action) => {
                const Icon = action.icon;
                return (
                  <button
                    key={action.label}
                    onClick={action.onClick}
                    disabled={action.disabled}
                    className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-3 font-['Outfit'] text-xs font-medium transition-all ${action.color}`}
                  >
                    <Icon size={13} />
                    <span>{action.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Audit Log ── */}
        <div className="rounded-xl border border-white/8 bg-[#0b1018] p-5">
          <SectionHeader>Recent Admin Activity</SectionHeader>
          <AdminTable
            loading={auditLoading}
            data={auditLogs}
            pagination={{ page: 1, total: auditLogs.length, limit: 10, onChange: () => {} }}
            columns={[
              { key: "created_at", label: "Time",   render: (v) => v ? <span className="font-['JetBrains_Mono'] text-[10px] text-white/40">{new Date(v).toLocaleString()}</span> : "—" },
              { key: "admin_id",   label: "Admin",  render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-[#8B5CF6]">#{v}</span> },
              { key: "action",     label: "Action", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-[#00E676] uppercase tracking-wider">{v}</span> },
              { key: "target_type",label: "Target", render: (v) => <span className="font-['Outfit'] text-xs text-white/50">{v ?? "—"}</span> },
              { key: "target_id",  label: "ID",     render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/35">{v ?? "—"}</span> },
              { key: "ip_address", label: "IP",     render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/25">{v ?? "—"}</span> },
            ]}
            emptyMessage="No recent admin activity"
          />
        </div>
      </div>
    </AdminLayout>
  );
}
