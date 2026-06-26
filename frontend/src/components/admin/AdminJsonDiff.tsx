import React from "react";

interface AdminJsonDiffProps {
  before?: Record<string, any> | null;
  after?: Record<string, any> | null;
}

function classifyKeys(
  before: Record<string, any>,
  after: Record<string, any>,
) {
  const allKeys = new Set([...Object.keys(before), ...Object.keys(after)]);
  const added: string[] = [];
  const removed: string[] = [];
  const changed: string[] = [];
  const unchanged: string[] = [];

  allKeys.forEach((k) => {
    const inBefore = k in before;
    const inAfter = k in after;
    if (!inBefore) added.push(k);
    else if (!inAfter) removed.push(k);
    else if (JSON.stringify(before[k]) !== JSON.stringify(after[k])) changed.push(k);
    else unchanged.push(k);
  });

  return { added, removed, changed, unchanged };
}

function ValueCell({ val }: { val: any }) {
  if (val === undefined) return <span className="text-white/20">—</span>;
  return (
    <span className="font-['JetBrains_Mono'] text-xs">
      {JSON.stringify(val, null, 0)}
    </span>
  );
}

export function AdminJsonDiff({ before, after }: AdminJsonDiffProps) {
  const b = before ?? {};
  const a = after ?? {};

  if (!before && !after) {
    return <p className="text-xs text-white/30 font-['Outfit']">No change data available</p>;
  }

  const { added, removed, changed, unchanged } = classifyKeys(b, a);
  const rows = [
    ...added.map((k) => ({ k, type: "added" as const })),
    ...removed.map((k) => ({ k, type: "removed" as const })),
    ...changed.map((k) => ({ k, type: "changed" as const })),
    ...unchanged.map((k) => ({ k, type: "unchanged" as const })),
  ];

  const rowStyle = {
    added:     "bg-[#00E676]/5 border-l-2 border-[#00E676]",
    removed:   "bg-red-500/5 border-l-2 border-red-500",
    changed:   "bg-yellow-400/5 border-l-2 border-yellow-400",
    unchanged: "border-l-2 border-transparent",
  };

  const labelStyle = {
    added:     "text-[#00E676]",
    removed:   "text-red-400",
    changed:   "text-yellow-400",
    unchanged: "text-white/30",
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <p className="mb-2 font-['Barlow_Condensed'] text-xs uppercase tracking-widest text-white/40">Before</p>
        <div className="rounded-lg border border-white/10 bg-[#0a0f16] p-3 space-y-0.5">
          {rows.map(({ k, type }) => (
            <div key={k} className={`flex gap-2 rounded px-2 py-1 ${rowStyle[type]}`}>
              <span className={`shrink-0 font-['JetBrains_Mono'] text-xs font-semibold ${labelStyle[type]}`}>
                {k}:
              </span>
              <span className="text-white/60 text-xs font-['JetBrains_Mono'] break-all">
                <ValueCell val={b[k]} />
              </span>
            </div>
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 font-['Barlow_Condensed'] text-xs uppercase tracking-widest text-white/40">After</p>
        <div className="rounded-lg border border-white/10 bg-[#0a0f16] p-3 space-y-0.5">
          {rows.map(({ k, type }) => (
            <div key={k} className={`flex gap-2 rounded px-2 py-1 ${rowStyle[type]}`}>
              <span className={`shrink-0 font-['JetBrains_Mono'] text-xs font-semibold ${labelStyle[type]}`}>
                {k}:
              </span>
              <span className="text-white/60 text-xs font-['JetBrains_Mono'] break-all">
                <ValueCell val={a[k]} />
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
