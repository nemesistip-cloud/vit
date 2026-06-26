import React, { useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";

export default function AdminConfig() {
  const { user } = useAuth() as any;
  const isSuperAdmin = user?.admin_role === "super_admin";

  const { data: config, loading, refetch } = useAdminData<any[]>("/api/admin/config");

  const [selected, setSelected] = useState<any>(null);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  // Create new
  const [createModal, setCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({ key: "", value: "", description: "" });
  const [creating, setCreating] = useState(false);

  const openEdit = (row: any) => {
    setSelected(row);
    setEditValue(typeof row.value === "string" ? row.value : JSON.stringify(row.value, null, 2));
  };

  const parseValue = (raw: string) => {
    try { return JSON.parse(raw); } catch { return raw; }
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await adminApi.updateConfig(selected.key, parseValue(editValue));
      toast.success(`Config updated: ${selected.key}`);
      refetch();
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!selected) return;
    try {
      await adminApi.deleteConfig(selected.key);
      toast.success(`Config deleted: ${selected.key}`);
      refetch();
      setDeleteConfirm(false);
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreate = async () => {
    if (!createForm.key) return;
    setCreating(true);
    try {
      await adminApi.createConfig({ key: createForm.key, value: parseValue(createForm.value), description: createForm.description });
      toast.success(`Config created: ${createForm.key}`);
      refetch();
      setCreateModal(false);
      setCreateForm({ key: "", value: "", description: "" });
    } catch (e: any) { toast.error(e.message); }
    finally { setCreating(false); }
  };

  const configList = config ?? [];

  return (
    <AdminLayout>
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <span className="font-['JetBrains_Mono'] text-xs text-white/30">{configList.length} config keys</span>
          {isSuperAdmin && (
            <button onClick={() => setCreateModal(true)}
              className="rounded-lg bg-[#00E676]/10 border border-[#00E676]/30 px-4 py-2 font-['Outfit'] text-xs text-[#00E676] hover:bg-[#00E676]/20">
              + New Config Key
            </button>
          )}
        </div>

        <AdminTable
          loading={loading}
          data={configList}
          onRowClick={openEdit}
          pagination={{ page: 1, total: configList.length, limit: 200, onChange: () => {} }}
          columns={[
            { key: "key", label: "Key", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-[#00E676]">{v}</span> },
            {
              key: "value", label: "Value",
              render: (v) => {
                const display = typeof v === "string" ? v : JSON.stringify(v);
                return <span className="font-['JetBrains_Mono'] text-xs text-white/60 line-clamp-1 max-w-xs">{display}</span>;
              },
            },
            { key: "description", label: "Description", render: (v) => <span className="text-xs text-white/40">{v ?? "—"}</span> },
            { key: "updated_at", label: "Updated", render: (v) => v ? new Date(v).toLocaleString() : "—" },
          ]}
          emptyMessage="No platform config found"
        />
      </div>

      {/* Edit Modal */}
      <AdminModal isOpen={!!selected} onClose={() => setSelected(null)} title={`Config: ${selected?.key}`} width="max-w-2xl">
        {selected && (
          <div className="flex flex-col gap-4">
            <div>
              <p className="mb-1 text-xs text-white/40">{selected.description ?? "No description"}</p>
              <p className="font-['JetBrains_Mono'] text-xs text-white/30">Last updated: {selected.updated_at ? new Date(selected.updated_at).toLocaleString() : "—"}</p>
            </div>
            <div>
              <label className="mb-1 block text-xs text-white/50">Value (JSON or plain string)</label>
              <textarea value={editValue} onChange={(e) => setEditValue(e.target.value)} rows={6}
                className="w-full rounded-lg border border-white/10 bg-[#0a0f16] px-4 py-3 font-['JetBrains_Mono'] text-sm text-white focus:border-[#00E676]/40 focus:outline-none" />
            </div>
            <div className="flex gap-3">
              <button onClick={handleSave} disabled={saving}
                className="flex-1 rounded-lg bg-[#00E676] py-2.5 font-['Outfit'] text-sm font-semibold text-black hover:bg-[#00c964] disabled:opacity-40">
                {saving ? "Saving…" : "Save"}
              </button>
              {isSuperAdmin && (
                <button onClick={() => setDeleteConfirm(true)}
                  className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 font-['Outfit'] text-xs text-red-400 hover:bg-red-500/20">
                  Delete
                </button>
              )}
            </div>
          </div>
        )}
      </AdminModal>

      {/* Create Modal */}
      <AdminModal isOpen={createModal} onClose={() => setCreateModal(false)} title="Create Config Key" width="max-w-lg">
        <div className="flex flex-col gap-4">
          {[
            { key: "key", label: "Config Key", placeholder: "e.g. feature_flags.predictions", rows: 1 },
            { key: "description", label: "Description", placeholder: "What does this control?", rows: 1 },
            { key: "value", label: "Value (JSON or string)", placeholder: '{"enabled": true}', rows: 4 },
          ].map(({ key, label, placeholder, rows }) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-white/50">{label}</label>
              {rows > 1 ? (
                <textarea rows={rows} value={(createForm as any)[key]}
                  onChange={(e) => setCreateForm((f) => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full rounded-lg border border-white/10 bg-[#0a0f16] px-3 py-2 font-['JetBrains_Mono'] text-sm text-white placeholder:text-white/20 focus:outline-none" />
              ) : (
                <input type="text" value={(createForm as any)[key]}
                  onChange={(e) => setCreateForm((f) => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full rounded-lg border border-white/10 bg-[#0a0f16] px-3 py-2 font-['Outfit'] text-sm text-white placeholder:text-white/20 focus:outline-none" />
              )}
            </div>
          ))}
          <button onClick={handleCreate} disabled={creating || !createForm.key}
            className="rounded-lg bg-[#00E676] py-2.5 font-['Outfit'] text-sm font-semibold text-black hover:bg-[#00c964] disabled:opacity-40">
            {creating ? "Creating…" : "Create Config Key"}
          </button>
        </div>
      </AdminModal>

      <AdminConfirmDialog isOpen={deleteConfirm} onClose={() => setDeleteConfirm(false)} onConfirm={handleDelete}
        title="Delete Config Key" message={`Permanently delete config key "${selected?.key}"? This may break features that depend on it.`}
        confirmLabel="Delete" dangerous />
    </AdminLayout>
  );
}
