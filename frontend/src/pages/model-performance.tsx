import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";
import {
  Brain, TrendingUp, TrendingDown, Minus, Activity,
  RefreshCw, CheckCircle, XCircle, AlertTriangle, Zap, Target,
} from "lucide-react";
import { toast } from "sonner";

interface ModelRow {
  model_key: string;
  model_name: string;
  model_type: string;
  version: string;
  is_active: boolean;
  auto_demoted: boolean;
  weight: number;
  accuracy: number | null;
  brier_score: number | null;
  log_loss: number | null;
  clv_score: number | null;
  clv_samples: number;
  predictions_total: number;
  predictions_correct: number;
  training_samples: number;
  pkl_loaded: boolean;
}

interface GlobalStats {
  total_settled: number;
  total_wins: number;
  win_rate: number;
  total_profit: number;
  sharpe_ratio: number;
  profit_trend: string;
}

interface PerformanceData {
  period_days: number;
  global_stats: GlobalStats;
  models: ModelRow[];
  model_count: number;
  active_count: number;
  generated_at: string;
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "improving") return <TrendingUp className="w-4 h-4 text-emerald-400" />;
  if (trend === "declining") return <TrendingDown className="w-4 h-4 text-red-400" />;
  return <Minus className="w-4 h-4 text-zinc-400" />;
}

function AccuracyBar({ value }: { value: number | null }) {
  if (value === null) return <span className="text-zinc-500 font-mono text-xs">—</span>;
  const pct = Math.round(value * 100);
  const color = pct >= 55 ? "bg-emerald-500" : pct >= 45 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="font-mono text-xs text-zinc-300 w-10 text-right">{pct}%</span>
    </div>
  );
}

const MODEL_TYPE_COLORS: Record<string, string> = {
  xgboost:     "text-orange-400 bg-orange-400/10 border-orange-400/20",
  neural_net:  "text-purple-400 bg-purple-400/10 border-purple-400/20",
  lstm:        "text-blue-400 bg-blue-400/10 border-blue-400/20",
  ensemble:    "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  poisson:     "text-green-400 bg-green-400/10 border-green-400/20",
  lightgbm:    "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
};

