import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Bot, TrendingUp, TrendingDown, Minus, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface AiPrediction {
  match_id: number;
  source: string;
  home_prob: number;
  draw_prob: number;
  away_prob: number;
  confidence: number;
  reason?: string | null;
  timestamp?: string | null;
}

interface AiSourceComparisonProps {
  matchId: string;
  homeTeam: string;
  awayTeam: string;
  modelHomeProb: number | null;
  modelDrawProb: number | null;
  modelAwayProb: number | null;
  betSide?: string | null;
}

const SOURCE_COLORS: Record<string, string> = {
  chatgpt:    "hsl(143 71% 45%)",
  gemini:     "hsl(var(--primary))",
  grok:       "hsl(211 100% 60%)",
  deepseek:   "hsl(262 83% 58%)",
  perplexity: "hsl(173 80% 50%)",
  claude:     "hsl(38 92% 50%)",
  default:    "hsl(var(--muted-foreground))",
};

function sourceColor(s: string) {
  return SOURCE_COLORS[s.toLowerCase()] ?? SOURCE_COLORS.default;
}

function ProbCell({ prob, color, label }: { prob: number; color: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-[9px] font-mono text-muted-foreground uppercase mb-0.5">{label}</div>
      <div className="font-mono text-[13px] font-bold" style={{ color }}>
        {(prob * 100).toFixed(0)}%
      </div>
      <div className="w-full bg-muted/30 rounded-full h-1 mt-0.5">
        <div
          className="h-1 rounded-full"
          style={{ width: `${prob * 100}%`, background: color }}
        />
      </div>
    </div>
  );
}

function DeltaBadge({ delta }: { delta: number }) {
  const pct = (delta * 100).toFixed(1);
  if (delta > 0.03)
    return (
      <span className="inline-flex items-center gap-0.5 font-mono text-[10px] text-emerald-400">
        <TrendingUp className="w-3 h-3" />+{pct}%
      </span>
    );
  if (delta < -0.03)
    return (
      <span className="inline-flex items-center gap-0.5 font-mono text-[10px] text-red-400">
        <TrendingDown className="w-3 h-3" />{pct}%
      </span>
    );
  return (
    <span className="inline-flex items-center gap-0.5 font-mono text-[10px] text-amber-400">
      <Minus className="w-3 h-3" />{pct}%
    </span>
  );
}

function pickLabel(h: number, d: number, a: number) {
  const max = Math.max(h, d, a);
  if (max === h) return "home";
  if (max === d) return "draw";
  return "away";
}

