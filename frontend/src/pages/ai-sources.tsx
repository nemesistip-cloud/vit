import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Redirect } from "wouter";
import {
  analyzeMatchWithPuter,
  isPuterAvailable,
  isPuterSignedIn,
  puterSignIn,
  puterSignOut,
  getPuterUser,
  waitForPuter,
  MatchAnalysis,
  PuterModel,
  PUTER_CLAUDE_MODEL,
  PUTER_GROK_MODEL,
  PUTER_LLAMA_MODEL,
  PUTER_MISTRAL_MODEL,
  PUTER_DEEPSEEK_MODEL,
} from "@/lib/puter-ai";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Brain,
  Play,
  Square,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Loader2,
  Upload,
  Trash2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Zap,
  Bot,
  BarChart3,
  AlertTriangle,
  Lock,
  LogIn,
  LogOut,
  User,
  Settings,
} from "lucide-react";

import { EnsembleLeaderboard } from "@/components/EnsembleLeaderboard";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AISourceMatch {
  id: number;
  home_team: string;
  away_team: string;
  league: string | null;
  match_date: string | null;
  status: string;
  sources: string[];
}

interface AISourcePred {
  id: number;
  source: string;
  home_prob: number;
  draw_prob: number;
  away_prob: number;
  confidence: number;
  reason: string | null;
  raw_content: string | null;
  submitted_by: number | null;
  is_certified: boolean;
  was_correct: boolean | null;
  timestamp: string | null;
}

type SlotStatus = "pending" | "running" | "ingesting" | "done" | "failed" | "skipped";

interface SlotResult {
  status: SlotStatus;
  analysis: MatchAnalysis | null;
  error?: string;
}

type MatchResults = Partial<Record<PuterModel, SlotResult>>;

const MODELS: { id: PuterModel; label: string; model: string; color: string }[] = [
  { id: "claude",   label: "Claude 3.5",    model: PUTER_CLAUDE_MODEL,   color: "text-purple-400" },
  { id: "grok",     label: "Grok",          model: PUTER_GROK_MODEL,     color: "text-cyan-400"   },
  { id: "llama",    label: "Llama 3.1 70B", model: PUTER_LLAMA_MODEL,    color: "text-orange-400" },
  { id: "mistral",  label: "Mistral Large", model: PUTER_MISTRAL_MODEL,  color: "text-blue-400"   },
  { id: "deepseek", label: "DeepSeek",      model: PUTER_DEEPSEEK_MODEL, color: "text-green-400"  },
];

// Delay between Puter calls — raised to 3.5s to stay within free tier limits
const DELAY_MS = 3500;

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

// ─── Puter Account Panel ──────────────────────────────────────────────────────

