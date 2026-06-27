import React, { useEffect, useRef } from "react";
import { useToast } from "@/hooks/use-toast";
import { Link } from "wouter";
import {
  Send,
  Download,
  ShoppingCart,
  Repeat,
  ArrowRight,
  ShieldCheck,
  ShieldAlert
} from "lucide-react";
import {
  useWalletOverview,
  useVITPrice,
  useVITPriceHistory,
  useTransactions,
  useStakeStatus
} from "@/hooks/useWallet";
import { WalletBalanceCard } from "@/components/wallet/WalletBalanceCard";
import { TransactionRow } from "@/components/wallet/TransactionRow";
import { PriceChart } from "@/components/wallet/PriceChart";

export function WalletOverview() {
  const { toast } = useToast();
  const prevBalanceRef = useRef<number | null>(null);
  const { data: wallet, isLoading: walletLoading } = useWalletOverview();
  const { data: price } = useVITPrice();
  const { data: history } = useVITPriceHistory(7);
  const { data: txs } = useTransactions(1);
  const { data: stake } = useStakeStatus();

  const priceData = history?.history.map((h) => h.price_usd) ?? [];
  const change = price?.change_24h_pct ?? 0;
  const isUp = change >= 0;

  useEffect(() => {
    if (wallet && prevBalanceRef.current !== null) {
      const diff = wallet.vitcoin_balance - prevBalanceRef.current;
      if (diff > 0.01) {
        toast({
          title: "Funds Received!",
          description: `+${diff.toLocaleString()} VIT has arrived in your wallet.`,
        });
      }
    }
    if (wallet) {
      prevBalanceRef.current = wallet.vitcoin_balance;
    }
  }, [wallet?.vitcoin_balance, toast]);

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
            <p className="text-[10px] uppercase tracking-widest text-white/30 font-['Outfit']">Total Balance</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-['JetBrains_Mono'] text-[36pt] leading-none font-black text-[#00E676]">
                {(wallet?.vitcoin_balance ?? 0).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
              </span>
              <span className="text-[14pt] text-white/40 font-['Outfit'] font-regular uppercase">VIT</span>
            </div>

            <div className="flex items-center gap-1.5 mt-2">
              {wallet?.kyc_verified ? (
                <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                  <ShieldCheck size={10} className="text-emerald-400" />
                  <span className="text-[9px] font-bold text-emerald-400 uppercase tracking-widest">Fully Protected</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                  <ShieldAlert size={10} className="text-amber-400" />
                  <span className="text-[9px] font-bold text-amber-400 uppercase tracking-widest">Action Required</span>
                </div>
              )}
            </div>

            <p className="text-[16pt] text-white/40 font-['Outfit'] font-light mt-1">
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
            <span className="text-[9px] text-white/40 font-['Outfit'] uppercase tracking-wider">VIT Price (24h)</span>
          </div>
        </div>

        {priceData.length > 1 && (
          <div className="mt-4">
            <PriceChart data={priceData} height={56} showLabels />
          </div>
        )}
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Send", href: "/wallet/withdraw", icon: Send, color: "bg-blue-500" },
          { label: "Receive", href: "/wallet/deposit", icon: Download, color: "bg-emerald-500" },
          { label: "Buy", href: "/wallet/buy-sell", icon: ShoppingCart, color: "bg-amber-500" },
          { label: "Swap", href: "/wallet/convert", icon: Repeat, color: "bg-purple-500" },
        ].map((action) => (
          <Link key={action.label} href={action.href}>
            <button className="flex flex-col items-center gap-2 group w-full">
              <div className={`w-12 h-12 rounded-full ${action.color} flex items-center justify-center text-white shadow-lg group-hover:scale-110 transition-transform`}>
                <action.icon size={20} />
              </div>
              <span className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit'] group-hover:text-white transition-colors">
                {action.label}
              </span>
            </button>
          </Link>
        ))}
      </div>

      <div className="space-y-6">
        <div>
          <h3 className="text-[10px] uppercase tracking-[0.2em] text-white/30 font-['Outfit'] mb-3 px-1">Tokens</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <WalletBalanceCard
              label="VITCoin"
              amount={wallet?.vitcoin_balance ?? 0}
              symbol="VIT"
              highlight
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
              label="NGN"
              amount={wallet?.ngn_balance ?? 0}
              symbol="₦"
              subLabel="USD"
              subAmount={(wallet?.ngn_balance ?? 0) * 0.00063}
            />
            <WalletBalanceCard
              label="Pi"
              amount={wallet?.pi_balance ?? 0}
              symbol="π"
            />
          </div>
        </div>

        <div>
          <h3 className="text-[10px] uppercase tracking-[0.2em] text-white/30 font-['Outfit'] mb-3 px-1">Pool Positions</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
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
        </div>
      </div>

      <div className="rounded-xl border border-[#00E676]/20 bg-[#00E676]/5 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Repeat size={14} className="text-[#00E676]" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-white">Quick Convert</span>
          </div>
          <Link href="/wallet/convert">
            <span className="text-[9px] text-[#00E676] uppercase tracking-widest hover:underline cursor-pointer">Advanced Swap</span>
          </Link>
        </div>
        <div className="flex items-center justify-between bg-black/20 rounded-lg p-3">
          <div className="flex flex-col">
            <span className="text-[9px] text-white/30 uppercase font-['Outfit']">Swap 100 VIT</span>
            <span className="text-sm font-bold text-white font-['JetBrains_Mono']">100.00 VIT</span>
          </div>
          <ArrowRight size={14} className="text-white/20" />
          <div className="flex flex-col items-end text-right">
            <span className="text-[9px] text-white/30 uppercase font-['Outfit']">Receive USD</span>
            <span className="text-sm font-bold text-[#00E676] font-['JetBrains_Mono']">≈ $10.00 USD</span>
          </div>
        </div>
        <Link href="/wallet/convert">
          <button className="w-full mt-3 py-2 bg-[#00E676] text-black rounded-lg text-[10px] font-bold uppercase tracking-widest hover:opacity-90 transition-opacity">
            Instant Convert
          </button>
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-white/30 font-['Outfit']">Lifetime Rewards</span>
          <span className="font-['JetBrains_Mono'] text-xl font-bold text-[#00E676]">
            {(wallet?.earnings_total ?? wallet?.earnings_30d ?? 0).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 4 })} VIT
          </span>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-white/30 font-['Outfit']">Pending Withdrawals</span>
          <span className="font-['JetBrains_Mono'] text-xl font-bold text-white">
            ₦{(wallet?.pending_withdrawals_total ?? 0).toLocaleString()}
          </span>
        </div>
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
