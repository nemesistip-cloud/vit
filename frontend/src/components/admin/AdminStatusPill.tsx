import React from "react";

const statusStyles: Record<string, string> = {
  active:     "bg-[#00E676]/15 text-[#00E676] border-[#00E676]/30",
  approved:   "bg-[#00E676]/15 text-[#00E676] border-[#00E676]/30",
  connected:  "bg-[#00E676]/15 text-[#00E676] border-[#00E676]/30",
  running:    "bg-[#8B5CF6]/15 text-[#8B5CF6] border-[#8B5CF6]/30",
  pending:    "bg-yellow-400/15 text-yellow-400 border-yellow-400/30",
  flagged:    "bg-red-500/15 text-red-400 border-red-500/30",
  rejected:   "bg-red-500/15 text-red-400 border-red-500/30",
  slashed:    "bg-red-500/15 text-red-400 border-red-500/30",
  banned:     "bg-red-500/15 text-red-400 border-red-500/30",
  inactive:   "bg-white/10 text-white/40 border-white/15",
  degraded:   "bg-white/10 text-white/40 border-white/15",
  offline:    "bg-white/10 text-white/30 border-white/10",
  suspended:  "bg-orange-500/15 text-orange-400 border-orange-500/30",
  completed:  "bg-blue-400/15 text-blue-400 border-blue-400/30",
  failed:     "bg-red-500/15 text-red-400 border-red-500/30",
  ok:         "bg-[#00E676]/15 text-[#00E676] border-[#00E676]/30",
};

interface AdminStatusPillProps {
  status: string;
  label?: string;
}

export function AdminStatusPill({ status, label }: AdminStatusPillProps) {
  const key = status?.toLowerCase() ?? "inactive";
  const style = statusStyles[key] ?? "bg-white/10 text-white/40 border-white/15";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 font-['JetBrains_Mono'] text-[10px] font-semibold uppercase tracking-wider ${style}`}
    >
      {label ?? status}
    </span>
  );
}
