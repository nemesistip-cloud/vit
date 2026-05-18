import { cn } from "@/lib/utils";

interface GaugeBar {
  label: string;
  value: number;
  color?: "cyan" | "neutral" | "orange" | "green" | "red";
}

interface ProbabilityGaugeProps {
  bars: GaugeBar[];
  className?: string;
  showPercentages?: boolean;
}

const COLOR_MAP = {
  cyan:    { bar: "bg-primary",           text: "text-primary",          bg: "bg-primary/10 border-primary/25" },
  neutral: { bar: "bg-muted-foreground/60", text: "text-muted-foreground", bg: "bg-muted/20 border-border" },
  orange:  { bar: "bg-orange-400",        text: "text-orange-400",       bg: "bg-orange-400/10 border-orange-400/25" },
  green:   { bar: "bg-emerald-500",       text: "text-emerald-400",      bg: "bg-emerald-500/10 border-emerald-500/25" },
  red:     { bar: "bg-red-500",           text: "text-red-400",          bg: "bg-red-500/10 border-red-500/25" },
};

export function ProbabilityGauge({ bars, className, showPercentages = true }: ProbabilityGaugeProps) {
  const max = Math.max(...bars.map(b => b.value), 0.01);

  return (
    <div className={cn("space-y-2", className)}>
      {bars.map((bar) => {
        const pct = (bar.value * 100).toFixed(1);
        const widthPct = (bar.value / max) * 100;
        const c = COLOR_MAP[bar.color ?? "neutral"];
        return (
          <div key={bar.label} className="space-y-1">
            <div className="flex items-center justify-between font-mono text-xs">
              <span className="text-muted-foreground uppercase tracking-wide">{bar.label}</span>
              {showPercentages && (
                <span className={cn("font-bold tabular-nums", c.text)}>{pct}%</span>
              )}
            </div>
            <div className="relative h-2 rounded-full bg-muted/30 overflow-hidden">
              <div
                className={cn("absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out", c.bar)}
                style={{ width: `${widthPct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

interface ProbabilityTrioProps {
  homeProb: number;
  drawProb: number;
  awayProb: number;
  homeLabel?: string;
  awayLabel?: string;
  className?: string;
}

export function ProbabilityTrio({
  homeProb, drawProb, awayProb,
  homeLabel = "Home", awayLabel = "Away",
  className,
}: ProbabilityTrioProps) {
  const total = homeProb + drawProb + awayProb || 1;
  const h = homeProb / total;
  const d = drawProb / total;
  const a = awayProb / total;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-1 h-3 rounded-full overflow-hidden">
        <div
          className="bg-primary h-full transition-all duration-700 ease-out"
          style={{ width: `${h * 100}%`, minWidth: h > 0 ? "2px" : 0 }}
        />
        <div
          className="bg-muted-foreground/40 h-full transition-all duration-700 ease-out"
          style={{ width: `${d * 100}%`, minWidth: d > 0 ? "2px" : 0 }}
        />
        <div
          className="bg-orange-400 h-full transition-all duration-700 ease-out"
          style={{ width: `${a * 100}%`, minWidth: a > 0 ? "2px" : 0 }}
        />
      </div>
      <div className="grid grid-cols-3 gap-2 text-center font-mono">
        <div className="space-y-0.5">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wide truncate">{homeLabel}</div>
          <div className="text-lg font-bold text-primary tabular-nums">{(homeProb * 100).toFixed(1)}%</div>
        </div>
        <div className="space-y-0.5">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wide">Draw</div>
          <div className="text-lg font-bold tabular-nums">{(drawProb * 100).toFixed(1)}%</div>
        </div>
        <div className="space-y-0.5">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wide truncate">{awayLabel}</div>
          <div className="text-lg font-bold text-orange-400 tabular-nums">{(awayProb * 100).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
}
