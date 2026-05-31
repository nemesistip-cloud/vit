import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Trophy,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Brain,
  Target,
  Activity,
  Zap,
} from "lucide-react";

interface ModelEntry {
  key: string;
  name: string;
  model_type?: string;
  weight: number;
  accuracy_1x2?: number;
  brier_score?: number;
  log_loss?: number;
  clv_score?: number;
  predictions_total: number;
  predictions_correct?: number;
  is_active: boolean;
  auto_demoted?: boolean;
  calibrated?: boolean;
  league_accuracy?: Record<string, { n: number; correct: number; acc: number }>;
}

type SortKey = "weight" | "accuracy_1x2" | "brier_score" | "log_loss" | "predictions_total";
type SortDir = "asc" | "desc";

function tierBadge(weight: number) {
  if (weight >= 2.0)  return <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/30 text-xs">Elite</Badge>;
  if (weight >= 1.3)  return <Badge className="bg-green-500/20 text-green-300 border-green-500/30 text-xs">Strong</Badge>;
  if (weight >= 0.8)  return <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30 text-xs">Active</Badge>;
  if (weight >= 0.3)  return <Badge className="bg-orange-500/20 text-orange-300 border-orange-500/30 text-xs">Weak</Badge>;
  return <Badge className="bg-red-500/20 text-red-300 border-red-500/30 text-xs">Penalised</Badge>;
}

