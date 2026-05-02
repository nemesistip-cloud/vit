import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BrainCircuit, Zap, Sparkles, RefreshCw, TrendingUp, AlertTriangle, Bot } from "lucide-react";
import { analyzeMatchWithPuter, isPuterAvailable, MatchAnalysis } from "@/lib/puter-ai";

const AI_PROVIDERS = {
  gemini: { name: "Gemini", color: "hsl(var(--primary))",   icon: Sparkles    },
  claude: { name: "Claude", color: "hsl(262 83% 58%)",      icon: BrainCircuit },
  grok:   { name: "Grok",   color: "hsl(var(--secondary))", icon: Zap          },
  puter:  { name: "Puter",  color: "hsl(173 80% 50%)",      icon: Bot          },
} as const;

type Provider = keyof typeof AI_PROVIDERS;

const RISK_COLOR: Record<string, string> = {
  LOW:    "text-emerald-500 border-emerald-500/30 bg-emerald-500/10",
  MEDIUM: "text-amber-500  border-amber-500/30  bg-amber-500/10",
  HIGH:   "text-red-500    border-red-500/30    bg-red-500/10",
};

interface Insight {
  summary?: string;
  key_factors?: string[];
  recommendation?: string;
  value_assessment?: string;
  risk_level?: string;
  insight_tags?: string[];
  confidence?: number;
  provider?: string;
  available?: boolean;
  error?: string | null;
  from_cache?: boolean;
}

interface ProviderResult extends Insight {
  source?: string;
  label?: string;
}

interface InsightsData {
  match_id?: number;
  sources_requested?: string[];
  cache_hits?: string[];
  results?: Record<string, ProviderResult>;
  gemini?: Insight;
  claude?: Insight;
  grok?: Insight;
  source?: string;
}

interface PuterInsightState {
  status: "idle" | "loading" | "done" | "error";
  insight?: Insight;
  error?: string;
}

