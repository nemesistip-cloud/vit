import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BrainCircuit, Zap, Sparkles, RefreshCw } from "lucide-react";

const AI_PROVIDERS = {
  gemini:  { name: "Gemini",  color: "hsl(var(--primary))",     icon: Sparkles },
  claude:  { name: "Claude",  color: "hsl(262 83% 58%)",        icon: BrainCircuit },
  grok:    { name: "Grok",    color: "hsl(var(--secondary))",   icon: Zap },
} as const;

type Provider = keyof typeof AI_PROVIDERS;

interface Insight {
  summary?: string;
  key_factors?: string[];
  recommendation?: string;
  confidence?: number;
  provider?: string;
}

interface InsightsData {
  gemini?: Insight;
  claude?: Insight;
  grok?: Insight;
  match_id?: number;
  source?: string;
}

function InsightCard({ provider, insight, isLoading }: { provider: Provider; insight?: Insight; isLoading: boolean }) {
  const { name, color, icon: Icon } = AI_PROVIDERS[provider];

  if (isLoading) {
    return (
      <Card className="bg-card/40 backdrop-blur border-border animate-pulse">
        <CardHeader className="pb-3">
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/5" />
        </CardContent>
      </Card>
    );
  }

  if (!insight) {
    return (
      <Card className="bg-card/20 backdrop-blur border-border/50">
        <CardContent className="flex flex-col items-center justify-center min-h-[200px] text-center">
          <Icon className="w-8 h-8 text-muted-foreground/40 mb-3" />
          <p className="font-mono text-xs text-muted-foreground uppercase">No insight available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur" style={{ borderColor: `${color}40`, borderWidth: "1px" }}>
      <CardHeader className="pb-3 border-b" style={{ borderColor: `${color}20` }}>
        <CardTitle className="flex items-center justify-between font-mono text-sm">
          <span className="flex items-center gap-2">
            <Icon className="w-4 h-4" style={{ color }} />
            <span style={{ color }}>{name}</span>
          </span>
          {insight.confidence != null && (
            <Badge variant="outline" className="font-mono text-xs" style={{ borderColor: `${color}40`, color }}>
              {(insight.confidence * 100).toFixed(0)}% confident
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        {insight.summary && (
          <div>
            <p className="text-xs font-mono text-muted-foreground uppercase mb-2">Summary</p>
            <p className="text-sm leading-relaxed">{insight.summary}</p>
          </div>
        )}

        {insight.key_factors && insight.key_factors.length > 0 && (
          <div>
            <p className="text-xs font-mono text-muted-foreground uppercase mb-2">Key Factors</p>
            <div className="space-y-2">
              {insight.key_factors.map((factor, i) => (
                <div
                  key={i}
                  className="flex gap-2 text-sm p-2 rounded bg-muted/30"
                  style={{ borderLeft: `3px solid ${color}` }}
                >
                  <span className="text-muted-foreground">→</span>
                  <span>{factor}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {insight.recommendation && (
          <div
            className="p-3 rounded-lg"
            style={{ background: `${color}10`, borderLeft: `3px solid ${color}` }}
          >
            <p className="text-xs font-mono uppercase mb-1" style={{ color }}>Recommendation</p>
            <p className="text-sm font-semibold">{insight.recommendation}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AIInsightComparison({ matchId }: { matchId: string }) {
  const { data: insights, isLoading, isError, refetch, isFetching } = useQuery<InsightsData>({
    queryKey: ["ai-insights", matchId],
    queryFn: () => apiGet<InsightsData>(`/predict/${matchId}/insights`),
    enabled: !!matchId,
    retry: false,
  });

  const hasAny = insights?.gemini || insights?.claude || insights?.grok;

  return (
    <Card className="bg-card/50 backdrop-blur border-border">
      <CardHeader className="border-b border-border/50 pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono uppercase flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            Multi-AI Intelligence
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`w-3 h-3 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
            {isFetching ? "FETCHING..." : "REFRESH"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-6">
        {isError && !isLoading && (
          <div className="text-center py-8 space-y-2">
            <BrainCircuit className="w-8 h-8 text-muted-foreground/30 mx-auto" />
            <p className="font-mono text-xs text-muted-foreground uppercase">AI insights require a prediction to be run first</p>
            <p className="font-mono text-[10px] text-muted-foreground/60">Run the ML Ensemble on this match to generate insights</p>
          </div>
        )}
        {!isError && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(["gemini", "claude", "grok"] as Provider[]).map((provider) => (
                <InsightCard
                  key={provider}
                  provider={provider}
                  insight={insights?.[provider]}
                  isLoading={isLoading}
                />
              ))}
            </div>

            {insights?.source === "ml_fallback" && !isLoading && (
              <div className="mt-4 px-3 py-2 bg-muted/30 rounded-lg border border-border/40 text-center">
                <p className="text-[10px] font-mono text-muted-foreground">
                  Insights generated from ML ensemble — configure AI API keys for LLM analysis
                </p>
              </div>
            )}

            {hasAny && !isLoading && (
              <div className="mt-6 p-4 bg-muted/20 rounded-lg border border-border/50">
                <p className="text-xs font-mono text-muted-foreground uppercase mb-3">Provider Status</p>
                <div className="grid grid-cols-3 gap-3">
                  {(["gemini", "claude", "grok"] as Provider[]).map((p) => {
                    const { name, color, icon: Icon } = AI_PROVIDERS[p];
                    const available = !!insights?.[p];
                    return (
                      <div key={p} className="flex items-center gap-2 p-2 rounded bg-background/50 border border-border/30">
                        <Icon className="w-3 h-3" style={{ color: available ? color : "hsl(var(--muted-foreground))" }} />
                        <div>
                          <p className="text-xs font-mono font-bold" style={{ color: available ? color : "hsl(var(--muted-foreground))" }}>
                            {name}
                          </p>
                          <p className="text-[10px] font-mono text-muted-foreground">
                            {available ? "Generated" : "Pending"}
                          </p>
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
