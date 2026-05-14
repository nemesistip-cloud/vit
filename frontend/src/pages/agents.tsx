import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Redirect } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Activity, RefreshCw, Play, ChevronDown, ChevronUp,
  ShieldCheck, Brain, Cpu, DollarSign, BarChart3,
  Database, Zap, Eye, Settings, Clock, CheckCircle2,
  XCircle, AlertTriangle, Loader2, Wifi, WifiOff,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentSnapshot {
  name: string;
  enabled: boolean;
  status: "idle" | "running" | "ok" | "error" | "disabled";
  run_count: number;
  error_count: number;
  last_run_at: string | null;
  next_run_at: string | null;
  last_error: string | null;
  last_result: Record<string, unknown> | null;
  interval_seconds: number;
}

interface CoordinatorStatus {
  coordinator: {
    started_at: string;
    agent_count: number;
    running_tasks: number;
  };
  agents: Record<string, AgentSnapshot>;
}

// ── Agent metadata ────────────────────────────────────────────────────────────

const AGENT_META: Record<string, { label: string; category: string; icon: React.ReactNode; description: string }> = {
  "performance-monitor":   { label: "Performance Monitor",    category: "ML",           icon: <Activity className="w-4 h-4" />,    description: "Tracks model accuracy across live results" },
  "weight-optimizer":      { label: "Weight Optimizer",       category: "ML",           icon: <Brain className="w-4 h-4" />,       description: "Auto-tunes ensemble model weights" },
  "retrain-trigger":       { label: "Retrain Trigger",        category: "ML",           icon: <RefreshCw className="w-4 h-4" />,   description: "Kicks off retraining when accuracy dips" },
  "model-promoter":        { label: "Model Auto-Promoter",    category: "ML",           icon: <Zap className="w-4 h-4" />,         description: "Promotes new model versions on stat significance" },
  "match-scout":           { label: "Match Scout",            category: "Intelligence", icon: <Eye className="w-4 h-4" />,         description: "Generates pre-match intelligence briefs" },
  "news-sentinel":         { label: "News Sentinel",          category: "Intelligence", icon: <Wifi className="w-4 h-4" />,        description: "Monitors team news and injury feeds" },
  "odds-anomaly":          { label: "Odds Anomaly Detector",  category: "Intelligence", icon: <AlertTriangle className="w-4 h-4" />, description: "Flags unusual market movements" },
  "fixture-gap":           { label: "Fixture Gap Filler",     category: "Data",         icon: <Database className="w-4 h-4" />,    description: "Auto-fills missing fixture data" },
  "kyc-screener":          { label: "KYC Auto-Screener",      category: "Compliance",   icon: <ShieldCheck className="w-4 h-4" />, description: "Vision AI screens identity submissions" },
  "fraud-review":          { label: "Fraud Reviewer",         category: "Compliance",   icon: <ShieldCheck className="w-4 h-4" />, description: "AI risk narrative + auto-resolve fraud flags" },
  "audit-sentinel":        { label: "Audit Sentinel",         category: "Compliance",   icon: <Eye className="w-4 h-4" />,         description: "Nightly audit log monitoring" },
  "prediction-moderator":  { label: "Prediction Moderator",   category: "Quality",      icon: <CheckCircle2 className="w-4 h-4" />, description: "AI quality-gates prediction submissions" },
  "withdrawal-gatekeeper": { label: "Withdrawal Gatekeeper",  category: "Finance",      icon: <DollarSign className="w-4 h-4" />,  description: "Rule cascade auto-approval for withdrawals" },
  "revenue-optimizer":     { label: "Revenue Optimizer",      category: "Finance",      icon: <DollarSign className="w-4 h-4" />,  description: "Daily revenue analysis and pricing recs" },
  "accumulator-publisher": { label: "Accumulator Publisher",  category: "Publishing",   icon: <Zap className="w-4 h-4" />,         description: "Auto-publishes best accumulators to Telegram" },
  "analytics-reporter":    { label: "Analytics Reporter",     category: "Reporting",    icon: <BarChart3 className="w-4 h-4" />,   description: "Weekly narrative analytics report" },
  "marketplace-audit":     { label: "Marketplace Auditor",    category: "Platform",     icon: <Settings className="w-4 h-4" />,    description: "Claude code audits marketplace listings" },
  "governance-executor":   { label: "Governance Executor",    category: "Platform",     icon: <Settings className="w-4 h-4" />,    description: "Auto-executes passed proposals after timelock" },
  "self-healing":          { label: "Self-Healing Monitor",   category: "Infrastructure", icon: <Cpu className="w-4 h-4" />,      description: "Watches agents + applies auto-fixes" },
};

