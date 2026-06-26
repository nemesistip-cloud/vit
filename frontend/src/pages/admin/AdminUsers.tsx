import React, { useState, useCallback, useEffect } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { adminApi } from "@/api/admin";
import { useAdminData } from "@/hooks/useAdminData";
import { toast } from "sonner";

const ROLES = ["user", "admin", "validator"];
const TIERS = ["free", "viewer", "analyst", "pro", "elite"];

function useDebounce<T>(value: T, ms: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => { const t = setTimeout(() => setDebounced(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return debounced;
}

export default function AdminUsers() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [tier, setTier] = useState("");
  const [isActive, setIsActive] = useState<string>("");
  const debouncedSearch = useDebounce(search, 300);

  const params: Record<string, any> = { page, limit: 50 };
  if (debouncedSearch) params.search = debouncedSearch;
  if (role) params.role = role;
  if (tier) params.subscription_tier = tier;
  if (isActive !== "") params.is_active = isActive === "true";

  const { data, loading, refetch } = useAdminData<any>("/api/admin/users", params);

  const [selected, setSelected] = useState<any>(null);
  const [editForm, setEditForm] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [resetConfirm, setResetConfirm] = useState(false);

  const openUser = (row: any) => { setSelected(row); setEditForm({ role: row.role, subscription_tier: row.subscription_tier, is_active: row.is_active, withdrawals_frozen: row.withdrawals_frozen, is_flagged: row.is_flagged }); };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await adminApi.updateUser(selected.id, editForm);
      toast.success("User updated");
      refetch();
      setSelected(null);
    } catch (e: any) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  const handleReset = async () => {
    if (!selected) return;
    try { await adminApi.resetUserPassword(selected.id); toast.success("Reset email sent"); setResetConfirm(false); }
    catch (e: any) { toast.error(e.message); }
  };

  const handleDelete = async () => {
    if (!selected) return;
    try { await adminApi.deleteUser(selected.id); toast.success("User deactivated"); refetch(); setDeleteConfirm(false); setSelected(null); }
    catch (e: any) { toast.error(e.message); }
  };

  const handleExport = async () => {
    try {
      const blob = await adminApi.exportUsers({ search: debouncedSearch, role: role || undefined, subscription_tier: tier || undefined });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "users.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) { toast.error(e.message); }
  };

  const users = data?.users ?? [];
  const total = data?.total ?? 0;

  return (
    <AdminLayout>
      <div className="flex flex-col gap-4">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search username or email…"
            className="flex-1 min-w-48 rounded-lg border border-white/10 bg-white/5 px-4 py-2 font-['Outfit'] text-sm text-white placeholder:text-white/30 focus:border-[#00E676]/40 focus:outline-none"
          />
          <select value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }}
            className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
            <option value="">All roles</option>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={tier} onChange={(e) => { setTier(e.target.value); setPage(1); }}
            className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
            <option value="">All tiers</option>
            {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={isActive} onChange={(e) => { setIsActive(e.target.value); setPage(1); }}
            className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
            <option value="">All status</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
          <button onClick={handleExport}
            className="rounded-lg border border-[#00E676]/30 bg-[#00E676]/10 px-4 py-2 font-['Outfit'] text-xs text-[#00E676] hover:bg-[#00E676]/20">
            Export CSV
          </button>
        </div>

        {/* Table */}
        <AdminTable
          loading={loading}
          data={users}
          onRowClick={openUser}
          pagination={{ page, total, limit: 50, onChange: setPage }}
          columns={[
            { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">#{v}</span> },
            { key: "username", label: "Username", render: (v) => <span className="font-semibold">{v}</span> },
            { key: "email", label: "Email", render: (v) => <span className="text-white/60 text-xs">{v}</span> },
            { key: "role", label: "Role", render: (v) => <AdminStatusPill status={v === "admin" ? "active" : "inactive"} label={v} /> },
            { key: "subscription_tier", label: "Tier" },
            { key: "is_active", label: "Status", render: (v) => <AdminStatusPill status={v ? "active" : "inactive"} /> },
            { key: "wallet_balance", label: "Balance", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{Number(v).toLocaleString()} VIT</span> },
            { key: "prediction_count", label: "Predictions", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{v}</span> },
            { key: "created_at", label: "Joined", render: (v) => v ? new Date(v).toLocaleDateString() : "—" },
          ]}
        />
      </div>

      {/* User Detail Slide-over */}
      <AdminModal isOpen={!!selected} onClose={() => setSelected(null)} title={`User #${selected?.id} — ${selected?.username}`} width="max-w-xl">
        {selected && (
          <div className="flex flex-col gap-5">
            <div className="grid grid-cols-2 gap-3 rounded-lg bg-white/5 p-4 text-sm">
              <div><span className="text-white/40 text-xs">Email</span><p className="text-white/80">{selected.email}</p></div>
              <div><span className="text-white/40 text-xs">KYC</span><p><AdminStatusPill status={selected.kyc_status ?? "unverified"} /></p></div>
              <div><span className="text-white/40 text-xs">Balance</span><p className="font-['JetBrains_Mono']">{Number(selected.wallet_balance).toLocaleString()} VIT</p></div>
              <div><span className="text-white/40 text-xs">Predictions</span><p className="font-['JetBrains_Mono']">{selected.prediction_count}</p></div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block font-['Outfit'] text-xs text-white/50">Role</label>
                <select value={editForm.role} onChange={(e) => setEditForm((f: any) => ({ ...f, role: e.target.value }))}
                  className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 text-sm text-white">
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block font-['Outfit'] text-xs text-white/50">Tier</label>
                <select value={editForm.subscription_tier} onChange={(e) => setEditForm((f: any) => ({ ...f, subscription_tier: e.target.value }))}
                  className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 text-sm text-white">
                  {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              {[
                { key: "is_active", label: "Account Active" },
                { key: "withdrawals_frozen", label: "Freeze Withdrawals" },
                { key: "is_flagged", label: "Flag Account" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center gap-3 rounded-lg bg-white/5 px-4 py-2.5 cursor-pointer">
                  <input type="checkbox" checked={!!editForm[key]}
                    onChange={(e) => setEditForm((f: any) => ({ ...f, [key]: e.target.checked }))}
                    className="h-4 w-4 accent-[#00E676]" />
                  <span className="font-['Outfit'] text-sm text-white/70">{label}</span>
                </label>
              ))}
            </div>

            <div className="flex gap-2">
              <button onClick={handleSave} disabled={saving}
                className="flex-1 rounded-lg bg-[#00E676] py-2.5 font-['Outfit'] text-sm font-semibold text-black hover:bg-[#00c964] disabled:opacity-40">
                {saving ? "Saving…" : "Save Changes"}
              </button>
              <button onClick={() => setResetConfirm(true)}
                className="rounded-lg border border-yellow-400/30 bg-yellow-400/10 px-4 py-2.5 font-['Outfit'] text-xs text-yellow-400 hover:bg-yellow-400/20">
                Reset Password
              </button>
              <button onClick={() => setDeleteConfirm(true)}
                className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 font-['Outfit'] text-xs text-red-400 hover:bg-red-500/20">
                Delete
              </button>
            </div>
          </div>
        )}
      </AdminModal>

      <AdminConfirmDialog isOpen={resetConfirm} onClose={() => setResetConfirm(false)} onConfirm={handleReset}
        title="Reset Password" message={`Send password reset email to ${selected?.email}?`} confirmLabel="Send Reset" />
      <AdminConfirmDialog isOpen={deleteConfirm} onClose={() => setDeleteConfirm(false)} onConfirm={handleDelete}
        title="Deactivate User" message={`Deactivate ${selected?.username}? This sets is_active=false.`}
        confirmLabel="Deactivate" dangerous />
    </AdminLayout>
  );
}