function PuterAccountPanel() {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const ready = isPuterAvailable() || await waitForPuter(5000);
    if (!ready) { setSignedIn(false); return; }
    const ok = await isPuterSignedIn();
    setSignedIn(ok);
    if (ok) {
      const user = await getPuterUser();
      setUsername(user?.username ?? null);
    } else {
      setUsername(null);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleSignIn = async () => {
    setBusy(true);
    try {
      await puterSignIn();
      await refresh();
      toast.success("Signed in to Puter");
    } catch (e: any) {
      toast.error(e?.message || "Puter sign-in failed");
    } finally { setBusy(false); }
  };

  const handleSwitchAccount = async () => {
    setBusy(true);
    try {
      await puterSignOut();
      await refresh();
      toast.info("Signed out — sign in with a different account to reset rate limits");
    } catch (e: any) {
      toast.error(e?.message || "Failed to switch account");
    } finally { setBusy(false); }
  };

  if (!isPuterAvailable()) return null;

  return (
    <div className="flex items-center gap-2 flex-wrap bg-card/60 border border-border rounded-lg px-3 py-2">
      <User className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      {signedIn === null ? (
        <span className="text-xs text-muted-foreground">Checking Puter…</span>
      ) : signedIn && username ? (
        <>
          <span className="text-xs text-foreground/80">
            Puter: <span className="text-cyan-400 font-mono">{username}</span>
          </span>
          <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px]">signed in</Badge>
          <button
            onClick={handleSwitchAccount}
            disabled={busy}
            className="text-[11px] text-muted-foreground hover:text-amber-400 flex items-center gap-1 ml-auto transition-colors"
          >
            <LogOut className="w-3 h-3" />
            Switch account
          </button>
        </>
      ) : (
        <>
          <span className="text-xs text-muted-foreground">Not signed in to Puter</span>
          <button
            onClick={handleSignIn}
            disabled={busy}
            className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 ml-auto transition-colors"
          >
            <LogIn className="w-3 h-3" />
            Sign in
          </button>
        </>
      )}
      {busy && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground shrink-0" />}
    </div>
  );
}

function fmtPct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function fmtDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

function SlotBadge({ status }: { status: SlotStatus }) {
  const cfg: Record<SlotStatus, { label: string; cls: string; icon: React.ReactNode }> = {
    pending:   { label: "Pending",   cls: "bg-muted/40 text-foreground/80",            icon: null },
    running:   { label: "Querying…", cls: "bg-blue-500/20 text-blue-300 border border-blue-500/40",  icon: <Loader2 className="w-3 h-3 animate-spin mr-1" /> },
    ingesting: { label: "Saving…",   cls: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40", icon: <Loader2 className="w-3 h-3 animate-spin mr-1" /> },
    done:      { label: "Done",      cls: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30", icon: <CheckCircle2 className="w-3 h-3 mr-1" /> },
    failed:    { label: "Failed",    cls: "bg-rose-500/20 text-rose-300 border border-rose-500/30",   icon: <XCircle className="w-3 h-3 mr-1" /> },
    skipped:   { label: "Skipped",   cls: "bg-muted/30 text-muted-foreground",         icon: null },
  };
  const c = cfg[status];
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${c.cls}`}>
      {c.icon}{c.label}
    </span>
  );
}

// ─── Probability Bar ──────────────────────────────────────────────────────────

function ProbBar({ home, draw, away }: { home: number; draw: number; away: number }) {
  return (
    <div className="flex rounded overflow-hidden h-2 w-full mt-1">
      <div className="bg-emerald-500" style={{ width: `${home * 100}%` }} title={`Home ${fmtPct(home)}`} />
      <div className="bg-muted/40"   style={{ width: `${draw * 100}%` }} title={`Draw ${fmtPct(draw)}`} />
      <div className="bg-rose-500"   style={{ width: `${away * 100}%` }} title={`Away ${fmtPct(away)}`} />
    </div>
  );
}

// ─── Match Card ───────────────────────────────────────────────────────────────

function MatchCard({
  match,
  results,
  activeModels,
}: {
  match: AISourceMatch;
  results: MatchResults;
  activeModels: PuterModel[];
}) {
  const [expanded, setExpanded] = useState(false);
  const anyRunning = activeModels.some(
    (m) => results[m]?.status === "running" || results[m]?.status === "ingesting"
  );
  const anyDone = activeModels.some((m) => results[m]?.status === "done");
  const allFailed = activeModels.every(
    (m) => results[m]?.status === "failed" || results[m]?.status === "skipped"
  );

  const borderCls = anyRunning
    ? "border-blue-500/50 shadow-blue-500/10 shadow-md"
    : anyDone
    ? "border-emerald-500/30"
    : allFailed
    ? "border-rose-500/30"
    : "border-border";

  return (
    <Card className={`bg-card border ${borderCls} transition-all duration-300`}>
      <CardContent className="p-3 space-y-2">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-foreground truncate">
              {match.home_team} <span className="text-muted-foreground">vs</span> {match.away_team}
            </div>
            <div className="text-xs text-muted-foreground flex flex-wrap gap-1 mt-0.5">
              {match.league && <span>{match.league}</span>}
              {match.match_date && <span>· {fmtDate(match.match_date)}</span>}
            </div>
          </div>
          {anyRunning && (
            <Cpu className="w-4 h-4 text-blue-400 animate-pulse shrink-0 mt-0.5" />
          )}
        </div>

        {/* Per-model status row */}
        <div className="flex flex-wrap gap-2">
          {activeModels.map((m) => {
            const slot = results[m];
            const model = MODELS.find((x) => x.id === m);
            if (!model) return null;
            return (
              <div key={m} className="flex items-center gap-1.5">
                <span className={`text-xs font-medium ${model.color}`}>{model.label}</span>
                <SlotBadge status={slot?.status ?? "pending"} />
              </div>
            );
          })}
          {(match.sources?.length ?? 0) > 0 && (
            <div className="flex gap-1 flex-wrap">
              {match.sources.map((s) => (
                <Badge
                  key={s}
                  className="bg-muted/40 text-muted-foreground text-[10px] px-1.5 py-0 border-0 capitalize"
                >
                  {s} ✓
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Results display */}
        {anyDone && (
          <div className="space-y-2 pt-1">
            {activeModels.map((m) => {
              const slot = results[m];
              if (slot?.status !== "done" || !slot.analysis) return null;
              const a = slot.analysis;
              const model = MODELS.find((x) => x.id === m);
              if (!model) return null;
              return (
                <div key={m} className="bg-muted/20 rounded p-2 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold ${model.color}`}>{model.label}</span>
                    <span className="text-xs text-muted-foreground">
                      conf {fmtPct(a.confidence)}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-1 text-xs text-center">
                    <div>
                      <div className="text-muted-foreground">Home</div>
                      <div className="text-emerald-400 font-bold">{fmtPct(a.home_prob)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Draw</div>
                      <div className="text-foreground/80 font-bold">{fmtPct(a.draw_prob)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Away</div>
                      <div className="text-rose-400 font-bold">{fmtPct(a.away_prob)}</div>
                    </div>
                  </div>
                  <ProbBar home={a.home_prob} draw={a.draw_prob} away={a.away_prob} />
                  {a.reason && (
                    <p className="text-[11px] text-muted-foreground italic">{a.reason}</p>
                  )}
                  {(a.key_factors?.length ?? 0) > 0 && (
                    <button
                      className="text-[10px] text-cyan-500 hover:text-cyan-400 flex items-center gap-0.5"
                      onClick={() => setExpanded((x) => !x)}
                    >
                      {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      {expanded ? "Less" : `${a.key_factors.length} key factors`}
                    </button>
                  )}
                  {expanded && (
                    <ul className="text-[11px] text-muted-foreground space-y-0.5 pl-2">
                      {(a.key_factors ?? []).map((f, i) => (
                        <li key={i} className="flex gap-1">
                          <span className="text-cyan-500">•</span> {f}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Errors */}
        {activeModels.map((m) => {
          const slot = results[m];
          if (slot?.status !== "failed") return null;
          return (
            <p key={m} className="text-[11px] text-rose-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 shrink-0" />
              {MODELS.find((x) => x.id === m)?.label ?? m}: {slot.error || "Analysis failed"}
            </p>
          );
        })}
      </CardContent>
    </Card>
  );
}

// ─── AI Performance Stats Panel ──────────────────────────────────────────────

interface AIPerf {
  source: string;
  accuracy: number;
  calibration_score: number;
  sample_size: number;
  total_predictions: number;
  current_weight: number;
  certified: boolean;
  ingested_count: number;
}

function PerformanceStatsPanel() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["ai-sources", "performance"],
    queryFn: () =>
      apiGet<{
        performance: AIPerf[];
        total_ingested: number;
        source_counts: Record<string, number>;
        message?: string;
      }>("/api/admin/ai-sources/performance"),
    refetchInterval: 60000,
    retry: 1,
  });

  const [refreshing, setRefreshing] = useState(false);

  const triggerUpdate = async () => {
    setRefreshing(true);
    try {
      await apiPost("/api/admin/ai-sources/update-performance", {});
      qc.invalidateQueries({ queryKey: ["ai-sources", "performance"] });
      toast.success("Performance metrics recalculated");
    } catch (e: any) {
      toast.error(e?.message || "Update failed");
    } finally {
      setRefreshing(false);
    }
  };

  const data = q.data;
  const sourceCounts = data?.source_counts ?? {};
  const hasPerf = (data?.performance?.length ?? 0) > 0;

  return (
    <Card className="bg-muted/20 border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-foreground text-base">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            AI Source Performance
            {(data?.total_ingested ?? 0) > 0 && (
              <Badge className="bg-muted/40 text-foreground/80 border-0 text-[10px] ml-1">
                {data!.total_ingested} ingested
              </Badge>
            )}
          </CardTitle>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs text-muted-foreground hover:text-foreground border border-border"
            onClick={triggerUpdate}
            disabled={refreshing}
          >
            {refreshing ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <RefreshCw className="w-3 h-3 mr-1" />}
            Recalc
          </Button>
        </div>
        <CardDescription>
          Accuracy tracked after matches settle. Weights auto-adjust for ensemble scoring.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {q.isLoading ? (
          <Skeleton className="h-16 w-full bg-muted/40" />
        ) : q.isError ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/20 rounded p-2.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            Performance data unavailable — metrics are computed after matches settle.
            <button
              onClick={() => qc.invalidateQueries({ queryKey: ["ai-sources", "performance"] })}
              className="ml-auto text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" /> Retry
            </button>
          </div>
        ) : !hasPerf ? (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              {data?.message ?? "No performance data yet — metrics are computed after matches settle."}
            </p>
            {Object.keys(sourceCounts).length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1.5 font-medium">Ingested by source:</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(sourceCounts).map(([src, cnt]) => (
                    <Badge key={src} className="bg-muted/40 text-foreground/80 border-0 capitalize text-[10px]">
                      {src}: {cnt}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {data!.performance.map((p) => (
              <div key={p.source} className="bg-card/60 rounded p-2.5 text-xs">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 capitalize text-[10px]">
                      {p.source}
                    </Badge>
                    {p.certified && (
                      <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px]">
                        certified
                      </Badge>
                    )}
                  </div>
                  <span className="text-muted-foreground text-[10px]">{p.ingested_count} predictions</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-muted-foreground">Accuracy</div>
                    <div className={`font-bold ${p.accuracy >= 0.6 ? "text-emerald-400" : p.accuracy >= 0.45 ? "text-amber-400" : "text-rose-400"}`}>
                      {fmtPct(p.accuracy)}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Calibration</div>
                    <div className="text-foreground/80 font-bold">{fmtPct(p.calibration_score)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Weight</div>
                    <div className="text-cyan-400 font-bold">{p.current_weight.toFixed(2)}×</div>
                  </div>
                </div>
                {p.sample_size > 0 && (
                  <div className="mt-1 text-[10px] text-muted-foreground/60">
                    Based on {p.sample_size} settled match{p.sample_size !== 1 ? "es" : ""}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Server-Side Analysis Panel ───────────────────────────────────────────────

interface ServerResult {
  match_id: number;
  match: string;
  status: string;
  home_prob?: number;
  draw_prob?: number;
  away_prob?: number;
  confidence?: number;
  reason?: string;
  error?: string;
  method?: "ai_cascade" | "ml_ensemble";
}

function ServerAnalysisPanel({ matchCount }: { matchCount: number }) {
  const qc = useQueryClient();
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<ServerResult[] | null>(null);
  const [summary, setSummary] = useState<{
    ingested: number;
    skipped: number;
    mlFallback: number;
  } | null>(null);

  const run = async () => {
    setRunning(true);
    setResults(null);
    setSummary(null);
    try {
      const data = await apiPost<{
        status: string;
        processed: number;
        ingested: number;
        skipped: number;
        ml_fallback_used: number;
        results: ServerResult[];
      }>("/api/admin/ai-sources/run-server", { limit: Math.min(matchCount || 20, 50) });
      setResults(data.results ?? []);
      setSummary({
        ingested: data.ingested ?? 0,
        skipped: data.skipped ?? 0,
        mlFallback: data.ml_fallback_used ?? 0,
      });
      if ((data.ingested ?? 0) > 0) {
        const ml = data.ml_fallback_used ?? 0;
        const ai = (data.ingested ?? 0) - ml;
        const parts = [];
        if (ai > 0) parts.push(`${ai} via AI cascade`);
        if (ml > 0) parts.push(`${ml} via ML ensemble`);
        toast.success(`Analysis complete — ${data.ingested} ingested (${parts.join(", ")})`);
        qc.invalidateQueries({ queryKey: ["ai-sources"] });
      } else {
        toast.warning("Server analysis ran but no predictions could be generated");
      }
    } catch (e: any) {
      toast.error(e?.message || "Server analysis failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card className="bg-muted/20 border-border">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-foreground text-base">
          <Settings className="w-5 h-5 text-amber-400" />
          Server-Side Analysis
          <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] ml-1">
            no Puter needed
          </Badge>
        </CardTitle>
        <CardDescription>
          Uses the AI cascade (Gemini → Claude → OpenAI → Grok) first, then automatically
          falls back to the ML ensemble when AI providers are unavailable.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {summary && (
          <div className={`grid gap-3 text-center ${summary.mlFallback > 0 ? "grid-cols-3" : "grid-cols-2"}`}>
            <div className="bg-card/60 rounded p-2">
              <div className="text-xl font-bold text-emerald-400">{summary.ingested}</div>
              <div className="text-xs text-muted-foreground">Ingested</div>
            </div>
            {summary.mlFallback > 0 && (
              <div className="bg-blue-900/30 border border-blue-500/20 rounded p-2">
                <div className="text-xl font-bold text-blue-400">{summary.mlFallback}</div>
                <div className="text-xs text-muted-foreground">ML Ensemble</div>
              </div>
            )}
            <div className="bg-card/60 rounded p-2">
              <div className="text-xl font-bold text-amber-400">{summary.skipped}</div>
              <div className="text-xs text-muted-foreground">Skipped</div>
            </div>
          </div>
        )}

        <Button
          onClick={run}
          disabled={running}
          className="bg-amber-500 hover:bg-amber-600 text-black font-semibold w-full"
        >
          {running ? (
            <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Analysing…</>
          ) : (
            <><Cpu className="w-4 h-4 mr-2" />Run Server Analysis{matchCount > 0 && <span className="ml-2 text-xs opacity-70">{matchCount} matches</span>}</>
          )}
        </Button>

        {results && results.length > 0 && (
          <div className="space-y-1 max-h-64 overflow-y-auto pr-1">
            {results.map((r) => (
              <div key={r.match_id} className="flex items-start gap-2 text-xs py-1 border-b border-border/50 last:border-0">
                <span className={`shrink-0 font-medium ${r.status === "ingested" ? "text-emerald-400" : r.status === "skipped" ? "text-amber-400" : "text-rose-400"}`}>
                  {r.status === "ingested" ? "✓" : r.status === "skipped" ? "—" : "✗"}
                </span>
                <span className="text-foreground/80 flex-1 truncate">{r.match}</span>
                {r.status === "ingested" && r.method && (
                  <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded-full border font-mono ${
                    r.method === "ml_ensemble"
                      ? "text-blue-400 bg-blue-500/10 border-blue-500/30"
                      : "text-purple-400 bg-purple-500/10 border-purple-500/30"
                  }`}>
                    {r.method === "ml_ensemble" ? "ML" : "AI"}
                  </span>
                )}
                {r.status === "ingested" && r.home_prob != null && (
                  <span className="text-muted-foreground shrink-0 font-mono">
                    {fmtPct(r.home_prob)}/{fmtPct(r.draw_prob ?? 0)}/{fmtPct(r.away_prob ?? 0)}
                  </span>
                )}
                {r.error && (
                  <span className="text-rose-400 shrink-0 truncate max-w-[120px]">{r.error}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Manual Upload Form ───────────────────────────────────────────────────────

const ALLOWED_SOURCES = ["claude", "grok", "chatgpt", "gemini", "deepseek", "perplexity", "mistral", "manual", "server"];

function ManualUploadForm({ matches }: { matches: AISourceMatch[] }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);
  const [form, setForm] = useState({
    source: "claude",
    home_prob: "0.40",
    draw_prob: "0.28",
    away_prob: "0.32",
    confidence: "0.70",
    reason: "",
    raw_content: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!selectedMatchId) { toast.error("Pick a match first"); return; }
    const h = parseFloat(form.home_prob);
    const d = parseFloat(form.draw_prob);
    const a = parseFloat(form.away_prob);
    if ([h, d, a].some((n) => Number.isNaN(n))) {
      toast.error("Probabilities must be valid numbers");
      return;
    }
    setSubmitting(true);
    try {
      await apiPost("/api/admin/ai-sources/ingest", {
        match_id: selectedMatchId,
        source: form.source,
        home_prob: h,
        draw_prob: d,
        away_prob: a,
        confidence: parseFloat(form.confidence) || 0.7,
        reason: form.reason || null,
        raw_content: form.raw_content || null,
      });
      toast.success("AI source uploaded");
      setForm((f) => ({ ...f, reason: "", raw_content: "" }));
      qc.invalidateQueries({ queryKey: ["ai-sources"] });
    } catch (e: any) {
      toast.error(e?.message || "Upload failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="bg-muted/20 border-border">
      <button
        className="w-full flex items-center justify-between px-5 py-4 text-left"
        onClick={() => setOpen((x) => !x)}
      >
        <div className="flex items-center gap-2">
          <Upload className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground/80">Manual Upload</span>
          <Badge className="bg-muted/40 text-muted-foreground text-[10px] border-0 ml-1">fallback</Badge>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
      </button>

      {open && (
        <CardContent className="pt-0 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label className="text-foreground/80 text-xs">Match</Label>
              <Select
                value={selectedMatchId ? String(selectedMatchId) : ""}
                onValueChange={(v) => setSelectedMatchId(parseInt(v, 10))}
              >
                <SelectTrigger className="bg-card border-border text-foreground text-sm">
                  <SelectValue placeholder="Select a match" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border text-foreground max-h-72">
                  {matches.map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                      {m.home_team} vs {m.away_team}
                      {m.league ? ` · ${m.league}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-foreground/80 text-xs">AI Source</Label>
              <Select value={form.source} onValueChange={(v) => setForm((f) => ({ ...f, source: v }))}>
                <SelectTrigger className="bg-card border-border text-foreground text-sm capitalize">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-card border-border text-foreground">
                  {ALLOWED_SOURCES.map((s) => (
                    <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {(["home_prob", "draw_prob", "away_prob", "confidence"] as const).map((k) => (
              <div key={k}>
                <Label className="text-foreground/80 text-xs capitalize">{k.replace("_", " ")}</Label>
                <Input
                  type="number" step="0.01" min="0" max="1"
                  value={(form as any)[k]}
                  onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))}
                  className="bg-card border-border text-foreground text-sm"
                />
              </div>
            ))}
          </div>

          <div>
            <Label className="text-foreground/80 text-xs">Short reason</Label>
            <Input
              value={form.reason}
              onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
              placeholder="e.g. Home side missing 2 starting CBs, away in form"
              maxLength={500}
              className="bg-card border-border text-foreground text-sm"
            />
          </div>

          <div>
            <Label className="text-foreground/80 text-xs">Raw analysis (full paste)</Label>
            <Textarea
              value={form.raw_content}
              onChange={(e) => setForm((f) => ({ ...f, raw_content: e.target.value }))}
              placeholder="Paste the full reasoning text here…"
              rows={5}
              maxLength={20000}
              className="bg-card border-border text-foreground font-mono text-xs"
            />
            <p className="text-xs text-muted-foreground/60 mt-1">{form.raw_content.length}/20000</p>
          </div>

          <div className="flex justify-end">
            <Button
              onClick={submit}
              disabled={submitting || !selectedMatchId}
              className="bg-muted/40 hover:bg-muted/30 text-foreground text-sm"
            >
              <Upload className="w-4 h-4 mr-2" />
              {submitting ? "Uploading…" : "Upload"}
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

// ─── Existing Sources Panel ───────────────────────────────────────────────────

function ExistingSourcesPanel({ matchId }: { matchId: number | null }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["ai-sources", "match", matchId],
    queryFn: () =>
      apiGet<{ match: AISourceMatch; predictions: AISourcePred[] }>(
        `/api/admin/ai-sources/match/${matchId}`
      ),
    enabled: !!matchId,
  });

  const [deleting, setDeleting] = useState<number | null>(null);

  const remove = async (id: number) => {
    setDeleting(id);
    try {
      await apiDelete(`/api/admin/ai-sources/${id}`);
      toast.success("Removed");
      qc.invalidateQueries({ queryKey: ["ai-sources"] });
    } catch (e: any) {
      toast.error(e?.message || "Delete failed");
    } finally {
      setDeleting(null);
    }
  };

  if (!matchId) return null;

  const preds = q.data?.predictions ?? [];

  return (
    <Card className="bg-muted/20 border-border">
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-sm text-foreground/80 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          Ingested Sources
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {q.isLoading ? (
          <Skeleton className="h-16 w-full bg-muted/40" />
        ) : preds.length === 0 ? (
          <p className="text-xs text-muted-foreground">No sources ingested yet.</p>
        ) : (
          <div className="space-y-2">
            {preds.map((p) => (
              <div key={p.id} className="border border-border rounded p-2.5 bg-card/50 text-xs">
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 capitalize text-[10px]">
                      {p.source}
                    </Badge>
                    <span className="text-muted-foreground">conf {fmtPct(p.confidence)}</span>
                    {p.was_correct === true && (
                      <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px]">✓ correct</Badge>
                    )}
                    {p.was_correct === false && (
                      <Badge className="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px]">✗ missed</Badge>
                    )}
                  </div>
                  <Button
                    size="sm" variant="ghost"
                    className="text-rose-400 hover:text-rose-300 h-6 w-6 p-0"
                    onClick={() => remove(p.id)}
                    disabled={deleting === p.id}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center mb-1.5">
                  <div>Home <span className="text-emerald-400 font-bold">{fmtPct(p.home_prob)}</span></div>
                  <div>Draw <span className="text-foreground/80 font-bold">{fmtPct(p.draw_prob)}</span></div>
                  <div>Away <span className="text-rose-400 font-bold">{fmtPct(p.away_prob)}</span></div>
                </div>
                <ProbBar home={p.home_prob} draw={p.draw_prob} away={p.away_prob} />
                {p.reason && <p className="text-muted-foreground italic mt-1.5">{p.reason}</p>}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AISourcesPage() {
  const { user, isAdmin, hasTier } = useAuth();
  const qc = useQueryClient();

  const [selectedModels, setSelectedModels] = useState<Set<PuterModel>>(new Set(["claude", "grok"]));
  const [agentStatus, setAgentStatus] = useState<"idle" | "running" | "done">("idle");
  const [results, setResults] = useState<Map<number, MatchResults>>(new Map());
  const [progress, setProgress] = useState({ current: 0, total: 0, matchLabel: "" });
  const [focusMatchId, setFocusMatchId] = useState<number | null>(null);
  const [puterDetected, setPuterDetected] = useState<boolean>(isPuterAvailable());
  const shouldStop = useRef(false);

  useEffect(() => {
    if (!puterDetected) {
      waitForPuter(6000).then((ok) => {
        if (ok) setPuterDetected(true);
      });
    }
  }, []);

  if (!user) return <Redirect to="/login" />;
  if (!isAdmin && !hasTier("analyst")) return <Redirect to="/subscription" />;

  const permsQ = useQuery({
    queryKey: ["ai-sources", "perms"],
    queryFn: () =>
      apiGet<{ can_upload: boolean; role: string; tier: string }>("/api/admin/ai-sources/permissions"),
  });

  const matchesQ = useQuery({
    queryKey: ["ai-sources", "matches"],
    queryFn: () => apiGet<{ matches: AISourceMatch[] }>("/api/admin/ai-sources/matches?limit=50"),
    // Load as soon as the permissions check finishes (success or error).
    // The backend enforces authorization — non-admin users receive 403.
    enabled: !permsQ.isLoading,
    retry: 2,
  });

  const matches = matchesQ.data?.matches ?? [];
  const activeModels = [...selectedModels] as PuterModel[];

  const updateSlot = (matchId: number, model: PuterModel, patch: Partial<SlotResult>) => {
    setResults((prev) => {
      const next = new Map(prev);
      const existing = next.get(matchId) ?? {};
      next.set(matchId, {
        ...existing,
        [model]: { ...(existing[model] ?? { status: "pending", analysis: null }), ...patch },
      });
      return next;
    });
  };

  const runAgents = useCallback(async () => {
    if (!matches.length) { toast.error("No matches loaded yet"); return; }
    if (!isPuterAvailable()) {
      toast.error("Puter.js not ready — refresh and sign in via Puter");
      return;
    }
    if (activeModels.length === 0) { toast.error("Select at least one AI model"); return; }

    shouldStop.current = false;
    setAgentStatus("running");
    setResults(new Map());
    setProgress({ current: 0, total: matches.length, matchLabel: "" });

    let processed = 0;

    for (let i = 0; i < matches.length; i++) {
      if (shouldStop.current) break;
      const match = matches[i];

      setProgress({
        current: i,
        total: matches.length,
        matchLabel: `${match.home_team} vs ${match.away_team}`,
      });

      for (const model of activeModels) {
        if (shouldStop.current) break;

        updateSlot(match.id, model, { status: "running", analysis: null });

        try {
          const analysis = await analyzeMatchWithPuter(
            match.home_team,
            match.away_team,
            match.league ?? "Unknown League",
            0.34,
            0.33,
            0.33,
            model
          );

          updateSlot(match.id, model, { status: "ingesting", analysis });

          await apiPost("/api/admin/ai-sources/ingest", {
            match_id: match.id,
            source: model,
            home_prob: analysis.home_prob,
            draw_prob: analysis.draw_prob,
            away_prob: analysis.away_prob,
            confidence: analysis.confidence,
            reason: analysis.reason,
            raw_content: analysis.raw_content,
          });

          updateSlot(match.id, model, { status: "done" });
        } catch (e: any) {
          const errMsg: string = e?.message || "Unknown error";
          const isRateLimit = errMsg.toLowerCase().includes("rate limit") ||
            errMsg.includes("429") || errMsg.toLowerCase().includes("quota");

          updateSlot(match.id, model, { status: "failed", error: errMsg });

          if (isRateLimit) {
            toast.warning(
              `Rate limit hit on ${model}. Switch Puter account to continue, or wait a minute.`,
              { duration: 8000 }
            );
            // Extended cooldown on rate limit
            await sleep(15000);
          }
        }

        if (!shouldStop.current) await sleep(DELAY_MS);
      }

      processed++;
      setProgress((p) => ({ ...p, current: processed }));
    }

    setAgentStatus("done");
    qc.invalidateQueries({ queryKey: ["ai-sources"] });

    if (shouldStop.current) {
      toast.info(`Stopped after ${processed}/${matches.length} matches`);
    } else {
      toast.success(`AI agents complete — ${processed} matches processed`);
    }
  }, [matches, activeModels]);

  const stopAgents = () => {
    shouldStop.current = true;
    toast.info("Stopping after current match…");
  };

  const toggleModel = (m: PuterModel) => {
    setSelectedModels((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });
  };

  const puterReady = puterDetected;

  const totalSlots = matches.length * activeModels.length;
  const doneSlots = [...results.values()].reduce((acc, mr) => {
    return acc + activeModels.filter((m) => mr[m]?.status === "done").length;
  }, 0);
  const failedSlots = [...results.values()].reduce((acc, mr) => {
    return acc + activeModels.filter((m) => mr[m]?.status === "failed").length;
  }, 0);
  const progressPct = totalSlots > 0 ? Math.round((doneSlots / totalSlots) * 100) : 0;

  if (permsQ.isLoading) {
    return (
      <div className="w-full">
        <Skeleton className="h-32 w-full bg-muted/20" />
      </div>
    );
  }

  if (permsQ.data && !permsQ.data.can_upload) {
    return (
      <div className="w-full flex items-center justify-center py-20">
        <Card className="bg-muted/20 border-border max-w-md w-full">
          <CardContent className="p-8 text-center">
            <Lock className="w-10 h-10 mx-auto mb-3 text-amber-400" />
            <h3 className="text-lg font-semibold mb-2">Access Restricted</h3>
            <p className="text-sm text-muted-foreground">
              AI Source access requires an admin account or{" "}
              <span className="text-cyan-400">analyst, pro, or elite</span> subscription.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="max-w-5xl mx-auto space-y-5">

        {/* ── Header ─────────────────────────────────────────── */}
        <div className="flex items-start gap-3">
          <Brain className="w-7 h-7 text-cyan-400 shrink-0 mt-1" />
          <div>
            <h1 className="text-2xl font-bold">AI Sources</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Autonomous agents query Claude & Grok via Puter (free) for every match and
              self-ingest the analysis into the prediction ensemble.
            </p>
          </div>
        </div>

        {/* ── Agent Control Panel ─────────────────────────────── */}
        <Card className="bg-muted/20 border-border">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-foreground text-base">
              <Bot className="w-5 h-5 text-cyan-400" />
              Autonomous AI Agent
              {agentStatus === "running" && (
                <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/40 animate-pulse ml-2">
                  Running
                </Badge>
              )}
              {agentStatus === "done" && (
                <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 ml-2">
                  Complete
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Selects all upcoming matches, queries each AI model, normalises probabilities, and
              ingests results automatically — zero human effort.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Model Toggles */}
            <div>
              <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">
                AI Models (FREE via Puter.js)
              </p>
              <div className="flex gap-2 flex-wrap">
                {MODELS.map((m) => {
                  const active = selectedModels.has(m.id);
                  return (
                    <button
                      key={m.id}
                      onClick={() => toggleModel(m.id)}
                      disabled={agentStatus === "running"}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-all ${
                        active
                          ? "border-cyan-500/60 bg-cyan-500/10 text-foreground"
                          : "border-border bg-card text-muted-foreground"
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      <Zap className={`w-3.5 h-3.5 ${active ? "text-cyan-400" : "text-muted-foreground/60"}`} />
                      {m.label}
                      <span className="text-[10px] text-muted-foreground">{m.model}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Puter account panel */}
            <PuterAccountPanel />

            {/* Puter warning */}
            {!puterReady && (
              <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 rounded p-2.5 text-xs text-amber-300">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                Puter.js not detected — ensure the CDN script is loaded and you are signed in to Puter.
              </div>
            )}

            {/* Stats row */}
            {agentStatus !== "idle" && (
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-card/60 rounded p-2">
                  <div className="text-xl font-bold text-foreground">{matches.length}</div>
                  <div className="text-xs text-muted-foreground">Matches</div>
                </div>
                <div className="bg-card/60 rounded p-2">
                  <div className="text-xl font-bold text-emerald-400">{doneSlots}</div>
                  <div className="text-xs text-muted-foreground">Ingested</div>
                </div>
                <div className="bg-card/60 rounded p-2">
                  <div className="text-xl font-bold text-rose-400">{failedSlots}</div>
                  <div className="text-xs text-muted-foreground">Failed</div>
                </div>
              </div>
            )}

            {/* Progress bar */}
            {agentStatus === "running" && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span className="truncate">{progress.matchLabel}</span>
                  <span className="shrink-0 ml-2">
                    {progress.current}/{progress.total} matches
                  </span>
                </div>
                <div className="h-2 rounded-full bg-muted/40 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {DELAY_MS / 1000}s cooldown between calls · auto-retries on rate limit · switch Puter account if blocked.
                </p>
              </div>
            )}

            {/* Controls */}
            <div className="flex gap-2 flex-wrap">
              {agentStatus !== "running" ? (
                <Button
                  onClick={runAgents}
                  disabled={!puterReady || matchesQ.isLoading || activeModels.length === 0}
                  className="bg-cyan-500 hover:bg-cyan-600 text-black font-semibold"
                >
                  <Play className="w-4 h-4 mr-2" />
                  {agentStatus === "done" ? "Run Again" : "Run AI Agents"}
                  {matches.length > 0 && (
                    <span className="ml-2 text-xs opacity-70">
                      {matches.length} matches × {activeModels.length} models
                    </span>
                  )}
                </Button>
              ) : (
                <Button
                  onClick={stopAgents}
                  variant="outline"
                  className="border-rose-500/50 text-rose-400 hover:bg-rose-500/10"
                >
                  <Square className="w-4 h-4 mr-2" />
                  Stop
                </Button>
              )}
              <Button
                onClick={() => qc.invalidateQueries({ queryKey: ["ai-sources"] })}
                variant="outline"
                className="border-border text-muted-foreground hover:bg-muted/40"
                disabled={agentStatus === "running"}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh Matches
              </Button>
            </div>

            {matchesQ.isLoading && (
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" /> Loading matches…
              </p>
            )}
            {!matchesQ.isLoading && matches.length === 0 && (
              <p className="text-xs text-amber-400">
                No upcoming matches found — sync fixtures first via Admin → Fixtures.
              </p>
            )}
          </CardContent>
        </Card>

        {/* ── Match Grid ─────────────────────────────────────── */}
        {(agentStatus !== "idle" || results.size > 0) && matches.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3 flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              Match Processing Queue
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {matches.map((match) => (
                <div key={match.id} onClick={() => setFocusMatchId(match.id === focusMatchId ? null : match.id)} className="cursor-pointer">
                  <MatchCard
                    match={match}
                    results={results.get(match.id) ?? {}}
                    activeModels={activeModels}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Server-Side Analysis ────────────────────────────── */}
        <ServerAnalysisPanel matchCount={matches.length} />

        {/* ── Ingested Sources for focused match ─────────────── */}
        {focusMatchId && <ExistingSourcesPanel matchId={focusMatchId} />}

        {/* ── AI Performance Stats ─────────────────────────────── */}
        <PerformanceStatsPanel />

        {/* ── P3#15: Ensemble Model Leaderboard ───────────────── */}
        <EnsembleLeaderboard />

        {/* ── Manual Upload (collapsed by default) ───────────── */}
        <ManualUploadForm matches={matches} />

      </div>
    </div>
  );
}
