import React from "react";
import type { WalletTx } from "@/hooks/useWallet";

const TYPE_LABELS: Record<string, string> = {
  deposit: "Deposit",
  withdrawal: "Withdrawal",
  buy: "Buy VITCoin",
  sell: "Sell VITCoin",
  conversion: "Convert",
  stake: "Stake",
  unstake: "Unstake",
  reward: "Reward",
  earn: "Earn",
  fee: "Fee",
  p2p_escrow: "P2P Escrow",
  p2p_release: "P2P Release",
  p2p_refund: "P2P Refund",
  vault_deposit: "Vault Deposit",
  vault_withdrawal: "Vault Withdrawal",
  referral_claim: "Referral Claim",
  bridge_lock: "Bridge Lock",
  bridge_unlock: "Bridge Unlock",
  subscription: "Subscription",
  welcome_bonus: "Welcome Bonus",
};

const STATUS_COLOR: Record<string, string> = {
  confirmed: "text-[#00E676]",
  pending: "text-yellow-400",
  failed: "text-red-400",
  reversed: "text-orange-400",
};

const CURRENCY_SYMBOLS: Record<string, string> = {
  NGN: "₦",
  USD: "$",
  USDT: "₮",
  PI: "π",
  VITCoin: "VIT",
};

interface TransactionRowProps {
  tx: WalletTx;
  compact?: boolean;
}

export function TransactionRow({ tx, compact = false }: TransactionRowProps) {
  const isCredit = tx.direction === "credit";
  const label = TYPE_LABELS[tx.type] ?? tx.type;
  const symbol = CURRENCY_SYMBOLS[tx.currency] ?? tx.currency;
  const statusClass = STATUS_COLOR[tx.status] ?? "text-white/50";
  const date = new Date(tx.created_at);
  const dateStr = compact
    ? date.toLocaleDateString("en", { month: "short", day: "numeric" })
    : date.toLocaleString("en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });

  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/[0.04] last:border-0 gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold
            ${isCredit ? "bg-[#00E676]/10 text-[#00E676]" : "bg-red-500/10 text-red-400"}`}
        >
          {isCredit ? "+" : "−"}
        </div>
        <div className="min-w-0">
          <p className="text-sm text-white font-['Outfit'] truncate">{label}</p>
          {!compact && tx.description && (
            <p className="text-[10px] text-white/30 font-['Outfit'] truncate">{tx.description}</p>
          )}
          <p className="text-[10px] text-white/20 font-['JetBrains_Mono']">{dateStr}</p>
        </div>
      </div>
      <div className="text-right flex-shrink-0">
        <p
          className={`font-['JetBrains_Mono'] text-sm font-semibold ${
            isCredit ? "text-[#00E676]" : "text-white/70"
          }`}
        >
          {isCredit ? "+" : "−"}
          {tx.amount.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 6 })}{" "}
          <span className="text-[10px] font-normal">{symbol}</span>
        </p>
        <p className={`text-[10px] font-['Outfit'] ${statusClass}`}>{tx.status}</p>
      </div>
    </div>
  );
}
