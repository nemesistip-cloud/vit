import { cn } from "@/lib/utils";
import { Brain, Zap, TrendingUp, AlertTriangle, CheckCircle2, MinusCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ModelInterpretationProps {
  homeProb: number;
  drawProb: number;
  awayProb: number;
  homeTeam: string;
  awayTeam: string;
  confidence?: number;
  edge?: number | null;
  betSide?: string | null;
  entryOdds?: number | null;
  modelCount?: number;
  className?: string;
}

function getVerdict(h: number, d: number, a: number, conf: number) {
  const maxP = Math.max(h, d, a);
  const leader = maxP === h ? "home" : maxP === d ? "draw" : "away";
  const margin = maxP - (leader === "home" ? Math.max(d, a) : leader === "draw" ? Math.max(h, a) : Math.max(h, d));
  const strength = margin > 0.18 ? "strong" : margin > 0.08 ? "moderate" : "slim";
  return { leader, margin, strength };
}

function confidenceLabel(c: number) {
  if (c >= 0.75) return { text: "HIGH", color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/30" };
  if (c >= 0.55) return { text: "MEDIUM", color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/30" };
  return { text: "LOW", color: "text-red-400", bg: "bg-red-500/10 border-red-500/30" };
}

export function ModelInterpretation({
  homeProb, drawProb, awayProb,
  homeTeam, awayTeam,
  confidence = 0,
  edge,
  betSide,
  entryOdds,
  modelCount,
  className,
}: ModelInterpretationProps) {
  const { leader, strength } = getVerdict(homeProb, drawProb, awayProb, confidence);
  const leaderLabel = leader === "home" ? homeTeam : leader === "draw" ? "Draw" : awayTeam;
  const conf = confidenceLabel(confidence);

  const hasEdge = edge != null && !isNaN(edge);
  const edgePositive = hasEdge && edge! > 0;

  const strengthDesc = {
    strong:   "The ensemble strongly agrees on this outcome.",
    moderate: "The ensemble shows moderate conviction.",
    slim:     "The models are split — proceed with caution.",
  }[strength];

  const summaryText = (() => {
    if (strength === "slim") {
      return `The 13-model ensemble sees this as a closely-contested match. No clear favourite emerges — the probability spread between all outcomes is narrow.`;
    }
    const pct = (Math.max(homeProb, drawProb, awayProb) * 100).toFixed(0);
    return `The ensemble assigns a ${pct}% probability to a ${leaderLabel} ${leader === "draw" ? "" : "win"}, indicating a ${strength} lean backed by ${modelCount ?? 13} child models.`;
  })();

  return (
    <div className={cn("rounded-xl border border-primary/15 bg-gradient-to-br from-primary/5 via-transparent to-purple-500/5 p-4 space-y-3", className)}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-primary">Ensemble Verdict</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant="outline" className={cn("font-mono text-[9px] uppercase", conf.bg, conf.color)}>
            {conf.text} CONF
          </Badge>
          {hasEdge && (
            <Badge variant="outline" className={cn("font-mono text-[9px] uppercase", edgePositive ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : "bg-red-500/10 border-red-500/30 text-red-400")}>
              {edgePositive ? "+" : ""}{((edge ?? 0) * 100).toFixed(1)}% edge
            </Badge>
          )}
        </div>
      </div>

      <div className="flex items-start gap-3">
        <div className={cn(
          "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
          strength === "strong" ? "bg-primary/15 border border-primary/30" :
          strength === "moderate" ? "bg-amber-500/15 border border-amber-500/30" :
          "bg-muted/20 border border-border"
        )}>
          {strength === "strong" ? <CheckCircle2 className="w-5 h-5 text-primary" /> :
           strength === "moderate" ? <TrendingUp className="w-5 h-5 text-amber-400" /> :
           <MinusCircle className="w-5 h-5 text-muted-foreground" />}
        </div>
        <div className="space-y-1 min-w-0">
          <div className="font-mono text-sm font-bold text-foreground">
            {leaderLabel}
            {leader !== "draw" && <span className="text-muted-foreground font-normal"> to win</span>}
            <span className="ml-2 font-mono text-[10px] text-muted-foreground uppercase">({strength})</span>
          </div>
          <p className="font-mono text-[11px] text-muted-foreground leading-relaxed">{summaryText}</p>
        </div>
      </div>

      {betSide && (
        <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2">
          <Zap className="w-3.5 h-3.5 text-primary flex-shrink-0" />
          <div className="font-mono text-xs text-muted-foreground">
            <span className="text-foreground font-semibold uppercase">{betSide.replace("_", " ")}</span>
            {entryOdds && <span> @ <span className="text-primary font-bold">{entryOdds}</span></span>}
            <span className="ml-1">recommended by the model</span>
          </div>
        </div>
      )}

      {strength === "slim" && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
          <p className="font-mono text-[11px] text-amber-400/80">
            Low-conviction match. Consider smaller stake sizes or avoiding this fixture.
          </p>
        </div>
      )}
    </div>
  );
}
