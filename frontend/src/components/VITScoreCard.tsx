import { cn } from "@/lib/utils";
import { Shield, Zap, Brain, TrendingUp } from "lucide-react";

interface VITComponents {
  value: number;
  intelligence: number;
  trust: number;
}

interface VITScoreCardProps {
  vitScore: number;
  vitTier: string;
  vitComponents?: VITComponents | null;
  edge?: number | null;
  agreementPct?: number | null;
  confidence?: number | null;
  className?: string;
  compact?: boolean;
}

const TIER_CONFIG: Record<string, { label: string; color: string; bg: string; border: string; glow: string }> = {
  ELITE:     { label: "ELITE",     color: "text-yellow-300", bg: "bg-yellow-400/10", border: "border-yellow-400/40", glow: "shadow-yellow-400/20" },
  STRONG:    { label: "STRONG",    color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/40", glow: "shadow-emerald-400/20" },
  SOLID:     { label: "SOLID",     color: "text-blue-400",   bg: "bg-blue-500/10",   border: "border-blue-500/40",   glow: "shadow-blue-400/20" },
  WATCHLIST: { label: "WATCHLIST", color: "text-amber-400",  bg: "bg-amber-500/10",  border: "border-amber-500/40",  glow: "shadow-amber-400/10" },
  SKIP:      { label: "SKIP",      color: "text-muted-foreground", bg: "bg-muted/20", border: "border-border", glow: "" },
};

function PillarBar({ label, icon: Icon, value, color, description }: {
  label: string; icon: typeof Zap; value: number; color: string; description: string;
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
          style={{ width: `${Math.min(100, value)}%` }}
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
  className,
  compact = false,
}: VITScoreCardProps) {
  const tier = TIER_CONFIG[vitTier] ?? TIER_CONFIG.SKIP;
  const score = Math.round(vitScore ?? 0);

  const vComp = vitComponents?.value   ?? Math.min(100, (edge ?? 0) * 500);
  const iComp = vitComponents?.intelligence ?? (agreementPct ?? 0) * 100;
  const tComp = vitComponents?.trust   ?? (confidence ?? 0) * 100;

  if (compact) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <div className={cn("rounded-lg border px-2.5 py-1 flex items-center gap-2", tier.bg, tier.border)}>
          <Shield className={cn("w-3 h-3", tier.color)} />
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
        <div className="flex items-center gap-2">
          <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", tier.bg, tier.border, "border")}>
            <Shield className={cn("w-4 h-4", tier.color)} />
          </div>
          <div>
            <div className="font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground">VIT Score</div>
            <div className="font-mono text-[9px] text-muted-foreground/60">Value · Intelligence · Trust</div>
          </div>
        </div>
        <div className="text-right">
          <div className={cn("font-mono text-3xl font-black", tier.color)}>{score}</div>
          <div className={cn("font-mono text-[10px] font-bold uppercase tracking-widest", tier.color)}>{tier.label}</div>
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

      <div className="grid grid-cols-3 gap-3 pt-1">
        <PillarBar
          label="Value"
          icon={TrendingUp}
          value={vComp}
          color="text-emerald-400"
          description={`${(vComp / 5).toFixed(1)}% edge over market`}
        />
        <PillarBar
          label="Intel"
          icon={Brain}
          value={iComp}
          color="text-blue-400"
          description={`${iComp.toFixed(0)}% model agreement`}
        />
        <PillarBar
          label="Trust"
          icon={Shield}
          value={tComp}
          color="text-purple-400"
          description={`${tComp.toFixed(0)}% calibrated conf`}
        />
      </div>

      <div className="text-[9px] font-mono text-muted-foreground/50 text-center">
        V×0.40 + I×0.35 + T×0.25 · Trained on 50,000 historical fixtures
      </div>
    </div>
  );
}

export function VITTierBadge({ tier, score }: { tier: string; score: number }) {
  const cfg = TIER_CONFIG[tier] ?? TIER_CONFIG.SKIP;
  return (
    <span className={cn(
      "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider",
      cfg.bg, cfg.border, cfg.color
    )}>
      <Shield className="w-2.5 h-2.5" />
      VIT {Math.round(score)} · {cfg.label}
    </span>
  );
}