export default function ModelPerformancePage() {
  const { data: config } = usePublicConfig();
  const [days, setDays] = useState("30");
  const [syncing, setSyncing] = useState(false);

  const { data, isLoading, refetch } = useQuery<PerformanceData>({
    queryKey: ["model-performance", days],
    queryFn: () => apiGet(`/api/models/performance?days=${days}`),
    staleTime: 120_000,
  });

  const handleSync = async () => {
    setSyncing(true);
    try {
      await apiPost("/api/models/performance/sync");
      toast.success("Performance sync triggered — data will refresh in ~30s");
      setTimeout(() => refetch(), 5000);
    } catch {
      toast.error("Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const gs = data?.global_stats;
  const models = data?.models ?? [];

  const chartData = models
    .filter((m) => m.accuracy !== null)
    .sort((a, b) => (b.accuracy ?? 0) - (a.accuracy ?? 0))
    .slice(0, 12)
    .map((m) => ({
      name: m.model_key.replace(/_v\d+$/, "").replace(/_/g, " "),
      accuracy: m.accuracy !== null ? Math.round((m.accuracy ?? 0) * 100) : 0,
      weight:   Math.round(m.weight * 100),
      clv:      m.clv_score !== null ? Math.round((m.clv_score ?? 0) * 100) : 0,
    }));

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Brain className="w-6 h-6 text-cyan-400" />
            Model Performance
          </h1>
          <p className="text-zinc-400 text-sm mt-1">
            Real-time accuracy tracking across all {config?.platform?.model_count || 13} ensemble models
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-32 bg-zinc-900 border-zinc-700 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 days</SelectItem>
              <SelectItem value="30">30 days</SelectItem>
              <SelectItem value="90">90 days</SelectItem>
              <SelectItem value="365">1 year</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={syncing}
            className="border-zinc-700 text-zinc-300"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
            Sync
          </Button>
        </div>
      </div>

      {/* Global Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          {
            label: "Win Rate",
            value: `${gs?.win_rate ?? 0}%`,
            sub: `${gs?.total_wins ?? 0} / ${gs?.total_settled ?? 0} settled`,
            icon: <Target className="w-4 h-4 text-cyan-400" />,
            color: "text-cyan-400",
          },
          {
            label: "Total Profit",
            value: `${(gs?.total_profit ?? 0) >= 0 ? "+" : ""}${(gs?.total_profit ?? 0).toFixed(2)}`,
            sub: `Last ${days} days`,
            icon: <TrendingUp className="w-4 h-4 text-emerald-400" />,
            color: (gs?.total_profit ?? 0) >= 0 ? "text-emerald-400" : "text-red-400",
          },
          {
            label: "Sharpe Ratio",
            value: (gs?.sharpe_ratio ?? 0).toFixed(3),
            sub: "> 1.0 = excellent",
            icon: <Activity className="w-4 h-4 text-purple-400" />,
            color: (gs?.sharpe_ratio ?? 0) >= 1 ? "text-purple-400" : "text-zinc-400",
          },
          {
            label: "Active Models",
            value: `${data?.active_count ?? 0} / ${data?.model_count ?? 0}`,
            sub: "in ensemble",
            icon: <Zap className="w-4 h-4 text-yellow-400" />,
            color: "text-yellow-400",
          },
          {
            label: "Profit Trend",
            value: gs?.profit_trend ?? "—",
            sub: `${days}d window`,
            icon: <TrendIcon trend={gs?.profit_trend ?? "neutral"} />,
            color: gs?.profit_trend === "improving" ? "text-emerald-400" : gs?.profit_trend === "declining" ? "text-red-400" : "text-zinc-400",
          },
        ].map((stat) => (
          <Card key={stat.label} className="bg-zinc-900 border-zinc-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                {stat.icon}
                <span className="text-zinc-400 text-xs uppercase tracking-wider">{stat.label}</span>
              </div>
              <div className={`text-xl font-bold font-mono ${stat.color}`}>{stat.value}</div>
              <div className="text-zinc-500 text-xs mt-1">{stat.sub}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Accuracy Chart */}
      {chartData.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-300">Model Accuracy vs Weight</CardTitle>
            <CardDescription className="text-xs text-zinc-500">
              Bar = accuracy (%), Line = ensemble weight (scaled)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#71717a", fontSize: 10 }}
                  angle={-35}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fill: "#71717a", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: 6, fontSize: 11 }}
                  labelStyle={{ color: "#e4e4e7" }}
                />
                <ReferenceLine y={50} stroke="#ef4444" strokeDasharray="4 2" label={{ value: "50%", fill: "#ef4444", fontSize: 10 }} />
                <Bar dataKey="accuracy" fill="#06b6d4" radius={[3, 3, 0, 0]} name="Accuracy %" />
                <Line type="monotone" dataKey="weight" stroke="#a855f7" strokeWidth={2} dot={false} name="Weight %" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Model Table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-zinc-300">
            All Models ({models.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-zinc-500 text-sm">Loading models…</div>
          ) : models.length === 0 ? (
            <div className="p-8 text-center text-zinc-500 text-sm">No model data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase tracking-wider">
                    <th className="text-left p-3 pl-4">Model</th>
                    <th className="text-left p-3">Type</th>
                    <th className="text-left p-3">Status</th>
                    <th className="text-left p-3 min-w-32">Accuracy</th>
                    <th className="text-right p-3">Weight</th>
                    <th className="text-right p-3">Brier</th>
                    <th className="text-right p-3">CLV</th>
                    <th className="text-right p-3 pr-4">Preds</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={m.model_key} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                      <td className="p-3 pl-4">
                        <div className="font-mono text-xs text-white">{m.model_key}</div>
                        <div className="text-zinc-500 text-xs">{m.model_name}</div>
                      </td>
                      <td className="p-3">
                        <Badge
                          variant="outline"
                          className={`text-xs ${MODEL_TYPE_COLORS[m.model_type] ?? "text-zinc-400 bg-zinc-400/10 border-zinc-400/20"}`}
                        >
                          {m.model_type}
                        </Badge>
                      </td>
                      <td className="p-3">
                        {m.is_active ? (
                          <div className="flex items-center gap-1.5">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400 text-xs">Active</span>
                          </div>
                        ) : m.auto_demoted ? (
                          <div className="flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
                            <span className="text-yellow-400 text-xs">Demoted</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <XCircle className="w-3.5 h-3.5 text-red-400" />
                            <span className="text-red-400 text-xs">Inactive</span>
                          </div>
                        )}
                      </td>
                      <td className="p-3 min-w-32">
                        <AccuracyBar value={m.accuracy} />
                      </td>
                      <td className="p-3 text-right font-mono text-xs text-zinc-300">
                        {(m.weight * 100).toFixed(1)}%
                      </td>
                      <td className="p-3 text-right font-mono text-xs text-zinc-400">
                        {m.brier_score !== null ? m.brier_score.toFixed(3) : "—"}
                      </td>
                      <td className="p-3 text-right font-mono text-xs">
                        {m.clv_score !== null ? (
                          <span className={m.clv_score >= 0 ? "text-emerald-400" : "text-red-400"}>
                            {m.clv_score >= 0 ? "+" : ""}{(m.clv_score * 100).toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-zinc-500">—</span>
                        )}
                      </td>
                      <td className="p-3 pr-4 text-right font-mono text-xs text-zinc-400">
                        {m.predictions_total.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