function InsightCard({
  provider,
  insight,
  isLoading,
  puterState,
  onRunPuter,
  canRunPuter,
}: {
  provider: Provider;
  insight?: Insight;
  isLoading: boolean;
  puterState?: PuterInsightState;
  onRunPuter?: () => void;
  canRunPuter?: boolean;
}) {
  const { name, color, icon: Icon } = AI_PROVIDERS[provider];

  if (isLoading && provider !== "puter") {
    return (
      <Card className="bg-card/40 backdrop-blur border-border">
        <CardHeader className="pb-3">
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  /* ── Puter card special handling ── */
  if (provider === "puter") {
    const ps = puterState ?? { status: "idle" };

    if (ps.status === "idle") {
      return (
        <Card className="bg-card/20 backdrop-blur flex flex-col" style={{ borderColor: `${color}40`, borderWidth: "1px" }}>
          <CardContent className="flex flex-col items-center justify-center min-h-[200px] text-center gap-3 p-6">
            <Bot className="w-8 h-8" style={{ color }} />
            <p className="font-mono text-xs uppercase" style={{ color }}>Puter AI — Free</p>
            <p className="font-mono text-[10px] text-muted-foreground">
              Claude via Puter.js — no API key needed
            </p>
            {canRunPuter ? (
              <Button
                size="sm"
                className="font-mono text-xs mt-1"
                style={{ background: color, color: "#000" }}
                onClick={onRunPuter}
              >
                Analyze Free
              </Button>
            ) : (
              <p className="font-mono text-[10px] text-amber-500/80">
                Puter not ready — ensure Puter.js is loaded
              </p>
            )}
          </CardContent>
        </Card>
      );
    }

    if (ps.status === "loading") {
      return (
        <Card className="bg-card/40 backdrop-blur border-border" style={{ borderColor: `${color}40`, borderWidth: "1px" }}>
          <CardHeader className="pb-3">
            <Skeleton className="h-6 w-32" style={{ background: `${color}20` }} />
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono" style={{ color }}>
              <Bot className="w-4 h-4 animate-pulse" />
              Querying Puter Claude…
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/5" />
          </CardContent>
        </Card>
      );
    }

    if (ps.status === "error") {
      return (
        <Card className="bg-card/20 backdrop-blur border-border/50">
          <CardContent className="flex flex-col items-center justify-center min-h-[200px] text-center gap-3 p-6">
            <Bot className="w-8 h-8 text-muted-foreground/40" />
            <p className="font-mono text-xs text-muted-foreground uppercase">Puter — Error</p>
            <p className="font-mono text-[10px] text-amber-500/80 max-w-[180px]">{ps.error}</p>
            {canRunPuter && (
              <Button size="sm" variant="outline" className="font-mono text-xs mt-1" onClick={onRunPuter}>
                Retry
              </Button>
            )}
          </CardContent>
        </Card>
      );
    }

    const ins = ps.insight;
    if (!ins) return null;
    const riskCls = RISK_COLOR[ins.risk_level?.toUpperCase() ?? "MEDIUM"] ?? RISK_COLOR.MEDIUM;

    return (
      <Card className="bg-card/50 backdrop-blur flex flex-col" style={{ borderColor: `${color}40`, borderWidth: "1px" }}>
        <CardHeader className="pb-3 border-b shrink-0" style={{ borderColor: `${color}20` }}>
          <CardTitle className="flex items-center justify-between font-mono text-sm gap-2 flex-wrap">
            <span className="flex items-center gap-2">
              <Bot className="w-4 h-4 shrink-0" style={{ color }} />
              <span style={{ color }}>Puter</span>
              <span className="text-[9px] font-mono text-muted-foreground/50 border border-border/40 rounded px-1">free</span>
            </span>
            <div className="flex items-center gap-1.5 flex-wrap">
              {ins.risk_level && (
                <Badge variant="outline" className={`font-mono text-[10px] px-1.5 ${riskCls}`}>
                  {ins.risk_level}
                </Badge>
              )}
              {ins.confidence != null && (
                <Badge variant="outline" className="font-mono text-[10px]" style={{ borderColor: `${color}40`, color }}>
                  {(ins.confidence * 100).toFixed(0)}%
                </Badge>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4 flex-1">
          {ins.summary && (
            <div>
              <p className="text-[10px] font-mono text-muted-foreground uppercase mb-1.5">Analysis</p>
              <p className="text-sm leading-relaxed">{ins.summary}</p>
            </div>
          )}
          {ins.key_factors && ins.key_factors.length > 0 && (
            <div>
              <p className="text-[10px] font-mono text-muted-foreground uppercase mb-1.5">Key Factors</p>
              <div className="space-y-1.5">
                {ins.key_factors.map((f, i) => (
                  <div key={i} className="flex gap-2 text-sm p-2 rounded-md bg-muted/30" style={{ borderLeft: `2px solid ${color}` }}>
                    <TrendingUp className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color }} />
                    <span className="text-sm leading-snug">{f}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {ins.recommendation && (
            <div className="p-3 rounded-lg" style={{ background: `${color}08`, borderLeft: `3px solid ${color}` }}>
              <p className="text-[10px] font-mono uppercase mb-1" style={{ color }}>Recommendation</p>
              <p className="text-sm font-semibold">{ins.recommendation}</p>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  /* ── Standard provider card ── */
  if (!insight || insight.available === false) {
    const errMsg = insight?.error;
    return (
      <Card className="bg-card/20 backdrop-blur border-border/50">
        <CardContent className="flex flex-col items-center justify-center min-h-[200px] text-center gap-3 p-6">
          <Icon className="w-8 h-8 text-muted-foreground/40" />
          <p className="font-mono text-xs text-muted-foreground uppercase">{name} — No insight</p>
          {errMsg && (
            <p className="font-mono text-[10px] text-amber-500/80 max-w-[180px]">{errMsg}</p>
          )}
        </CardContent>
      </Card>
    );
  }

  const riskCls = RISK_COLOR[insight.risk_level?.toUpperCase() ?? "MEDIUM"] ?? RISK_COLOR.MEDIUM;

  return (
    <Card className="bg-card/50 backdrop-blur flex flex-col" style={{ borderColor: `${color}40`, borderWidth: "1px" }}>
      <CardHeader className="pb-3 border-b shrink-0" style={{ borderColor: `${color}20` }}>
        <CardTitle className="flex items-center justify-between font-mono text-sm gap-2 flex-wrap">
          <span className="flex items-center gap-2">
            <Icon className="w-4 h-4 shrink-0" style={{ color }} />
            <span style={{ color }}>{name}</span>
            {insight.from_cache && (
              <span className="text-[9px] font-mono text-muted-foreground/50 border border-border/40 rounded px-1">cached</span>
            )}
          </span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {insight.risk_level && (
              <Badge variant="outline" className={`font-mono text-[10px] px-1.5 ${riskCls}`}>
                {insight.risk_level}
              </Badge>
            )}
            {insight.confidence != null && (
              <Badge variant="outline" className="font-mono text-[10px]" style={{ borderColor: `${color}40`, color }}>
                {(insight.confidence * 100).toFixed(0)}%
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4 space-y-4 flex-1">
        {insight.summary && (
          <div>
            <p className="text-[10px] font-mono text-muted-foreground uppercase mb-1.5">Analysis</p>
            <p className="text-sm leading-relaxed">{insight.summary}</p>
          </div>
        )}

        {insight.key_factors && insight.key_factors.length > 0 && (
          <div>
            <p className="text-[10px] font-mono text-muted-foreground uppercase mb-1.5">Key Factors</p>
            <div className="space-y-1.5">
              {insight.key_factors.map((factor, i) => (
                <div
                  key={i}
                  className="flex gap-2 text-sm p-2 rounded-md bg-muted/30"
                  style={{ borderLeft: `2px solid ${color}` }}
                >
                  <TrendingUp className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color }} />
                  <span className="text-sm leading-snug">{factor}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {insight.value_assessment && (
          <div>
            <p className="text-[10px] font-mono text-muted-foreground uppercase mb-1.5">Value Assessment</p>
            <p className="text-sm leading-relaxed text-muted-foreground">{insight.value_assessment}</p>
          </div>
        )}

        {insight.recommendation && (
          <div
            className="p-3 rounded-lg"
            style={{ background: `${color}08`, borderLeft: `3px solid ${color}` }}
          >
            <p className="text-[10px] font-mono uppercase mb-1" style={{ color }}>Recommendation</p>
            <p className="text-sm font-semibold">{insight.recommendation}</p>
          </div>
        )}

        {insight.insight_tags && insight.insight_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {insight.insight_tags.map((tag, i) => (
              <span
                key={i}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border"
                style={{ color, borderColor: `${color}40`, background: `${color}08` }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function resolveInsight(data: InsightsData | undefined, provider: Exclude<Provider, "puter">): Insight | undefined {
  if (!data) return undefined;
  if (data.results?.[provider]) return data.results[provider];
  return (data as any)[provider];
}

export function AIInsightComparison({
  matchId,
  homeTeam,
  awayTeam,
  league,
}: {
  matchId: string;
  homeTeam?: string;
  awayTeam?: string;
  league?: string;
}) {
  const { data: insights, isLoading, isError, refetch, isFetching } = useQuery<InsightsData>({
    queryKey: ["ai-insights", matchId],
    queryFn: () => apiGet<InsightsData>(`/ai/multi-insights/${matchId}`),
    enabled: !!matchId,
    retry: 1,
    staleTime: 5 * 60 * 1000,
  });

  const [puterState, setPuterState] = useState<PuterInsightState>({ status: "idle" });

  const runPuter = async () => {
    if (!homeTeam || !awayTeam) return;
    setPuterState({ status: "loading" });
    try {
      const analysis: MatchAnalysis = await analyzeMatchWithPuter(
        homeTeam,
        awayTeam,
        league ?? "Football",
        insights?.results?.["gemini"]?.confidence ?? 0.34,
        0.33,
        0.33,
        "claude",
      );
      const insight: Insight = {
        available: true,
        summary: analysis.reason,
        key_factors: analysis.key_factors,
        confidence: analysis.confidence,
        risk_level: analysis.confidence >= 0.7 ? "LOW" : analysis.confidence >= 0.55 ? "MEDIUM" : "HIGH",
        recommendation: `Home ${(analysis.home_prob * 100).toFixed(0)}% · Draw ${(analysis.draw_prob * 100).toFixed(0)}% · Away ${(analysis.away_prob * 100).toFixed(0)}%`,
      };
      setPuterState({ status: "done", insight });
    } catch (e: any) {
      setPuterState({ status: "error", error: e?.message || "Puter analysis failed" });
    }
  };

  const serverProviders: Exclude<Provider, "puter">[] = ["gemini", "claude", "grok"];
  const allProviders: Provider[] = ["gemini", "claude", "grok", "puter"];

  const serverHasAny = serverProviders.some(
    (p) => resolveInsight(insights, p)?.available !== false && resolveInsight(insights, p) != null,
  );
  const cacheHits    = insights?.cache_hits ?? [];
  const isFromCache  = cacheHits.length === (insights?.sources_requested?.length ?? 0) && cacheHits.length > 0;
  const canRunPuter  = isPuterAvailable() && !!homeTeam && !!awayTeam;

  return (
    <Card className="bg-card/50 backdrop-blur border-border">
      <CardHeader className="border-b border-border/50 pb-4">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="font-mono uppercase flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            Multi-AI Intelligence
          </CardTitle>
          <div className="flex items-center gap-2">
            {isFromCache && !isFetching && (
              <span className="text-[9px] font-mono text-muted-foreground/60 border border-border/40 rounded px-1.5 py-0.5">
                from cache
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              className="font-mono text-xs h-7 px-2.5"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RefreshCw className={`w-3 h-3 mr-1 ${isFetching ? "animate-spin" : ""}`} />
              {isFetching ? "FETCHING…" : "REFRESH"}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-6">
        {isError && !isLoading && (
          <div className="text-center py-8 space-y-2">
            <AlertTriangle className="w-8 h-8 text-amber-500/50 mx-auto" />
            <p className="font-mono text-xs text-muted-foreground uppercase">AI insights require a prediction first</p>
            <p className="font-mono text-[10px] text-muted-foreground/60">
              Run the ML Ensemble on this match, then refresh insights
            </p>
          </div>
        )}

        {!isError && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              {allProviders.map((provider) => (
                <InsightCard
                  key={provider}
                  provider={provider}
                  insight={provider !== "puter" ? resolveInsight(insights, provider) : undefined}
                  isLoading={isLoading}
                  puterState={provider === "puter" ? puterState : undefined}
                  onRunPuter={provider === "puter" ? runPuter : undefined}
                  canRunPuter={provider === "puter" ? canRunPuter : undefined}
                />
              ))}
            </div>

            {(insights?.source === "ml_fallback" || insights?.source === "neural_ensemble") && !isLoading && (
              <div className="mt-4 px-3 py-2 bg-muted/30 rounded-lg border border-border/40 text-center">
                <p className="text-[10px] font-mono text-muted-foreground">
                  Server insights from ML ensemble — Puter AI above runs free Claude analysis in-browser
                </p>
              </div>
            )}

            {(serverHasAny || puterState.status === "done") && !isLoading && (
              <div className="mt-6 p-4 bg-muted/20 rounded-lg border border-border/50">
                <p className="text-xs font-mono text-muted-foreground uppercase mb-3">Provider Status</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {allProviders.map((p) => {
                    const { name, color, icon: Icon } = AI_PROVIDERS[p];
                    let available = false;
                    let cached    = false;
                    let errMsg: string | undefined;
                    let statusLabel = "pending";

                    if (p === "puter") {
                      available   = puterState.status === "done";
                      statusLabel = puterState.status === "done" ? "live (free)" : puterState.status === "loading" ? "running…" : puterState.status === "error" ? "error" : "idle";
                      errMsg      = puterState.error;
                    } else {
                      const result = resolveInsight(insights, p);
                      available    = result?.available !== false && !!result;
                      cached       = cacheHits.includes(p);
                      errMsg       = result?.error ?? undefined;
                      statusLabel  = available ? (cached ? "cached" : "live") : errMsg ? "error" : "pending";
                    }

                    return (
                      <div key={p} className="flex items-center gap-2 p-2 rounded bg-background/50 border border-border/30">
                        <Icon className="w-3 h-3 shrink-0" style={{ color: available ? color : "hsl(var(--muted-foreground))" }} />
                        <div className="min-w-0">
                          <p className="text-xs font-mono font-bold truncate" style={{ color: available ? color : "hsl(var(--muted-foreground))" }}>
                            {name}
                          </p>
                          <p className="text-[9px] font-mono text-muted-foreground">{statusLabel}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