function pct(v?: number | null) {
  if (v == null) return "–";
  return `${(v * 100).toFixed(1)}%`;
}
function num(v?: number | null, dp = 4) {
  if (v == null) return "–";
  return v.toFixed(dp);
}
function bar(v: number, max: number, color: string) {
  const pct = Math.min(100, Math.round((v / max) * 100));
  return (
    <div className="w-full bg-white/5 rounded-full h-1.5 mt-1">
      <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function EnsembleLeaderboard() {
  const [sortKey, setSortKey]   = useState<SortKey>("weight");
  const [sortDir, setSortDir]   = useState<SortDir>("desc");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAll, setShowAll]   = useState(false);

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ["ensemble-leaderboard"],
    queryFn: () => apiGet<{ models: ModelEntry[] }>("/api/ai-engine/performance"),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });

  const models: ModelEntry[] = data?.models ?? [];

  const sorted = [...models].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    return sortDir === "desc" ? (bv as number) - (av as number) : (av as number) - (bv as number);
  });

  const visible = showAll ? sorted : sorted.slice(0, 8);
  const activeCount  = models.filter(m => m.is_active).length;
  const demotedCount = models.filter(m => m.auto_demoted).length;
  const avgWeight    = models.length ? models.reduce((s, m) => s + m.weight, 0) / models.length : 0;
  const bestAccuracy = Math.max(0, ...models.map(m => m.accuracy_1x2 ?? 0));

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortDir(d => d === "desc" ? "asc" : "desc");
    else { setSortKey(k); setSortDir("desc"); }
  }

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <ChevronDown className="w-3 h-3 opacity-30" />;
    return sortDir === "desc"
      ? <ChevronDown className="w-3 h-3 text-blue-400" />
      : <ChevronUp   className="w-3 h-3 text-blue-400" />;
  }

  return (
    <Card className="bg-black/40 border-white/10">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4 text-yellow-400" />
            <CardTitle className="text-sm font-semibold text-white">Ensemble Leaderboard</CardTitle>
            <Badge className="bg-white/10 text-white/60 text-xs border-0 ml-1">
              {models.length} models
            </Badge>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => refetch()}
            disabled={isFetching}
            className="h-7 px-2 text-xs text-white/60 hover:text-white"
          >
            <RefreshCw className={`w-3 h-3 mr-1 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
        <CardDescription className="text-xs text-white/40 mt-1">
          Live model weights, accuracy, and calibration — updated after each settled match
        </CardDescription>

        {/* ── Summary row ───────────────────────────────────────── */}
        <div className="grid grid-cols-4 gap-2 mt-3">
          {[
            { label: "Active",     value: activeCount,        icon: <Activity className="w-3 h-3" />, color: "text-green-400" },
            { label: "Demoted",    value: demotedCount,       icon: <TrendingDown className="w-3 h-3" />, color: "text-red-400" },
            { label: "Avg Weight", value: avgWeight.toFixed(2), icon: <Brain className="w-3 h-3" />, color: "text-blue-400" },
            { label: "Best Acc",   value: pct(bestAccuracy),  icon: <Target className="w-3 h-3" />, color: "text-yellow-400" },
          ].map(({ label, value, icon, color }) => (
            <div key={label} className="bg-white/5 rounded-lg p-2 text-center">
              <div className={`flex items-center justify-center gap-1 ${color} text-xs mb-0.5`}>
                {icon}
                <span>{label}</span>
              </div>
              <div className="text-white font-mono text-sm font-semibold">{value}</div>
            </div>
          ))}
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {isLoading ? (
          <div className="px-4 pb-4 space-y-2">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full bg-white/5" />)}
          </div>
        ) : (
          <>
            {/* ── Table header ───────────────────────────────────── */}
            <div className="px-4 pb-1">
              <div className="grid grid-cols-12 gap-1 text-xs text-white/40 uppercase tracking-wide border-b border-white/10 pb-1.5">
                <div className="col-span-1 text-center">#</div>
                <div className="col-span-4">Model</div>
                <button className="col-span-2 flex items-center gap-0.5 hover:text-white/70 cursor-pointer justify-end" onClick={() => toggleSort("weight")}>
                  Weight <SortIcon k="weight" />
                </button>
                <button className="col-span-2 flex items-center gap-0.5 hover:text-white/70 cursor-pointer justify-end" onClick={() => toggleSort("accuracy_1x2")}>
                  Acc <SortIcon k="accuracy_1x2" />
                </button>
                <button className="col-span-2 flex items-center gap-0.5 hover:text-white/70 cursor-pointer justify-end" onClick={() => toggleSort("brier_score")}>
                  Brier <SortIcon k="brier_score" />
                </button>
                <div className="col-span-1 text-center">N</div>
              </div>
            </div>

            {/* ── Rows ───────────────────────────────────────────── */}
            <div className="divide-y divide-white/5">
              {visible.map((m, idx) => {
                const isExp = expanded === m.key;
                const rank  = sorted.indexOf(m) + 1;
                return (
                  <div key={m.key}>
                    <div
                      className="px-4 py-2 grid grid-cols-12 gap-1 items-center hover:bg-white/5 cursor-pointer transition-colors"
                      onClick={() => setExpanded(isExp ? null : m.key)}
                    >
                      {/* Rank */}
                      <div className="col-span-1 text-center">
                        {rank <= 3 ? (
                          <span className={`text-sm font-bold ${rank === 1 ? "text-yellow-400" : rank === 2 ? "text-gray-300" : "text-amber-600"}`}>
                            {rank === 1 ? "🥇" : rank === 2 ? "🥈" : "🥉"}
                          </span>
                        ) : (
                          <span className="text-xs text-white/30 font-mono">{rank}</span>
                        )}
                      </div>

                      {/* Model name + status */}
                      <div className="col-span-4 min-w-0">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="text-xs text-white font-medium truncate">{m.name || m.key}</span>
                          {!m.is_active && <Badge className="bg-red-500/20 text-red-300 text-[10px] border-0 shrink-0">Off</Badge>}
                          {m.auto_demoted && <Badge className="bg-orange-500/20 text-orange-300 text-[10px] border-0 shrink-0">Demoted</Badge>}
                        </div>
                        <div className="text-[10px] text-white/30 truncate">{m.model_type || m.key}</div>
                      </div>

                      {/* Weight */}
                      <div className="col-span-2 text-right">
                        <span className="text-xs font-mono text-white">{m.weight.toFixed(3)}</span>
                        {bar(m.weight, 5.0, "bg-blue-500")}
                      </div>

                      {/* Accuracy */}
                      <div className="col-span-2 text-right">
                        <span className={`text-xs font-mono ${
                          (m.accuracy_1x2 ?? 0) >= 0.55 ? "text-green-400" :
                          (m.accuracy_1x2 ?? 0) >= 0.45 ? "text-white" : "text-red-400"
                        }`}>{pct(m.accuracy_1x2)}</span>
                        {m.accuracy_1x2 != null && bar(m.accuracy_1x2, 1.0, "bg-green-500")}
                      </div>

                      {/* Brier */}
                      <div className="col-span-2 text-right">
                        <span className={`text-xs font-mono ${
                          (m.brier_score ?? 1) <= 0.2 ? "text-green-400" :
                          (m.brier_score ?? 1) <= 0.35 ? "text-white" : "text-red-400"
                        }`}>{num(m.brier_score, 3)}</span>
                        {m.brier_score != null && bar(1 - m.brier_score, 1.0, "bg-purple-500")}
                      </div>

                      {/* N samples */}
                      <div className="col-span-1 text-center">
                        <span className="text-[10px] text-white/50 font-mono">{m.predictions_total}</span>
                      </div>
                    </div>

                    {/* ── Expanded detail ─────────────────────────── */}
                    {isExp && (
                      <div className="px-4 pb-3 bg-white/3 border-l-2 border-blue-500/40">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2 mb-3">
                          {[
                            { label: "Log Loss",    value: num(m.log_loss, 4)  },
                            { label: "CLV Score",   value: num(m.clv_score, 5) },
                            { label: "Correct",     value: `${m.predictions_correct ?? "–"} / ${m.predictions_total}` },
                            { label: "Calibrated",  value: m.calibrated ? "Yes" : "–" },
                          ].map(({ label, value }) => (
                            <div key={label} className="bg-white/5 rounded p-2">
                              <div className="text-[10px] text-white/40 uppercase tracking-wide">{label}</div>
                              <div className="text-xs text-white font-mono mt-0.5">{value}</div>
                            </div>
                          ))}
                        </div>

                        {/* Weight tier */}
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] text-white/40">Tier</span>
                          {tierBadge(m.weight)}
                          {m.model_type && (
                            <Badge className="bg-white/10 text-white/50 text-[10px] border-0">
                              {m.model_type}
                            </Badge>
                          )}
                        </div>

                        {/* Per-league accuracy */}
                        {m.league_accuracy && Object.keys(m.league_accuracy).length > 0 && (
                          <div className="mt-2">
                            <div className="text-[10px] text-white/40 uppercase tracking-wide mb-1">Per-League Accuracy</div>
                            <div className="flex flex-wrap gap-1.5">
                              {Object.entries(m.league_accuracy)
                                .sort((a, b) => b[1].n - a[1].n)
                                .slice(0, 6)
                                .map(([league, stats]) => (
                                  <div key={league} className="bg-white/5 rounded px-2 py-1 text-[10px]">
                                    <span className="text-white/60">{league}</span>
                                    <span className="text-white/80 font-mono ml-1">
                                      {pct(stats.acc)}
                                    </span>
                                    <span className="text-white/30 ml-0.5">({stats.n})</span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* ── Show more / less ───────────────────────────────── */}
            {models.length > 8 && (
              <div className="px-4 py-2 border-t border-white/10 text-center">
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs text-white/50 hover:text-white"
                  onClick={() => setShowAll(v => !v)}
                >
                  {showAll ? (
                    <><ChevronUp className="w-3 h-3 mr-1" /> Show Top 8</>
                  ) : (
                    <><ChevronDown className="w-3 h-3 mr-1" /> Show All {models.length} Models</>
                  )}
                </Button>
              </div>
            )}

            {models.length === 0 && (
              <div className="px-4 pb-4 text-center text-xs text-white/40 py-8">
                <Zap className="w-6 h-6 mx-auto mb-2 opacity-30" />
                No model performance data yet — run predictions to populate the leaderboard.
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
