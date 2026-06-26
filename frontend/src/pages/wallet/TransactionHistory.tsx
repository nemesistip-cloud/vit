import React, { useState } from "react";
import { useTransactions } from "@/hooks/useWallet";
import { TransactionRow } from "@/components/wallet/TransactionRow";

const TYPE_FILTERS = ["All", "deposit", "withdrawal", "buy", "sell", "stake", "unstake", "conversion", "reward", "vault_deposit", "vault_withdrawal", "p2p_release", "referral_claim", "bridge_lock", "bridge_unlock"];
const CURRENCY_FILTERS = ["All", "VITCoin", "NGN", "USD", "USDT", "PI"];

export function TransactionHistory() {
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState("All");
  const [currencyFilter, setCurrencyFilter] = useState("All");

  const { data, isLoading, isFetching } = useTransactions(
    page,
    currencyFilter !== "All" ? currencyFilter : undefined,
    typeFilter !== "All" ? typeFilter : undefined,
  );

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-['Barlow_Condensed'] text-2xl font-bold uppercase text-white">Transaction History</h2>
          <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">
            {data?.total ?? 0} total transactions
          </p>
        </div>
        <a
          href="/api/wallet/statement/export"
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-2 rounded-lg border border-white/[0.08] text-xs font-['Outfit'] text-white/50 hover:text-white hover:border-white/20 transition-all uppercase tracking-wide"
        >
          Export CSV ↓
        </a>
      </div>

      <div className="flex flex-col gap-2">
        <div className="overflow-x-auto scrollbar-hide">
          <div className="flex gap-1 min-w-max">
            {TYPE_FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => { setTypeFilter(f); setPage(1); }}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-['Outfit'] uppercase tracking-wide whitespace-nowrap transition-all ${
                  typeFilter === f ? "bg-[#00E676]/10 text-[#00E676] border border-[#00E676]/20" : "text-white/30 hover:text-white/60 border border-transparent"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto scrollbar-hide">
          <div className="flex gap-1 min-w-max">
            {CURRENCY_FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => { setCurrencyFilter(f); setPage(1); }}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-['Outfit'] uppercase tracking-wide whitespace-nowrap transition-all ${
                  currencyFilter === f ? "bg-[#8B5CF6]/10 text-[#8B5CF6] border border-[#8B5CF6]/20" : "text-white/30 hover:text-white/60 border border-transparent"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-2 min-h-[200px]">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-[#00E676]/20 border-t-[#00E676] rounded-full animate-spin" />
          </div>
        ) : !data?.transactions.length ? (
          <div className="py-12 text-center">
            <p className="text-sm text-white/20 font-['Outfit']">No transactions found</p>
          </div>
        ) : (
          <div className={`transition-opacity ${isFetching ? "opacity-60" : ""}`}>
            {data.transactions.map((tx) => (
              <TransactionRow key={tx.id} tx={tx} />
            ))}
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg border border-white/[0.08] text-xs font-['Outfit'] text-white/40 hover:text-white disabled:opacity-30 transition-all uppercase tracking-wide"
          >
            ← Prev
          </button>
          <span className="text-xs font-['JetBrains_Mono'] text-white/40">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 rounded-lg border border-white/[0.08] text-xs font-['Outfit'] text-white/40 hover:text-white disabled:opacity-30 transition-all uppercase tracking-wide"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
