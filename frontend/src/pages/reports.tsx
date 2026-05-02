import { useState, useEffect, useRef } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Activity, Brain, AlertTriangle, BarChart3, RefreshCw,
  ChevronDown, ChevronUp, Radio, Target, Zap, Shield,
  TrendingUp, Clock, Bot, Newspaper, Play,
} from "lucide-react";
import { vitWS } from "@/lib/websocket";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AgentReport {
  id: number;
  agent_name: string;
  insight_type: string;
  match_id: number | null;
  team: string | null;
  content: string;
  meta: Record<string, any> | null;
  confidence: number | null;
  ai_provider: string | null;
  created_at: string | null;
}

interface LiveScore {
  id: number;
  home_team: string;
  away_team: string;
  league: string | null;
  home_score: number | null;
  away_score: number | null;
  status: string;
  kickoff: string | null;
}

interface ReportsData { count: number; reports: AgentReport[] }
interface LiveData    { live_count: number; matches: LiveScore[] }

// ─── Config ───────────────────────────────────────────────────────────────────

const AGENT_CONFIG: Record<string, { label: string; color: string; icon: React.FC<any>; bg: string }> = {
  "match-scout":        { label: "Match Scout",       color: "text-cyan-400",    icon: Brain,         bg: "border-cyan-500/30 bg-cyan-500/5" },
  "news-sentinel":      { label: "News Sentinel",     color: "text-amber-400",   icon: Newspaper,     bg: "border-amber-500/30 bg-amber-500/5" },
  "analytics-reporter": { label: "Analytics",         color: "text-violet-400",  icon: BarChart3,     bg: "border-violet-500/30 bg-violet-500/5" },
  "odds-anomaly":       { label: "Odds Anomaly",      color: "text-rose-400",    icon: AlertTriangle, bg: "border-rose-500/30 bg-rose-500/5" },
  "live-match-tracker": { label: "Live Tracker",      color: "text-green-400",   icon: Radio,         bg: "border-green-500/30 bg-green-500/5" },
  "prediction-moderator":{ label: "Moderator",        color: "text-blue-400",    icon: Shield,        bg: "border-blue-500/30 bg-blue-500/5" },
  "performance-monitor": { label: "Perf Monitor",     color: "text-orange-400",  icon: Activity,      bg: "border-orange-500/30 bg-orange-500/5" },
  "fraud-review":        { label: "Fraud Review",     color: "text-red-400",     icon: Shield,        bg: "border-red-500/30 bg-red-500/5" },
  "accumulator-publisher":{ label: "Accumulator",     color: "text-emerald-400", icon: Target,        bg: "border-emerald-500/30 bg-emerald-500/5" },
};

const DEFAULT_CONFIG = { label: "Agent", color: "text-gray-400", icon: Bot, bg: "border-gray-500/30 bg-gray-500/5" };

const SEVERITY_CLS: Record<string, string> = {
  CRITICAL: "text-red-400 border-red-500/40 bg-red-500/10",
  HIGH:     "text-rose-400 border-rose-500/40 bg-rose-500/10",
  MEDIUM:   "text-amber-400 border-amber-500/40 bg-amber-500/10",
  LOW:      "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
};

const RISK_CLS: Record<string, string> = {
  HIGH:   "text-red-400 border-red-500/40 bg-red-500/10",
  MEDIUM: "text-amber-400 border-amber-500/40 bg-amber-500/10",
  LOW:    "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
};

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// ─── Live Scores Ticker ───────────────────────────────────────────────────────