export function AiSourceComparison({
  matchId,
  homeTeam,
  awayTeam,
  modelHomeProb,
  modelDrawProb,
  modelAwayProb,
  betSide,
}: AiSourceComparisonProps) {
  const { data, isLoading } = useQuery<{ predictions: AiPrediction[] }>({
    queryKey: ["ai-source-predictions", matchId],
    queryFn: () => apiGet<{ predictions: AiPrediction[] }>(`/ai/predictions/${matchId}`),
    enabled: !!matchId,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const predictions = data?.predictions ?? [];

  const hasModel = modelHomeProb != null && modelDrawProb != null && modelAwayProb != null;

  if (isLoading) {
    return (
      <Card className="bg-card/80 border-border">
        <CardHeader className="pb-3 border-b border-border/50">
          <Skeleton className="h-5 w-48" />
        </CardHeader>
        <CardContent className="pt-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!predictions.length && !hasModel) return null;

  const modelPick = hasModel ? pickLabel(modelHomeProb!, modelDrawProb!, modelAwayProb!) : null;

  return (
    <Card className="bg-card/80 border-border">
      <CardHeader className="pb-3 border-b border-border/50">
        <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          AI Source Predictions
          <Badge variant="outline" className="font-mono text-[10px] ml-1">
            {predictions.length} source{predictions.length !== 1 ? "s" : ""}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {/* Our ensemble model row */}
        {hasModel && (
          <div className="rounded-lg border border-primary/25 bg-primary/5 px-3 py-3">
            <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-5 rounded-full bg-primary" />
                <span className="font-mono text-xs font-bold text-primary uppercase">VIT Ensemble (13 models)</span>
                {betSide && (
                  <Badge variant="outline" className="font-mono text-[10px] bg-primary/10 border-primary/30 text-primary">
                    picks {betSide.replace("_", " ").toUpperCase()}
                  </Badge>
                )}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <ProbCell prob={modelHomeProb!} color="hsl(var(--primary))" label={homeTeam.split(" ")[0]} />
              <ProbCell prob={modelDrawProb!} color="hsl(var(--primary))" label="Draw" />
              <ProbCell prob={modelAwayProb!} color="hsl(var(--primary))" label={awayTeam.split(" ")[0]} />
            </div>
          </div>
        )}

        {/* AI source rows */}
        {predictions.map((pred, i) => {
          const color = sourceColor(pred.source);
          const pick = pickLabel(pred.home_prob, pred.draw_prob, pred.away_prob);
          const agreesWithModel = modelPick != null && pick === modelPick;

          const deltaHome = hasModel ? pred.home_prob - modelHomeProb! : null;
          const deltaDraw = hasModel ? pred.draw_prob - modelDrawProb! : null;
          const deltaAway = hasModel ? pred.away_prob - modelAwayProb! : null;

          return (
            <div
              key={i}
              className={cn(
                "rounded-lg border px-3 py-3 transition-colors",
                agreesWithModel
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : "border-border/40 bg-background/40"
              )}
            >
              <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-5 rounded-full" style={{ background: color }} />
                  <span className="font-mono text-xs font-bold uppercase" style={{ color }}>
                    {pred.source}
                  </span>
                  <Badge
                    variant="outline"
                    className="font-mono text-[10px]"
                    style={{ borderColor: `${color}40`, color }}
                  >
                    picks {pick.toUpperCase()}
                  </Badge>
                  {agreesWithModel && (
                    <span className="inline-flex items-center gap-0.5 text-[10px] font-mono text-emerald-400">
                      <CheckCircle2 className="w-3 h-3" /> agrees
                    </span>
                  )}
                </div>
                <span className="font-mono text-[10px] text-muted-foreground">
                  {(pred.confidence * 100).toFixed(0)}% conf
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <ProbCell prob={pred.home_prob} color={color} label={homeTeam.split(" ")[0]} />
                  {deltaHome != null && (
                    <div className="text-center mt-0.5">
                      <DeltaBadge delta={deltaHome} />
                    </div>
                  )}
                </div>
                <div>
                  <ProbCell prob={pred.draw_prob} color={color} label="Draw" />
                  {deltaDraw != null && (
                    <div className="text-center mt-0.5">
                      <DeltaBadge delta={deltaDraw} />
                    </div>
                  )}
                </div>
                <div>
                  <ProbCell prob={pred.away_prob} color={color} label={awayTeam.split(" ")[0]} />
                  {deltaAway != null && (
                    <div className="text-center mt-0.5">
                      <DeltaBadge delta={deltaAway} />
                    </div>
                  )}
                </div>
              </div>

              {pred.reason && (
                <p className="mt-2 text-[11px] text-muted-foreground leading-snug border-t border-border/30 pt-2">
                  {pred.reason}
                </p>
              )}
            </div>
          );
        })}

        {!predictions.length && hasModel && (
          <div className="text-center py-4">
            <Bot className="w-7 h-7 text-muted-foreground/20 mx-auto mb-2" />
            <p className="font-mono text-[11px] text-muted-foreground/60 uppercase">
              No external AI source predictions uploaded for this match
            </p>
            <p className="font-mono text-[10px] text-muted-foreground/40 mt-1">
              Upload ChatGPT, DeepSeek, or other AI picks via Admin → AI Sources
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
