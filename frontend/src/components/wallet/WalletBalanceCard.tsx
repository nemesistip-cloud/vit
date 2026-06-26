import React from "react";
import { Plus } from "lucide-react";

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
  const fmt = (v: number | string) => {
    if (typeof v === "number") {
      if (v === 0) return "0";
      return v.toLocaleString("en", {
        minimumFractionDigits: 2,
        maximumFractionDigits: v < 1 ? 6 : 2
      });
    }
    return v;
  };

  return (
    <div
      className={`
        relative rounded-xl border p-4 flex flex-col gap-1 transition-all overflow-hidden
        backdrop-blur-sm shadow-xl hover:shadow-2xl hover:border-white/10
        ${highlight
          ? "border-[#00E676]/40 bg-[#00E676]/10"
          : "border-white/[0.06] bg-white/[0.03]"}
      `}
    >
      {/* Animated gradient background for highlight cards */}
      {highlight && (
        <div className="absolute inset-0 -z-10 opacity-10 bg-gradient-to-br from-[#00E676] via-transparent to-emerald-500 animate-pulse" />
      )}

      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">
          {label}
        </span>
        {icon && <span className="opacity-60">{icon}</span>}
      </div>

      <div className="flex items-baseline gap-1.5 mt-1">
        {Number(amount) === 0 ? (
          <button className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/[0.05] border border-dashed border-white/10 text-[10px] text-white/40 hover:text-white hover:border-white/30 transition-all font-bold uppercase tracking-wider">
            <Plus size={10} /> Add {label}
          </button>
        ) : (
          <>
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
          </>
        )}
      </div>

      {subLabel && subAmount !== undefined && Number(subAmount) !== 0 && (
        <div className="flex items-center gap-1 mt-0.5">
          <span className="text-[10px] text-white/30 font-['Outfit']">{subLabel}</span>
          <span className="text-[10px] font-['JetBrains_Mono'] text-white/50">{fmt(subAmount)}</span>
        </div>
      )}
    </div>
  );
}
