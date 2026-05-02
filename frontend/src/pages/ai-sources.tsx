import { useState, useRef, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Redirect } from "wouter";
import {
  analyzeMatchWithPuter,
  isPuterAvailable,
  MatchAnalysis,
  PuterModel,
  PUTER_CLAUDE_MODEL,
  PUTER_GROK_MODEL,
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
} from "lucide-react";

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
  { id: "claude", label: "Claude", model: PUTER_CLAUDE_MODEL, color: "text-purple-400" },
  { id: "grok",   label: "Grok",   model: PUTER_GROK_MODEL,  color: "text-cyan-400"   },
];

const DELAY_MS = 2000;

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
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
            const model = MODELS.find((x) => x.id === m)!;
            return (
              <div key={m} className="flex items-center gap-1.5">
                <span className={`text-xs font-medium ${model.color}`}>{model.label}</span>
                <SlotBadge status={slot?.status ?? "pending"} />
              </div>
            );
          })}
          {match.sources.length > 0 && (
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
              const model = MODELS.find((x) => x.id === m)!;
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
                  {a.key_factors.length > 0 && (
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
                      {a.key_factors.map((f, i) => (
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
              {MODELS.find((x) => x.id === m)!.label}: {slot.error || "Analysis failed"}
            </p>
          );
        })}
      </CardContent>
    </Card>
  );
}

// ─── Manual Upload Form ───────────────────────────────────────────────────────

const ALLOWED_SOURCES = ["claude", "grok", "chatgpt", "gemini", "deepseek", "perplexity", "mistral", "manual"];

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
      await apiPost("/admin/ai-sources/ingest", {
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
    <Card className="bg-gray-800/60 border-gray-700">
      <button
        className="w-full flex items-center justify-between px-5 py-4 text-left"
        onClick={() => setOpen((x) => !x)}
      >
        <div className="flex items-center gap-2">
          <Upload className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-semibold text-gray-300">Manual Upload</span>
          <Badge className="bg-gray-700 text-gray-400 text-[10px] border-0 ml-1">fallback</Badge>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </button>

      {open && (
        <CardContent className="pt-0 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label className="text-gray-300 text-xs">Match</Label>
              <Select
                value={selectedMatchId ? String(selectedMatchId) : ""}
                onValueChange={(v) => setSelectedMatchId(parseInt(v, 10))}
              >
                <SelectTrigger className="bg-gray-900 border-gray-700 text-white text-sm">
                  <SelectValue placeholder="Select a match" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-700 text-white max-h-72">
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
              <Label className="text-gray-300 text-xs">AI Source</Label>
              <Select value={form.source} onValueChange={(v) => setForm((f) => ({ ...f, source: v }))}>
                <SelectTrigger className="bg-gray-900 border-gray-700 text-white text-sm capitalize">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-700 text-white">
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
                <Label className="text-gray-300 text-xs capitalize">{k.replace("_", " ")}</Label>
                <Input
                  type="number" step="0.01" min="0" max="1"
                  value={(form as any)[k]}
                  onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))}
                  className="bg-gray-900 border-gray-700 text-white text-sm"
                />
              </div>
            ))}
          </div>

          <div>
            <Label className="text-gray-300 text-xs">Short reason</Label>
            <Input
              value={form.reason}
              onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
              placeholder="e.g. Home side missing 2 starting CBs, away in form"
              maxLength={500}
              className="bg-gray-900 border-gray-700 text-white text-sm"
            />
          </div>

          <div>
            <Label className="text-gray-300 text-xs">Raw analysis (full paste)</Label>
            <Textarea
              value={form.raw_content}
              onChange={(e) => setForm((f) => ({ ...f, raw_content: e.target.value }))}
              placeholder="Paste the full reasoning text here…"
              rows={5}
              maxLength={20000}
              className="bg-gray-900 border-gray-700 text-white font-mono text-xs"
            />
            <p className="text-xs text-gray-600 mt-1">{form.raw_content.length}/20000</p>
          </div>

          <div className="flex justify-end">
            <Button
              onClick={submit}
              disabled={submitting || !selectedMatchId}
              className="bg-gray-700 hover:bg-gray-600 text-white text-sm"
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
        `/admin/ai-sources/match/${matchId}`
      ),
    enabled: !!matchId,
  });

  const [deleting, setDeleting] = useState<number | null>(null);

  const remove = async (id: number) => {
    setDeleting(id);
    try {
      await apiDelete(`/admin/ai-sources/${id}`);
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
  const qc = useQueryClient();

  const [selectedModels, setSelectedModels] = useState<Set<PuterModel>>(new Set(["claude", "grok"]));
  const [agentStatus, setAgentStatus] = useState<"idle" | "running" | "done">("idle");
  const [results, setResults] = useState<Map<number, MatchResults>>(new Map());
  const [progress, setProgress] = useState({ current: 0, total: 0, matchLabel: "" });
  const [focusMatchId, setFocusMatchId] = useState<number | null>(null);
  const shouldStop = useRef(false);

  if (!user) return <Redirect to="/login" />;
  if (!isAdmin && !hasTier("analyst")) return <Redirect to="/subscription" />;

  const permsQ = useQuery({
    queryKey: ["ai-sources", "perms"],
    queryFn: () =>
      apiGet<{ can_upload: boolean; role: string; tier: string }>("/admin/ai-sources/permissions"),
  });

  const matchesQ = useQuery({
    queryKey: ["ai-sources", "matches"],
    queryFn: () => apiGet<{ matches: AISourceMatch[] }>("/admin/ai-sources/matches?limit=50"),
    enabled: !!permsQ.data?.can_upload,
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

          await apiPost("/admin/ai-sources/ingest", {
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
          updateSlot(match.id, model, {
            status: "failed",
            error: e?.message || "Unknown error",
          });
        }

        await sleep(DELAY_MS);
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

  const puterReady = isPuterAvailable();

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
            <h1 className="text-2xl font-bold">AI Sources</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              Autonomous agents query Claude & Grok via Puter (free) for every match and
              self-ingest the analysis into the prediction ensemble.
            </p>
          </div>
        </div>

        {/* ── Agent Control Panel ─────────────────────────────── */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-white text-base">
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
              <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">
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
                  Rate-limited to 1 call per {DELAY_MS / 1000}s to stay within Puter free tier.
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

        {/* ── Ingested Sources for focused match ─────────────── */}
        {focusMatchId && <ExistingSourcesPanel matchId={focusMatchId} />}

        {/* ── Manual Upload (collapsed by default) ───────────── */}
        <ManualUploadForm matches={matches} />

      </div>
    </div>
  );
}
