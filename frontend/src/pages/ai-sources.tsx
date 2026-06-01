import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Redirect } from "wouter";
import {
  MatchAnalysis,
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


];
const DELAY_MS = 3500;

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}


  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setSignedIn(ok);
    if (ok) {
      setUsername(user?.username ?? null);
    } else {
      setUsername(null);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleSignIn = async () => {
    setBusy(true);
    try {
      await refresh();
    } catch (e: any) {
    } finally { setBusy(false); }
  };

  const handleSwitchAccount = async () => {
    setBusy(true);
    try {
      await refresh();
      toast.info("Signed out — sign in with a different account to reset rate limits");
    } catch (e: any) {
      toast.error(e?.message || "Failed to switch account");
    } finally { setBusy(false); }
  };


  return (
    <div className="flex items-center gap-2 flex-wrap bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2">
      <User className="w-3.5 h-3.5 text-gray-400 shrink-0" />
      {signedIn === null ? (
      ) : signedIn && username ? (
        <>
          <span className="text-xs text-gray-300">
          </span>
          <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px]">signed in</Badge>
          <button
            onClick={handleSwitchAccount}
            disabled={busy}
            className="text-[11px] text-gray-400 hover:text-amber-400 flex items-center gap-1 ml-auto transition-colors"
          >
            <LogOut className="w-3 h-3" />
            Switch account
          </button>
        </>
      ) : (
        <>
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
      {busy && <Loader2 className="w-3 h-3 animate-spin text-gray-400 shrink-0" />}
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
    pending:   { label: "Pending",   cls: "bg-gray-700 text-gray-300",            icon: null },
    running:   { label: "Querying…", cls: "bg-blue-500/20 text-blue-300 border border-blue-500/40",  icon: <Loader2 className="w-3 h-3 animate-spin mr-1" /> },
    ingesting: { label: "Saving…",   cls: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40", icon: <Loader2 className="w-3 h-3 animate-spin mr-1" /> },
    done:      { label: "Done",      cls: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30", icon: <CheckCircle2 className="w-3 h-3 mr-1" /> },
    failed:    { label: "Failed",    cls: "bg-rose-500/20 text-rose-300 border border-rose-500/30",   icon: <XCircle className="w-3 h-3 mr-1" /> },
    skipped:   { label: "Skipped",   cls: "bg-gray-600/40 text-gray-500",         icon: null },
  };
  const c = cfg[status];
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${c.cls}`}>
      {c.icon}{c.label}
    </span>
  );
}

// ─── Probability Bar ──────────────────────────────────────────────────────────


// ─── Quantum Shard Visualization ──────────────────────────────────────────

function QuantumShardMonitor({
  tasks,
  results
}: {
  results: Map<number, MatchResults>
}) {
  const activeShards = tasks.filter(t => {
    const res = results.get(t.match.id)?.[t.model];
    return res?.status === "running" || res?.status === "ingesting";
  });

  if (activeShards.length === 0) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2 mb-4 animate-in fade-in slide-in-from-top-2 duration-500">
      {activeShards.map((shard, i) => (
        <div key={`shard-${i}`} className="bg-gray-900 border border-cyan-500/30 rounded-lg p-2 flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono text-cyan-400 uppercase tracking-tighter">Shard {i+1}</span>
            <Zap className="w-2.5 h-2.5 text-cyan-400 animate-pulse" />
          </div>
          <div className="text-[10px] font-bold text-white truncate">{shard.match.home_team.split(" ")[0]}</div>
          <div className="text-[9px] text-gray-500 uppercase">{shard.model}</div>
          <div className="h-1 bg-gray-800 rounded-full overflow-hidden mt-1">
            <div className="h-full bg-cyan-500 animate-progress-fast" style={{ width: "60%" }} />
          </div>
        </div>
      ))}
    </div>
  );
}
function ProbBar({ home, draw, away }: { home: number; draw: number; away: number }) {
  return (
    <div className="flex rounded overflow-hidden h-2 w-full mt-1">
      <div className="bg-emerald-500" style={{ width: `${home * 100}%` }} title={`Home ${fmtPct(home)}`} />
      <div className="bg-gray-500"   style={{ width: `${draw * 100}%` }} title={`Draw ${fmtPct(draw)}`} />
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
    : "border-gray-700";

  return (
    <Card className={`bg-gray-900 border ${borderCls} transition-all duration-300`}>
      <CardContent className="p-3 space-y-2">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-white truncate">
              {match.home_team} <span className="text-gray-500">vs</span> {match.away_team}
            </div>
            <div className="text-xs text-gray-500 flex flex-wrap gap-1 mt-0.5">
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
                  className="bg-gray-700/50 text-gray-400 text-[10px] px-1.5 py-0 border-0 capitalize"
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
                <div key={m} className="bg-gray-800/60 rounded p-2 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold ${model.color}`}>{model.label}</span>
                    <span className="text-xs text-gray-400">
                      conf {fmtPct(a.confidence)}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-1 text-xs text-center">
                    <div>
                      <div className="text-gray-400">Home</div>
                      <div className="text-emerald-400 font-bold">{fmtPct(a.home_prob)}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Draw</div>
                      <div className="text-gray-300 font-bold">{fmtPct(a.draw_prob)}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Away</div>
                      <div className="text-rose-400 font-bold">{fmtPct(a.away_prob)}</div>
                    </div>
                  </div>
                  <ProbBar home={a.home_prob} draw={a.draw_prob} away={a.away_prob} />
                  {a.reason && (
                    <p className="text-[11px] text-gray-400 italic">{a.reason}</p>
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
                    <ul className="text-[11px] text-gray-400 space-y-0.5 pl-2">
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
    <Card className="bg-gray-800/60 border-gray-700">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white text-base">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            AI Source Performance
            {(data?.total_ingested ?? 0) > 0 && (
              <Badge className="bg-gray-700 text-gray-300 border-0 text-[10px] ml-1">
                {data!.total_ingested} ingested
              </Badge>
            )}
          </CardTitle>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs text-gray-400 hover:text-white border border-gray-700"
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
          <Skeleton className="h-16 w-full bg-gray-700" />
        ) : !hasPerf ? (
          <div className="space-y-2">
            <p className="text-xs text-gray-500">
              {data?.message ?? "No performance data yet — metrics are computed after matches settle."}
            </p>
            {Object.keys(sourceCounts).length > 0 && (
              <div>
                <p className="text-xs text-gray-400 mb-1.5 font-medium">Ingested by source:</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(sourceCounts).map(([src, cnt]) => (
                    <Badge key={src} className="bg-gray-700 text-gray-300 border-0 capitalize text-[10px]">
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
              <div key={p.source} className="bg-gray-900/60 rounded p-2.5 text-xs">
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
                  <span className="text-gray-500 text-[10px]">{p.ingested_count} predictions</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-gray-400">Accuracy</div>
                    <div className={`font-bold ${p.accuracy >= 0.6 ? "text-emerald-400" : p.accuracy >= 0.45 ? "text-amber-400" : "text-rose-400"}`}>
                      {fmtPct(p.accuracy)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400">Calibration</div>
                    <div className="text-gray-300 font-bold">{fmtPct(p.calibration_score)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400">Weight</div>
                    <div className="text-cyan-400 font-bold">{p.current_weight.toFixed(2)}×</div>
                  </div>
                </div>
                {p.sample_size > 0 && (
                  <div className="mt-1 text-[10px] text-gray-600">
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
    <Card className="bg-gray-800/60 border-gray-700">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-white text-base">
          <Settings className="w-5 h-5 text-amber-400" />
          Server-Side Analysis
          <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] ml-1">
          </Badge>
        </CardTitle>
        <CardDescription>
          Uses the AI cascade (Native Ensemble) first, then automatically
          falls back to the 13-model ML ensemble when AI providers are unavailable.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {summary && (
          <div className={`grid gap-3 text-center ${summary.mlFallback > 0 ? "grid-cols-3" : "grid-cols-2"}`}>
            <div className="bg-gray-900/60 rounded p-2">
              <div className="text-xl font-bold text-emerald-400">{summary.ingested}</div>
              <div className="text-xs text-gray-500">Ingested</div>
            </div>
            {summary.mlFallback > 0 && (
              <div className="bg-blue-900/30 border border-blue-500/20 rounded p-2">
                <div className="text-xl font-bold text-blue-400">{summary.mlFallback}</div>
                <div className="text-xs text-gray-500">ML Ensemble</div>
              </div>
            )}
            <div className="bg-gray-900/60 rounded p-2">
              <div className="text-xl font-bold text-amber-400">{summary.skipped}</div>
              <div className="text-xs text-gray-500">Skipped</div>
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
              <div key={r.match_id} className="flex items-start gap-2 text-xs py-1 border-b border-gray-700/50 last:border-0">
                <span className={`shrink-0 font-medium ${r.status === "ingested" ? "text-emerald-400" : r.status === "skipped" ? "text-amber-400" : "text-rose-400"}`}>
                  {r.status === "ingested" ? "✓" : r.status === "skipped" ? "—" : "✗"}
                </span>
                <span className="text-gray-300 flex-1 truncate">{r.match}</span>
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
                  <span className="text-gray-500 shrink-0 font-mono">
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
    <Card className="bg-gray-800/40 border-gray-700">
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-sm text-gray-300 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          Ingested Sources
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {q.isLoading ? (
          <Skeleton className="h-16 w-full bg-gray-700" />
        ) : preds.length === 0 ? (
          <p className="text-xs text-gray-500">No sources ingested yet.</p>
        ) : (
          <div className="space-y-2">
            {preds.map((p) => (
              <div key={p.id} className="border border-gray-700 rounded p-2.5 bg-gray-900/50 text-xs">
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 capitalize text-[10px]">
                      {p.source}
                    </Badge>
                    <span className="text-gray-500">conf {fmtPct(p.confidence)}</span>
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
                  <div>Draw <span className="text-gray-300 font-bold">{fmtPct(p.draw_prob)}</span></div>
                  <div>Away <span className="text-rose-400 font-bold">{fmtPct(p.away_prob)}</span></div>
                </div>
                <ProbBar home={p.home_prob} draw={p.draw_prob} away={p.away_prob} />
                {p.reason && <p className="text-gray-400 italic mt-1.5">{p.reason}</p>}
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
  if (!user) return <Redirect to="/login" />;
  if (!isAdmin && !hasTier("analyst")) return <Redirect to="/subscription" />;
  const qc = useQueryClient();

  const [agentStatus, setAgentStatus] = useState<"idle" | "running" | "done">("idle");
  const [results, setResults] = useState<Map<number, MatchResults>>(new Map());
  const [progress, setProgress] = useState({ current: 0, total: 0, matchLabel: "" });
  const [focusMatchId, setFocusMatchId] = useState<number | null>(null);
  const shouldStop = useRef(false);
  const [quantumMode, setQuantumMode] = useState(false);
  const [concurrency, setConcurrency] = useState(3);

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
      return;
    }
    if (activeModels.length === 0) { toast.error("Select at least one AI model"); return; }

    shouldStop.current = false;
    setAgentStatus("running");
    setResults(new Map());

    matches.forEach(m => {
      activeModels.forEach(mod => {
        allTasks.push({ match: m, model: mod });
      });
    });

    setActiveTasks(allTasks);
    setProgress({ current: 0, total: allTasks.length, matchLabel: "Starting Quantum Sourcing..." });

    let completed = 0;
    const limit = quantumMode ? concurrency : 1;
    const taskQueue = [...allTasks];

      if (shouldStop.current) return;
      const { match, model } = task;

      updateSlot(match.id, model, { status: "running", analysis: null });
      try {
          match.home_team,
          match.away_team,
          match.league ?? "Unknown League",
          0.34, 0.33, 0.33,
          model
        );

        if (shouldStop.current) return;
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
        updateSlot(match.id, model, { status: "failed", error: errMsg });
        if (errMsg.toLowerCase().includes("rate limit")) {
           toast.warning(`Rate limit on ${model}. Quantum shard throttled.`);
        }
      } finally {
        completed++;
        setProgress(p => ({
          ...p,
          current: completed,
          matchLabel: `${task.match.home_team} vs ${task.match.away_team}`
        }));
        if (!shouldStop.current) {
           await sleep(quantumMode ? 500 : DELAY_MS);
        }
      }
    };

    const worker = async () => {
      while (taskQueue.length > 0 && !shouldStop.current) {
        const task = taskQueue.shift();
        if (task) await executeTask(task);
      }
    };

    const workers = [];
    for (let i = 0; i < limit; i++) {
      workers.push(worker());
    }

    await Promise.all(workers);

    setAgentStatus("done");
    qc.invalidateQueries({ queryKey: ["ai-sources"] });
    if (shouldStop.current) {
      toast.info("Stopped Quantum Sourcing");
    } else {
      toast.success(`Quantum Sourcing Complete - ${completed} tasks processed`);
    }

  const stopAgents = () => {
    shouldStop.current = true;
    toast.info("Stopping Quantum shards…");
  };

    setSelectedModels((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });
  };


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
      <div className="min-h-screen bg-gray-950 text-white p-4">
        <Skeleton className="h-32 w-full bg-gray-800" />
      </div>
    );
  }

  if (permsQ.data && !permsQ.data.can_upload) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-4 flex items-center justify-center">
        <Card className="bg-gray-800 border-gray-700 max-w-md w-full">
          <CardContent className="p-8 text-center">
            <Lock className="w-10 h-10 mx-auto mb-3 text-amber-400" />
            <h3 className="text-lg font-semibold mb-2">Access Restricted</h3>
            <p className="text-sm text-gray-400">
              AI Source access requires an admin account or{" "}
              <span className="text-cyan-400">analyst, pro, or elite</span> subscription.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4 md:p-6 pb-24">
      <div className="max-w-5xl mx-auto space-y-5">

        {/* ── Header ─────────────────────────────────────────── */}
        <div className="flex items-start gap-3">
          <Brain className="w-7 h-7 text-cyan-400 shrink-0 mt-1" />
          <div>
            <h1 className="text-2xl font-bold">Quantum AI Sources</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              self-ingest the analysis into the prediction ensemble.
            </p>
          </div>
        </div>

        {/* ── Agent Control Panel ─────────────────────────────── */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-white text-base">
              <Bot className="w-5 h-5 text-cyan-400" />
              Quantum AI Sourcing Hub
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
              <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">
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
                          ? "border-cyan-500/60 bg-cyan-500/10 text-white"
                          : "border-gray-700 bg-gray-900 text-gray-500"
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      <Zap className={`w-3.5 h-3.5 ${active ? "text-cyan-400" : "text-gray-600"}`} />
                      {m.label}
                      <span className="text-[10px] text-gray-500">{m.model}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Quantum Mode Toggle */}
            <div className="flex items-center justify-between p-3 rounded-lg border border-cyan-500/30 bg-cyan-500/5">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-full ${quantumMode ? "bg-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.5)]" : "bg-gray-700"}`}>
                  <Zap className={`w-4 h-4 ${quantumMode ? "text-black animate-pulse" : "text-gray-400"}`} />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">Next-Gen Quantum Sourcing</p>
                  <p className="text-[11px] text-cyan-400/70">Multi-threaded shard processing • High throughput</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {quantumMode && (
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 uppercase font-bold">Shards:</span>
                    <input
                      type="range" min="1" max="8"
                      value={concurrency}
                      onChange={(e) => setConcurrency(parseInt(e.target.value))}
                      className="w-16 h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                    <span className="text-xs font-mono text-cyan-400 w-3">{concurrency}</span>
                  </div>
                )}
                <button
                  onClick={() => setQuantumMode(!quantumMode)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${quantumMode ? "bg-cyan-500" : "bg-gray-700"}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${quantumMode ? "translate-x-6" : "translate-x-1"}`} />
                </button>
              </div>
            </div>

              <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 rounded p-2.5 text-xs text-amber-300">
                <AlertTriangle className="w-4 h-4 shrink-0" />
              </div>
            )}

            {/* Stats row */}
            {agentStatus !== "idle" && (
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-gray-900/60 rounded p-2">
                  <div className="text-xl font-bold text-white">{matches.length}</div>
                  <div className="text-xs text-gray-500">Matches</div>
                </div>
                <div className="bg-gray-900/60 rounded p-2">
                  <div className="text-xl font-bold text-emerald-400">{doneSlots}</div>
                  <div className="text-xs text-gray-500">Ingested</div>
                </div>
                <div className="bg-gray-900/60 rounded p-2">
                  <div className="text-xl font-bold text-rose-400">{failedSlots}</div>
                  <div className="text-xs text-gray-500">Failed</div>
                </div>
              </div>
            )}

            {/* Quantum Shard Monitor */}
            <QuantumShardMonitor tasks={activeTasks} results={results} />
            {/* Progress bar */}
            {agentStatus === "running" && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-gray-400">
                  <span className="truncate">{progress.matchLabel}</span>
                  <span className="shrink-0 ml-2">
                    {progress.current}/{progress.total} matches
                  </span>
                </div>
                <div className="h-2 rounded-full bg-gray-700 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <p className="text-[11px] text-gray-500">
                </p>
              </div>
            )}

            {/* Controls */}
            <div className="flex gap-2 flex-wrap">
              {agentStatus !== "running" ? (
                <Button
                  onClick={runAgents}
                  className="bg-cyan-500 hover:bg-cyan-600 text-black font-semibold"
                >
                  <Play className="w-4 h-4 mr-2" />
                  {agentStatus === "done" ? "Run Again" : "Initialize Quantum Sourcing"}
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
                className="border-gray-600 text-gray-400 hover:bg-gray-700"
                disabled={agentStatus === "running"}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh Matches
              </Button>
            </div>

            {matchesQ.isLoading && (
              <p className="text-xs text-gray-500 flex items-center gap-1">
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
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3 flex items-center gap-2">
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


      </div>
    </div>
  );
}
