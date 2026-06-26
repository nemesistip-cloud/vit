import React, { useEffect, useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminKPICard } from "@/components/admin/AdminKPICard";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminTable } from "@/components/admin/AdminTable";
import { useAdminData, apiFetch } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";

export default function AdminDashboard() {
  const { data: health, loading: healthLoading, refetch } = useAdminData<any>("/api/admin/system/health");
  const { data: metrics, loading: metricsLoading } = useAdminData<any>("/api/admin/system/metrics");
  const { data: auditData, loading: auditLoading } = useAdminData<any>("/api/admin/audit-log", { limit: 10, page: 1 });
  const { data: usersData } = useAdminData<any>("/api/admin/users", { limit: 1 });
  const { data: withdrawalData } = useAdminData<any>("/api/admin/wallet/withdrawal-queue");
  const { data: vitPrice } = useAdminData<any>("/api/admin/wallet/vitcoin-price");
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

  const auditLogs = auditData?.logs ?? [];

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">
        {/* KPI Grid */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <AdminKPICard
            label="Total Users"
            value={usersData?.total ?? "—"}
            color="green"
            loading={!usersData}
          />
          <AdminKPICard
            label="Models Ready"
            value={health?.models_ready ?? "—"}
            color="purple"
            loading={healthLoading}
          />
          <AdminKPICard
            label="VITCoin Price"
            value={vitPrice ? `$${Number(vitPrice.current_price_usd).toFixed(4)}` : "—"}
            color="yellow"
            loading={!vitPrice}
          />
          <AdminKPICard
            label="Open Withdrawals"
            value={withdrawalData?.length ?? "—"}
            color="red"
            loading={!withdrawalData}
          />
          <AdminKPICard
            label="Total Predictions"
            value={health?.total_predictions?.toLocaleString() ?? "—"}
            color="blue"
            loading={healthLoading}
          />
          <AdminKPICard
            label="24h Requests"
            value={metrics?.requests_24h?.toLocaleString() ?? "—"}
            color="green"
            loading={metricsLoading}
          />
          <AdminKPICard
            label="Error Rate"
            value={metrics ? `${metrics.error_rate_pct}%` : "—"}
            color={metrics?.error_rate_pct > 5 ? "red" : "green"}
            loading={metricsLoading}
          />
          <AdminKPICard
            label="Avg Response"
            value={metrics ? `${Math.round(metrics.avg_response_ms)}ms` : "—"}
            color="purple"
            loading={metricsLoading}
          />
        </div>

        {/* Status + Quick Actions */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* System Status */}
          <div className="rounded-xl border border-white/10 bg-[#0d1117] p-5">
            <h2 className="mb-4 font-['Barlow_Condensed'] text-sm font-semibold uppercase tracking-widest text-white/50">
              System Status
            </h2>
            {healthLoading ? (
              <div className="h-24 animate-pulse rounded-lg bg-white/5" />
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Database", status: health?.database?.status ?? "unknown" },
                  { label: "Redis", status: health?.redis?.status ?? "unknown" },
                  { label: "AI Engine", status: (health?.models_ready ?? 0) > 0 ? "active" : "degraded" },
                  { label: "Tachyon", status: (health?.tachyon_nodes ?? 0) > 0 ? "active" : "degraded" },
                ].map((s) => (
                  <div key={s.label} className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2">
                    <span className="font-['Outfit'] text-xs text-white/60">{s.label}</span>
                    <AdminStatusPill status={s.status} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="rounded-xl border border-white/10 bg-[#0d1117] p-5">
            <h2 className="mb-4 font-['Barlow_Condensed'] text-sm font-semibold uppercase tracking-widest text-white/50">
              Quick Actions
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={handleRetrainAll}
                className="rounded-lg border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-4 py-3 font-['Outfit'] text-xs text-[#8B5CF6] transition-colors hover:bg-[#8B5CF6]/20"
              >
                🤖 Retrain All
              </button>
              <button
                onClick={handleFlushCache}
                disabled={flushLoading}
                className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-['Outfit'] text-xs text-red-400 transition-colors hover:bg-red-500/20 disabled:opacity-40"
              >
                🗑 {flushLoading ? "Flushing…" : "Flush Cache"}
              </button>
              <button
                onClick={() => adminApi.exportUsers().then((b) => {
                  const url = URL.createObjectURL(b);
                  const a = document.createElement("a"); a.href = url; a.download = "users.csv"; a.click();
                  URL.revokeObjectURL(url);
                })}
                className="rounded-lg border border-[#00E676]/30 bg-[#00E676]/10 px-4 py-3 font-['Outfit'] text-xs text-[#00E676] transition-colors hover:bg-[#00E676]/20"
              >
                📤 Export Users
              </button>
              <button
                onClick={refetch}
                className="rounded-lg border border-white/10 bg-white/5 px-4 py-3 font-['Outfit'] text-xs text-white/50 transition-colors hover:bg-white/10"
              >
                🔄 Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Recent Audit Log */}
        <div className="rounded-xl border border-white/10 bg-[#0d1117] p-5">
          <h2 className="mb-4 font-['Barlow_Condensed'] text-sm font-semibold uppercase tracking-widest text-white/50">
            Recent Admin Activity
          </h2>
          <AdminTable
            loading={auditLoading}
            data={auditLogs}
            pagination={{ page: 1, total: auditLogs.length, limit: 10, onChange: () => {} }}
            columns={[
              { key: "created_at", label: "Time", render: (v) => v ? new Date(v).toLocaleString() : "—" },
              { key: "admin_id", label: "Admin", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">#{v}</span> },
              { key: "action", label: "Action", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-[#00E676]">{v}</span> },
              { key: "target_type", label: "Target" },
              { key: "target_id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{v ?? "—"}</span> },
              { key: "ip_address", label: "IP", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{v ?? "—"}</span> },
            ]}
            emptyMessage="No recent admin activity"
          />
        </div>
      </div>
    </AdminLayout>
  );
}
