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
  Store, Package, ShoppingCart, Tag, Filter,
  Search, ExternalLink, Trash2, CheckCircle,
  XCircle, AlertTriangle, Database, TrendingUp,
  BarChart3, User, History
} from "lucide-react";

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
      toast.success("LISTING_APPROVED_LIVE");
      refetch();
      setApproveConfirm(false);
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleReject = async () => {
    if (!selected) return;
    try {
      await adminApi.rejectMarketplaceListing(selected.id, rejectNote);
      toast.success("LISTING_REJECTED_AUDIT");
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
      toast.success("LISTING_PURGED");
      refetch();
      setDeleteConfirm(false);
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const list = useMemo(() => listings ?? [], [listings]);

  const stats = useMemo(() => {
    return {
      total: list.length,
      pending: list.filter(l => !l.is_active).length,
      active: list.filter(l => l.is_active).length,
      revenue: "4.2K VIT" // Mocked
    };
  }, [list]);

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">

        {/* ── Marketplace Header ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-sm bg-amber-500/10 border border-amber-500/20">
              <Store size={20} className="text-amber-400" />
            </div>
            <div>
              <h1 className="font-['Barlow_Condensed'] text-xl font-bold uppercase tracking-wider text-white">Marketplace Operations</h1>
              <p className="font-['Outfit'] text-xs text-white/40">Audit model listings, manage creator packages, and monitor sales volume</p>
            </div>
          </div>
        </div>

        {/* ── Marketplace Metrics ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Inventory Total", value: stats.total, icon: Package, color: "text-white" },
            { label: "Active Listings", value: stats.active, icon: CheckCircle, color: "text-[#00E676]" },
            { label: "Review Queue", value: stats.pending, icon: History, color: stats.pending > 0 ? "text-amber-400" : "text-white/20" },
            { label: "Platform Rev", value: stats.revenue, icon: TrendingUp, color: "text-purple-400" },
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

        {/* ── Discovery & Registry ── */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
               <div className="relative w-64">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" />
                  <input placeholder="Filter by asset..." className="w-full rounded-sm border border-white/10 bg-white/5 pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-amber-500/50" />
               </div>
               <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
                 className="rounded-sm border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-xs text-white/60 focus:outline-none">
                 <option value="">ALL STATUS</option>
                 {["pending", "active", "rejected", "suspended"].map((s) => <option key={s} value={s}>{s.toUpperCase()}</option>)}
               </select>
            </div>
            <span className="font-['JetBrains_Mono'] text-[10px] text-white/20 uppercase tracking-widest">{list.length} assets registered</span>
          </div>

          <AdminTable
            loading={loading}
            data={list}
            onRowClick={setSelected}
            pagination={{ page: 1, total: list.length, limit: 200, onChange: () => {} }}
            columns={[
              { key: "id", label: "SKU", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-white/30">#PKG_${String(v).slice(0, 8)}</span> },
              { key: "name", label: "Asset Name", render: (v) => <span className="font-bold text-xs">{v}</span> },
              { key: "category", label: "Vertical", render: (v) => <span className="text-[10px] font-bold text-white/40 uppercase">{v}</span> },
              { key: "model_key", label: "Engine Reference", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] text-purple-400 font-bold uppercase">{v}</span> },
              { key: "price_per_call", label: "Unit Price", render: (v) => <span className="font-['JetBrains_Mono'] text-[10px] font-bold text-[#00E676]">{v} VIT</span> },
              { key: "is_active", label: "Operational State", render: (v) => <AdminStatusPill status={v ? "active" : "pending"} /> },
              {
                key: "id", label: "Tactical",
                render: (id, row) => (
                  <div className="flex gap-2">
                    {!row.is_active && (
                      <button onClick={(e) => { e.stopPropagation(); setSelected(row); setApproveConfirm(true); }}
                        className="rounded-sm bg-[#00E676]/10 border border-[#00E676]/20 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[#00E676] hover:bg-[#00E676]/20 transition-all">approve</button>
                    )}
                    <button onClick={(e) => { e.stopPropagation(); setSelected(row); setRejectModal(true); }}
                      className="rounded-sm bg-yellow-400/10 border border-yellow-400/20 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-yellow-400 hover:bg-yellow-400/20 transition-all">audit</button>
                    <button onClick={(e) => { e.stopPropagation(); setSelected(row); setDeleteConfirm(true); }}
                      className="rounded-sm bg-red-500/10 border border-red-500/20 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-red-400 hover:bg-red-500/20 transition-all">purge</button>
                  </div>
                ),
              },
            ]}
            emptyMessage="No marketplace assets detected"
          />
        </div>
      </div>

      {/* ── Asset Intelligence Detail ── */}
      <AdminModal isOpen={!!selected && !approveConfirm && !rejectModal && !deleteConfirm} onClose={() => setSelected(null)} title={`Asset Profile — #PKG_${selected?.id?.slice(0,8)}`} width="max-w-3xl">
        {selected && (
          <div className="flex flex-col gap-6 p-2">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
               <div className="md:col-span-4 flex flex-col gap-4">
                  <div className="rounded-sm border border-white/10 bg-white/[0.01] p-5 flex flex-col items-center text-center gap-3">
                     <div className="w-20 h-20 rounded-sm bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                        <Package size={40} className="text-amber-400" />
                     </div>
                     <div>
                        <h2 className="text-md font-bold text-white">{selected.name}</h2>
                        <span className="text-[9px] font-mono text-white/30 uppercase tracking-widest">SKU: {selected.id}</span>
                     </div>
                     <AdminStatusPill status={selected.is_active ? "active" : "pending"} />
                  </div>
                  <div className="rounded-sm border border-white/10 bg-white/[0.01] p-4 space-y-3">
                     <div className="flex items-center justify-between text-[11px]">
                        <span className="text-white/40 font-bold uppercase">Base License</span>
                        <span className="text-[#00E676] font-mono">{selected.price_per_call} VIT</span>
                     </div>
                     <div className="flex items-center justify-between text-[11px]">
                        <span className="text-white/40 font-bold uppercase">Volume (24h)</span>
                        <span className="text-white font-mono">142 calls</span>
                     </div>
                     <div className="flex items-center justify-between text-[11px]">
                        <span className="text-white/40 font-bold uppercase">Platform Fee</span>
                        <span className="text-white font-mono">15%</span>
                     </div>
                  </div>
               </div>

               <div className="md:col-span-8 flex flex-col gap-6">
                  <div className="rounded-sm border border-white/10 bg-white/[0.01] p-5">
                    <h3 className="font-['Barlow_Condensed'] text-[10px] font-bold uppercase tracking-[0.2em] text-white/40 mb-4">Metadata & Rationale</h3>
                    <div className="grid grid-cols-2 gap-4 mb-4">
                       <div className="flex flex-col gap-1">
                          <span className="text-[9px] font-bold text-white/30 uppercase">Engine Key</span>
                          <span className="text-xs font-mono text-purple-400">{selected.model_key}</span>
                       </div>
                       <div className="flex flex-col gap-1">
                          <span className="text-[9px] font-bold text-white/30 uppercase">Category</span>
                          <span className="text-xs font-bold text-white/80">{selected.category}</span>
                       </div>
                    </div>
                    <div className="flex flex-col gap-1">
                       <span className="text-[9px] font-bold text-white/30 uppercase">Description</span>
                       <p className="text-xs text-white/60 leading-relaxed italic">"{selected.description ?? "No description provided."}"</p>
                    </div>
                    {selected.gcs_uri && (
                       <div className="mt-4 pt-4 border-t border-white/5 flex flex-col gap-1">
                          <span className="text-[9px] font-bold text-white/30 uppercase">GCS Resource Link</span>
                          <span className="text-[10px] font-mono text-cyan-400/70 truncate">{selected.gcs_uri}</span>
                       </div>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    {!selected.is_active && (
                      <button onClick={() => setApproveConfirm(true)} className="flex-1 rounded-sm bg-[#00E676] py-3 text-[10px] font-bold uppercase tracking-[0.2em] text-black hover:bg-[#00c964] transition-all">APPROVE LICENSE</button>
                    )}
                    <button onClick={() => setRejectModal(true)} className="flex-1 rounded-sm border border-yellow-400/20 bg-yellow-400/10 py-3 text-[10px] font-bold uppercase tracking-widest text-yellow-400 hover:bg-yellow-400/20 transition-all">REJECT & ARCHIVE</button>
                    <button onClick={() => setDeleteConfirm(true)} className="rounded-sm border border-red-500/20 bg-red-500/10 px-6 py-3 text-[10px] font-bold uppercase tracking-widest text-red-400 hover:bg-red-500/20 transition-all">PURGE</button>
                  </div>
               </div>
            </div>
          </div>
        )}
      </AdminModal>

      {/* Reject Modal */}
      <AdminModal isOpen={rejectModal} onClose={() => setRejectModal(false)} title="Marketplace Rejection Audit">
        <div className="flex flex-col gap-4 p-2">
          <div>
            <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-white/30">Compliance Audit Rationale</label>
            <textarea value={rejectNote} onChange={(e) => setRejectNote(e.target.value)} rows={4}
              placeholder="Document the reasons for rejecting this listing..."
              className="w-full rounded-sm border border-white/10 bg-white/5 px-3 py-3 text-xs text-white focus:outline-none focus:border-red-500/50" />
          </div>
          <div className="flex gap-3">
            <button onClick={() => setRejectModal(false)} className="flex-1 rounded-sm border border-white/10 py-3 text-[10px] font-bold uppercase tracking-widest text-white/30 hover:bg-white/5 transition-all">cancel</button>
            <button onClick={handleReject} disabled={!rejectNote} className="flex-1 rounded-sm bg-red-600 py-3 text-[10px] font-bold uppercase tracking-widest text-white hover:bg-red-700 disabled:opacity-40 transition-all">confirm rejection</button>
          </div>
        </div>
      </AdminModal>

      <AdminConfirmDialog isOpen={approveConfirm} onClose={() => setApproveConfirm(false)} onConfirm={handleApprove}
        title="Approve Asset Listing" message={`Confirm public activation of "${selected?.name}" SKU? This asset will be made available for protocol participant interaction immediately.`} confirmLabel="APPROVE LIVE" />
      <AdminConfirmDialog isOpen={deleteConfirm} onClose={() => setDeleteConfirm(false)} onConfirm={handleDelete}
        title="Asset Purge" message={`Confirm permanent deletion of SKU: ${selected?.name}? This action is destructive and cannot be reversed.`}
        confirmLabel="CONFIRM PURGE" dangerous />
    </AdminLayout>
  );
}