const CATEGORY_COLORS: Record<string, string> = {
  "ML":             "bg-violet-500/20 text-violet-300 border-violet-500/30",
  "Intelligence":   "bg-blue-500/20 text-blue-300 border-blue-500/30",
  "Data":           "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  "Compliance":     "bg-orange-500/20 text-orange-300 border-orange-500/30",
  "Finance":        "bg-green-500/20 text-green-300 border-green-500/30",
  "Quality":        "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  "Publishing":     "bg-pink-500/20 text-pink-300 border-pink-500/30",
  "Reporting":      "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
  "Platform":       "bg-teal-500/20 text-teal-300 border-teal-500/30",
  "Infrastructure": "bg-red-500/20 text-red-300 border-red-500/30",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(iso: string | null): string {
  if (!iso) return "never";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

function nextRunIn(iso: string | null): string {
  if (!iso) return "—";
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  if (diff <= 0) return "now";
  if (diff < 60) return `${Math.round(diff)}s`;
  if (diff < 3600) return `${Math.round(diff / 60)}m`;
  return `${Math.round(diff / 3600)}h`;
}

function intervalLabel(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${s / 60}m`;
  if (s < 86400) return `${s / 3600}h`;
  return `${s / 86400}d`;
}

// ── Status indicator ──────────────────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  const classes: Record<string, string> = {
    running:  "bg-blue-400 animate-pulse",
    ok:       "bg-green-400",
    error:    "bg-red-400",
    idle:     "bg-muted/50",
    disabled: "bg-muted/40",
  };
  return (
    <span className={cn("inline-block w-2 h-2 rounded-full", classes[status] ?? "bg-muted/50")} />
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    running:  { label: "Running",  className: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
    ok:       { label: "OK",       className: "bg-green-500/20 text-green-300 border-green-500/30" },
    error:    { label: "Error",    className: "bg-red-500/20 text-red-300 border-red-500/30" },
    idle:     { label: "Idle",     className: "bg-muted/50/20 text-foreground/80 border-border/40" },
    disabled: { label: "Disabled", className: "bg-muted/40/20 text-muted-foreground border-border/30" },
  };
  const c = config[status] ?? config.idle;
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", c.className)}>
      {c.label}
    </span>
  );
}

// ── Agent Card ────────────────────────────────────────────────────────────────

function AgentCard({ name, snap, onTrigger, triggering }: {
  name: string;
  snap: AgentSnapshot;
  onTrigger: (name: string) => void;
  triggering: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = AGENT_META[name] ?? {
    label: name, category: "Other", icon: <Settings className="w-4 h-4" />, description: "",
  };
  const catColor = CATEGORY_COLORS[meta.category] ?? "bg-muted/50/20 text-foreground/80 border-border/40";
  const hasResult = snap.last_result && Object.keys(snap.last_result).length > 0;

  return (
    <Card className="bg-card/60 border-border/50 hover:border-border/70 transition-colors">
      <CardHeader className="pb-2 pt-4 px-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <StatusDot status={snap.status} />
            <span className="text-sm font-semibold text-foreground truncate">{meta.label}</span>
          </div>
          <StatusBadge status={snap.status} />
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className={cn("text-xs px-1.5 py-0.5 rounded border", catColor)}>
            {meta.category}
          </span>
          <span className="text-xs text-muted-foreground">every {intervalLabel(snap.interval_seconds)}</span>
        </div>
        {meta.description && (
          <p className="text-xs text-muted-foreground mt-1 leading-snug">{meta.description}</p>
        )}
      </CardHeader>

      <CardContent className="px-4 pb-4 space-y-3">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-muted/20/50 rounded-lg p-2">
            <div className="text-sm font-bold text-foreground">{snap.run_count}</div>
            <div className="text-xs text-muted-foreground">Runs</div>
          </div>
          <div className="bg-muted/20/50 rounded-lg p-2">
            <div className={cn("text-sm font-bold", snap.error_count > 0 ? "text-red-400" : "text-foreground")}>
              {snap.error_count}
            </div>
            <div className="text-xs text-muted-foreground">Errors</div>
          </div>
          <div className="bg-muted/20/50 rounded-lg p-2">
            <div className="text-sm font-bold text-cyan-400">{nextRunIn(snap.next_run_at)}</div>
            <div className="text-xs text-muted-foreground">Next run</div>
          </div>
        </div>

        {/* Timing */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Last: {relativeTime(snap.last_run_at)}
          </span>
        </div>

        {/* Last error */}
        {snap.last_error && (
          <div className="bg-red-950/40 border border-red-800/30 rounded-lg px-3 py-2">
            <p className="text-xs text-red-400 font-medium mb-0.5">Last error</p>
            <p className="text-xs text-red-300 break-all line-clamp-2">{snap.last_error}</p>
          </div>
        )}

        {/* Last result (expandable) */}
        {hasResult && (
          <div>
            <button
              onClick={() => setExpanded(v => !v)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground/90 transition-colors"
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              Last result
            </button>
            {expanded && (
              <pre className="mt-2 text-xs bg-background/60 border border-border/40 rounded-lg p-2 overflow-auto max-h-40 text-foreground/80 leading-snug">
                {JSON.stringify(snap.last_result, null, 2)}
              </pre>
            )}
          </div>
        )}

        {/* Trigger button */}
        <Button
          size="sm"
          variant="outline"
          onClick={() => onTrigger(name)}
          disabled={triggering || snap.status === "disabled"}
          className="w-full border-border text-foreground/80 hover:bg-muted/40 hover:text-foreground text-xs h-8"
        >
          {triggering ? (
            <><Loader2 className="w-3 h-3 mr-1.5 animate-spin" />Triggering…</>
          ) : (
            <><Play className="w-3 h-3 mr-1.5" />Run Now</>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

// ── AI Provider Status Bar ────────────────────────────────────────────────────

function ProviderStatusBar() {
  const keys = [
    { name: "Gemini",    env: "GEMINI_API_KEY",  color: "text-blue-400" },
    { name: "Claude",    env: "CLAUDE_API_KEY",  color: "text-orange-400" },
    { name: "OpenAI",    env: "OPENAI_API_KEY",  color: "text-green-400" },
    { name: "xAI/Grok", env: "XAI_API_KEY",     color: "text-purple-400" },
  ];

  const { data } = useQuery({
    queryKey: ["ai-provider-status"],
    queryFn: () => apiGet<{ providers: Record<string, { configured: boolean; available: boolean; cooling: boolean; cooling_for_seconds: number; failing: boolean; last_error_code: number | null }>; priority: string[] }>("/api/agents/providers"),
    refetchInterval: 15000,
    retry: false,
  });

  return (
    <Card className="bg-card/60 border-border/50">
      <CardContent className="px-4 py-3">
        <div className="flex items-center gap-1 mb-2">
          <Brain className="w-4 h-4 text-muted-foreground" />
          <span className="text-xs font-semibold text-foreground/80 uppercase tracking-wide">AI Providers</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {keys.map(({ name, color }) => {
            const providers = data?.providers ?? {};
            const info = providers[name.toLowerCase().replace("/", "")] ??
                         providers[name.split("/")[0].toLowerCase()] ??
                         null;
            const available = info?.available ?? false;
            const cooling = info?.cooling ?? false;
            const configured = info?.configured ?? false;
            const failing = info?.failing ?? false;
            const errCode = info?.last_error_code ?? null;
            const statusLabel = !configured
              ? "no key"
              : failing
              ? `failing${errCode ? ` (${errCode})` : ""}`
              : cooling
              ? `cooling ${info?.cooling_for_seconds}s`
              : "ready";
            return (
              <div key={name} className="flex items-center gap-2 bg-muted/20/50 rounded-lg px-2 py-1.5">
                {available ? (
                  <Wifi className={cn("w-3 h-3", color)} />
                ) : (
                  <WifiOff className={cn("w-3 h-3", failing ? "text-red-500" : "text-muted-foreground/60")} />
                )}
                <div className="min-w-0">
                  <div className={cn("text-xs font-medium truncate", available ? color : failing ? "text-red-400" : "text-muted-foreground")}>
                    {name}
                  </div>
                  <div className={cn("text-xs", failing ? "text-red-500/70" : "text-muted-foreground/60")}>
                    {statusLabel}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const CATEGORIES = ["All", "ML", "Intelligence", "Data", "Compliance", "Finance", "Quality", "Publishing", "Reporting", "Platform", "Infrastructure"];

export default function AgentsPage() {
  const { isAdmin } = useAuth();
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown, setCountdown] = useState(10);
  const [triggeringAgent, setTriggeringAgent] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");
  const countdownRef = useRef(countdown);
  countdownRef.current = countdown;

  if (!isAdmin) return <Redirect to="/dashboard" />;

  const { data, isLoading, isError, refetch, dataUpdatedAt } = useQuery({
    queryKey: ["agents-status"],
    queryFn: () => apiGet<CoordinatorStatus>("/api/agents/status"),
    refetchInterval: autoRefresh ? 10000 : false,
    staleTime: 5000,
  });

  // Countdown timer
  useEffect(() => {
    if (!autoRefresh) return;
    setCountdown(10);
    const tick = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) return 10;
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(tick);
  }, [autoRefresh, dataUpdatedAt]);

  const triggerMutation = useMutation({
    mutationFn: (name: string) => apiPost(`/api/agents/trigger/${name}`),
    onSuccess: (_, name) => {
      toast.success(`Agent "${name}" triggered`);
      setTriggeringAgent(null);
      setTimeout(refetch, 1500);
    },
    onError: (_, name) => {
      toast.error(`Failed to trigger "${name}"`);
      setTriggeringAgent(null);
    },
  });

  const handleTrigger = (name: string) => {
    setTriggeringAgent(name);
    triggerMutation.mutate(name);
  };

  const coordinator = data?.coordinator;
  const agents = data?.agents ?? {};
  const agentEntries = Object.entries(agents);

  const filteredAgents = agentEntries.filter(([name, snap]) => {
    const meta = AGENT_META[name];
    const categoryMatch = filterCategory === "All" || meta?.category === filterCategory;
    const statusMatch = filterStatus === "All" || snap.status === filterStatus;
    return categoryMatch && statusMatch;
  });

  const statusCounts = {
    ok:      agentEntries.filter(([, s]) => s.status === "ok").length,
    running: agentEntries.filter(([, s]) => s.status === "running").length,
    error:   agentEntries.filter(([, s]) => s.status === "error").length,
    idle:    agentEntries.filter(([, s]) => s.status === "idle").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-6 h-6 text-cyan-400" />
            <h1 className="text-2xl font-bold text-foreground">Agent Control Room</h1>
          </div>
          <p className="text-muted-foreground text-sm mt-0.5">
            {coordinator ? (
              <>
                {coordinator.agent_count} agents · {coordinator.running_tasks} running ·
                started {relativeTime(coordinator.started_at)}
              </>
            ) : "Loading…"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(v => !v)}
            className={cn(
              "border-border text-foreground/80 text-xs h-8",
              autoRefresh && "border-cyan-700 text-cyan-300"
            )}
          >
            <RefreshCw className={cn("w-3 h-3 mr-1.5", autoRefresh && "animate-spin")} />
            {autoRefresh ? `Auto (${countdown}s)` : "Auto-refresh off"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="border-border text-foreground/80 text-xs h-8"
          >
            <RefreshCw className="w-3 h-3 mr-1.5" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Healthy",  value: statusCounts.ok,      color: "text-green-400",  bg: "bg-green-500/10 border-green-500/20" },
          { label: "Running",  value: statusCounts.running,  color: "text-blue-400",   bg: "bg-blue-500/10 border-blue-500/20" },
          { label: "Error",    value: statusCounts.error,    color: "text-red-400",    bg: "bg-red-500/10 border-red-500/20" },
          { label: "Idle",     value: statusCounts.idle,     color: "text-muted-foreground",  bg: "bg-muted/20/50 border-border/50" },
        ].map(({ label, value, color, bg }) => (
          <Card key={label} className={cn("border", bg)}>
            <CardContent className="p-4 text-center">
              <div className={cn("text-2xl font-bold", color)}>{value}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* AI Provider status */}
      <ProviderStatusBar />

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-xs text-muted-foreground mr-1">Category:</span>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={cn(
                "text-xs px-2 py-1 rounded-full border transition-colors",
                filterCategory === cat
                  ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                  : "border-border text-muted-foreground hover:border-border"
              )}
            >
              {cat}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-muted-foreground mr-1">Status:</span>
          {["All", "ok", "running", "error", "idle"].map(s => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={cn(
                "text-xs px-2 py-1 rounded-full border transition-colors",
                filterStatus === s
                  ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                  : "border-border text-muted-foreground hover:border-border"
              )}
            >
              {s === "All" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Agent grid */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i} className="bg-card/60 border-border/50 h-64 animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <Card className="bg-red-950/30 border-red-800/30">
          <CardContent className="p-6 text-center">
            <XCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
            <p className="text-red-300">Failed to load agent status</p>
            <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-3 border-red-700 text-red-300">
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {!isLoading && !isError && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredAgents.map(([name, snap]) => (
              <AgentCard
                key={name}
                name={name}
                snap={snap}
                onTrigger={handleTrigger}
                triggering={triggeringAgent === name}
              />
            ))}
          </div>

          {filteredAgents.length === 0 && (
            <div className="text-center py-16 text-muted-foreground">
              No agents match the current filters
            </div>
          )}

          <p className="text-xs text-muted-foreground/60 text-center">
            {agentEntries.length} total agents · showing {filteredAgents.length} ·
            last updated {new Date(dataUpdatedAt).toLocaleTimeString()}
          </p>
        </>
      )}
    </div>
  );
}
