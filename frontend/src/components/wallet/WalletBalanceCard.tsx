import React from "react";

interface WalletBalanceCardProps {
  label: string;
  amount: number | string;
  symbol?: string;
  subLabel?: string;
  subAmount?: number | string;
  highlight?: boolean;
  icon?: React.ReactNode;
}

export function WalletBalanceCard({
  label,
  amount,
  symbol = "",
  subLabel,
  subAmount,
  highlight = false,
  icon,
}: WalletBalanceCardProps) {
  const fmt = (v: number | string) =>
    typeof v === "number"
      ? v.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 6 })
      : v;

  return (
    <div
      className={`
        relative rounded-xl border p-4 flex flex-col gap-1 transition-all
        ${highlight
          ? "border-[#00E676]/40 bg-[#00E676]/5"
          : "border-white/[0.06] bg-white/[0.02]"}
      `}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">
          {label}
        </span>
        {icon && <span className="opacity-60">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-1.5 mt-1">
        <span
          className={`font-['JetBrains_Mono'] text-xl font-bold ${
            highlight ? "text-[#00E676]" : "text-white"
          }`}
        >
          {fmt(amount)}
        </span>
        {symbol && (
          <span className="text-xs text-white/40 font-['Outfit'] uppercase">{symbol}</span>
        )}
      </div>
      {subLabel && subAmount !== undefined && (
        <div className="flex items-center gap-1 mt-0.5">
          <span className="text-[10px] text-white/30 font-['Outfit']">{subLabel}</span>
          <span className="text-[10px] font-['JetBrains_Mono'] text-white/50">{fmt(subAmount)}</span>
        </div>
      )}
    </div>
  );
}
