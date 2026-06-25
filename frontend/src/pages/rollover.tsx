import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import {
  Zap, Shield, AlertTriangle, XCircle, RefreshCw,
  TrendingUp, Activity, Target, ChevronRight, Clock,
  BarChart3, Sigma, Cpu, CheckCircle2, Info
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Fixture {
  home_team: string;
  away_team: string;
  league: string;
  kickoff_time: string | null;
  opening_odds_home?: number | null;
  opening_odds_draw?: number | null;
  opening_odds_away?: number | null;
}

interface ConflictFlag {
  type: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  reason: string;
}

interface TopScore {
  score: string;
  probability: number;
}

interface Certificate {
  id: number;
  fixture_id: number;
  outcome: string;
  outcome_label: string;
  signal_density: number;
  model_confidence: number;
  simulation_agreement: number;
  status: "certified" | "watchlist" | "rejected";
  kelly_fraction: number;
  xg_source: string;
  home_lambda: number;
  away_lambda: number;
  mc_home_prob: number;
  mc_draw_prob: number;
  mc_away_prob: number;
  mc_btts_prob: number;
  mc_over25_prob: number;
  mc_under25_prob: number;
  mc_over35_prob?: number;
  simulations_run: number;
  top_correct_scores?: TopScore[];
  conflict_flags: ConflictFlag[];
  created_at: string;
  fixture: Fixture;
}

interface Stats {
  total_certified: number;
  total_watchlist: number;
  total_rejected: number;
  total_all: number;
  avg_signal_density: number;
  avg_model_confidence: number;
  avg_simulation_agreement: number;
  win_rate: number | null;
  total_settled: number;
  last_run_at: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_META = {
  certified: {
    label: "Certified",
    icon: CheckCircle2,
    bg: "bg-emerald-500/10 border-emerald-500/20",
    text: "text-emerald-400",
    badge: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    dot: "bg-emerald-400",
  },
  watchlist: {
    label: "Watchlist",
    icon: AlertTriangle,
    bg: "bg-amber-500/10 border-amber-500/20",
    text: "text-amber-400",
    badge: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    dot: "bg-amber-400",
  },
  rejected: {
    label: "Rejected",
    icon: XCircle,
    bg: "bg-red-500/10 border-red-500/20",
    text: "text-red-400",
    badge: "bg-red-500/20 text-red-400 border border-red-500/30",
    dot: "bg-red-400",
  },
};

const XG_SOURCE_LABELS: Record<string, string> = {
  odds_closing: "Live Closing Odds",
  odds_opening: "Opening Odds",
  model_probs:  "Model Probabilities",
  league_prior: "League Prior",
};

const SEVERITY_STYLE: Record<string, string> = {
  HIGH:   "text-red-400 bg-red-500/10 border-red-500/30",
  MEDIUM: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  LOW:    "text-blue-400 bg-blue-500/10 border-blue-500/30",
};

function fmt(n: number | null | undefined, digits = 1): string {
  if (n == null) return "—";
  return (n * 100).toFixed(digits) + "%";
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function DensityBar({ value }: { value: number }) {
  const color =
    value >= 72 ? "bg-emerald-500"
    : value >= 55 ? "bg-amber-500"
    : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs font-mono tabular-nums text-muted-foreground w-8 text-right">
        {value.toFixed(0)}
      </span>
    </div>
  );
}

function ProbBar({
  label, value, highlight = false
}: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`w-16 shrink-0 ${highlight ? "text-white font-semibold" : "text-muted-foreground"}`}>
        {label}
      </span>
      <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${highlight ? "bg-primary" : "bg-white/20"}`}
          style={{ width: `${(value * 100).toFixed(1)}%` }}
        />
      </div>
      <span className={`w-10 text-right font-mono tabular-nums ${highlight ? "text-white" : "text-muted-foreground"}`}>
        {fmt(value, 1)}
      </span>
    </div>
  );
}

// ── Certificate Card ──────────────────────────────────────────────────────────

function CertCard({ cert, expanded, onToggle }: {
  cert: Certificate;
  expanded: boolean;
  onToggle: () => void;
}) {
  const meta = STATUS_META[cert.status];
  const Icon = meta.icon;
  const kf   = cert.kelly_fraction;

  return (
    <div
      className={`rounded-xl border ${meta.bg} transition-all duration-200`}
    >
      {/* Header row */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer select-none"
        onClick={onToggle}
      >
        {/* Status dot */}
        <div className={`mt-1 w-2 h-2 rounded-full shrink-0 ${meta.dot}`} />

        {/* Fixture info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white truncate">
              {cert.fixture?.home_team ?? "?"} vs {cert.fixture?.away_team ?? "?"}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${meta.badge}`}>
              {meta.label}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-[11px] text-muted-foreground flex-wrap">
            <span>{cert.fixture?.league ?? "—"}</span>
            {cert.fixture?.kickoff_time && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {fmtDate(cert.fixture.kickoff_time)}
              </span>
            )}
          </div>
        </div>

        {/* Outcome badge */}
        <div className="text-right shrink-0">
          <div className="text-sm font-bold text-white">{cert.outcome_label}</div>
          <div className="text-[10px] text-muted-foreground mt-0.5">Recommended outcome</div>
        </div>

        <ChevronRight
          className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
        />
      </div>

      {/* Quick metrics row */}
      <div className="px-4 pb-3 grid grid-cols-3 gap-3 border-t border-white/5 pt-3">
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Signal Density</div>
          <DensityBar value={cert.signal_density} />
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">MC Agreement</div>
          <div className="flex items-center gap-1">
            <span className={`text-sm font-mono font-bold ${
              cert.simulation_agreement >= 0.60 ? "text-emerald-400"
              : cert.simulation_agreement >= 0.45 ? "text-amber-400"
              : "text-red-400"
            }`}>
              {fmt(cert.simulation_agreement)}
            </span>
          </div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Kelly Stake</div>
          <div className="text-sm font-mono font-bold text-primary">
            {kf > 0 ? fmt(kf) : "—"}
          </div>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-white/5 p-4 space-y-5">

          {/* Monte Carlo distribution */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Sigma className="w-3.5 h-3.5 text-primary" />
              <span className="text-xs font-semibold text-white uppercase tracking-widest">
                Monte Carlo Distribution
              </span>
              <span className="text-[10px] text-muted-foreground ml-auto">
                {(cert.simulations_run ?? 10000).toLocaleString()} simulations
              </span>
            </div>
            <div className="space-y-1.5">
              <ProbBar label="Home Win" value={cert.mc_home_prob} highlight={cert.outcome === "home_win"} />
              <ProbBar label="Draw"     value={cert.mc_draw_prob} highlight={cert.outcome === "draw"} />
              <ProbBar label="Away Win" value={cert.mc_away_prob} highlight={cert.outcome === "away_win"} />
              <ProbBar label="BTTS"     value={cert.mc_btts_prob} highlight={cert.outcome === "btts_yes"} />
              <ProbBar label="Over 2.5" value={cert.mc_over25_prob} highlight={cert.outcome === "over_2_5"} />
              {cert.mc_over35_prob != null && (
                <ProbBar label="Over 3.5" value={cert.mc_over35_prob} />
              )}
            </div>
          </div>

          {/* xG / Poisson parameters */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-white/3 border border-white/5 p-3">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                Home λ (xG proxy)
              </div>
              <div className="text-xl font-mono font-bold text-white">
                {cert.home_lambda?.toFixed(2) ?? "—"}
              </div>
              <div className="text-[10px] text-muted-foreground mt-1">
                {XG_SOURCE_LABELS[cert.xg_source] ?? cert.xg_source}
              </div>
            </div>
            <div className="rounded-lg bg-white/3 border border-white/5 p-3">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                Away λ (xG proxy)
              </div>
              <div className="text-xl font-mono font-bold text-white">
                {cert.away_lambda?.toFixed(2) ?? "—"}
              </div>
              <div className="text-[10px] text-muted-foreground mt-1">
                Expected goals (away)
              </div>
            </div>
          </div>

          {/* Top correct scores */}
          {cert.top_correct_scores && cert.top_correct_scores.length > 0 && (
            <div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                Top Correct Scores
              </div>
              <div className="flex flex-wrap gap-2">
                {cert.top_correct_scores.map((s, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-1.5 text-xs bg-white/5 rounded-lg px-2.5 py-1.5"
                  >
                    <span className="font-bold text-white font-mono">{s.score}</span>
                    <span className="text-muted-foreground">{fmt(s.probability)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model confidence + signal breakdown */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg bg-white/3 border border-white/5 p-3">
              <div className="text-muted-foreground mb-1">Model Confidence</div>
              <div className="text-base font-mono font-bold text-white">
                {fmt(cert.model_confidence)}
              </div>
            </div>
            <div className="rounded-lg bg-white/3 border border-white/5 p-3">
              <div className="text-muted-foreground mb-1">Signal Density</div>
              <div className={`text-base font-mono font-bold ${
                cert.signal_density >= 72 ? "text-emerald-400"
                : cert.signal_density >= 55 ? "text-amber-400"
                : "text-red-400"
              }`}>
                {cert.signal_density.toFixed(1)} / 100
              </div>
            </div>
          </div>

          {/* Opening odds */}
          {cert.fixture?.opening_odds_home && (
            <div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Opening Odds</div>
              <div className="flex gap-2">
                {[
                  { label: "1", value: cert.fixture.opening_odds_home },
                  { label: "X", value: cert.fixture.opening_odds_draw },
                  { label: "2", value: cert.fixture.opening_odds_away },
                ].map(({ label, value }) => (
                  <div key={label} className="flex-1 rounded-lg bg-white/5 border border-white/5 p-2 text-center">
                    <div className="text-[10px] text-muted-foreground">{label}</div>
                    <div className="text-sm font-mono font-bold text-white mt-0.5">
                      {value?.toFixed(2) ?? "—"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Conflict flags */}
          {cert.conflict_flags.length > 0 && (
            <div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                Signal Flags
              </div>
              <div className="space-y-1.5">
                {cert.conflict_flags.map((flag, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-2 text-xs rounded-lg border px-3 py-2 ${SEVERITY_STYLE[flag.severity]}`}
                  >
                    <Info className="w-3 h-3 mt-0.5 shrink-0" />
                    <span>{flag.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-[10px] text-muted-foreground flex items-center gap-1 pt-1">
            <Clock className="w-3 h-3" />
            Certified {fmtDate(cert.created_at)}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type FilterTab = "all" | "certified" | "watchlist" | "rejected";

export default function RolloverPage() {
  const { user } = useAuth();
  const isAdmin = (user as any)?.is_admin === true;
  const qc = useQueryClient();

  const [tab, setTab]         = useState<FilterTab>("certified");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (id: number) =>
    setExpanded(prev => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });

  // Stats
  const statsQ = useQuery<Stats>({
    queryKey: ["rollover-stats"],
    queryFn:  () => apiGet("/api/rollover/stats"),
    refetchInterval: 60_000,
  });

  // Certified picks
  const certsQ = useQuery<{ items: Certificate[]; total: number }>({
    queryKey: ["rollover-certs", tab],
    queryFn:  () => apiGet(`/api/rollover/certified${tab !== "all" ? `?status=${tab}` : ""}&limit=100`),
    refetchInterval: 60_000,
  });

  // Run pipeline mutation
  const runMutation = useMutation({
    mutationFn: () => apiPost("/api/rollover/run?days_ahead=7&n_simulations=10000"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rollover-stats"] });
      qc.invalidateQueries({ queryKey: ["rollover-certs"] });
    },
  });

  const stats = statsQ.data;
  const certs = certsQ.data?.items ?? [];
  const totalCerts = certsQ.data?.total ?? 0;

  const TABS: { key: FilterTab; label: string; count?: number }[] = [
    { key: "certified", label: "Certified",  count: stats?.total_certified },
    { key: "watchlist", label: "Watchlist",  count: stats?.total_watchlist },
    { key: "rejected",  label: "Rejected",   count: stats?.total_rejected },
    { key: "all",       label: "All",        count: stats?.total_all },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">

        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-5 h-5 text-primary" />
              <h1 className="text-xl font-bold text-white">Rollover Engine</h1>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 uppercase tracking-wider">
                Monte Carlo
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Poisson simulation · Signal Density scoring · Certified picks
            </p>
          </div>

          {isAdmin && (
            <button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-50 hover:bg-primary/90 transition-colors shrink-0"
            >
              {runMutation.isPending ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Cpu className="w-4 h-4" />
              )}
              {runMutation.isPending ? "Running…" : "Run Engine"}
            </button>
          )}
        </div>

        {/* Pipeline result banner */}
        {runMutation.isSuccess && runMutation.data && (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm">
            <div className="font-semibold text-emerald-400 mb-1 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              Pipeline complete
            </div>
            <div className="text-muted-foreground grid grid-cols-3 gap-2 mt-2 text-xs">
              <div>✅ Certified: <span className="font-bold text-emerald-400">{runMutation.data.certified}</span></div>
              <div>⚠️ Watchlist: <span className="font-bold text-amber-400">{runMutation.data.watchlist}</span></div>
              <div>❌ Rejected: <span className="font-bold text-red-400">{runMutation.data.rejected}</span></div>
            </div>
          </div>
        )}
        {runMutation.isError && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400">
            Pipeline failed. Check backend logs.
          </div>
        )}

        {/* ── Stats bar ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            {
              label: "Certified",
              value: stats?.total_certified ?? "—",
              icon: Shield,
              accent: "text-emerald-400",
            },
            {
              label: "Avg Signal",
              value: stats?.avg_signal_density != null ? `${stats.avg_signal_density.toFixed(0)}/100` : "—",
              icon: Activity,
              accent: "text-primary",
            },
            {
              label: "Avg Confidence",
              value: stats?.avg_model_confidence != null ? fmt(stats.avg_model_confidence) : "—",
              icon: Target,
              accent: "text-blue-400",
            },
            {
              label: "Win Rate",
              value: stats?.win_rate != null ? fmt(stats.win_rate) : stats?.total_settled === 0 ? "No data" : "—",
              icon: TrendingUp,
              accent: stats?.win_rate != null && stats.win_rate >= 0.55 ? "text-emerald-400" : "text-muted-foreground",
            },
          ].map(({ label, value, icon: Icon, accent }) => (
            <div
              key={label}
              className="rounded-xl border border-white/5 bg-white/2 p-4"
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-3.5 h-3.5 ${accent}`} />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</span>
              </div>
              <div className={`text-xl font-mono font-bold ${accent}`}>{value}</div>
            </div>
          ))}
        </div>

        {/* Last run info */}
        {stats?.last_run_at && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="w-3 h-3" />
            Last pipeline run: {fmtDate(stats.last_run_at)}
          </div>
        )}

        {/* ── Filter tabs ────────────────────────────────────────────── */}
        <div className="flex items-center gap-1 bg-white/3 border border-white/5 rounded-xl p-1">
          {TABS.map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === key
                  ? "bg-white/8 text-white"
                  : "text-muted-foreground hover:text-white"
              }`}
            >
              {label}
              {count != null && (
                <span className="text-[10px] font-bold bg-white/8 rounded-full px-1.5 py-0.5">
                  {count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ── Certificate list ───────────────────────────────────────── */}
        {certsQ.isLoading && (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {certsQ.isError && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-sm text-red-400 text-center">
            Failed to load certifications
          </div>
        )}

        {!certsQ.isLoading && certs.length === 0 && (
          <div className="rounded-xl border border-white/5 bg-white/2 p-10 text-center">
            <BarChart3 className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <div className="text-sm text-muted-foreground">
              {isAdmin
                ? "No certifications yet — click Run Engine to start the pipeline"
                : "No certifications found for this filter"}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {certs.map((cert) => (
            <CertCard
              key={cert.id}
              cert={cert}
              expanded={expanded.has(cert.id)}
              onToggle={() => toggle(cert.id)}
            />
          ))}
        </div>

        {totalCerts > certs.length && (
          <div className="text-center text-xs text-muted-foreground py-2">
            Showing {certs.length} of {totalCerts} certifications
          </div>
        )}
      </div>
    </div>
  );
}
