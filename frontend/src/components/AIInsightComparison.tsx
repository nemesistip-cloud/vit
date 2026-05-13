import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BrainCircuit, Zap, Sparkles, RefreshCw, TrendingUp,
  AlertTriangle, Bot, CheckCircle2, WifiOff, BarChart2,
} from "lucide-react";
import { analyzeMatchWithPuter, isPuterAvailable, MatchAnalysis } from "@/lib/puter-ai";

const AI_PROVIDERS = {
  gemini:        { name: "Gemini",              color: "hsl(var(--primary))",   icon: Sparkles     },
  claude:        { name: "Claude",              color: "hsl(262 83% 58%)",      icon: BrainCircuit },
  grok:          { name: "Grok",                color: "hsl(var(--secondary))", icon: Zap           },
  puter:         { name: "Puter",               color: "hsl(173 80% 50%)",      icon: Bot           },
  deterministic: { name: "VIT Statistical Engine", color: "hsl(220 70% 60%)", icon: BarChart2     },
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
  is_fallback?: boolean;
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

// ── Shared filled insight card ────────────────────────────────────────────────

function FilledInsightCard({
  provider,
  insight,
  color,
  icon: Icon,
  fullWidth = false,
  isFallback = false,
}: {
  provider: string;
  insight: Insight;
  color: string;
  icon: React.ElementType;
  fullWidth?: boolean;
  isFallback?: boolean;
}) {
  const riskCls = RISK_COLOR[insight.risk_level?.toUpperCase() ?? "MEDIUM"] ?? RISK_COLOR.MEDIUM;

  return (
    <Card
      className={`bg-card/60 flex flex-col ${fullWidth ? "col-span-full" : ""}`}
      style={{ borderColor: `${color}40`, borderWidth: "1px" }}
    >
      <CardHeader className="pb-3 border-b shrink-0" style={{ borderColor: `${color}20` }}>
        <CardTitle className="flex items-center justify-between font-mono text-sm gap-2 flex-wrap">
          <span className="flex items-center gap-2">
            <Icon className="w-4 h-4 shrink-0" style={{ color }} />
            <span style={{ color }}>{provider}</span>
            {isFallback && (
              <span className="text-[9px] font-mono text-muted-foreground/60 border border-border/40 rounded px-1">
                statistical
              </span>
            )}
            {insight.from_cache && !isFallback && (
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
      <CardContent className={`pt-4 space-y-4 flex-1 ${fullWidth ? "grid md:grid-cols-2 gap-6 space-y-0" : ""}`}>
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
              {insight.key_factors.map((f, i) => (
                <div key={i} className="flex gap-2 text-sm p-2 rounded-md bg-muted/30" style={{ borderLeft: `2px solid ${color}` }}>
                  <TrendingUp className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color }} />
                  <span className="text-sm leading-snug">{f}</span>
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
          <div className="p-3 rounded-lg" style={{ background: `${color}08`, borderLeft: `3px solid ${color}` }}>
            <p className="text-[10px] font-mono uppercase mb-1" style={{ color }}>Recommendation</p>
            <p className="text-sm font-semibold">{insight.recommendation}</p>
          </div>
        )}
        {insight.insight_tags && insight.insight_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {insight.insight_tags.map((tag, i) => (
              <span key={i} className="text-[9px] font-mono px-1.5 py-0.5 rounded border"
                style={{ color, borderColor: `${color}40`, background: `${color}08` }}>
                {tag}
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Puter hero card ───────────────────────────────────────────────────────────

function PuterHeroCard({
  puterState, onRun, canRun, homeTeam, awayTeam,
}: {
  puterState: PuterInsightState; onRun: () => void;
  canRun: boolean; homeTeam?: string; awayTeam?: string;
}) {
  const color = AI_PROVIDERS.puter.color;

  if (puterState.status === "loading") {
    return (
      <Card className="col-span-full bg-card/60" style={{ borderColor: `${color}40`, borderWidth: "1px" }}>
        <CardContent className="py-10 flex flex-col items-center gap-4">
          <Bot className="w-8 h-8 animate-pulse" style={{ color }} />
          <p className="font-mono text-sm" style={{ color }}>Puter AI is analyzing {homeTeam} vs {awayTeam}…</p>
          <p className="text-xs text-muted-foreground font-mono">Free browser-side analysis — no API key needed</p>
          <div className="w-full max-w-sm space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6 mx-auto" />
            <Skeleton className="h-3 w-4/6 mx-auto" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (puterState.status === "done" && puterState.insight) {
    return (
      <FilledInsightCard
        provider="Puter AI · Free"
        insight={puterState.insight}
        color={color}
        icon={Bot}
        fullWidth
      />
    );
  }

  if (puterState.status === "error") {
    return (
      <Card className="col-span-full bg-card/60" style={{ borderColor: `${color}30`, borderWidth: "1px" }}>
        <CardContent className="py-8 flex flex-col items-center gap-3">
          <Bot className="w-7 h-7 text-muted-foreground/40" />
          <p className="font-mono text-xs text-muted-foreground uppercase">Puter AI — Analysis failed</p>
          <p className="font-mono text-[10px] text-amber-500/80 text-center max-w-xs">{puterState.error}</p>
          {canRun && (
            <Button size="sm" variant="outline" className="font-mono text-xs mt-1" onClick={onRun}>
              Retry Free Analysis
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="col-span-full bg-card/60" style={{ borderColor: `${color}40`, borderWidth: "1px", background: `${color}05` }}>
      <CardContent className="py-10 flex flex-col items-center gap-4 text-center">
        <Bot className="w-10 h-10" style={{ color }} />
        <div>
          <p className="font-mono text-base font-bold" style={{ color }}>Puter AI — Free Analysis</p>
          <p className="text-sm text-muted-foreground mt-1">
            Server AI providers are unavailable. Get a full tactical analysis powered by
            Claude via Puter.js — completely free, runs in your browser.
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-4 text-xs text-muted-foreground font-mono">
          {["No API key needed", "Browser-side Claude", "Tactical probabilities", "Key factors"].map((t) => (
            <span key={t} className="flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-500" /> {t}
            </span>
          ))}
        </div>
        {canRun ? (
          <Button
            size="lg" className="font-mono gap-2 mt-2"
            style={{ background: color, color: "#000" }} onClick={onRun}
          >
            <Bot className="w-4 h-4" /> Analyze Free with Puter AI
          </Button>
        ) : (
          <p className="font-mono text-[10px] text-amber-500/80">
            Puter.js not ready — ensure you are on a supported browser
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Standard server provider card ─────────────────────────────────────────────

function ServerInsightCard({
  provider, insight, isLoading,
}: {
  provider: Exclude<Provider, "puter" | "deterministic">;
  insight?: Insight;
  isLoading: boolean;
}) {
  const { name, color, icon: Icon } = AI_PROVIDERS[provider];

  if (isLoading) {
    return (
      <Card className="bg-card/40 border-border">
        <CardHeader className="pb-3"><Skeleton className="h-6 w-32" /></CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/5" />
        </CardContent>
      </Card>
    );
  }

  if (!insight || insight.available === false) {
    return (
      <Card className="bg-card/30 border-border/40">
        <CardContent className="flex flex-col items-center justify-center min-h-[180px] text-center gap-2 p-6">
          <Icon className="w-7 h-7 text-muted-foreground/20" />
          <p className="font-mono text-[11px] text-muted-foreground/50 uppercase">{name}</p>
          <p className="font-mono text-[10px] text-muted-foreground/40">Unavailable</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <FilledInsightCard
      provider={name}
      insight={insight}
      color={color}
      icon={Icon}
      isFallback={insight.is_fallback}
    />
  );
}

// ── Puter grid card ───────────────────────────────────────────────────────────

function PuterGridCard({
  puterState, onRun, canRun,
}: {
  puterState: PuterInsightState; onRun: () => void; canRun: boolean;
}) {
  const color = AI_PROVIDERS.puter.color;

  if (puterState.status === "loading") {
    return (
      <Card className="bg-card/40" style={{ borderColor: `${color}40`, borderWidth: "1px" }}>
        <CardHeader className="pb-3"><Skeleton className="h-6 w-32" style={{ background: `${color}20` }} /></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-mono" style={{ color }}>
            <Bot className="w-4 h-4 animate-pulse" /> Analyzing…
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </CardContent>
      </Card>
    );
  }

  if (puterState.status === "done" && puterState.insight) {
    return <FilledInsightCard provider="Puter" insight={puterState.insight} color={color} icon={Bot} />;
  }

  if (puterState.status === "error") {
    return (
      <Card className="bg-card/30 border-border/40">
        <CardContent className="flex flex-col items-center justify-center min-h-[180px] text-center gap-2 p-6">
          <Bot className="w-7 h-7 text-muted-foreground/30" />
          <p className="font-mono text-[10px] text-amber-500/80">{puterState.error}</p>
          {canRun && (
            <Button size="sm" variant="outline" className="font-mono text-xs mt-1" onClick={onRun}>Retry</Button>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/30 flex flex-col" style={{ borderColor: `${color}40`, borderWidth: "1px" }}>
      <CardContent className="flex flex-col items-center justify-center min-h-[180px] text-center gap-3 p-6">
        <Bot className="w-7 h-7" style={{ color }} />
        <p className="font-mono text-xs font-bold" style={{ color }}>Puter AI · Free</p>
        <p className="font-mono text-[10px] text-muted-foreground">Browser-side Claude — no key</p>
        {canRun ? (
          <Button size="sm" className="font-mono text-xs" style={{ background: color, color: "#000" }} onClick={onRun}>
            Analyze Free
          </Button>
        ) : (
          <p className="font-mono text-[10px] text-amber-500/80">Puter not ready</p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function resolveInsight(data: InsightsData | undefined, provider: Exclude<Provider, "puter">): Insight | undefined {
  if (!data) return undefined;
  if (data.results?.[provider]) return data.results[provider];
  return (data as any)[provider];
}

// ── Main component ────────────────────────────────────────────────────────────

export function AIInsightComparison({
  matchId, homeTeam, awayTeam, league,
}: {
  matchId: string; homeTeam?: string; awayTeam?: string; league?: string;
}) {
  const { data: insights, isLoading, isError, refetch, isFetching } = useQuery<InsightsData>({
    queryKey: ["ai-insights", matchId],
    queryFn: () => apiGet<InsightsData>(`/ai/multi-insights/${matchId}`),
    enabled: !!matchId,
    retry: 1,
    staleTime: 5 * 60 * 1000,
  });

  const [puterState, setPuterState] = useState<PuterInsightState>({ status: "idle" });
  const autoTriggered = useRef(false);

  const canRunPuter = isPuterAvailable() && !!homeTeam && !!awayTeam;
  const serverProviders: Exclude<Provider, "puter" | "deterministic">[] = ["gemini", "claude", "grok"];

  const serverInsights = serverProviders.map((p) => resolveInsight(insights, p));

  // Has any LLM slot with real (non-fallback) data?
  const hasRealLLM = serverInsights.some(
    (ins) => ins?.available !== false && ins != null && !ins.is_fallback
  );
  // Any server slot at all (including fallback)?
  const serverHasAny = serverInsights.some(
    (ins) => ins?.available !== false && ins != null
  );
  // Deterministic slot from backend deduplication
  const deterministicInsight = resolveInsight(insights, "deterministic");
  const hasDeterministic = !!deterministicInsight && deterministicInsight.available !== false;

  // All server providers truly failed (no real LLM AND no deterministic fallback)
  const allServerFailed = !isLoading && !isError &&
    !serverHasAny && !hasDeterministic;

  // Auto-trigger Puter when all server providers are truly unavailable
  useEffect(() => {
    if (
      allServerFailed &&
      !autoTriggered.current &&
      canRunPuter &&
      puterState.status === "idle" &&
      homeTeam && awayTeam
    ) {
      autoTriggered.current = true;
      runPuter();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allServerFailed, canRunPuter]);

  const runPuter = async () => {
    if (!homeTeam || !awayTeam) return;
    setPuterState({ status: "loading" });
    try {
      const priors = {
        home: resolveInsight(insights, "gemini")?.confidence ?? 0.34,
        draw: 0.33,
        away: 0.33,
      };
      const analysis: MatchAnalysis = await analyzeMatchWithPuter(
        homeTeam, awayTeam, league ?? "Football",
        priors.home, priors.draw, priors.away, "claude",
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

  const cacheHits   = insights?.cache_hits ?? [];
  const isFromCache = cacheHits.length === (insights?.sources_requested?.length ?? 0) && cacheHits.length > 0;

  return (
    <Card className="bg-card/60 border-border">
      <CardHeader className="border-b border-border/50 pb-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <CardTitle className="font-mono uppercase flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            Multi-AI Intelligence
            {allServerFailed && puterState.status !== "done" && (
              <span className="text-[10px] font-mono font-normal text-muted-foreground border border-border/40 rounded px-1.5 py-0.5 flex items-center gap-1">
                <WifiOff className="w-3 h-3" /> server offline · Puter fallback
              </span>
            )}
            {hasDeterministic && !hasRealLLM && (
              <span className="text-[10px] font-mono font-normal text-blue-400/80 border border-blue-400/30 rounded px-1.5 py-0.5 flex items-center gap-1">
                <BarChart2 className="w-3 h-3" /> statistical engine
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {isFromCache && !isFetching && (
              <span className="text-[9px] font-mono text-muted-foreground/60 border border-border/40 rounded px-1.5 py-0.5">
                from cache
              </span>
            )}
            <Button
              variant="outline" size="sm"
              className="font-mono text-xs h-7 px-2.5"
              onClick={() => { autoTriggered.current = false; refetch(); }}
              disabled={isFetching}
            >
              <RefreshCw className={`w-3 h-3 mr-1 ${isFetching ? "animate-spin" : ""}`} />
              {isFetching ? "FETCHING…" : "REFRESH"}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-6">
        {/* Error state */}
        {isError && !isLoading && (
          <div className="text-center py-8 space-y-3">
            <AlertTriangle className="w-8 h-8 text-amber-500/50 mx-auto" />
            <p className="font-mono text-xs text-muted-foreground uppercase">
              AI insights require a prediction first
            </p>
            <p className="font-mono text-[10px] text-muted-foreground/60">
              Run the ML Ensemble on this match, then refresh insights
            </p>
            {canRunPuter && (
              <div className="pt-2">
                <p className="text-xs text-muted-foreground mb-2">
                  Or get a free browser-side analysis now:
                </p>
                <Button
                  size="sm" className="font-mono gap-2"
                  style={{ background: AI_PROVIDERS.puter.color, color: "#000" }}
                  onClick={runPuter}
                  disabled={puterState.status === "loading"}
                >
                  <Bot className="w-3 h-3" />
                  {puterState.status === "loading" ? "Analyzing…" : "Analyze Free with Puter"}
                </Button>
              </div>
            )}
            {puterState.status === "done" && puterState.insight && (
              <div className="mt-4">
                <FilledInsightCard
                  provider="Puter AI · Free"
                  insight={puterState.insight}
                  color={AI_PROVIDERS.puter.color}
                  icon={Bot}
                  fullWidth
                />
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
                <PuterGridCard puterState={{ status: "idle" }} onRun={runPuter} canRun={canRunPuter} />
              </div>
            )}

            {/* Deterministic fallback — all LLMs were down, backend consolidated into 1 card */}
            {!isLoading && hasDeterministic && !hasRealLLM && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4">
                  <FilledInsightCard
                    provider="VIT Statistical Engine"
                    insight={deterministicInsight!}
                    color={AI_PROVIDERS.deterministic.color}
                    icon={BarChart2}
                    fullWidth
                    isFallback
                  />
                </div>
                {/* Still show Puter option alongside */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-muted/20 border border-border/40 flex items-start gap-3">
                    <BarChart2 className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                    <p className="text-[11px] font-mono text-muted-foreground leading-relaxed">
                      Live AI providers (Gemini, Claude, Grok) are temporarily unavailable.
                      The VIT Statistical Engine above provides a deterministic analysis from
                      the 13-model ensemble. Try Puter AI for a free LLM-powered breakdown:
                    </p>
                  </div>
                  <PuterGridCard puterState={puterState} onRun={runPuter} canRun={canRunPuter} />
                </div>
              </div>
            )}

            {/* All providers truly failed — Puter takes full width */}
            {!isLoading && allServerFailed && (
              <div className="grid grid-cols-1 gap-4">
                <PuterHeroCard
                  puterState={puterState} onRun={runPuter} canRun={canRunPuter}
                  homeTeam={homeTeam} awayTeam={awayTeam}
                />
              </div>
            )}

            {/* Normal 4-col grid — at least one real LLM answered */}
            {!isLoading && serverHasAny && (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                {serverProviders.map((p) => (
                  <ServerInsightCard
                    key={p} provider={p}
                    insight={resolveInsight(insights, p)}
                    isLoading={false}
                  />
                ))}
                <PuterGridCard puterState={puterState} onRun={runPuter} canRun={canRunPuter} />
              </div>
            )}

            {/* Provider status footer */}
            {!isLoading && (serverHasAny || hasDeterministic || puterState.status === "done") && (
              <div className="mt-5 p-3 bg-muted/20 rounded-lg border border-border/40">
                <div className="flex items-center gap-3 flex-wrap">
                  <p className="text-[10px] font-mono text-muted-foreground uppercase shrink-0">Providers</p>
                  {(["gemini", "claude", "grok", "deterministic", "puter"] as Provider[]).map((p) => {
                    const { name, color, icon: Icon } = AI_PROVIDERS[p];
                    let active = false;
                    if (p === "puter") {
                      active = puterState.status === "done";
                    } else if (p === "deterministic") {
                      active = hasDeterministic;
                    } else {
                      const r = resolveInsight(insights, p);
                      active = !!r && r.available !== false && !r.is_fallback;
                    }
                    return (
                      <div key={p} className="flex items-center gap-1.5">
                        <Icon className="w-3 h-3" style={{ color: active ? color : "hsl(var(--muted-foreground))" }} />
                        <span className="text-[10px] font-mono" style={{ color: active ? color : undefined }}>
                          {name}
                        </span>
                        <span className={`w-1.5 h-1.5 rounded-full ${active ? "bg-emerald-500" : "bg-muted-foreground/30"}`} />
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
