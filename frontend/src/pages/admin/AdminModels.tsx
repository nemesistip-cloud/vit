import React, { useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";

type Tab = "models" | "jobs";

export default function AdminModels() {
  const [tab, setTab] = useState<Tab>("models");
  const [jPage, setJPage] = useState(1);
  const [jStatus, setJStatus] = useState("");

  const { data: models, loading: mLoading, refetch: refetchModels } = useAdminData<any[]>("/api/admin/models");

  const jParams: Record<string, any> = { page: jPage, limit: 50 };
  if (jStatus) jParams.status = jStatus;
  const { data: jobData, loading: jLoading } = useAdminData<any>("/api/admin/training-jobs", jParams);

  const [retrainKey, setRetrainKey] = useState<string | null>(null);
  const [retrainAllConfirm, setRetrainAllConfirm] = useState(false);

  const handleRetrainModel = async () => {
    if (!retrainKey) return;
    try {
      await adminApi.retrainModel(retrainKey);
      toast.success(`Retrain queued: ${retrainKey}`);
      setRetrainKey(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRetrainAll = async () => {
    try { await adminApi.retrainAll(); toast.success("Full ensemble retrain queued"); setRetrainAllConfirm(false); }
    catch (e: any) { toast.error(e.message); }
  };

  const modelList = models ?? [];
  const jobs = jobData?.jobs ?? [];

  return (
    <AdminLayout>
      <div className="flex flex-col gap-4">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-white/10">
          {([
            { key: "models", label: `Models (${modelList.length})` },
            { key: "jobs", label: "Training Jobs" },
          ] as { key: Tab; label: string }[]).map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-5 py-2.5 font-['Outfit'] text-sm transition-colors border-b-2 -mb-px ${
                tab === t.key ? "border-[#00E676] text-[#00E676]" : "border-transparent text-white/40 hover:text-white/70"
              }`}>{t.label}</button>
          ))}
          {tab === "models" && (
            <button onClick={() => setRetrainAllConfirm(true)}
              className="ml-auto rounded-lg border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-4 py-2 font-['Outfit'] text-xs text-[#8B5CF6] hover:bg-[#8B5CF6]/20">
              🤖 Retrain All
            </button>
          )}
        </div>

        {/* Models */}
        {tab === "models" && (
          <AdminTable
            loading={mLoading}
            data={modelList}
            pagination={{ page: 1, total: modelList.length, limit: 200, onChange: () => {} }}
            columns={[
              { key: "key", label: "Key", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-[#00E676]">{v}</span> },
              { key: "name", label: "Name" },
              { key: "model_type", label: "Type", render: (v) => <span className="text-xs text-white/50">{v ?? "—"}</span> },
              { key: "is_active", label: "Status", render: (v) => <AdminStatusPill status={v ? "active" : "inactive"} /> },
              {
                key: "weight", label: "Weight",
                render: (v) => (
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10">
                      <div className="h-full rounded-full bg-[#00E676]" style={{ width: `${Math.min(100, Number(v) * 100)}%` }} />
                    </div>
                    <span className="font-['JetBrains_Mono'] text-xs">{Number(v).toFixed(2)}</span>
                  </div>
                ),
              },
              { key: "accuracy", label: "Accuracy", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{(Number(v) * 100).toFixed(1)}%</span> },
              { key: "clv_score", label: "CLV Score", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{Number(v).toFixed(4)}</span> },
              { key: "version", label: "Version", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{v ?? "—"}</span> },
              {
                key: "key", label: "Actions",
                render: (k) => (
                  <button onClick={(e) => { e.stopPropagation(); setRetrainKey(k); }}
                    className="rounded bg-[#8B5CF6]/10 px-2.5 py-1 text-xs text-[#8B5CF6] hover:bg-[#8B5CF6]/20">
                    Retrain
                  </button>
                ),
              },
            ]}
            emptyMessage="No models found"
          />
        )}

        {/* Training Jobs */}
        {tab === "jobs" && (
          <>
            <div className="flex gap-3">
              <select value={jStatus} onChange={(e) => { setJStatus(e.target.value); setJPage(1); }}
                className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
                <option value="">All status</option>
                {["pending", "running", "completed", "failed"].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <AdminTable
              loading={jLoading}
              data={jobs}
              pagination={{ page: jPage, total: jobData?.total ?? 0, limit: 50, onChange: setJPage }}
              columns={[
                { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{String(v).slice(0, 8)}…</span> },
                { key: "model_key", label: "Model", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-[#00E676]">{v ?? "all"}</span> },
                { key: "status", label: "Status", render: (v) => <AdminStatusPill status={v} /> },
                {
                  key: "progress_pct", label: "Progress",
                  render: (v) => (
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10">
                        <div className="h-full rounded-full bg-[#8B5CF6]" style={{ width: `${Number(v)}%` }} />
                      </div>
                      <span className="font-['JetBrains_Mono'] text-xs">{Number(v).toFixed(0)}%</span>
                    </div>
                  ),
                },
                { key: "created_at", label: "Started", render: (v) => v ? new Date(v).toLocaleString() : "—" },
                { key: "completed_at", label: "Finished", render: (v) => v ? new Date(v).toLocaleString() : "—" },
              ]}
              emptyMessage="No training jobs found"
            />
          </>
        )}
      </div>

      <AdminConfirmDialog isOpen={!!retrainKey} onClose={() => setRetrainKey(null)} onConfirm={handleRetrainModel}
        title="Retrain Model" message={`Queue retrain for model: ${retrainKey}? This may take several minutes.`} />
      <AdminConfirmDialog isOpen={retrainAllConfirm} onClose={() => setRetrainAllConfirm(false)} onConfirm={handleRetrainAll}
        title="Retrain All Models" message="Queue a full ensemble retrain? This will retrain all active models and may take 15-30 minutes." />
    </AdminLayout>
  );
}
