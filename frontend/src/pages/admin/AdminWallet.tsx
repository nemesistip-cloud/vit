import React, { useState } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { AdminModal } from "@/components/admin/AdminModal";
import { AdminConfirmDialog } from "@/components/admin/AdminConfirmDialog";
import { useAdminData } from "@/hooks/useAdminData";
import { adminApi } from "@/api/admin";
import { toast } from "sonner";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { useAuth } from "@/lib/auth";

type Tab = "transactions" | "withdrawals" | "vitcoin";

export default function AdminWallet() {
  const [tab, setTab] = useState<Tab>("transactions");
  const [page, setPage] = useState(1);
  const [txType, setTxType] = useState("");
  const [txStatus, setTxStatus] = useState("");
  const { user } = useAuth() as any;
  const isSuperAdmin = user?.admin_role === "super_admin";

  // Transactions
  const txParams: Record<string, any> = { page, limit: 50 };
  if (txType) txParams.type = txType;
  if (txStatus) txParams.status = txStatus;
  const { data: txData, loading: txLoading } = useAdminData<any>("/api/admin/wallet/transactions", txParams);

  // Withdrawals
  const { data: withdrawals, loading: wLoading, refetch: refetchW } = useAdminData<any[]>("/api/admin/wallet/withdrawal-queue");

  // VITCoin
  const { data: priceData, loading: priceLoading, refetch: refetchPrice } = useAdminData<any>("/api/admin/wallet/vitcoin-price");

  // Credit/Debit modal
  const [creditModal, setCreditModal] = useState(false);
  const [debitModal, setDebitModal] = useState(false);
  const [creditForm, setCreditForm] = useState({ user_id: "", amount: "", currency: "VIT", reason: "" });
  const [debitForm, setDebitForm] = useState({ user_id: "", amount: "", currency: "VIT", reason: "" });

  // Rejection modal
  const [rejectModal, setRejectModal] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  // Price override
  const [priceOverride, setPriceOverride] = useState("");
  const [priceConfirm, setPriceConfirm] = useState(false);

  const handleCredit = async () => {
    try {
      await adminApi.manualCredit({ user_id: Number(creditForm.user_id), amount: Number(creditForm.amount), currency: creditForm.currency, reason: creditForm.reason });
      toast.success("Credit applied"); setCreditModal(false);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDebit = async () => {
    try {
      await adminApi.manualDebit({ user_id: Number(debitForm.user_id), amount: Number(debitForm.amount), currency: debitForm.currency, reason: debitForm.reason });
      toast.success("Debit applied"); setDebitModal(false);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApproveWithdrawal = async (id: string) => {
    try { await adminApi.approveWithdrawal(id); toast.success("Approved"); refetchW(); }
    catch (e: any) { toast.error(e.message); }
  };

  const handleRejectWithdrawal = async () => {
    if (!rejectModal) return;
    try { await adminApi.rejectWithdrawal(rejectModal, rejectReason); toast.success("Rejected"); setRejectModal(null); setRejectReason(""); refetchW(); }
    catch (e: any) { toast.error(e.message); }
  };

  const handlePriceOverride = async () => {
    try { await adminApi.overrideVITCoinPrice(Number(priceOverride)); toast.success("Price updated"); setPriceConfirm(false); setPriceOverride(""); refetchPrice(); }
    catch (e: any) { toast.error(e.message); }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "transactions", label: "Transactions" },
    { key: "withdrawals", label: "Withdrawal Queue" },
    { key: "vitcoin", label: "VITCoin Price" },
  ];

  return (
    <AdminLayout>
      <div className="flex flex-col gap-4">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-white/10 pb-0">
          {tabs.map((t) => (
            <button key={t.key} onClick={() => { setTab(t.key); setPage(1); }}
              className={`px-5 py-2.5 font-['Outfit'] text-sm transition-colors border-b-2 -mb-px ${
                tab === t.key ? "border-[#00E676] text-[#00E676]" : "border-transparent text-white/40 hover:text-white/70"
              }`}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Transactions Tab */}
        {tab === "transactions" && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <select value={txType} onChange={(e) => { setTxType(e.target.value); setPage(1); }}
                className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
                <option value="">All types</option>
                {["deposit", "withdrawal", "subscription", "prediction_reward", "admin_credit", "admin_debit", "fee"].map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <select value={txStatus} onChange={(e) => { setTxStatus(e.target.value); setPage(1); }}
                className="rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-['Outfit'] text-sm text-white/70">
                <option value="">All status</option>
                {["pending", "completed", "failed", "reversed"].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <div className="ml-auto flex gap-2">
                <button onClick={() => setCreditModal(true)} className="rounded-lg bg-[#00E676]/10 border border-[#00E676]/30 px-4 py-2 text-xs text-[#00E676] font-['Outfit'] hover:bg-[#00E676]/20">+ Credit</button>
                <button onClick={() => setDebitModal(true)} className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-2 text-xs text-red-400 font-['Outfit'] hover:bg-red-500/20">- Debit</button>
              </div>
            </div>
            <AdminTable
              loading={txLoading}
              data={txData?.transactions ?? []}
              pagination={{ page, total: txData?.total ?? 0, limit: 50, onChange: setPage }}
              columns={[
                { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{String(v).slice(0, 8)}…</span> },
                { key: "user_id", label: "User", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">#{v}</span> },
                { key: "type", label: "Type" },
                { key: "amount", label: "Amount", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{Number(v).toLocaleString()}</span> },
                { key: "currency", label: "Currency" },
                { key: "status", label: "Status", render: (v) => <AdminStatusPill status={v} /> },
                { key: "created_at", label: "Date", render: (v) => v ? new Date(v).toLocaleString() : "—" },
              ]}
            />
          </>
        )}

        {/* Withdrawals Tab */}
        {tab === "withdrawals" && (
          <AdminTable
            loading={wLoading}
            data={withdrawals ?? []}
            pagination={{ page: 1, total: withdrawals?.length ?? 0, limit: 100, onChange: () => {} }}
            columns={[
              { key: "id", label: "ID", render: (v) => <span className="font-['JetBrains_Mono'] text-xs text-white/40">{String(v).slice(0, 8)}…</span> },
              { key: "username", label: "User" },
              { key: "email", label: "Email", render: (v) => <span className="text-xs text-white/50">{v}</span> },
              { key: "kyc_status", label: "KYC", render: (v) => <AdminStatusPill status={v ?? "unverified"} /> },
              { key: "amount", label: "Amount", render: (v) => <span className="font-['JetBrains_Mono'] text-xs">{Number(v).toLocaleString()}</span> },
              { key: "currency", label: "Currency" },
              { key: "requested_at", label: "Requested", render: (v) => v ? new Date(v).toLocaleString() : "—" },
              {
                key: "id", label: "Actions",
                render: (id, row) => (
                  <div className="flex gap-2">
                    <button onClick={(e) => { e.stopPropagation(); handleApproveWithdrawal(id); }}
                      className="rounded bg-[#00E676]/10 px-2.5 py-1 text-xs text-[#00E676] hover:bg-[#00E676]/20">Approve</button>
                    <button onClick={(e) => { e.stopPropagation(); setRejectModal(id); }}
                      className="rounded bg-red-500/10 px-2.5 py-1 text-xs text-red-400 hover:bg-red-500/20">Reject</button>
                  </div>
                ),
              },
            ]}
            emptyMessage="No pending withdrawals"
          />
        )}

        {/* VITCoin Tab */}
        {tab === "vitcoin" && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-[#00E676]/20 bg-[#00E676]/5 p-5">
                <p className="text-xs text-white/40 font-['Outfit'] uppercase tracking-widest">Current Price</p>
                <p className="mt-1 font-['JetBrains_Mono'] text-3xl font-bold text-[#00E676]">
                  ${priceData ? Number(priceData.current_price_usd).toFixed(6) : "—"}
                </p>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs text-white/40 font-['Outfit'] uppercase tracking-widest">Circulating Supply</p>
                <p className="mt-1 font-['JetBrains_Mono'] text-3xl font-bold text-white/80">
                  {priceData ? Number(priceData.circulating_supply).toLocaleString() : "—"}
                </p>
              </div>
            </div>

            {!priceLoading && priceData?.history?.length > 0 && (
              <div className="rounded-xl border border-white/10 bg-[#0d1117] p-5">
                <p className="mb-3 font-['Barlow_Condensed'] text-xs uppercase tracking-widest text-white/40">30-Day Price History</p>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={priceData.history}>
                    <XAxis dataKey="calculated_at" hide />
                    <YAxis hide domain={["auto", "auto"]} />
                    <Tooltip
                      contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                      labelStyle={{ color: "rgba(255,255,255,0.4)", fontSize: 10 }}
                      formatter={(v: any) => [`$${Number(v).toFixed(6)}`, "Price"]}
                    />
                    <Area type="monotone" dataKey="price_usd" stroke="#00E676" fill="rgba(0,230,118,0.08)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {isSuperAdmin && (
              <div className="rounded-xl border border-yellow-400/20 bg-yellow-400/5 p-5">
                <p className="mb-3 font-['Barlow_Condensed'] text-xs uppercase tracking-widest text-yellow-400">Price Override (Super Admin)</p>
                <div className="flex gap-3">
                  <input type="number" step="0.000001" min="0" value={priceOverride} onChange={(e) => setPriceOverride(e.target.value)}
                    placeholder="New price in USD"
                    className="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-2 font-['JetBrains_Mono'] text-sm text-white placeholder:text-white/30 focus:outline-none" />
                  <button onClick={() => setPriceConfirm(true)} disabled={!priceOverride}
                    className="rounded-lg bg-yellow-400/20 border border-yellow-400/30 px-5 py-2 font-['Outfit'] text-sm text-yellow-400 hover:bg-yellow-400/30 disabled:opacity-40">
                    Override
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Credit Modal */}
      <AdminModal isOpen={creditModal} onClose={() => setCreditModal(false)} title="Manual Credit">
        <div className="flex flex-col gap-4">
          {[{ key: "user_id", label: "User ID", type: "number" }, { key: "amount", label: "Amount", type: "number" }, { key: "currency", label: "Currency", type: "text" }, { key: "reason", label: "Reason", type: "text" }].map(({ key, label, type }) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-white/50">{label}</label>
              <input type={type} value={(creditForm as any)[key]} onChange={(e) => setCreditForm((f) => ({ ...f, [key]: e.target.value }))}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:outline-none" />
            </div>
          ))}
          <button onClick={handleCredit} className="rounded-lg bg-[#00E676] py-2.5 text-sm font-semibold text-black hover:bg-[#00c964]">Apply Credit</button>
        </div>
      </AdminModal>

      {/* Debit Modal */}
      <AdminModal isOpen={debitModal} onClose={() => setDebitModal(false)} title="Manual Debit">
        <div className="flex flex-col gap-4">
          {[{ key: "user_id", label: "User ID", type: "number" }, { key: "amount", label: "Amount", type: "number" }, { key: "currency", label: "Currency", type: "text" }, { key: "reason", label: "Reason", type: "text" }].map(({ key, label, type }) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-white/50">{label}</label>
              <input type={type} value={(debitForm as any)[key]} onChange={(e) => setDebitForm((f) => ({ ...f, [key]: e.target.value }))}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:outline-none" />
            </div>
          ))}
          <button onClick={handleDebit} className="rounded-lg bg-red-600 py-2.5 text-sm font-semibold text-white hover:bg-red-700">Apply Debit</button>
        </div>
      </AdminModal>

      {/* Reject Withdrawal */}
      <AdminModal isOpen={!!rejectModal} onClose={() => setRejectModal(null)} title="Reject Withdrawal">
        <div className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-xs text-white/50">Rejection reason</label>
            <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
              rows={3} className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:outline-none" />
          </div>
          <div className="flex gap-3">
            <button onClick={() => setRejectModal(null)} className="flex-1 rounded-lg border border-white/10 py-2.5 text-sm text-white/60">Cancel</button>
            <button onClick={handleRejectWithdrawal} disabled={!rejectReason} className="flex-1 rounded-lg bg-red-600 py-2.5 text-sm font-semibold text-white disabled:opacity-40">Reject</button>
          </div>
        </div>
      </AdminModal>

      <AdminConfirmDialog isOpen={priceConfirm} onClose={() => setPriceConfirm(false)} onConfirm={handlePriceOverride}
        title="Override VITCoin Price" message={`Set VITCoin price to $${priceOverride} USD? This affects all wallet balances.`}
        confirmLabel="Override" dangerous />
    </AdminLayout>
  );
}
