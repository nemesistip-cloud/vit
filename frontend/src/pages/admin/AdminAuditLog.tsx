import React, { useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminJsonDiff } from "@/components/admin/AdminJsonDiff";
import { useAdminData } from "@/hooks/useAdminData";

const ACTION_GROUPS = [
  "user.", "wallet.", "match.", "config.", "model.", "system.", "validator.", "appeal.", "withdrawal.", "vitcoin."
];

export default function AdminAuditLog() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [targetType, setTargetType] = useState("");
  const [adminIdFilter, setAdminIdFilter] = useState("");

  const params: Record<string, any> = { page, limit: 50 };
  if (action) params.action = action;
  if (targetType) params.target_type = targetType;
  if (adminIdFilter) params.admin_id = adminIdFilter;

  const { data, loading } = useAdminData<any>("/api/admin/audit-log", params);

  const [selected, setSelected] = useState<any>(null);

  const logs = data?.logs ?? [];

  const actionColor = (a: string) => {
    if (a.includes("delete") || a.includes("slash") || a.includes("debit")) return "text-red-400";
    if (a.includes("create") || a.includes("credit") || a.includes("approve")) return "text-[#00E676]";
    if (a.includes("update") || a.includes("override")) return "text-yellow-400";
    return "text-white/60";
  };

  return (
    <AdminLayout>
      <div className="flex flex-col gap-4">
        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <input
            value={adminIdFilter}
            onChange={(e) => { setAdminIdFilter(e.target.value); setPage(1); }}
            placeholder="Filter by admin ID…"
            className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 font-['JetBrains_Mono'] text-sm text-white placeholder:text-white/30 focus:outline-none"
          />
          <select value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }}
            className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
            <option value="">All actions</option>
            {ACTION_GROUPS.map((g) => <option key={g} value={g}>{g}*</option>)}
          </select>
          <select value={targetType} onChange={(e) => { setTargetType(e.target.value); setPage(1); }}
            className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
            <option value="">All resources</option>
            {["user", "match", "platform_config", "model", "validator", "validator_appeal", "withdrawal", "vitcoin_price"].map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        {/* Table */}
        <AdminTable
          loading={loading}
          data={logs}
          onRowClick={setSelected}
          pagination={{ page, total: data?.total ?? 0, limit: 50, onChange: setPage }}
          columns={[
            { key: "created_at", label: "Time", render: (v) => v ? new Date(v).toLocaleString() : "—" },
            { key: "admin_id", label: "Admin", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">#{v}</span> },
            {
              key: "action", label: "Action",
              render: (v) => <span className={`font-['JetBrains_Mono'] text-xs ${actionColor(v)}`}>{v}</span>,
            },
            { key: "target_type", label: "Resource", render: (v) => <span className="text-xs text-white/50">{v ?? "—"}</span> },
            { key: "target_id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{v ?? "—"}</span> },
            { key: "ip_address", label: "IP", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/30">{v ?? "—"}</span> },
            {
              key: "before", label: "Δ Changes",
              render: (v, row) => {
                const hasChanges = row.before || row.after;
                return hasChanges ? (
                  <span className="rounded bg-yellow-400/10 px-2 py-0.5 font-['JetBrains_Mono'] text-xs text-yellow-400">diff</span>
                ) : (
                  <span className="text-white/20 text-xs">—</span>
                );
              },
            },
          ]}
          emptyMessage="No audit log entries"
        />
      </div>

      {/* Detail Slide-over */}
      <AdminModal isOpen={!!selected} onClose={() => setSelected(null)} title={`Audit: ${selected?.action}`} width="max-w-3xl">
        {selected && (
          <div className="flex flex-col gap-5">
            <div className="grid grid-cols-3 gap-3 rounded-lg bg-white/5 p-4 text-sm">
              {[
                { label: "Admin ID", value: `#${selected.admin_id}` },
                { label: "Action", value: <span className={`font-['JetBrains_Mono'] ${actionColor(selected.action)}`}>{selected.action}</span> },
                { label: "Time", value: selected.created_at ? new Date(selected.created_at).toLocaleString() : "—" },
                { label: "Resource", value: selected.target_type ?? "—" },
                { label: "Target ID", value: <span className="font-['JetBrains_Mono'] text-xs">{selected.target_id ?? "—"}</span> },
                { label: "IP Address", value: <span className="font-['JetBrains_Mono'] text-xs">{selected.ip_address ?? "—"}</span> },
              ].map(({ label, value }) => (
                <div key={label}><span className="text-xs text-white/40">{label}</span><p className="mt-0.5 text-white/80">{value}</p></div>
              ))}
            </div>

            {(selected.before || selected.after) && (
              <div>
                <p className="mb-3 font-['Barlow_Condensed'] text-xs font-semibold uppercase tracking-widest text-white/40">Change Diff</p>
                <AdminJsonDiff before={selected.before} after={selected.after} />
              </div>
            )}
          </div>
        )}
      </AdminModal>
    </AdminLayout>
  );
}
