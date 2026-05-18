import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, AlertCircle, CheckCircle2, Info } from "lucide-react";

type FactorSentiment = "positive" | "negative" | "neutral" | "warning";

interface FactorCardProps {
  label: string;
  value?: string | number;
  description?: string;
  sentiment?: FactorSentiment;
  icon?: React.ElementType;
  className?: string;
}

const SENTIMENT = {
  positive: {
    container: "border-emerald-500/20 bg-emerald-500/5",
    label: "text-emerald-400",
    icon: CheckCircle2,
    iconColor: "text-emerald-400",
  },
  negative: {
    container: "border-red-500/20 bg-red-500/5",
    label: "text-red-400",
    icon: TrendingDown,
    iconColor: "text-red-400",
  },
  neutral: {
    container: "border-border/50 bg-muted/10",
    label: "text-muted-foreground",
    icon: Minus,
    iconColor: "text-muted-foreground",
  },
  warning: {
    container: "border-amber-500/20 bg-amber-500/5",
    label: "text-amber-400",
    icon: AlertCircle,
    iconColor: "text-amber-400",
  },
};

export function FactorCard({ label, value, description, sentiment = "neutral", icon, className }: FactorCardProps) {
  const s = SENTIMENT[sentiment];
  const Icon = icon ?? s.icon;

  return (
    <div className={cn("rounded-lg border p-3 space-y-1.5 transition-colors", s.container, className)}>
      <div className="flex items-start gap-2">
        <Icon className={cn("w-3.5 h-3.5 mt-0.5 flex-shrink-0", s.iconColor)} />
        <div className="min-w-0 flex-1">
          <div className={cn("font-mono text-[10px] uppercase tracking-wider font-semibold", s.label)}>{label}</div>
          {value !== undefined && (
            <div className="font-mono text-sm font-bold text-foreground mt-0.5 tabular-nums">{value}</div>
          )}
          {description && (
            <div className="font-mono text-[11px] text-muted-foreground mt-1 leading-relaxed">{description}</div>
          )}
        </div>
      </div>
    </div>
  );
}

interface FactorGridProps {
  factors: FactorCardProps[];
  columns?: 1 | 2 | 3;
  className?: string;
}

export function FactorGrid({ factors, columns = 2, className }: FactorGridProps) {
  const colClass = columns === 1 ? "grid-cols-1" : columns === 3 ? "grid-cols-1 sm:grid-cols-3" : "grid-cols-1 sm:grid-cols-2";
  return (
    <div className={cn("grid gap-2", colClass, className)}>
      {factors.map((f, i) => (
        <FactorCard key={i} {...f} />
      ))}
    </div>
  );
}
