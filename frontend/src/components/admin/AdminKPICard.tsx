import React from "react";

type CardColor = "green" | "purple" | "red" | "yellow" | "blue";

const colorMap: Record<CardColor, { border: string; text: string; bg: string }> = {
  green:  { border: "border-[#00E676]/20", text: "text-[#00E676]",  bg: "bg-[#00E676]/5"  },
  purple: { border: "border-[#8B5CF6]/20", text: "text-[#8B5CF6]",  bg: "bg-[#8B5CF6]/5"  },
  red:    { border: "border-red-500/20",   text: "text-red-400",    bg: "bg-red-500/5"    },
  yellow: { border: "border-yellow-400/20",text: "text-yellow-400", bg: "bg-yellow-400/5" },
  blue:   { border: "border-blue-400/20",  text: "text-blue-400",   bg: "bg-blue-400/5"   },
};

interface AdminKPICardProps {
  label: string;
  value: string | number;
  delta?: string;
  color?: CardColor;
  icon?: React.ReactNode;
  loading?: boolean;
}

export function AdminKPICard({
  label,
  value,
  delta,
  color = "green",
  icon,
  loading = false,
}: AdminKPICardProps) {
  const c = colorMap[color];
  const isPositiveDelta = delta?.startsWith("+");
  const isNegativeDelta = delta?.startsWith("-");

  return (
    <div className={`rounded-xl border ${c.border} ${c.bg} p-4`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="font-['Outfit'] text-xs uppercase tracking-widest text-white/40">{label}</p>
          {loading ? (
            <div className="mt-2 h-7 w-24 animate-pulse rounded bg-white/10" />
          ) : (
            <p className={`mt-1 font-['JetBrains_Mono'] text-2xl font-bold ${c.text}`}>
              {value}
            </p>
          )}
          {delta && !loading && (
            <p
              className={`mt-1 font-['JetBrains_Mono'] text-xs ${
                isPositiveDelta ? "text-[#00E676]" : isNegativeDelta ? "text-red-400" : "text-white/40"
              }`}
            >
              {delta}
            </p>
          )}
        </div>
        {icon && (
          <div className={`rounded-lg p-2 ${c.bg}`}>
            <span className={c.text}>{icon}</span>
          </div>
        )}
      </div>
    </div>
  );
}
