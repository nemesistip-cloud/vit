import React, { useState, useMemo } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminJsonDiff } from "@/components/admin/AdminJsonDiff";
import { useAdminData } from "@/hooks/useAdminData";
import {
  FileText, Shield, Search, Filter, History,
  Activity, ArrowRight, User, Terminal, Globe,
  Clock, Database, Lock
} from "lucide-react";

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

  const logs = useMemo(() => data?.logs ?? [], [data]);

  const actionColor = (a: string) => {
    if (a.includes("delete") || a.includes("slash") || a.includes("debit") || a.includes("reject")) return "text-red-400";
    if (a.includes("create") || a.includes("credit") || a.includes("approve") || a.includes("reinstate")) return "text-[#00E676]";
    if (a.includes("update") || a.includes("override") || a.includes("set_result")) return "text-yellow-400";
    return "text-cyan-400/60";
  };

  const getIcon = (resource: string) => {
    switch(resource) {
      case 'user': return <User size={12} />;
      case 'platform_config': return <Database size={12} />;
      case 'model': return <Activity size={12} />;
      case 'validator': return <Shield size={12} />;
      case 'vitcoin_price': return <Lock size={12} />;
      default: return <FileText size={12} />;
    }
  };

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">

        {/* ── Header ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-sm bg-white/5 border border-white/10">
              <FileText size={20} className="text-white/60" />
            </div>
            <div>
              <h1 className="font-['Barlow_Condensed'] text-xl font-bold uppercase tracking-wider text-white">Global Audit Ledger</h1>
              <p className="font-['Outfit'] text-xs text-white/40">Immutable record of all administrative operations, security events, and state mutations</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-sm border border-[#00E676]/20 bg-[#00E676]/5">
             <div className="w-1.5 h-1.5 rounded-full bg-[#00E676] animate-pulse" />
             <span className="font-['JetBrains_Mono'] text-[9px] text-[#00E676] font-bold uppercase tracking-widest">ledger_active</span>
          </div>
        </div>

        {/* ── Filters ── */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-4 relative">
             <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" />
             <input
               value={adminIdFilter}
               onChange={(e) => { setAdminIdFilter(e.target.value); setPage(1); }}
               placeholder="Filter by Admin Identifier..."
               className="w-full rounded-sm border border-white/10 bg-white/5 pl-9 pr-4 py-2.5 font-['Outfit'] text-xs text-white placeholder:text-white/20 focus:border-white/30 focus:outline-none"
             />
          </div>
          <div className="md:col-span-4">
            <select value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }}
              className="w-full rounded-sm border border-white/10 bg-[#0d1117] px-3 py-2.5 font-['Outfit'] text-xs text-white/60 focus:outline-none">
              <option value="">ALL ACTION GROUPS</option>
              {ACTION_GROUPS.map((g) => <option key={g} value={g}>{g.toUpperCase()}*</option>)}
            </select>
          </div>
          <div className="md:col-span-4">
            <select value={targetType} onChange={(e) => { setTargetType(e.target.value); setPage(1); }}
              className="w-full rounded-sm border border-white/10 bg-[#0d1117] px-3 py-2.5 font-['Outfit'] text-xs text-white/60 focus:outline-none">
              <option value="">ALL RESOURCES</option>
              {["user", "match", "platform_config", "model", "validator", "validator_appeal", "withdrawal", "vitcoin_price"].map((r) => (
                <option key={r} value={r}>{r.toUpperCase().replace('_', ' ')}</option>
              ))}
            </select>
          </div>
        </div>

        {/* ── Table ── */}
        <AdminTable
          loading={loading}
          data={logs}
          onRowClick={setSelected}
          pagination={{ page, total: data?.total ?? 0, limit: 50, onChange: setPage }}
          columns={[
            { key: "created_at", label: "Timestamp", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/30">{v ? new Date(v).toLocaleString() : "—"}</span> },
            { key: "admin_id", label: "Authority", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-purple-400 font-bold">#ADM_${v}</span> },
            {
              key: "action", label: "Protocol Operation",
              render: (v) => <span className={`font-['JetBrains_Mono'] text-[10px] font-bold uppercase tracking-tighter ${actionColor(v)}`}>{v}</span>,
            },
            { key: "target_type", label: "Resource", render: (v) => (
               <div className="flex items-center gap-2">
                  <span className="text-white/20">{getIcon(v)}</span>
                  <span className="text-[10px] text-white/40 uppercase font-bold tracking-widest">{v ?? "—"}</span>
               </div>
            )},
            { key: "target_id", label: "Entity Ref", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/30 italic">{v ?? "—"}</span> },
            { key: "ip_address", label: "Source IP", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/20">{v ?? "—"}</span> },
            {
              key: "before", label: "Mutation",
              render: (v, row) => {
                const hasChanges = row.before || row.after;
                return hasChanges ? (
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-sm border border-yellow-400/20 bg-yellow-400/5 text-[9px] font-bold text-yellow-400 uppercase tracking-widest">
                    <Activity size={8} /> diff
                  </div>
                ) : (
                  <span className="text-white/5 text-[10px] uppercase font-bold tracking-widest">static</span>
                );
              },
            },
          ]}
          emptyMessage="No audit trail events detected"
        />
      </div>

      {/* ── Mutation Analysis Slide-over ── */}
      <AdminModal isOpen={!!selected} onClose={() => setSelected(null)} title={`Mutation Analysis — ${selected?.action?.toUpperCase()}`} width="max-w-4xl">
        {selected && (
          <div className="flex flex-col gap-6 p-2">
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Administrative Entity", value: `#ADM_${selected.admin_id}` },
                { label: "Operation Signature", value: <span className={`font-['JetBrains_Mono'] ${actionColor(selected.action)}`}>{selected.action}</span> },
                { label: "Temporal Reference", value: selected.created_at ? new Date(selected.created_at).toLocaleString() : "—" },
                { label: "Target Resource", value: selected.target_type ?? "—" },
                { label: "Resource Identifier", value: <span className="font-['JetBrains_Mono'] text-xs">{selected.target_id ?? "—"}</span> },
                { label: "Origin Gateway", value: <span className="font-['JetBrains_Mono'] text-xs">{selected.ip_address ?? "—"}</span> },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-sm bg-white/5 p-4 flex flex-col gap-1 border border-white/5">
                   <span className="text-[9px] font-bold text-white/30 uppercase tracking-[0.2em]">{label}</span>
                   <div className="text-xs font-bold text-white/80">{value}</div>
                </div>
              ))}
            </div>

            {(selected.before || selected.after) && (
              <div className="rounded-sm border border-white/10 bg-white/[0.01] p-6">
                <div className="flex items-center gap-2 mb-6">
                   <Terminal size={14} className="text-white/20" />
                   <h3 className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-white/40">State Delta Analysis</h3>
                </div>
                <div className="rounded-sm bg-black/20 p-2 border border-white/5">
                   <AdminJsonDiff before={selected.before} after={selected.after} />
                </div>
              </div>
            )}

            <div className="rounded-sm border border-white/10 bg-white/[0.01] p-6">
               <h3 className="font-['Barlow_Condensed'] text-[10px] font-bold uppercase tracking-[0.2em] text-white/40 mb-4 flex items-center gap-2">
                  <Globe size={12} /> Origin Metadata
               </h3>
               <div className="bg-black/40 p-4 rounded-sm font-['JetBrains_Mono'] text-[10px] text-white/30 leading-relaxed">
                  AUTH_METHOD: JWT_BEARER<br />
                  ENCRYPTION: AES_256_GCM<br />
                  USER_AGENT: Mozilla/5.0 (Terminal/Admin-Core-v5.5)
               </div>
            </div>
          </div>
        )}
      </AdminModal>
    </AdminLayout>
  );
}
