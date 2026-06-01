import { cn } from "@/lib/utils";
import { Shield, Clock, Brain, TrendingUp } from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";

interface VITComponents {
  value: number;
  analytics: number;
  trust: number;
  recency?: number;
}

interface VITScoreCardProps {
  vitScore: number;
  vitTier: string;
  vitComponents?: VITComponents | null;
  edge?: number | null;
  agreementPct?: number | null;
  confidence?: number | null;
  hasMarketOdds?: boolean;
  className?: string;
  compact?: boolean;
}

const TIER_CONFIG: Record<string, { label: string; color: string; bg: string; border: string; glow: string }> = {
  ELITE:     { label: "ELITE",     color: "text-yellow-400",        bg: "bg-yellow-400/10",  border: "border-yellow-400/40",  glow: "shadow-yellow-400/20" },
  STRONG:    { label: "STRONG",    color: "text-emerald-400",       bg: "bg-emerald-500/10", border: "border-emerald-500/40", glow: "shadow-emerald-400/20" },
  SOLID:     { label: "SOLID",     color: "text-blue-400",          bg: "bg-blue-500/10",    border: "border-blue-500/40",    glow: "shadow-blue-400/20" },
  WATCHLIST: { label: "WATCHLIST", color: "text-amber-400",         bg: "bg-amber-500/10",   border: "border-amber-500/40",   glow: "shadow-amber-400/10" },
  SKIP:      { label: "SKIP",      color: "text-muted-foreground",  bg: "bg-muted/20",       border: "border-border",         glow: "" },
};

function PillarBar({ label, icon: Icon, value, color, description }: {
  label: string; icon: typeof Shield; value: number; color: string; description: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Icon className={cn("w-3 h-3", color)} />
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
        </div>
        <span className={cn("font-mono text-xs font-bold", color)}>{value.toFixed(1)}</span>
      </div>
      <div className="h-1.5 bg-muted/30 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", color.replace("text-", "bg-"))}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      <p className="font-mono text-[9px] text-muted-foreground/70">{description}</p>
    </div>
  );
}

export function VITScoreCard({
  vitScore,
  vitTier,
  vitComponents,
  edge,
  agreementPct,
  confidence,
  hasMarketOdds,
  className,
  compact = false,
}: VITScoreCardProps) {
  const tier  = TIER_CONFIG[vitTier] ?? TIER_CONFIG.SKIP;
  const score = Math.round(vitScore ?? 0);

  const vComp = vitComponents?.value        ?? Math.min(100, (edge ?? 0) * 500);
  const iComp = vitComponents?.analytics ?? (agreementPct ?? 0) * 100;
  const tComp = vitComponents?.trust        ?? (confidence ?? 0) * 100;
  const rComp = vitComponents?.recency      ?? 100;

  if (compact) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <div className={cn("rounded-lg border px-2.5 py-1 flex items-center gap-2", tier.bg, tier.border)}>
          <BrandLogo iconOnly size={14} />
          <span className={cn("font-mono text-xs font-bold", tier.color)}>VIT {score}</span>
          <span className={cn("font-mono text-[9px] uppercase", tier.color)}>{tier.label}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      "rounded-xl border p-4 space-y-4",
      tier.bg, tier.border,
      tier.glow ? `shadow-lg ${tier.glow}` : "",
      className
    )}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn("flex items-center justify-center")}>
            <BrandLogo size={32} />
          </div>
          <div>
            <div className="font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground">VIT Score v3</div>
            <div className="font-mono text-[9px] text-muted-foreground/60">Value · Analytics · Trust · Recency</div>
          </div>
        </div>
        <div className="text-right">
          <div className={cn("font-mono text-3xl font-black", tier.color)}>{score}</div>
          <div className="flex items-center gap-1.5 justify-end mt-0.5">
            <div className={cn("font-mono text-[10px] font-bold uppercase tracking-widest", tier.color)}>{tier.label}</div>
            {hasMarketOdds === true && (
              <span className="font-mono text-[8px] bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded px-1 py-0.5">LIVE ODDS</span>
            )}
          </div>
        </div>
      </div>

      <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-1000",
            vitTier === "ELITE"     ? "bg-gradient-to-r from-yellow-400 to-yellow-300" :
            vitTier === "STRONG"    ? "bg-gradient-to-r from-emerald-500 to-emerald-400" :
            vitTier === "SOLID"     ? "bg-gradient-to-r from-blue-500 to-blue-400" :
            vitTier === "WATCHLIST" ? "bg-gradient-to-r from-amber-500 to-amber-400" :
            "bg-muted"
          )}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>

      <div className="grid grid-cols-4 gap-2 pt-1">
        <PillarBar
          label="Value"
          icon={TrendingUp}
          value={vComp}
          color="text-emerald-400"
          description={`${(vComp / 5).toFixed(1)}% edge`}
        />
        <PillarBar
          label="Intel"
          icon={Brain}
          value={iComp}
          color="text-blue-400"
          description={`${iComp.toFixed(0)}% agree`}
        />
        <PillarBar
          label="Trust"
          icon={Shield}
          value={tComp}
          color="text-purple-400"
          description={`${tComp.toFixed(0)}% conf`}
        />
        <PillarBar
          label="Recent"
          icon={Clock}
          value={rComp}
          color="text-cyan-400"
          description={rComp >= 90 ? "< 5 h old" : rComp >= 50 ? "< 24 h" : "stale"}
        />
      </div>

      <div className="text-[9px] font-mono text-muted-foreground/50 text-center">
        V×0.35 + I×0.30 + T×0.25 + R×0.10 · Argmax-consensus · Brier-calibrated weights
      </div>
    </div>
  );
}

export function VITTierBadge({ tier, score }: { tier: string; score: number }) {
  const cfg = TIER_CONFIG[tier] ?? TIER_CONFIG.SKIP;
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider",
      cfg.bg, cfg.border, cfg.color
    )}>
      <BrandLogo iconOnly size={10} />
      VIT {Math.round(score)} · {cfg.label}
    </span>
  );
}
