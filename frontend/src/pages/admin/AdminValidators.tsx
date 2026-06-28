import React, { useState, useMemo } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import {
  Shield, Network, UserCheck, AlertTriangle,
  Activity, Zap, TrendingUp, Search, RefreshCw,
  Slash, CheckCircle, XCircle, FileText
} from "lucide-react";

type Tab = "validators" | "appeals" | "performance";

export default function AdminValidators() {
  const [tab, setTab] = useState<Tab>("validators");
  const { user } = useAuth() as any;
  const isSuperAdmin = user?.admin_role === "super_admin";

  const { data: validators, loading: vLoading, refetch: refetchV } = useAdminData<any[]>("/api/admin/validators");
  const { data: appeals, loading: aLoading, refetch: refetchA } = useAdminData<any[]>("/api/admin/validators/appeals");

  const [selected, setSelected] = useState<any>(null);
  const [slashForm, setSlashForm] = useState({ amount: "", reason: "" });
  const [slashLoading, setSlashLoading] = useState(false);
  const [reinstateConfirm, setReinstateConfirm] = useState(false);

  const [appealSelected, setAppealSelected] = useState<any>(null);
  const [appealNote, setAppealNote] = useState("");
  const [appealLoading, setAppealLoading] = useState(false);

  const handleSlash = async () => {
    if (!selected || !slashForm.amount || !slashForm.reason) return;
    setSlashLoading(true);
    try {
      await adminApi.slashValidator(selected.id, { amount: Number(slashForm.amount), reason: slashForm.reason });
      toast.success("VALIDATOR_SLASH_EXECUTED");
      refetchV();
      setSelected(null);
      setSlashForm({ amount: "", reason: "" });
    } catch (e: any) { toast.error(e.message); }
    finally { setSlashLoading(false); }
  };

  const handleReinstate = async () => {
    if (!selected) return;
    try {
      await adminApi.reinstateValidator(selected.id);
      toast.success("VALIDATOR_REINSTATED");
      refetchV();
      setReinstateConfirm(false);
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAppealDecision = async (decision: "approved" | "rejected") => {
    if (!appealSelected) return;
    setAppealLoading(true);
    try {
      await adminApi.updateAppeal(appealSelected.id, { decision, admin_note: appealNote });
      toast.success(`APPEAL_${decision.toUpperCase()}`);
      refetchA();
      setAppealSelected(null);
      setAppealNote("");
    } catch (e: any) { toast.error(e.message); }
    finally { setAppealLoading(false); }
  };

  const vList = useMemo(() => validators ?? [], [validators]);
  const aList = useMemo(() => appeals ?? [], [appeals]);

  const stats = useMemo(() => {
    const active = vList.filter(v => v.status === 'active');
    const totalStake = vList.reduce((acc, v) => acc + (v.stake_amount || 0), 0);
    return {
      total: vList.length,
      active: active.length,
      totalStake: totalStake.toLocaleString(),
      pendingAppeals: aList.length
    };
  }, [vList, aList]);

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">

        {/* ── Validator Header ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-sm bg-[#00E676]/10 border border-[#00E676]/20">
              <Shield size={20} className="text-[#00E676]" />
            </div>
            <div>
              <h1 className="font-['Barlow_Condensed'] text-xl font-bold uppercase tracking-wider text-white">Validator Network Ops</h1>
              <p className="font-['Outfit'] text-xs text-white/40">Manage consensus participants, stake security, and dispute resolution</p>
            </div>
          </div>
          <button onClick={() => refetchV()}
            className="p-2 rounded-sm border border-white/5 bg-white/5 text-white/40 hover:text-white transition-all">
            <RefreshCw size={14} className={vLoading ? "animate-spin" : ""} />
          </button>
        </div>

        {/* ── Network Metrics ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Total Nodes", value: stats.total, icon: Network, color: "text-white" },
            { label: "Active Consensus", value: stats.active, icon: Activity, color: "text-[#00E676]" },
            { label: "Total Staked", value: `${stats.totalStake} VIT`, icon: Zap, color: "text-purple-400" },
            { label: "Pending Appeals", value: stats.pendingAppeals, icon: FileText, color: stats.pendingAppeals > 0 ? "text-amber-400" : "text-white/20" },
          ].map((k, i) => (
            <div key={i} className="rounded-sm border border-white/5 bg-white/[0.02] p-4 flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="font-['JetBrains_Mono'] text-[9px] uppercase tracking-widest text-white/30">{k.label}</span>
                <k.icon size={12} className={k.color} />
              </div>
              <span className={`font-['JetBrains_Mono'] text-xl font-bold ${k.color}`}>{k.value}</span>
            </div>
          ))}
        </div>

        {/* ── Navigation ── */}
        <div className="flex gap-1 border-b border-white/10">
          {[
            { key: "validators", label: "Node Registry", icon: Shield },
            { key: "appeals", label: "Dispute Queue", icon: FileText },
            { key: "performance", label: "Slashing Ledger", icon: AlertTriangle },
          ].map((t) => (
            <button key={t.key} onClick={() => setTab(t.key as Tab)}
              className={`flex items-center gap-2 px-5 py-3 font-['Outfit'] text-[11px] font-bold uppercase tracking-widest transition-all border-b-2 -mb-px ${
                tab === t.key ? "border-[#00E676] text-[#00E676] bg-[#00E676]/5" : "border-transparent text-white/30 hover:text-white/60 hover:bg-white/[0.02]"
              }`}>
              <t.icon size={12} />
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Registry View ── */}
        {tab === "validators" && (
          <AdminTable
            loading={vLoading}
            data={vList}
            onRowClick={setSelected}
            pagination={{ page: 1, total: vList.length, limit: 200, onChange: () => {} }}
            columns={[
              { key: "id", label: "NID", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/30">#NODE_${v}</span> },
              { key: "user_id", label: "Entity", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-cyan-400 font-bold">#USR_${v}</span> },
              { key: "status", label: "State", render: (v) => <AdminStatusPill status={v} /> },
              { key: "stake_amount", label: "Stake Volume", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] font-bold text-white">{Number(v).toLocaleString()} VIT</span> },
              { key: "trust_score", label: "Trust Index", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-purple-400 font-bold">{Number(v).toFixed(2)}</span> },
              { key: "accurate_predictions", label: "Accurate", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/40">{v}</span> },
              { key: "total_predictions", label: "Total Ops", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/40">{v}</span> },
              {
                key: "id", label: "Performance",
                render: (_, row) => {
                  const acc = row.total_predictions > 0 ? (row.accurate_predictions / row.total_predictions * 100).toFixed(1) : "—";
                  return <span className="font-['JetBrains_Mono'] text-[10px] font-bold text-[#00E676]">{acc}{row.total_predictions > 0 ? "%" : ""}</span>;
                },
              },
              { key: "created_at", label: "Commissioned", render: (v) => <span className="text-[10px] text-white/30">{v ? new Date(v).toLocaleDateString() : "—"}</span> },
            ]}
          />
        )}

        {/* ── Dispute Queue ── */}
        {tab === "appeals" && (
          <AdminTable
            loading={aLoading}
            data={aList}
            onRowClick={setAppealSelected}
            pagination={{ page: 1, total: aList.length, limit: 200, onChange: () => {} }}
            columns={[
              { key: "id", label: "Appeal ID", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/30">APP_${String(v).slice(0, 8)}</span> },
              { key: "validator_id", label: "Node Ref", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-cyan-400 font-bold">#NODE_${v}</span> },
              { key: "status", label: "Status", render: (v) => <AdminStatusPill status={v} /> },
              { key: "reason", label: "Rationale", render: (v) => <span className="text-[10px] text-white/60 line-clamp-1 italic max-w-md">{v ?? "—"}</span> },
              { key: "created_at", label: "Submitted", render: (v) => <span className="text-[10px] text-white/30">{v ? new Date(v).toLocaleDateString() : "—"}</span> },
            ]}
            emptyMessage="No pending consensus disputes"
          />
        )}

        {/* ── Slashing Ledger Placeholder ── */}
        {tab === "performance" && (
          <div className="rounded-sm border border-white/10 bg-white/[0.01] p-10 flex flex-col items-center justify-center text-center gap-4">
             <AlertTriangle size={40} className="text-red-500/20" />
             <h2 className="font-['Barlow_Condensed'] text-lg font-bold uppercase tracking-widest text-white/40">Slashing & Penalty Ledger</h2>
             <p className="max-w-md font-['Outfit'] text-xs text-white/30 leading-relaxed">
               Historical record of all stake penalties, node decommissions, and regulatory actions taken against the validator network.
             </p>
          </div>
        )}

      </div>

      {/* ── Node Detail & Tactical Actions ── */}
      <AdminModal isOpen={!!selected && tab === "validators"} onClose={() => setSelected(null)} title={`Node Analysis — #NODE_${selected?.id}`} width="max-w-2xl">
        {selected && (
          <div className="flex flex-col gap-6 p-2">
            <div className="grid grid-cols-3 gap-4">
               {[
                 { label: "Consensus State", value: <AdminStatusPill status={selected.status} /> },
                 { label: "Entity ID", value: `#USR_${selected.user_id}` },
                 { label: "Locked Stake", value: `${Number(selected.stake_amount).toLocaleString()} VIT` },
                 { label: "Trust Factor", value: Number(selected.trust_score).toFixed(2) },
                 { label: "Accurate Ops", value: selected.accurate_predictions },
                 { label: "Total Volume", value: selected.total_predictions },
               ].map(({ label, value }) => (
                 <div key={label} className="rounded-sm bg-white/5 p-3 flex flex-col gap-1">
                   <span className="text-[9px] font-bold text-white/30 uppercase tracking-tighter">{label}</span>
                   <div className="text-xs font-bold text-white/80">{value}</div>
                 </div>
               ))}
            </div>

            {/* Slashing Protocol */}
            <div className="rounded-sm border border-red-500/20 bg-red-500/5 p-5">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle size={14} className="text-red-400" />
                <h3 className="font-['Barlow_Condensed'] text-[10px] font-bold uppercase tracking-[0.2em] text-red-400">Slashing Protocol — Stake Penalty</h3>
              </div>
              <div className="flex flex-col gap-3">
                <div className="grid grid-cols-2 gap-3">
                   <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] font-bold uppercase tracking-widest text-white/30">Penalty Amount (VIT)</label>
                      <input type="number" min="0" placeholder="0.00" value={slashForm.amount}
                        onChange={(e) => setSlashForm((f) => ({ ...f, amount: e.target.value }))}
                        className="w-full rounded-sm border border-white/10 bg-[#0b1018] px-3 py-2.5 text-xs text-white focus:outline-none focus:border-red-500/50 font-mono" />
                   </div>
                   <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] font-bold uppercase tracking-widest text-white/30">Execution Rationale</label>
                      <input type="text" placeholder="Protocol violation reference..." value={slashForm.reason}
                        onChange={(e) => setSlashForm((f) => ({ ...f, reason: e.target.value }))}
                        className="w-full rounded-sm border border-white/10 bg-[#0b1018] px-3 py-2.5 text-xs text-white focus:outline-none focus:border-red-500/50" />
                   </div>
                </div>
                <button onClick={handleSlash} disabled={slashLoading || !slashForm.amount || !slashForm.reason}
                  className="w-full rounded-sm bg-red-600 py-3 text-[10px] font-bold uppercase tracking-[0.2em] text-white hover:bg-red-700 disabled:opacity-40 transition-all">
                  {slashLoading ? "EXECUTING SLASH..." : "EXECUTE STAKE PENALTY"}
                </button>
              </div>
            </div>

            {/* Admin Controls */}
            {isSuperAdmin && (
              <div className="flex flex-col gap-3">
                <h3 className="font-['Barlow_Condensed'] text-[10px] font-bold uppercase tracking-[0.2em] text-white/30">Super-User Authorization</h3>
                <button onClick={() => setReinstateConfirm(true)}
                  className="w-full rounded-sm border border-purple-500/30 bg-purple-500/10 py-3 text-[10px] font-bold uppercase tracking-[0.2em] text-purple-400 hover:bg-purple-500/20 transition-all">
                  REINSTATE NODE TO CONSENSUS
                </button>
              </div>
            )}
          </div>
        )}
      </AdminModal>

      {/* ── Dispute Resolution Modal ── */}
      <AdminModal isOpen={!!appealSelected} onClose={() => setAppealSelected(null)} title={`Dispute Resolution — APP_${appealSelected?.id?.slice(0,8)}`} width="max-w-xl">
        {appealSelected && (
          <div className="flex flex-col gap-6 p-2">
            <div className="rounded-sm bg-white/5 p-5 border border-white/5">
              <span className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em] block mb-3">Participant Rationale</span>
              <p className="text-xs text-white/70 leading-relaxed italic">"${appealSelected.reason ?? "No rationale provided"}"</p>
              {appealSelected.evidence && (
                <div className="mt-4 pt-4 border-t border-white/5">
                  <span className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em] block mb-2">Evidence Hash / Reference</span>
                  <p className="font-['JetBrains_Mono'] text-[10px] text-cyan-400 break-all bg-black/40 p-2 rounded-sm">{appealSelected.evidence}</p>
                </div>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/30">Audit Findings Note</label>
              <textarea value={appealNote} onChange={(e) => setAppealNote(e.target.value)} rows={3}
                placeholder="Document audit results here..."
                className="w-full rounded-sm border border-white/10 bg-white/5 px-3 py-3 text-xs text-white focus:outline-none focus:border-cyan-500/50" />
            </div>
            <div className="flex gap-3">
              <button onClick={() => handleAppealDecision("approved")} disabled={appealLoading}
                className="flex-1 rounded-sm bg-[#00E676] py-3 text-[10px] font-bold uppercase tracking-[0.2em] text-black hover:bg-[#00c964] transition-all flex items-center justify-center gap-2">
                <CheckCircle size={14} /> APPROVE APPEAL
              </button>
              <button onClick={() => handleAppealDecision("rejected")} disabled={appealLoading}
                className="flex-1 rounded-sm bg-red-600 py-3 text-[10px] font-bold uppercase tracking-[0.2em] text-white hover:bg-red-700 transition-all flex items-center justify-center gap-2">
                <XCircle size={14} /> REJECT APPEAL
              </button>
            </div>
          </div>
        )}
      </AdminModal>

      <AdminConfirmDialog isOpen={reinstateConfirm} onClose={() => setReinstateConfirm(false)} onConfirm={handleReinstate}
        title="Node Reinstatement" message={`Confirm reinstatement of node #NODE_${selected?.id} and restoration of active consensus status?`} confirmLabel="CONFIRM REINSTATE" />
    </AdminLayout>
  );
}
