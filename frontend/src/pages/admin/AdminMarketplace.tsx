import React, { useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";

export default function AdminMarketplace() {
  const [filterStatus, setFilterStatus] = useState("");
  const params: Record<string, any> = {};
  if (filterStatus) params.status = filterStatus;

  const { data: listings, loading, refetch } = useAdminData<any[]>("/api/admin/marketplace/listings", params);

  const [selected, setSelected] = useState<any>(null);
  const [rejectNote, setRejectNote] = useState("");
  const [rejectModal, setRejectModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [approveConfirm, setApproveConfirm] = useState(false);

  const handleApprove = async () => {
    if (!selected) return;
    try {
      await adminApi.approveMarketplaceListing(selected.id);
      toast.success("Listing approved");
      refetch();
      setApproveConfirm(false);
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleReject = async () => {
    if (!selected) return;
    try {
      await adminApi.rejectMarketplaceListing(selected.id, rejectNote);
      toast.success("Listing rejected");
      refetch();
      setRejectModal(false);
      setSelected(null);
      setRejectNote("");
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDelete = async () => {
    if (!selected) return;
    try {
      await adminApi.deleteMarketplaceListing(selected.id);
      toast.success("Listing deleted");
      refetch();
      setDeleteConfirm(false);
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const list = listings ?? [];

  return (
    <AdminLayout>
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
            <option value="">All listings</option>
            {["pending", "active", "rejected", "suspended"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <span className="font-['JetBrains_Mono'] text-xs text-white/30">{list.length} listings</span>
        </div>

        <AdminTable
          loading={loading}
          data={list}
          onRowClick={setSelected}
          pagination={{ page: 1, total: list.length, limit: 200, onChange: () => {} }}
          columns={[
            { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{String(v).slice(0, 8)}…</span> },
            { key: "name", label: "Name", render: (v) => <span className="font-semibold">{v}</span> },
            { key: "category", label: "Category" },
            { key: "model_key", label: "Model Key", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-[#00E676]">{v}</span> },
            { key: "price_per_call", label: "Price", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{v} VIT</span> },
            { key: "is_active", label: "Status", render: (v) => <AdminStatusPill status={v ? "active" : "pending"} /> },
            {
              key: "id", label: "Actions",
              render: (id, row) => (
                <div className="flex gap-2">
                  {!row.is_active && (
                    <button onClick={(e) => { e.stopPropagation(); setSelected(row); setApproveConfirm(true); }}
                      className="rounded bg-[#00E676]/10 px-2.5 py-1 text-xs text-[#00E676] hover:bg-[#00E676]/20">Approve</button>
                  )}
                  <button onClick={(e) => { e.stopPropagation(); setSelected(row); setRejectModal(true); }}
                    className="rounded bg-yellow-400/10 px-2.5 py-1 text-xs text-yellow-400 hover:bg-yellow-400/20">Reject</button>
                  <button onClick={(e) => { e.stopPropagation(); setSelected(row); setDeleteConfirm(true); }}
                    className="rounded bg-red-500/10 px-2.5 py-1 text-xs text-red-400 hover:bg-red-500/20">Delete</button>
                </div>
              ),
            },
          ]}
          emptyMessage="No marketplace listings found"
        />
      </div>

      {/* Detail */}
      <AdminModal isOpen={!!selected && !approveConfirm && !rejectModal && !deleteConfirm} onClose={() => setSelected(null)} title={selected?.name ?? "Listing"}>
        {selected && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 rounded-lg bg-white/5 p-4 text-sm">
              {[
                { label: "ID", value: selected.id },
                { label: "Category", value: selected.category },
                { label: "Model Key", value: selected.model_key },
                { label: "Price/Call", value: `${selected.price_per_call} VIT` },
                { label: "Status", value: <AdminStatusPill status={selected.is_active ? "active" : "pending"} /> },
                { label: "GCS URI", value: <span className="font-['JetBrains_Mono'] text-xs break-all">{selected.gcs_uri ?? "—"}</span> },
              ].map(({ label, value }) => (
                <div key={label}><span className="text-xs text-white/40">{label}</span><p className="mt-0.5 text-white/80">{value}</p></div>
              ))}
              {selected.description && (
                <div className="col-span-2"><span className="text-xs text-white/40">Description</span><p className="mt-0.5 text-white/70 text-sm">{selected.description}</p></div>
              )}
            </div>
            <div className="flex gap-2">
              {!selected.is_active && (
                <button onClick={() => setApproveConfirm(true)} className="flex-1 rounded-lg bg-[#00E676] py-2.5 text-sm font-semibold text-black hover:bg-[#00c964]">Approve</button>
              )}
              <button onClick={() => setRejectModal(true)} className="flex-1 rounded-lg bg-yellow-400/10 border border-yellow-400/30 py-2.5 text-sm text-yellow-400 hover:bg-yellow-400/20">Reject</button>
              <button onClick={() => setDeleteConfirm(true)} className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/20">Delete</button>
            </div>
          </div>
        )}
      </AdminModal>

      {/* Reject Modal */}
      <AdminModal isOpen={rejectModal} onClose={() => setRejectModal(false)} title="Reject Listing">
        <div className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-xs text-white/50">Rejection note</label>
            <textarea value={rejectNote} onChange={(e) => setRejectNote(e.target.value)} rows={3}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:outline-none" />
          </div>
          <div className="flex gap-3">
            <button onClick={() => setRejectModal(false)} className="flex-1 rounded-lg border border-white/10 py-2.5 text-sm text-white/60">Cancel</button>
            <button onClick={handleReject} disabled={!rejectNote} className="flex-1 rounded-lg bg-red-600 py-2.5 text-sm font-semibold text-white disabled:opacity-40">Reject</button>
          </div>
        </div>
      </AdminModal>

      <AdminConfirmDialog isOpen={approveConfirm} onClose={() => setApproveConfirm(false)} onConfirm={handleApprove}
        title="Approve Listing" message={`Approve "${selected?.name}" and make it publicly available?`} confirmLabel="Approve" />
      <AdminConfirmDialog isOpen={deleteConfirm} onClose={() => setDeleteConfirm(false)} onConfirm={handleDelete}
        title="Delete Listing" message={`Permanently delete "${selected?.name}"? This cannot be undone.`}
        confirmLabel="Delete" dangerous />
    </AdminLayout>
  );
}