function LiveScoresTicker({ scores, wsGoals }: { scores: LiveScore[]; wsGoals: LiveScore[] }) {
  const all = [
    ...wsGoals,
    ...scores.filter(s => !wsGoals.find(w => w.id === s.id)),
  ];
  if (all.length === 0) return null;
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-green-500/10 border border-green-500/30 rounded-xl overflow-x-auto">
      <Radio className="w-4 h-4 text-green-400 animate-pulse shrink-0" />
      <div className="flex items-center gap-4 min-w-0">
        {all.map((m) => (
          <div key={m.id} className="flex items-center gap-2 shrink-0">
            <span className="text-xs font-mono text-white font-semibold whitespace-nowrap">
              {m.home_team} <span className="text-green-400 font-bold">{m.home_score ?? "?"}-{m.away_score ?? "?"}</span> {m.away_team}
            </span>
            {m.league && (
              <span className="text-[10px] font-mono text-green-600">· {m.league.replace(/_/g, " ")}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Report Card ──────────────────────────────────────────────────────────────

function ReportCard({ report }: { report: AgentReport }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = AGENT_CONFIG[report.agent_name] ?? DEFAULT_CONFIG;
  const Icon = cfg.icon;
  const meta = report.meta ?? {};

  const riskLevel   = meta.risk_level ?? meta.severity;
  const riskCls     = RISK_CLS[riskLevel?.toUpperCase()] ?? SEVERITY_CLS[riskLevel?.toUpperCase()];
  const keyFactors: string[] = meta.key_factors ?? [];
  const inPlayBet   = meta.in_play_bet;
  const valuePick   = meta.value_pick ?? meta.betting_implication;
  const momentum    = meta.momentum;
  const teamStats   = meta.stats;
  const matchLabel  = meta.match ?? (meta.team ? `Team: ${meta.team}` : null);
  const isLive      = report.insight_type === "live_update";
  const isAnalytics = report.insight_type === "daily_brief" || report.insight_type === "weekly_report";

  return (
    <Card className={`border ${cfg.bg} transition-all duration-200`}>
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Icon className={`w-4 h-4 shrink-0 ${cfg.color}`} />
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className={`text-xs font-mono font-bold ${cfg.color}`}>{cfg.label}</span>
                {isLive && (
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                    <Radio className="w-2.5 h-2.5" /> LIVE
                  </span>
                )}
                {report.insight_type === "weekly_report" && (
                  <Badge className="bg-violet-500/20 text-violet-300 border-violet-500/30 text-[9px]">weekly</Badge>
                )}
                {riskCls && riskLevel && (
                  <Badge variant="outline" className={`text-[9px] font-mono ${riskCls}`}>{riskLevel}</Badge>
                )}
                {momentum && (
                  <Badge variant="outline" className="text-[9px] font-mono text-blue-400 border-blue-500/30">
                    {momentum} momentum
                  </Badge>
                )}
              </div>
              {matchLabel && (
                <p className="text-[11px] font-mono text-muted-foreground mt-0.5 truncate">{matchLabel}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {report.confidence != null && (
              <span className={`text-[10px] font-mono ${cfg.color}`}>{(report.confidence * 100).toFixed(0)}%</span>
            )}
            <span className="text-[10px] font-mono text-muted-foreground/60 flex items-center gap-1">
              <Clock className="w-2.5 h-2.5" />{timeAgo(report.created_at)}
            </span>
          </div>
        </div>

        {/* Content */}
        <p className={`text-sm leading-relaxed ${expanded ? "" : "line-clamp-3"}`}>
          {report.content}
        </p>

        {/* Key Factors */}
        {keyFactors.length > 0 && expanded && (
          <div className="space-y-1">
            <p className="text-[10px] font-mono text-muted-foreground uppercase">Key Factors</p>
            {keyFactors.map((f, i) => (
              <div key={i} className={`flex gap-2 text-xs p-1.5 rounded bg-background/40 border-l-2 ${cfg.color.replace("text-", "border-")}`}>
                <TrendingUp className={`w-3 h-3 shrink-0 mt-0.5 ${cfg.color}`} />
                {f}
              </div>
            ))}
          </div>
        )}

        {/* Value Pick / In-Play Bet */}
        {(valuePick || inPlayBet) && expanded && (
          <div className={`p-2.5 rounded-lg border-l-2 ${cfg.color.replace("text-", "border-")} bg-background/30`}>
            <p className="text-[10px] font-mono uppercase text-muted-foreground mb-1">
              {inPlayBet ? "In-Play Opportunity" : "Value Pick"}
            </p>
            <p className="text-sm font-semibold">{inPlayBet || valuePick}</p>
          </div>
        )}

        {/* Analytics stats */}
        {isAnalytics && teamStats && expanded && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 pt-1">
            {[
              ["Active Users", teamStats.active_users],
              ["New Subs", teamStats.new_subscriptions],
              ["Predictions", teamStats.predictions],
              ["Accuracy", teamStats.accuracy_rate != null ? `${(teamStats.accuracy_rate * 100).toFixed(1)}%` : "N/A"],
              ["Avg Edge", teamStats.avg_edge != null ? `${(teamStats.avg_edge * 100).toFixed(2)}%` : "N/A"],
              ["Pending WD", teamStats.pending_withdrawals],
            ].map(([label, val]) => val !== undefined && (
              <div key={label as string} className="bg-background/40 rounded p-2 text-center">
                <div className={`text-sm font-bold ${cfg.color}`}>{val}</div>
                <div className="text-[10px] text-muted-foreground font-mono">{label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(x => !x)}
          className={`flex items-center gap-1 text-[10px] font-mono ${cfg.color} hover:opacity-80 transition-opacity`}
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? "Collapse" : "Expand report"}
        </button>
      </CardContent>
    </Card>
  );
}

// ─── Filter Tabs ──────────────────────────────────────────────────────────────

const FILTERS = [
  { id: "all",          label: "All" },
  { id: "match-scout",  label: "Scouts" },
  { id: "news-sentinel",label: "Injuries" },
  { id: "live-match-tracker", label: "Live" },
  { id: "analytics-reporter", label: "Analytics" },
  { id: "odds-anomaly", label: "Odds" },
];

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const qc = useQueryClient();
  const [agentFilter, setAgentFilter] = useState("all");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshCountdown, setRefreshCountdown] = useState(30);
  const [wsGoals, setWsGoals] = useState<LiveScore[]>([]);
  const [generateMsg, setGenerateMsg] = useState<string | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const generateMutation = useMutation({
    mutationFn: () => apiPost<{ triggered: string[]; message: string }>("/agents/generate-now"),
    onSuccess: (data) => {
      setGenerateMsg(data.message);
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["agent-reports"] });
        setGenerateMsg(null);
      }, 8000);
    },
    onError: () => setGenerateMsg("Failed to trigger agents — check server logs"),
  });

  const reportsQ = useQuery<ReportsData>({
    queryKey: ["agent-reports", agentFilter],
    queryFn: () => apiGet<ReportsData>(
      `/agents/reports?limit=60${agentFilter !== "all" ? `&agent=${agentFilter}` : ""}`
    ),
    refetchInterval: autoRefresh ? 30_000 : false,
    staleTime: 15_000,
  });

  const liveQ = useQuery<LiveData>({
    queryKey: ["live-scores"],
    queryFn: () => apiGet<LiveData>("/agents/live-scores"),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });

  // Countdown ticker
  useEffect(() => {
    if (!autoRefresh) { setRefreshCountdown(30); return; }
    setRefreshCountdown(30);
    countdownRef.current = setInterval(() => {
      setRefreshCountdown(c => {
        if (c <= 1) { qc.invalidateQueries({ queryKey: ["agent-reports"] }); return 30; }
        return c - 1;
      });
    }, 1000);
    return () => { if (countdownRef.current) clearInterval(countdownRef.current); };
  }, [autoRefresh, qc]);

  // WebSocket — listen for live score + ai_signal events
  useEffect(() => {
    const off = vitWS.on("notification", (raw: any) => {
      const msg = raw ?? {};
      const evType = msg.event_type ?? msg.type;
      if (evType === "live_score_update" || evType === "goal_scored") {
        const p = msg.payload ?? msg;
        setWsGoals(prev => {
          const filtered = prev.filter(m => m.id !== p.match_id);
          return [{
            id: p.match_id, home_team: p.home_team, away_team: p.away_team,
            league: p.league, home_score: p.home_score, away_score: p.away_score,
            status: "live", kickoff: null,
          }, ...filtered].slice(0, 10);
        });
      }
      if (evType === "ai_signal") {
        qc.invalidateQueries({ queryKey: ["agent-reports"] });
      }
    });
    return off;
  }, [qc]);

  const reports = reportsQ.data?.reports ?? [];
  const liveScores = liveQ.data?.matches ?? [];
  const liveCount = liveQ.data?.live_count ?? wsGoals.length;

  // Summary stats
  const typeBreakdown = reports.reduce<Record<string, number>>((acc, r) => {
    const key = r.agent_name;
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-5 pb-24">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-mono font-bold uppercase tracking-tight flex items-center gap-2">
            <Activity className="w-6 h-6 text-primary" />
            Intelligence Reports
          </h1>
          <p className="text-sm font-mono text-muted-foreground mt-1">
            Real-time AI agent outputs · auto-refreshes every 30s
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <span className="text-[10px] font-mono text-muted-foreground">
            {autoRefresh ? `Refresh in ${refreshCountdown}s` : "Paused"}
          </span>
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs h-7 px-2.5 border-primary/40 text-primary hover:bg-primary/10"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
          >
            <Play className={`w-3 h-3 mr-1 ${generateMutation.isPending ? "animate-pulse" : ""}`} />
            {generateMutation.isPending ? "Running…" : "Generate Now"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs h-7 px-2.5"
            onClick={() => setAutoRefresh(x => !x)}
          >
            <RefreshCw className={`w-3 h-3 mr-1 ${reportsQ.isFetching ? "animate-spin" : ""}`} />
            {autoRefresh ? "Pause" : "Resume"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs h-7 px-2.5"
            onClick={() => qc.invalidateQueries({ queryKey: ["agent-reports", "live-scores"] })}
            disabled={reportsQ.isFetching}
          >
            <RefreshCw className={`w-3 h-3 ${reportsQ.isFetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Live Score Ticker */}
      <LiveScoresTicker scores={liveScores} wsGoals={wsGoals} />

      {/* Summary Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total Reports",  value: reportsQ.data?.count ?? 0,  icon: Brain,    color: "text-primary" },
          { label: "Live Now",       value: liveCount,                   icon: Radio,    color: "text-green-400" },
          { label: "Scouts Today",   value: typeBreakdown["match-scout"] ?? 0, icon: Target, color: "text-cyan-400" },
          { label: "Injury Alerts",  value: typeBreakdown["news-sentinel"] ?? 0, icon: AlertTriangle, color: "text-amber-400" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="bg-card/40 border-border/50">
            <CardContent className="p-4 flex items-center gap-3">
              <Icon className={`w-5 h-5 ${color} shrink-0`} />
              <div>
                <p className={`text-xl font-bold ${color}`}>{value}</p>
                <p className="text-[10px] font-mono text-muted-foreground">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Agent category strip */}
      <div className="flex gap-1.5 flex-wrap">
        {FILTERS.map(f => {
          const cfg = f.id !== "all" ? (AGENT_CONFIG[f.id] ?? DEFAULT_CONFIG) : null;
          const isActive = agentFilter === f.id;
          const count = f.id === "all" ? reports.length : (typeBreakdown[f.id] ?? 0);
          return (
            <button
              key={f.id}
              onClick={() => setAgentFilter(f.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
                isActive
                  ? "border-primary/60 bg-primary/10 text-primary"
                  : "border-border/40 bg-card/30 text-muted-foreground hover:border-border"
              }`}
            >
              {cfg && <cfg.icon className={`w-3 h-3 ${isActive ? "text-primary" : cfg.color}`} />}
              {f.label}
              {count > 0 && (
                <span className={`text-[9px] px-1 rounded-full border ${isActive ? "border-primary/40 bg-primary/10" : "border-border/40 bg-muted/30"}`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Generate feedback banner */}
      {generateMsg && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-primary/10 border border-primary/30 rounded-xl">
          <Zap className="w-4 h-4 text-primary shrink-0" />
          <p className="text-xs font-mono text-primary">{generateMsg}</p>
        </div>
      )}

      {/* Reports Feed */}
      {reportsQ.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <Card className="border-border/40">
          <CardContent className="py-16 flex flex-col items-center gap-4 text-center">
            <Brain className="w-10 h-10 text-muted-foreground/30" />
            <p className="font-mono text-sm text-muted-foreground uppercase">No reports yet</p>
            <p className="font-mono text-[11px] text-muted-foreground/60">
              {agentFilter !== "all"
                ? `No "${agentFilter}" reports found — try "All" or generate a fresh batch`
                : "Agents generate reports automatically — or tap below to run them now"}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="font-mono text-xs border-primary/40 text-primary hover:bg-primary/10"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              <Play className={`w-3 h-3 mr-1.5 ${generateMutation.isPending ? "animate-pulse" : ""}`} />
              {generateMutation.isPending ? "Running agents…" : "Generate Reports Now"}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {reports.map(r => <ReportCard key={r.id} report={r} />)}
        </div>
      )}
    </div>
  );
}
