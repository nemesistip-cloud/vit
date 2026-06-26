import React, { useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";

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
      toast.success("Result set");
      refetchMatches();
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!selected) return;
    try {
      await adminApi.deleteMatch(selected.id);
      toast.success("Match deleted");
      refetchMatches();
      setDeleteConfirm(false);
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecalcCLV = async () => {
    try { await adminApi.recalculateCLV(); toast.success("CLV recalculation queued"); setClvConfirm(false); }
    catch (e: any) { toast.error(e.message); }
  };

  return (
    <AdminLayout>
      <div className="flex flex-col gap-4">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-white/10">
          {(["matches", "predictions"] as Tab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-5 py-2.5 font-['Outfit'] text-sm capitalize transition-colors border-b-2 -mb-px ${
                tab === t ? "border-[#00E676] text-[#00E676]" : "border-transparent text-white/40 hover:text-white/70"
              }`}>{t}</button>
          ))}
        </div>

        {/* Matches */}
        {tab === "matches" && (
          <>
            <div className="flex flex-wrap gap-3">
              <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}
                className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
                <option value="">All status</option>
                {MATCH_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={sport} onChange={(e) => { setSport(e.target.value); setPage(1); }}
                className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
                <option value="">All sports</option>
                {["football", "basketball", "tennis", "cricket", "rugby"].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <AdminTable
              loading={matchLoading}
              data={matchData?.matches ?? []}
              onRowClick={openMatch}
              pagination={{ page, total: matchData?.total ?? 0, limit: 50, onChange: setPage }}
              columns={[
                { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{v}</span> },
                { key: "home_team", label: "Home" },
                { key: "away_team", label: "Away" },
                { key: "league", label: "League", render: (v) => <span className="text-xs text-white/50">{v ?? "—"}</span> },
                { key: "sport", label: "Sport" },
                { key: "match_date", label: "Date", render: (v) => v ? new Date(v).toLocaleString() : "—" },
                { key: "status", label: "Status", render: (v) => <AdminStatusPill status={v} /> },
                {
                  key: "actual_outcome", label: "Result",
                  render: (v, row) => v ? (
                    <span className="font-['JetBrains_Mono'] text-xs text-[#00E676]">
                      {v} {row.home_goals !== null ? `(${row.home_goals}-${row.away_goals})` : ""}
                    </span>
                  ) : <span className="text-white/20 text-xs">—</span>,
                },
              ]}
            />
          </>
        )}

        {/* Predictions */}
        {tab === "predictions" && (
          <>
            <div className="flex justify-end">
              <button onClick={() => setClvConfirm(true)}
                className="rounded-lg border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-4 py-2 font-['Outfit'] text-xs text-[#8B5CF6] hover:bg-[#8B5CF6]/20">
                Recalculate CLV
              </button>
            </div>
            <AdminTable
              loading={predLoading}
              data={predData?.predictions ?? []}
              pagination={{ page: pPage, total: predData?.total ?? 0, limit: 50, onChange: setPPage }}
              columns={[
                { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{v}</span> },
                { key: "user_id", label: "User", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">#{v}</span> },
                { key: "match_id", label: "Match", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/50">{v}</span> },
                { key: "market", label: "Market" },
                { key: "selection", label: "Selection" },
                { key: "was_correct", label: "Correct", render: (v) => v === null ? <span className="text-white/20">—</span> : <AdminStatusPill status={v ? "active" : "rejected"} label={v ? "Yes" : "No"} /> },
                { key: "clv", label: "CLV", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{v !== null && v !== undefined ? Number(v).toFixed(4) : "—"}</span> },
                { key: "created_at", label: "Date", render: (v) => v ? new Date(v).toLocaleDateString() : "—" },
              ]}
            />
          </>
        )}
      </div>

      {/* Set Result Modal */}
      <AdminModal isOpen={!!selected} onClose={() => setSelected(null)} title={`Match: ${selected?.home_team ?? ""} vs ${selected?.away_team ?? ""}`}>
        {selected && (
          <div className="flex flex-col gap-5">
            <div className="grid grid-cols-3 gap-3 rounded-lg bg-white/5 p-4 text-sm">
              <div><span className="text-xs text-white/40">Sport</span><p className="text-white/70">{selected.sport}</p></div>
              <div><span className="text-xs text-white/40">Date</span><p className="text-white/70">{selected.match_date ? new Date(selected.match_date).toLocaleString() : "—"}</p></div>
              <div><span className="text-xs text-white/40">Status</span><p><AdminStatusPill status={selected.status} /></p></div>
            </div>

            <div>
              <label className="mb-1 block text-xs text-white/50">Outcome</label>
              <select value={resultForm.actual_outcome} onChange={(e) => setResultForm((f) => ({ ...f, actual_outcome: e.target.value }))}
                className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 text-sm text-white">
                <option value="">Select outcome</option>
                {OUTCOMES.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs text-white/50">Home Goals</label>
                <input type="number" min="0" value={resultForm.home_goals} onChange={(e) => setResultForm((f) => ({ ...f, home_goals: e.target.value }))}
                  className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 text-sm text-white focus:outline-none" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-white/50">Away Goals</label>
                <input type="number" min="0" value={resultForm.away_goals} onChange={(e) => setResultForm((f) => ({ ...f, away_goals: e.target.value }))}
                  className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 text-sm text-white focus:outline-none" />
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={handleSetResult} disabled={saving || !resultForm.actual_outcome}
                className="flex-1 rounded-lg bg-[#00E676] py-2.5 font-['Outfit'] text-sm font-semibold text-black hover:bg-[#00c964] disabled:opacity-40">
                {saving ? "Saving…" : "Set Result"}
              </button>
              <button onClick={() => setDeleteConfirm(true)}
                className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 font-['Outfit'] text-xs text-red-400 hover:bg-red-500/20">
                Delete
              </button>
            </div>
          </div>
        )}
      </AdminModal>

      <AdminConfirmDialog isOpen={deleteConfirm} onClose={() => setDeleteConfirm(false)} onConfirm={handleDelete}
        title="Delete Match" message={`Mark match ${selected?.id} as deleted? Predictions will not be settled.`}
        confirmLabel="Delete" dangerous />
      <AdminConfirmDialog isOpen={clvConfirm} onClose={() => setClvConfirm(false)} onConfirm={handleRecalcCLV}
        title="Recalculate CLV" message="Queue a CLV recalculation job for all settled predictions? This may take a few minutes." />
    </AdminLayout>
  );
}
