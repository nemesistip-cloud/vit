import React, { useEffect, useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminKPICard } from "@/components/admin/AdminKPICard";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";

export default function AdminSystemHealth() {
  const { user } = useAuth() as any;
  const isSuperAdmin = user?.admin_role === "super_admin";

  const { data: health, loading: hLoading, refetch } = useAdminData<any>("/api/admin/system/health");
  const { data: metrics, loading: mLoading } = useAdminData<any>("/api/admin/system/metrics");

  const [flushConfirm, setFlushConfirm] = useState(false);
  const [flushing, setFlushing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(refetch, 15_000);
    return () => clearInterval(id);
  }, [refetch, autoRefresh]);

  const handleFlush = async () => {
    setFlushing(true);
    try {
      const r = await adminApi.flushCache();
      toast.success(`Cache flushed — ${(r as any).keys_flushed ?? 0} keys removed`);
      setFlushConfirm(false);
    } catch (e: any) { toast.error(e.message); }
    finally { setFlushing(false); }
  };

  const res = health?.resources ?? {};
  const cpuPct = res.cpu_pct ?? 0;
  const ramPct = res.ram_total_gb > 0 ? (res.ram_used_gb / res.ram_total_gb) * 100 : 0;
  const diskPct = res.disk_total_gb > 0 ? (res.disk_used_gb / res.disk_total_gb) * 100 : 0;

  const ServicesRow = ({ label, status }: { label: string; status: string }) => (
    <div className="flex items-center justify-between rounded-lg border border-white/5 bg-white/5 px-4 py-3">
      <span className="font-['Outfit'] text-sm text-white/70">{label}</span>
      <AdminStatusPill status={status} />
    </div>
  );

  const GaugeBar = ({ label, pct, color }: { label: string; pct: number; color: string }) => (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between">
        <span className="font-['Outfit'] text-xs text-white/50">{label}</span>
        <span className="font-['JetBrains_Mono'] text-xs" style={{ color }}>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">
        {/* Top Controls */}
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} className="accent-[#00E676]" />
            <span className="font-['Outfit'] text-sm text-white/50">Auto-refresh every 15s</span>
          </label>
          <div className="flex gap-3">
            <button onClick={refetch} className="rounded-lg border border-white/10 px-4 py-2 font-['Outfit'] text-xs text-white/50 hover:bg-white/10">
              🔄 Refresh Now
            </button>
            {isSuperAdmin && (
              <button onClick={() => setFlushConfirm(true)}
                className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 font-['Outfit'] text-xs text-red-400 hover:bg-red-500/20">
                🗑 Flush Cache
              </button>
            )}
          </div>
        </div>

        {/* KPI Row */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <AdminKPICard label="Overall Status" value={health?.status ?? "—"}
            color={health?.status === "ok" ? "green" : "red"} loading={hLoading} />
          <AdminKPICard label="Active Users" value={health?.active_users?.toLocaleString() ?? "—"}
            color="purple" loading={hLoading} />
          <AdminKPICard label="Models Ready" value={health?.models_ready ?? "—"} color="green" loading={hLoading} />
          <AdminKPICard label="Tachyon Nodes" value={health?.tachyon_nodes ?? "—"}
            color={(health?.tachyon_nodes ?? 0) > 0 ? "green" : "red"} loading={hLoading} />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Services */}
          <div className="rounded-xl border border-white/10 bg-[#0d1117] p-5">
            <h2 className="mb-4 font-['Barlow_Condensed'] text-sm font-semibold uppercase tracking-widest text-white/50">Services</h2>
            {hLoading ? (
              <div className="space-y-3">{[0,1,2,3].map(i => <div key={i} className="h-10 animate-pulse rounded-lg bg-white/5" />)}</div>
            ) : (
              <div className="space-y-2">
                <ServicesRow label="Database" status={health?.database?.status ?? "unknown"} />
                <ServicesRow label="Redis Cache" status={health?.redis?.status ?? "unknown"} />
                <ServicesRow label="AI Models" status={(health?.models_ready ?? 0) > 0 ? "active" : "degraded"} />
                <ServicesRow label="Tachyon VESS" status={(health?.tachyon_nodes ?? 0) > 0 ? "active" : "degraded"} />
              </div>
            )}
          </div>

          {/* Resources */}
          <div className="rounded-xl border border-white/10 bg-[#0d1117] p-5">
            <h2 className="mb-4 font-['Barlow_Condensed'] text-sm font-semibold uppercase tracking-widest text-white/50">Resource Usage</h2>
            {hLoading ? (
              <div className="space-y-4">{[0,1,2].map(i => <div key={i} className="h-8 animate-pulse rounded-lg bg-white/5" />)}</div>
            ) : (
              <div className="space-y-4">
                <GaugeBar label={`CPU — ${cpuPct.toFixed(1)}%`} pct={cpuPct}
                  color={cpuPct > 80 ? "#ef4444" : cpuPct > 60 ? "#facc15" : "#00E676"} />
                <GaugeBar label={`RAM — ${res.ram_used_gb?.toFixed(1) ?? 0} / ${res.ram_total_gb?.toFixed(1) ?? 0} GB`} pct={ramPct}
                  color={ramPct > 85 ? "#ef4444" : ramPct > 70 ? "#facc15" : "#8B5CF6"} />
                <GaugeBar label={`Disk — ${res.disk_used_gb?.toFixed(1) ?? 0} / ${res.disk_total_gb?.toFixed(1) ?? 0} GB`} pct={diskPct}
                  color={diskPct > 90 ? "#ef4444" : diskPct > 75 ? "#facc15" : "#60a5fa"} />
              </div>
            )}
          </div>
        </div>

        {/* Traffic Metrics */}
        <div className="rounded-xl border border-white/10 bg-[#0d1117] p-5">
          <h2 className="mb-4 font-['Barlow_Condensed'] text-sm font-semibold uppercase tracking-widest text-white/50">Traffic (24h)</h2>
          {mLoading ? (
            <div className="h-16 animate-pulse rounded-lg bg-white/5" />
          ) : (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {[
                { label: "Total Requests", value: metrics?.requests_24h?.toLocaleString() ?? "—" },
                { label: "Total Errors", value: metrics?.errors_24h?.toLocaleString() ?? "—" },
                { label: "Error Rate", value: metrics ? `${metrics.error_rate_pct}%` : "—" },
                { label: "Avg Response", value: metrics ? `${Math.round(metrics.avg_response_ms)}ms` : "—" },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-lg bg-white/5 p-3">
                  <p className="text-xs text-white/40 font-['Outfit'] uppercase tracking-widest">{label}</p>
                  <p className="mt-1 font-['JetBrains_Mono'] text-xl font-bold text-white/80">{value}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* App info */}
        <div className="rounded-xl border border-white/5 bg-white/5 px-5 py-3">
          <p className="font-['JetBrains_Mono'] text-xs text-white/30">
            VIT Network {health?.version ?? "v5.5.0"} · Running on port 5000
          </p>
        </div>
      </div>

      <AdminConfirmDialog
        isOpen={flushConfirm}
        onClose={() => setFlushConfirm(false)}
        onConfirm={handleFlush}
        title="Flush Cache"
        message="This will evict all admin:* and predictions:* keys from Redis. In-flight requests may see stale data briefly."
        confirmLabel="Flush Cache"
        dangerous
        loading={flushing}
      />
    </AdminLayout>
  );
}
