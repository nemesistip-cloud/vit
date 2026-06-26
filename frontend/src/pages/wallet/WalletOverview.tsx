import React from "react";
import { Link } from "wouter";
import { useWalletOverview, useVITPrice, useVITPriceHistory, useTransactions, useStakeStatus } from "@/hooks/useWallet";
import { WalletBalanceCard } from "@/components/wallet/WalletBalanceCard";
import { TransactionRow } from "@/components/wallet/TransactionRow";
import { PriceChart } from "@/components/wallet/PriceChart";

function StatBadge({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[9px] uppercase tracking-widest text-white/30 font-['Outfit']">{label}</span>
      <span className={`font-['JetBrains_Mono'] text-sm font-bold ${positive ? "text-[#00E676]" : positive === false ? "text-red-400" : "text-white"}`}>
        {value}
      </span>
    </div>
  );
}

export function WalletOverview() {
  const { data: wallet, isLoading: walletLoading } = useWalletOverview();
  const { data: price } = useVITPrice();
  const { data: history } = useVITPriceHistory(7);
  const { data: txs } = useTransactions(1);
  const { data: stake } = useStakeStatus();

  const priceData = history?.history.map((h) => h.price_usd) ?? [];
  const change = price?.change_24h_pct ?? 0;
  const isUp = change >= 0;

  if (walletLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-8 h-8 border-2 border-[#00E676]/20 border-t-[#00E676] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-white/30 font-['Outfit']">VITCoin Balance</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-['JetBrains_Mono'] text-4xl font-black text-[#00E676]">
                {(wallet?.vitcoin_balance ?? 0).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
              </span>
              <span className="text-sm text-white/40 font-['Outfit'] uppercase">VIT</span>
            </div>
            <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">
              ≈ ${((wallet?.vitcoin_balance ?? 0) * (price?.price_usd ?? 0.1)).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 4 })} USD
            </p>
          </div>

          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-1.5">
              <span className="font-['JetBrains_Mono'] text-lg font-bold text-white">
                ${price?.price_usd?.toFixed(4) ?? "—"}
              </span>
              <span className={`text-xs font-['Outfit'] px-1.5 py-0.5 rounded font-medium ${isUp ? "bg-[#00E676]/10 text-[#00E676]" : "bg-red-500/10 text-red-400"}`}>
                {isUp ? "+" : ""}{change.toFixed(2)}%
              </span>
            </div>
            <span className="text-[9px] text-white/20 font-['Outfit'] uppercase tracking-wider">24h change</span>
          </div>
        </div>

        {priceData.length > 1 && (
          <div className="mt-4">
            <PriceChart data={priceData} height={56} showLabels />
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <WalletBalanceCard
          label="NGN"
          amount={wallet?.ngn_balance ?? 0}
          symbol="₦"
          subLabel="USD"
          subAmount={(wallet?.ngn_balance ?? 0) * 0.00063}
        />
        <WalletBalanceCard
          label="USDT"
          amount={wallet?.usdt_balance ?? 0}
          symbol="₮"
        />
        <WalletBalanceCard
          label="USD"
          amount={wallet?.usd_balance ?? 0}
          symbol="$"
        />
        <WalletBalanceCard
          label="Pi"
          amount={wallet?.pi_balance ?? 0}
          symbol="π"
        />
        <WalletBalanceCard
          label="Staked VIT"
          amount={wallet?.staked_vitcoin ?? 0}
          symbol="VIT"
          highlight={!!wallet?.staked_vitcoin && wallet.staked_vitcoin > 0}
          subLabel="Daily est."
          subAmount={stake?.estimated_daily_reward?.toFixed(6) ?? "0"}
        />
        <WalletBalanceCard
          label="Portfolio USD"
          amount={wallet?.total_balance_usd ?? 0}
          symbol="$"
          highlight
        />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
        <StatBadge label="30d Earnings" value={`${wallet?.earnings_30d?.toFixed(4) ?? "0"} VIT`} positive={!!wallet?.earnings_30d} />
        <StatBadge label="Pending Withdrawal" value={`₦${(wallet?.pending_withdrawals_total ?? 0).toLocaleString()}`} />
        <StatBadge label="KYC Status" value={wallet?.kyc_verified ? "Verified" : "Pending"} positive={wallet?.kyc_verified} />
        <StatBadge label="Validator" value={stake?.validator_eligible ? "Eligible" : "Need 100 VIT"} positive={stake?.validator_eligible} />
      </div>

      <div className="flex gap-2 flex-wrap">
        {[
          { label: "Deposit", href: "/wallet/deposit" },
          { label: "Withdraw", href: "/wallet/withdraw" },
          { label: "Buy VIT", href: "/wallet/buy-sell" },
          { label: "Convert", href: "/wallet/convert" },
          { label: "Stake", href: "/wallet/stake" },
        ].map((btn) => (
          <Link key={btn.href} href={btn.href}>
            <button className="px-4 py-2 rounded-lg text-xs font-['Outfit'] font-medium uppercase tracking-wide border border-white/[0.08] hover:border-[#00E676]/30 hover:text-[#00E676] text-white/60 transition-all">
              {btn.label}
            </button>
          </Link>
        ))}
      </div>

      {txs && txs.transactions.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-['Barlow_Condensed'] text-lg font-bold uppercase text-white/80">Recent Transactions</h2>
            <Link href="/wallet/history">
              <span className="text-[10px] text-[#00E676]/60 hover:text-[#00E676] font-['Outfit'] uppercase tracking-widest cursor-pointer">
                View All →
              </span>
            </Link>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-2">
            {txs.transactions.slice(0, 5).map((tx) => (
              <TransactionRow key={tx.id} tx={tx} compact />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
