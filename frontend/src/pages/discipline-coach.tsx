import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ShieldCheck, AlertCircle, Zap, TrendingUp, HeartPulse, Brain,
  AlertTriangle, CheckCircle, Info,
} from "lucide-react";
import { toast } from "sonner";

interface Insight {
  type: "positive" | "warning" | "info";
  icon: string;
  title: string;
  body: string;
}

interface TiltProtection {
  daily_limit: number;
  daily_loss_used: number;
  pct_used: number;
}

interface DisciplineOverview {
  behavior_score: number;
  status: "DISCIPLINED" | "MODERATE" | "AT_RISK";
  percentile: string;
  streak: number;
  settled_predictions: number;
  win_rate: number;
  avg_stake: number;
  insights: Insight[];
  tilt_protection: TiltProtection;
  next_milestone: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; ring: string; arc: string }> = {
  DISCIPLINED: {
    label: "DISCIPLINED",
    color: "text-emerald-400",
    ring: "border-emerald-500/30 bg-emerald-500/5",
    arc: "text-emerald-500",
  },
  MODERATE: {
    label: "MODERATE",
    color: "text-yellow-400",
    ring: "border-yellow-500/30 bg-yellow-500/5",
    arc: "text-yellow-500",
  },
  AT_RISK: {
    label: "AT RISK",
    color: "text-red-400",
    ring: "border-red-500/30 bg-red-500/5",
    arc: "text-red-500",
  },
};

const INSIGHT_ICONS: Record<string, React.ReactNode> = {
  zap:    <Zap   className="w-5 h-5 text-emerald-400 shrink-0" />,
  alert:  <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0" />,
  brain:  <Brain className="w-5 h-5 text-cyan-400 shrink-0" />,
  trend:  <TrendingUp className="w-5 h-5 text-blue-400 shrink-0" />,
  info:   <Info  className="w-5 h-5 text-muted-foreground shrink-0" />,
};

const INSIGHT_STYLE: Record<string, string> = {
  positive: "bg-emerald-500/5 border-emerald-500/10",
  warning:  "bg-yellow-500/5 border-yellow-500/20",
  info:     "bg-muted/40 border-border/50",
};

const INSIGHT_TITLE_COLOR: Record<string, string> = {
  positive: "text-emerald-400",
  warning:  "text-yellow-400",
  info:     "text-muted-foreground",
};

function ScoreGauge({ score, arc }: { score: number; arc: string }) {
  const circumference = 364;
  const offset = circumference - (circumference * score) / 100;
  return (
    <div className="relative w-36 h-36 flex items-center justify-center">
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r="58" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-zinc-800" />
        <circle
          cx="64" cy="64" r="58"
          stroke="currentColor" strokeWidth="8" fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={arc}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div className="absolute text-4xl font-black font-mono">{score}</div>
    </div>
  );
}

