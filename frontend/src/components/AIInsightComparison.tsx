import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  BrainCircuit, Zap, Sparkles, RefreshCw, TrendingUp,
  AlertTriangle, Bot, CheckCircle2, WifiOff, Scale,
} from "lucide-react";

const AI_PROVIDERS = {
  gemini: { name: "Gemini", color: "hsl(var(--primary))",   icon: Sparkles     },
  claude: { name: "Claude", color: "hsl(262 83% 58%)",      icon: BrainCircuit },
  grok:   { name: "Grok",   color: "hsl(var(--secondary))", icon: Zap           },
  openai: { name: "GPT-4o", color: "hsl(150 60% 50%)",      icon: Sparkles      },
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
  home_prob?: number;
  draw_prob?: number;
  away_prob?: number;
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
  openai?: Insight;
  source?: string;
}

  status: "idle" | "loading" | "done" | "error";
  insight?: Insight;
  error?: string;
}

// ── Consensus Probability Component ──────────────────────────────────────────

  insights: (Insight | undefined)[],
}) {

  if (activeInsights.length === 0) return null;

  const avg = {
    home: activeInsights.reduce((acc, curr) => acc + (curr?.home_prob || 0), 0) / activeInsights.length,
    draw: activeInsights.reduce((acc, curr) => acc + (curr?.draw_prob || 0), 0) / activeInsights.length,
    away: activeInsights.reduce((acc, curr) => acc + (curr?.away_prob || 0), 0) / activeInsights.length,
  };

  return (
    <div className="mb-6 p-4 rounded-xl border border-primary/20 bg-primary/5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-primary" />
          <h3 className="font-mono text-xs uppercase font-bold tracking-wider text-primary">Multi-AI Probability Consensus</h3>
        </div>
        <Badge variant="outline" className="font-mono text-[10px] text-primary border-primary/30">
          {activeInsights.length} Models Aggregated
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "HOME", val: avg.home, color: "bg-emerald-500" },
          { label: "DRAW", val: avg.draw, color: "bg-amber-500" },
          { label: "AWAY", val: avg.away, color: "bg-blue-500" },
        ].map((item) => (
          <div key={item.label} className="space-y-1.5">
            <div className="flex justify-between items-end px-1">
              <span className="text-[10px] font-mono text-muted-foreground">{item.label}</span>
              <span className="text-sm font-mono font-bold">{(item.val * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 w-full bg-muted/30 rounded-full overflow-hidden">
              <div
                className={`h-full ${item.color} transition-all duration-1000 ease-out`}
                style={{ width: `${item.val * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-4 pt-1">
        <p className="text-[9px] font-mono text-muted-foreground uppercase">Model Individual Votes:</p>
        <div className="flex flex-wrap gap-2">
          {activeInsights.map((ins, i) => (
            <div key={i} className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: AI_PROVIDERS[ins?.provider as Provider]?.color || 'hsl(var(--primary))' }} />
              <span className="text-[9px] font-mono text-muted-foreground/80">
                {(ins?.home_prob || 0).toFixed(2)} / {(ins?.draw_prob || 0).toFixed(2)} / {(ins?.away_prob || 0).toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Shared filled insight card layout ────────────────────────────────────────

function FilledInsightCard({
  provider,
  insight,
  color,
  icon: Icon,
  fullWidth = false,
}: {
  provider: string;
  insight: Insight;
  color: string;
  icon: React.ElementType;
  fullWidth?: boolean;
}) {
  const riskCls = RISK_COLOR[insight.risk_level?.toUpperCase() ?? "MEDIUM"] ?? RISK_COLOR.MEDIUM;

  return (
    <Card
      className={`bg-card/50 backdrop-blur flex flex-col ${fullWidth ? "col-span-full" : ""}`}
      style={{ borderColor: `${color}40`, borderWidth: "1px" }}
    >
      <CardHeader className="pb-3 border-b shrink-0" style={{ borderColor: `${color}20` }}>
        <CardTitle className="flex items-center justify-between font-mono text-sm gap-2 flex-wrap">
          <span className="flex items-center gap-2">
            <Icon className="w-4 h-4 shrink-0" style={{ color }} />
            <span style={{ color }}>{provider}</span>
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
            {insight.confidence && (
              <div className="flex items-center gap-1 bg-muted/30 px-1.5 py-0.5 rounded border border-border/30">
                <TrendingUp className="w-3 h-3 text-muted-foreground" />
                <span className="text-[10px] font-mono">{(insight.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4 flex-1 flex flex-col space-y-4">
        {insight.summary && (
          <div className="space-y-1">
            <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-tight">Executive Summary</p>
            <p className="text-xs leading-relaxed text-foreground/90">{insight.summary}</p>
          </div>
        )}

        {insight.key_factors && insight.key_factors.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-mono text-muted-foreground uppercase">Core Signals</p>
            <div className="space-y-1.5">
              {insight.key_factors.slice(0, 3).map((f, i) => (
                <div key={i} className="flex gap-2 items-start group">
                  <div className="mt-1.5 w-1 h-1 rounded-full bg-primary/40 shrink-0 group-hover:bg-primary/80 transition-colors" />
                  <span className="text-[11px] leading-tight text-muted-foreground group-hover:text-foreground transition-colors">{f}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {insight.recommendation && (
          <div className="mt-auto pt-3 border-t border-border/20">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-500" />
              <p className="text-[10px] font-mono text-emerald-500 uppercase">Strategic Verdict</p>
            </div>
            <p className="text-[11px] font-bold font-mono text-foreground/90">
              {insight.recommendation}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Specific Provider Cards ──────────────────────────────────────────────────

function ServerInsightCard({
  provider,
  insight,
  isLoading,
}: {
  provider: Provider;
  insight?: Insight;
  isLoading: boolean;
}) {
  const { name, color, icon } = AI_PROVIDERS[provider];

  if (isLoading) {
    return (
      <Card className="bg-card/30 border-dashed border-border/40 animate-pulse h-[280px]">
        <CardHeader className="pb-3 border-b border-border/20">
          <Skeleton className="h-5 w-24 bg-muted/20" />
        </CardHeader>
        <CardContent className="pt-6 space-y-4">
          <Skeleton className="h-12 w-full bg-muted/10" />
          <Skeleton className="h-20 w-full bg-muted/10" />
        </CardContent>
      </Card>
    );
  }

  if (!insight || insight.available === false) {
    return (
      <Card className="bg-muted/5 border-dashed border-border/30 h-[280px] flex flex-col items-center justify-center text-center p-6 opacity-60">
        <AlertTriangle className="w-6 h-6 text-muted-foreground/30 mb-2" />
        <p className="text-[10px] font-mono text-muted-foreground uppercase mb-1">{name}</p>
        <p className="text-[9px] font-mono text-muted-foreground/50 italic">
          {insight?.error?.includes("limit") ? "Rate limited" : "Provider offline"}
        </p>
      </Card>
    );
  }

  return <FilledInsightCard provider={name} insight={insight} color={color} icon={icon} />;
}

  onRun,
  canRun,
}: {
  onRun: () => void;
  canRun: boolean;
}) {

    return (
      <Card className="bg-card/40 border-primary/20 animate-pulse h-[280px] flex flex-col items-center justify-center text-center">
        <Bot className="w-8 h-8 text-primary/40 animate-bounce mb-3" />
      </Card>
    );
  }

  }

  return (
    <Card className="bg-muted/5 border-dashed border-border/40 h-[280px] flex flex-col items-center justify-center p-6 text-center group hover:bg-muted/10 transition-colors">
      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        <Icon className="w-5 h-5 text-primary/60" />
      </div>
      <p className="text-[9px] font-mono text-muted-foreground/50 mb-4 px-2 italic">Client-side Claude — no server key required</p>
      {canRun ? (
        <Button
          size="sm"
          className="font-mono text-[10px] h-7 uppercase tracking-wider shadow-lg shadow-primary/10 hover:shadow-primary/20"
          style={{ background: color, color: "#000" }}
          onClick={onRun}
        >
          Analyze Free
        </Button>
      ) : (
        <Badge variant="secondary" className="font-mono text-[9px] opacity-50">Browser AI Pending</Badge>
      )}
    </Card>
  );
}

  onRun,
  canRun,
  homeTeam,
  awayTeam,
}: {
  onRun: () => void;
  canRun: boolean;
  homeTeam?: string;
  awayTeam?: string;
}) {

    return (
      <FilledInsightCard
        color={color}
        icon={Bot}
        fullWidth
      />
    );
  }

  return (
    <Card className="bg-primary/5 border-primary/20 overflow-hidden relative group">
      <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
        <Bot size={120} />
      </div>
      <CardHeader className="relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Bot className="w-6 h-6 text-primary" />
          </div>
          <div>
            <CardTitle className="font-mono text-sm text-primary uppercase">Browser-Side Intelligence Active</CardTitle>
            <p className="text-[10px] font-mono text-muted-foreground">Server providers are currently unavailable</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="relative z-10 pt-2 pb-6">
        <p className="text-xs text-muted-foreground max-w-md mb-5 leading-relaxed">
          I can perform a deep tactical analysis of <span className="text-foreground font-bold">{homeTeam} vs {awayTeam}</span> using
        </p>
        {canRun ? (
          <Button
            className="font-mono uppercase text-xs h-9 px-6 gap-2 shadow-xl shadow-primary/20"
            style={{ background: color, color: "#000" }}
            onClick={onRun}
          >
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Processing Tactical Data…
              </>
            ) : (
              <>
                <Bot className="w-4 h-4" />
                Analyze with Browser AI
              </>
            )}
          </Button>
        ) : (
        )}
      </CardContent>
    </Card>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

  if (!data) return undefined;
  if (data.results?.[provider]) return data.results[provider];
  return (data as any)[provider];
}

// ── Main component ────────────────────────────────────────────────────────────

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

  const autoTriggered = useRef(false);



  const serverInsights = serverProviders.map((p) => resolveInsight(insights, p));
  const serverHasAny   = serverInsights.some((ins) => ins?.available !== false && ins != null);
  const allServerFailed = !isLoading && !isError && serverInsights.every(
    (ins) => !ins || ins.available === false
  );

  useEffect(() => {
    if (
      allServerFailed &&
      !autoTriggered.current &&
      homeTeam &&
      awayTeam
    ) {
      autoTriggered.current = true;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps

    if (!homeTeam || !awayTeam) return;
    try {
      const priors = {
        home: resolveInsight(insights, "gemini")?.confidence ?? 0.34,
        draw: 0.33,
        away: 0.33,
      };
        homeTeam, awayTeam, league ?? "Football",
        priors.home, priors.draw, priors.away,
        "claude",
      );
      const insight: Insight = {
        available: true,
        summary: analysis.reason,
        key_factors: analysis.key_factors,
        confidence: analysis.confidence,
        home_prob: analysis.home_prob,
        draw_prob: analysis.draw_prob,
        away_prob: analysis.away_prob,
        risk_level: analysis.confidence >= 0.7 ? "LOW" : analysis.confidence >= 0.55 ? "MEDIUM" : "HIGH",
        recommendation: `Home ${(analysis.home_prob * 100).toFixed(0)}% · Draw ${(analysis.draw_prob * 100).toFixed(0)}% · Away ${(analysis.away_prob * 100).toFixed(0)}%`,
      };
    } catch (e: any) {
    }
  };

  const cacheHits   = insights?.cache_hits ?? [];
  const isFromCache = cacheHits.length === (insights?.sources_requested?.length ?? 0) && cacheHits.length > 0;

  return (
    <Card className="bg-card/50 backdrop-blur-md border-border/50 shadow-2xl rounded-2xl overflow-hidden">
      <CardHeader className="border-b border-border/30 bg-muted/10 pb-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <CardTitle className="font-mono uppercase flex items-center gap-2 tracking-tighter">
            <Sparkles className="w-5 h-5 text-primary" />
            AI Intelligence Comparison
              <Badge variant="outline" className="text-[9px] font-mono font-normal text-muted-foreground bg-amber-500/5 flex items-center gap-1 border-amber-500/20">
                <WifiOff className="w-3 h-3" /> server fallback active
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {isFromCache && !isFetching && (
              <span className="text-[9px] font-mono text-muted-foreground/60 border border-border/40 rounded-full px-2 py-0.5">
                cached result
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              className="font-mono text-[10px] h-7 px-3 rounded-full hover:bg-primary/5 transition-colors"
              onClick={() => { autoTriggered.current = false; refetch(); }}
              disabled={isFetching}
            >
              <RefreshCw className={`w-3 h-3 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
              {isFetching ? "SYNCING…" : "REFRESH"}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-6">
        {/* Error state */}
        {isError && !isLoading && (
          <div className="text-center py-12 space-y-4">
            <div className="w-16 h-16 rounded-full bg-amber-500/10 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-8 h-8 text-amber-500/50" />
            </div>
            <div className="space-y-1">
              <p className="font-mono text-xs text-muted-foreground uppercase font-bold">
                Intelligence Engine Unavailable
              </p>
              <p className="font-mono text-[10px] text-muted-foreground/60">
                Predictions must be generated before AI analysis can run.
              </p>
            </div>
              <div className="pt-4">
                <Button
                  size="sm"
                  className="font-mono gap-2 rounded-full px-6"
                >
                  <Bot className="w-4 h-4" />
                </Button>
              </div>
            )}
          </div>
        )}

        {!isError && (
          <>
            {/* Loading skeletons */}
            {isLoading && (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                {serverProviders.map((p) => (
                  <ServerInsightCard key={p} provider={p} isLoading />
                ))}
              </div>
            )}

            {/* Consensus Bars - New G07 feature */}
              <ConsensusBars
                insights={serverInsights}
              />
            )}

            {!isLoading && allServerFailed && (
              <div className="grid grid-cols-1 gap-4">
                  homeTeam={homeTeam}
                  awayTeam={awayTeam}
                />
              </div>
            )}

            {/* At least one server provider has data — normal grid */}
            {!isLoading && serverHasAny && (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                {serverProviders.map((p) => (
                  <ServerInsightCard
                    key={p}
                    provider={p}
                    insight={resolveInsight(insights, p)}
                    isLoading={false}
                  />
                ))}
              </div>
            )}

            {/* Provider status footer */}
              <div className="mt-8 p-4 bg-muted/10 rounded-2xl border border-border/30">
                <div className="flex items-center gap-4 flex-wrap">
                  <p className="text-[10px] font-mono text-muted-foreground uppercase font-bold tracking-widest shrink-0">Engine Connectivity</p>
                  <div className="flex flex-wrap gap-4">
                      const { name, color, icon: Icon } = AI_PROVIDERS[p];
                      let active = false;
                      } else {
                        const r = resolveInsight(insights, p);
                        active = !!r && r.available !== false;
                      }
                      return (
                        <div key={p} className="flex items-center gap-2">
                          <div
                            className={`w-2 h-2 rounded-full transition-shadow duration-500 ${active ? 'shadow-[0_0_8px_rgba(0,0,0,0.2)]' : ''}`}
                            style={{
                              backgroundColor: active ? color : "hsl(var(--muted-foreground)/0.2)",
                              boxShadow: active ? `0 0 10px ${color}40` : 'none'
                            }}
                          />
                          <span className={`text-[10px] font-mono font-bold ${active ? "" : "text-muted-foreground/30"}`} style={{ color: active ? color : undefined }}>
                            {name}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
