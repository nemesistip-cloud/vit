import React, { useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";

type Tab = "validators" | "appeals";

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
      toast.success("Validator slashed");
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
      toast.success("Validator reinstated");
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
      toast.success(`Appeal ${decision}`);
      refetchA();
      setAppealSelected(null);
      setAppealNote("");
    } catch (e: any) { toast.error(e.message); }
    finally { setAppealLoading(false); }
  };

  const vList = validators ?? [];
  const aList = appeals ?? [];

  return (
    <AdminLayout>
      <div className="flex flex-col gap-4">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-white/10">
          {([
            { key: "validators", label: `Validators (${vList.length})` },
            { key: "appeals", label: `Pending Appeals (${aList.length})` },
          ] as { key: Tab; label: string }[]).map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-5 py-2.5 font-['Outfit'] text-sm transition-colors border-b-2 -mb-px ${
                tab === t.key ? "border-[#00E676] text-[#00E676]" : "border-transparent text-white/40 hover:text-white/70"
              }`}>{t.label}</button>
          ))}
        </div>

        {/* Validators */}
        {tab === "validators" && (
          <AdminTable
            loading={vLoading}
            data={vList}
            onRowClick={setSelected}
            pagination={{ page: 1, total: vList.length, limit: 200, onChange: () => {} }}
            columns={[
              { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">#{v}</span> },
              { key: "user_id", label: "User", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">#{v}</span> },
              { key: "status", label: "Status", render: (v) => <AdminStatusPill status={v} /> },
              { key: "stake_amount", label: "Stake", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{Number(v).toLocaleString()} VIT</span> },
              { key: "trust_score", label: "Trust Score", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{Number(v).toFixed(2)}</span> },
              { key: "accurate_predictions", label: "Accurate" },
              { key: "total_predictions", label: "Total" },
              {
                key: "id", label: "Accuracy",
                render: (_, row) => {
                  const acc = row.total_predictions > 0 ? (row.accurate_predictions / row.total_predictions * 100).toFixed(1) : "—";
                  return <span className="font-['JetBrains_Mono'] text-xs text-[#00E676]">{acc}{row.total_predictions > 0 ? "%" : ""}</span>;
                },
              },
              { key: "created_at", label: "Joined", render: (v) => v ? new Date(v).toLocaleDateString() : "—" },
            ]}
            emptyMessage="No validators found"
          />
        )}

        {/* Appeals */}
        {tab === "appeals" && (
          <AdminTable
            loading={aLoading}
            data={aList}
            onRowClick={setAppealSelected}
            pagination={{ page: 1, total: aList.length, limit: 200, onChange: () => {} }}
            columns={[
              { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{String(v).slice(0, 8)}…</span> },
              { key: "validator_id", label: "Validator", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">#{v}</span> },
              { key: "status", label: "Status", render: (v) => <AdminStatusPill status={v} /> },
              { key: "reason", label: "Reason", render: (v) => <span className="text-xs text-white/60 line-clamp-1">{v ?? "—"}</span> },
              { key: "created_at", label: "Submitted", render: (v) => v ? new Date(v).toLocaleDateString() : "—" },
            ]}
            emptyMessage="No pending appeals"
          />
        )}
      </div>

      {/* Validator Action Modal */}
      <AdminModal isOpen={!!selected && tab === "validators"} onClose={() => setSelected(null)} title={`Validator #${selected?.id}`}>
        {selected && (
          <div className="flex flex-col gap-5">
            <div className="grid grid-cols-2 gap-3 rounded-lg bg-white/5 p-4 text-sm">
              {[
                { label: "Status", value: <AdminStatusPill status={selected.status} /> },
                { label: "User ID", value: `#${selected.user_id}` },
                { label: "Stake", value: `${Number(selected.stake_amount).toLocaleString()} VIT` },
                { label: "Trust Score", value: Number(selected.trust_score).toFixed(2) },
                { label: "Accurate", value: selected.accurate_predictions },
                { label: "Total", value: selected.total_predictions },
              ].map(({ label, value }) => (
                <div key={label}><span className="text-xs text-white/40">{label}</span><p className="mt-0.5 text-white/80">{value}</p></div>
              ))}
            </div>

            {/* Slash */}
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
              <p className="mb-3 font-['Barlow_Condensed'] text-xs uppercase tracking-widest text-red-400">Slash Stake</p>
              <div className="flex flex-col gap-2">
                <input type="number" min="0" placeholder="Slash amount (VIT)" value={slashForm.amount}
                  onChange={(e) => setSlashForm((f) => ({ ...f, amount: e.target.value }))}
                  className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 text-sm text-white focus:outline-none" />
                <input type="text" placeholder="Reason" value={slashForm.reason}
                  onChange={(e) => setSlashForm((f) => ({ ...f, reason: e.target.value }))}
                  className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 text-sm text-white focus:outline-none" />
                <button onClick={handleSlash} disabled={slashLoading || !slashForm.amount || !slashForm.reason}
                  className="rounded-lg bg-red-600 py-2.5 font-['Outfit'] text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-40">
                  {slashLoading ? "Slashing…" : "Execute Slash"}
                </button>
              </div>
            </div>

            {/* Reinstate (super admin only) */}
            {isSuperAdmin && (
              <button onClick={() => setReinstateConfirm(true)}
                className="rounded-lg border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 py-2.5 font-['Outfit'] text-sm text-[#8B5CF6] hover:bg-[#8B5CF6]/20">
                Reinstate Validator
              </button>
            )}
          </div>
        )}
      </AdminModal>

      {/* Appeal Decision Modal */}
      <AdminModal isOpen={!!appealSelected} onClose={() => setAppealSelected(null)} title={`Appeal #${appealSelected?.id}`}>
        {appealSelected && (
          <div className="flex flex-col gap-4">
            <div className="rounded-lg bg-white/5 p-4 text-sm">
              <p className="text-xs text-white/40 mb-1">Reason</p>
              <p className="text-white/70">{appealSelected.reason ?? "No reason provided"}</p>
              {appealSelected.evidence && (
                <>
                  <p className="text-xs text-white/40 mt-3 mb-1">Evidence</p>
                  <p className="text-white/70 text-xs">{appealSelected.evidence}</p>
                </>
              )}
            </div>
            <div>
              <label className="mb-1 block text-xs text-white/50">Admin Note (optional)</label>
              <textarea value={appealNote} onChange={(e) => setAppealNote(e.target.value)} rows={3}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:outline-none" />
            </div>
            <div className="flex gap-3">
              <button onClick={() => handleAppealDecision("approved")} disabled={appealLoading}
                className="flex-1 rounded-lg bg-[#00E676] py-2.5 text-sm font-semibold text-black hover:bg-[#00c964] disabled:opacity-40">
                Approve
              </button>
              <button onClick={() => handleAppealDecision("rejected")} disabled={appealLoading}
                className="flex-1 rounded-lg bg-red-600 py-2.5 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-40">
                Reject
              </button>
            </div>
          </div>
        )}
      </AdminModal>

      <AdminConfirmDialog isOpen={reinstateConfirm} onClose={() => setReinstateConfirm(false)} onConfirm={handleReinstate}
        title="Reinstate Validator" message={`Reinstate validator #${selected?.id} and restore active status?`} />
    </AdminLayout>
  );
}