export default function DisciplineCoachPage() {
  const [cooldownPending, setCooldownPending] = useState(false);

  const { data, isLoading, isError } = useQuery<DisciplineOverview>({
    queryKey: ["discipline-overview"],
    queryFn: () => apiGet("/api/compliance/discipline/overview"),
    staleTime: 60_000,
    retry: 1,
  });

  const cooldown = useMutation({
    mutationFn: () => apiPost("/api/compliance/discipline/cooldown", {}),
    onSuccess: (res: any) => {
      toast.success(res.message ?? "24h cooldown activated. ");
      setCooldownPending(false);
    },
    onError: (e: any) => {
      toast.error(e?.message ?? "Failed to activate cooldown");
      setCooldownPending(false);
    },
  });

  if (isError) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-3">
        <AlertCircle className="w-10 h-10 text-muted-foreground mx-auto" />
        <p className="text-muted-foreground">Could not load your discipline data. Please log in to view coaching insights.</p>
      </div>
    );
  }

  const cfg    = data ? STATUS_CONFIG[data.status] ?? STATUS_CONFIG.MODERATE : null;
  const tilt   = data?.tilt_protection;
  const streak = data?.streak ?? 0;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            Bankroll Discipline
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            AI-powered behavioral monitoring and tilt protection
          </p>
        </div>
        {isLoading ? (
          <Skeleton className="h-7 w-32 rounded-full" />
        ) : cfg && (
          <Badge className={`font-mono border ${cfg.ring} ${cfg.color}`}>
            STATUS: {cfg.label}
          </Badge>
        )}
      </div>

      {/* Score + Insights row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Score gauge */}
        <Card className="bg-card border-border/50 md:col-span-1">
          <CardHeader className="pb-2 text-center">
            <CardTitle className="text-sm font-mono text-zinc-500 uppercase">Behavior Score</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center py-6 gap-4">
            {isLoading ? (
              <Skeleton className="w-36 h-36 rounded-full" />
            ) : (
              <>
                <ScoreGauge score={data!.behavior_score} arc={cfg!.arc} />
                <p className="text-xs text-zinc-500 text-center px-4">
                  You are in the{" "}
                  <span className={`font-bold ${cfg!.color}`}>{data!.percentile}</span>{" "}
                  of disciplined users.
                </p>
                <div className="grid grid-cols-2 gap-2 w-full text-center text-xs">
                  <div className="bg-muted/50 rounded-lg py-2">
                    <p className="text-muted-foreground text-[10px] uppercase">Win Rate</p>
                    <p className="font-bold text-foreground">{(data!.win_rate * 100).toFixed(1)}%</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg py-2">
                    <p className="text-muted-foreground text-[10px] uppercase">Streak</p>
                    <p className={`font-bold ${streak > 0 ? "text-emerald-400" : streak < 0 ? "text-red-400" : "text-foreground"}`}>
                      {streak > 0 ? `+${streak}` : streak < 0 ? `${streak}` : "—"}
                    </p>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Coach Insights */}
        <Card className="bg-card border-border/50 md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Coach Insights</CardTitle>
            <CardDescription>Real-time feedback on your signal patterns</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading ? (
              Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-16 rounded-xl" />
              ))
            ) : (
              (data!.insights.length === 0 ? (
                <div className="flex gap-4 p-4 bg-muted/40 border border-border/50 rounded-xl">
                  <Info className="w-5 h-5 text-muted-foreground shrink-0" />
                  <div>
                    <h4 className="text-sm font-bold text-muted-foreground">No Insights Yet</h4>
                    <p className="text-xs text-zinc-400 mt-1">
                      Make some predictions to unlock personalised coaching.
                    </p>
                  </div>
                </div>
              ) : (
                data!.insights.map((ins, i) => (
                  <div
                    key={i}
                    className={`flex gap-4 p-4 border rounded-xl ${INSIGHT_STYLE[ins.type]}`}
                  >
                    {INSIGHT_ICONS[ins.icon] ?? <Info className="w-5 h-5 shrink-0" />}
                    <div>
                      <h4 className={`text-sm font-bold ${INSIGHT_TITLE_COLOR[ins.type]}`}>{ins.title}</h4>
                      <p className="text-xs text-zinc-400 mt-1">{ins.body}</p>
                    </div>
                  </div>
                ))
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tilt Protection */}
      <Card className="bg-zinc-900 border-red-500/20">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <HeartPulse className="w-5 h-5 text-red-400" />
            Tilt Protection
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {isLoading ? (
            <Skeleton className="h-10 w-full" />
          ) : tilt && (
            <>
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-xs text-zinc-400 uppercase tracking-wide">Daily Loss Limit Usage</span>
                  <span className="text-xs font-mono">
                    ${tilt.daily_loss_used.toFixed(2)} / ${tilt.daily_limit.toFixed(2)}
                  </span>
                </div>
                <Progress
                  value={tilt.pct_used}
                  className={`h-2 bg-zinc-800 ${tilt.pct_used > 75 ? "[&>div]:bg-red-500" : tilt.pct_used > 50 ? "[&>div]:bg-yellow-500" : "[&>div]:bg-emerald-500"}`}
                />
                {tilt.pct_used > 75 && (
                  <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Approaching daily limit — consider pausing.
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 border border-border/50 rounded-xl">
                  <h5 className="text-xs font-mono text-zinc-500 uppercase mb-2">Self-Exclusion</h5>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 p-0 h-auto"
                    onClick={() => {
                      setCooldownPending(true);
                      cooldown.mutate();
                    }}
                    disabled={cooldown.isPending || cooldownPending}
                  >
                    {cooldown.isPending ? "Activating..." : "Activate 24h Cooldown"}
                  </Button>
                  <p className="text-xs text-muted-foreground mt-1">
                    Pauses all prediction activity for 24 hours.
                  </p>
                </div>
                <div className="p-4 border border-border/50 rounded-xl">
                  <h5 className="text-xs font-mono text-zinc-500 uppercase mb-2">Next Milestone</h5>
                  <p className="text-sm text-zinc-300">{data!.next_milestone}</p>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Stats row */}
      {data && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Settled Predictions", value: data.settled_predictions },
            { label: "Win Rate", value: `${(data.win_rate * 100).toFixed(1)}%` },
            { label: "Avg Stake", value: `${(data.avg_stake * 100).toFixed(1)}%` },
          ].map(({ label, value }) => (
            <Card key={label} className="p-3 text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</p>
              <p className="text-lg font-bold text-foreground mt-1">{value}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
