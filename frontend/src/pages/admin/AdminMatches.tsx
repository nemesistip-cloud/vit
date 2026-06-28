import React, { useState, useMemo } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";
import {
  Trophy, TrendingUp, Search, Calendar, Globe,
  BarChart2, Activity, History, Zap, Trash2,
  CheckCircle2, AlertCircle, Filter, FilterX
} from "lucide-react";

type Tab = "matches" | "predictions";

const MATCH_STATUSES = ["upcoming", "live", "settled", "cancelled", "deleted"];
const OUTCOMES = ["1", "X", "2", "1X", "2X", "12", "over", "under", "btts", "no_btts"];

export default function AdminMatches() {
  const [tab, setTab] = useState<Tab>("matches");
  const [page, setPage] = useState(1);
  const [pPage, setPPage] = useState(1);
  const [status, setStatus] = useState("");
  const [sport, setSport] = useState("");

  const matchParams: Record<string, any> = { page, limit: 50 };
  if (status) matchParams.status = status;
  if (sport) matchParams.sport = sport;
  const { data: matchData, loading: matchLoading, refetch: refetchMatches } = useAdminData<any>("/api/admin/matches", matchParams);

  const predParams: Record<string, any> = { page: pPage, limit: 50 };
  const { data: predData, loading: predLoading, refetch: refetchPreds } = useAdminData<any>("/api/admin/predictions", predParams);

  const [selected, setSelected] = useState<any>(null);
  const [resultForm, setResultForm] = useState({ actual_outcome: "", home_goals: "", away_goals: "" });
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [clvConfirm, setClvConfirm] = useState(false);

  const openMatch = (row: any) => {
    setSelected(row);
    setResultForm({ actual_outcome: row.actual_outcome ?? "", home_goals: row.home_goals ?? "", away_goals: row.away_goals ?? "" });
  };

  const handleSetResult = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await adminApi.setMatchResult(selected.id, {
        actual_outcome: resultForm.actual_outcome,
        home_goals: resultForm.home_goals !== "" ? Number(resultForm.home_goals) : undefined,
        away_goals: resultForm.away_goals !== "" ? Number(resultForm.away_goals) : undefined,
      });
      toast.success("MATCH_RESULT_SET_SUCCESS");
      refetchMatches();
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!selected) return;
    try {
      await adminApi.deleteMatch(selected.id);
      toast.success("MATCH_DECOMMISSIONED");
      refetchMatches();
      setDeleteConfirm(false);
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecalcCLV = async () => {
    try { await adminApi.recalculateCLV(); toast.success("CLV_RECALC_QUEUED"); setClvConfirm(false); }
    catch (e: any) { toast.error(e.message); }
  };

  const mList = useMemo(() => matchData?.matches ?? [], [matchData]);
  const pList = useMemo(() => predData?.predictions ?? [], [predData]);

  const stats = useMemo(() => {
    return {
      activeMatches: mList.filter(m => m.status === 'upcoming' || m.status === 'live').length,
      totalPredictions: predData?.total ?? 0,
      settledRate: "88.2%" // Mocked
    };
  }, [mList, predData]);

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">

        {/* ── Header ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-sm bg-[#8B5CF6]/10 border border-[#8B5CF6]/20">
              <Trophy size={20} className="text-[#8B5CF6]" />
            </div>
            <div>
              <h1 className="font-['Barlow_Condensed'] text-xl font-bold uppercase tracking-wider text-white">Market & Prediction Ledger</h1>
              <p className="font-['Outfit'] text-xs text-white/40">Audit institutional prediction flows, settle market outcomes, and monitor closing line value</p>
            </div>
          </div>
          {tab === "predictions" && (
            <button onClick={() => setClvConfirm(true)}
              className="flex items-center gap-2 rounded-sm border border-purple-500/30 bg-purple-500/10 px-4 py-2 font-['Outfit'] text-[10px] font-bold uppercase tracking-widest text-purple-400 hover:bg-purple-500/20 transition-all">
              <Zap size={12} /> Recalculate CLV
            </button>
          )}
        </div>

        {/* ── Metrics ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Active Markets", value: stats.activeMatches, icon: Globe, color: "text-white" },
            { label: "Total Volume", value: stats.totalPredictions.toLocaleString(), icon: TrendingUp, color: "text-[#00E676]" },
            { label: "Settlement Rate", value: stats.settledRate, icon: CheckCircle2, color: "text-cyan-400" },
            { label: "Data Quality", value: "99.4%", icon: Activity, color: "text-purple-400" },
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

        {/* ── Tabs ── */}
        <div className="flex gap-1 border-b border-white/10">
          {[
            { key: "matches", label: "Market Registry", icon: Globe },
            { key: "predictions", label: "Prediction Ledger", icon: History },
          ].map((t) => (
            <button key={t.key} onClick={() => setTab(t.key as Tab)}
              className={`flex items-center gap-2 px-5 py-3 font-['Outfit'] text-[11px] font-bold uppercase tracking-widest transition-all border-b-2 -mb-px ${
                tab === t.key ? "border-purple-500 text-purple-400 bg-purple-500/5" : "border-transparent text-white/30 hover:text-white/60 hover:bg-white/[0.02]"
              }`}>
              <t.icon size={12} />
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Content ── */}
        {tab === "matches" && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-3">
               <div className="relative flex-1 max-w-sm">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" />
                  <input placeholder="Filter markets by ID or Team..." className="w-full rounded-sm border border-white/10 bg-white/5 pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-purple-500/50" />
               </div>
              <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}
                className="rounded-sm border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-xs text-white/60 focus:outline-none">
                <option value="">ALL STATUS</option>
                {MATCH_STATUSES.map((s) => <option key={s} value={s}>{s.toUpperCase()}</option>)}
              </select>
              <select value={sport} onChange={(e) => { setSport(e.target.value); setPage(1); }}
                className="rounded-sm border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-xs text-white/60 focus:outline-none">
                <option value="">ALL VERTICALS</option>
                {["football", "basketball", "tennis", "cricket", "rugby"].map((s) => <option key={s} value={s}>{s.toUpperCase()}</option>)}
              </select>
            </div>
            <AdminTable
              loading={matchLoading}
              data={mList}
              onRowClick={openMatch}
              pagination={{ page, total: matchData?.total ?? 0, limit: 50, onChange: setPage }}
              columns={[
                { key: "id", label: "MID", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/30">#M_${v}</span> },
                { key: "home_team", label: "Consensus Side A", render: (v) => <span className="font-bold text-xs">{v}</span> },
                { key: "away_team", label: "Consensus Side B", render: (v) => <span className="font-bold text-xs">{v}</span> },
                { key: "league", label: "Competition", render: (v) => <span className="text-[10px] text-white/40 uppercase font-bold tracking-tighter">{v ?? "—"}</span> },
                { key: "match_date", label: "Scheduled At", render: (v) => <span className="text-[10px] text-white/30">{v ? new Date(v).toLocaleString() : "—"}</span> },
                { key: "status", label: "State", render: (v) => <AdminStatusPill status={v} /> },
                {
                  key: "actual_outcome", label: "Audit Result",
                  render: (v, row) => v ? (
                    <span className="font-['JetBrains_Mono'] text-[10px] font-bold text-[#00E676] uppercase">
                      {v} {row.home_goals !== null ? `(${row.home_goals}-${row.away_goals})` : ""}
                    </span>
                  ) : <span className="text-white/10 text-[10px]">—</span>,
                },
              ]}
            />
          </div>
        )}

        {tab === "predictions" && (
          <AdminTable
            loading={predLoading}
            data={pList}
            pagination={{ page: pPage, total: predData?.total ?? 0, limit: 50, onChange: setPPage }}
            columns={[
              { key: "id", label: "TXID", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/30">#P_${v}</span> },
              { key: "user_id", label: "Entity", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-cyan-400 font-bold">#USR_${v}</span> },
              { key: "match_id", label: "Market Ref", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/30">#M_${v}</span> },
              { key: "market", label: "Vertical", render: (v) => <span className="text-[10px] font-bold text-white/40 uppercase">{v}</span> },
              { key: "selection", label: "Vector", render: (v) => <span className="font-bold text-xs">{v}</span> },
              { key: "was_correct", label: "Audit", render: (v) => v === null ? <span className="text-white/10">—</span> : <AdminStatusPill status={v ? "active" : "rejected"} label={v ? "CORRECT" : "ERROR"} /> },
              { key: "clv", label: "CLV_SIG", render: (v) => <span className={`font-['JetBrains_Mono'] text-[10px] font-bold ${Number(v) >= 0 ? 'text-cyan-400' : 'text-red-400'}`}>{v !== null && v !== undefined ? Number(v).toFixed(4) : "—"}</span> },
              { key: "created_at", label: "Logged At", render: (v) => <span className="text-[10px] text-white/30">{v ? new Date(v).toLocaleDateString() : "—"}</span> },
            ]}
          />
        )}

      </div>

      {/* ── Settlement Modal ── */}
      <AdminModal isOpen={!!selected} onClose={() => setSelected(null)} title={`Market Settlement — #M_${selected?.id}`} width="max-w-xl">
        {selected && (
          <div className="flex flex-col gap-6 p-2">
            <div className="rounded-sm border border-white/10 bg-white/[0.01] p-5">
               <div className="flex flex-col items-center text-center gap-2 mb-4">
                  <span className="text-[10px] font-bold text-white/20 uppercase tracking-[0.2em]">{selected.league}</span>
                  <h2 className="text-lg font-bold text-white uppercase">{selected.home_team} vs {selected.away_team}</h2>
                  <span className="text-[9px] font-mono text-white/30 tracking-widest">{new Date(selected.match_date).toLocaleString()}</span>
               </div>
               <div className="h-px bg-white/5 my-4" />
               <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1">
                     <span className="text-[9px] font-bold text-white/30 uppercase">Operational State</span>
                     <AdminStatusPill status={selected.status} />
                  </div>
                  <div className="flex flex-col gap-1 text-right">
                     <span className="text-[9px] font-bold text-white/30 uppercase">Vertical</span>
                     <span className="text-xs font-bold text-white/80 uppercase">{selected.sport}</span>
                  </div>
               </div>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-white/30">Validated Outcome Vector</label>
                <select value={resultForm.actual_outcome} onChange={(e) => setResultForm((f) => ({ ...f, actual_outcome: e.target.value }))}
                  className="w-full rounded-sm border border-white/10 bg-[#0d1117] px-3 py-3 text-xs text-white focus:outline-none focus:border-purple-500/50">
                  <option value="">SELECT VECTOR</option>
                  {OUTCOMES.map((o) => <option key={o} value={o}>{o.toUpperCase()}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-white/30">Side A Score</label>
                  <input type="number" min="0" value={resultForm.home_goals} onChange={(e) => setResultForm((f) => ({ ...f, home_goals: e.target.value }))}
                    className="w-full rounded-sm border border-white/10 bg-[#0d1117] px-3 py-3 text-sm text-white focus:outline-none font-mono" />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-white/30">Side B Score</label>
                  <input type="number" min="0" value={resultForm.away_goals} onChange={(e) => setResultForm((f) => ({ ...f, away_goals: e.target.value }))}
                    className="w-full rounded-sm border border-white/10 bg-[#0d1117] px-3 py-3 text-sm text-white focus:outline-none font-mono" />
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={handleSetResult} disabled={saving || !resultForm.actual_outcome}
                className="flex-1 rounded-sm bg-[#00E676] py-3 text-[10px] font-bold uppercase tracking-[0.2em] text-black hover:bg-[#00c964] disabled:opacity-40 transition-all">
                {saving ? "COMMITTING SETTLEMENT..." : "EXECUTE SETTLEMENT"}
              </button>
              <button onClick={() => setDeleteConfirm(true)}
                className="rounded-sm border border-red-500/20 bg-red-500/10 px-6 py-3 text-[10px] font-bold uppercase tracking-widest text-red-400 hover:bg-red-500/20 transition-all">
                DECOMMISSION
              </button>
            </div>
          </div>
        )}
      </AdminModal>

      <AdminConfirmDialog isOpen={deleteConfirm} onClose={() => setDeleteConfirm(false)} onConfirm={handleDelete}
        title="Market Decommission" message={`Confirm permanent decommission of market #M_${selected?.id}? This action will void all associated prediction vectors.`}
        confirmLabel="CONFIRM PURGE" dangerous />
      <AdminConfirmDialog isOpen={clvConfirm} onClose={() => setClvConfirm(false)} onConfirm={handleRecalcCLV}
        title="CLV Intelligence Re-calc" message="Queue global re-calculation of Closing Line Value for all settled prediction vectors? This protocol may take several minutes." confirmLabel="EXECUTE RE-CALC" />
    </AdminLayout>
  );
}
