import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, TrendingDown, BarChart2, RefreshCw, Activity, AlertCircle } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const DAYS_OPTIONS = [
  { value: "30",  label: "Last 30 Days" },
  { value: "60",  label: "Last 60 Days" },
  { value: "90",  label: "Last 90 Days" },
  { value: "180", label: "Last 6 Months" },
];

const STEP_OPTIONS = [
  { value: "7",  label: "Weekly steps" },
  { value: "14", label: "Bi-weekly steps" },
];

function pct(v: number | undefined) {
  if (v === undefined || v === null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function color(acc: number) {
  if (acc >= 0.60) return "#22c55e";
  if (acc >= 0.48) return "#f59e0b";
  return "#ef4444";
}

export default function BacktestPage() {
  const [daysBack, setDaysBack]  = useState("60");
  const [stepSize, setStepSize]  = useState("7");
  const [enabled,  setEnabled]   = useState(true);

  const { data, isLoading, isError, refetch, isFetching } = useQuery<any>({
    queryKey: ["/api/ai-engine/backtest/walk-forward", daysBack, stepSize],
    queryFn: () =>
      apiGet(`/api/ai-engine/backtest/walk-forward?days_back=${daysBack}&step_size=${stepSize}&min_window=14`),
    enabled,
    staleTime: 300_000,
  });

  const steps: any[] = data?.steps ?? [];
  const totalSamples: number = data?.total_samples ?? 0;

  // Build chart data — one row per step, one line per model
  const modelNames: string[] = Array.from(
    new Set(steps.flatMap((s: any) => (s.models ?? []).map((m: any) => m.model_name)))
  ).slice(0, 8);

  const chartData = steps.map((step: any) => {
    const row: Record<string, any> = {
      label: step.window_start ? step.window_start.slice(0, 10) : "",
      n: step.n_samples ?? 0,
    };
    for (const m of step.models ?? []) {
      row[m.model_name] = +(m.accuracy ?? 0).toFixed(3);
    }
    return row;
  });

  // Aggregate stats: avg accuracy per model across all steps
  const modelStats: Record<string, { sum: number; cnt: number }> = {};
  for (const step of steps) {
    for (const m of step.models ?? []) {
      if (!modelStats[m.model_name]) modelStats[m.model_name] = { sum: 0, cnt: 0 };
      modelStats[m.model_name].sum += m.accuracy ?? 0;
      modelStats[m.model_name].cnt += 1;
    }
  }
  const modelAvg = Object.entries(modelStats)
    .map(([name, s]) => ({ name, avg: s.cnt > 0 ? s.sum / s.cnt : 0 }))
    .sort((a, b) => b.avg - a.avg);

  const LINE_COLORS = [
    "#22c55e", "#06b6d4", "#f59e0b", "#a78bfa",
    "#f87171", "#34d399", "#fb923c", "#818cf8",
  ];

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex-1">
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            Walk-Forward Backtest
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Rolling model accuracy measured over historical settled predictions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={daysBack} onValueChange={setDaysBack}>
            <SelectTrigger className="w-36 bg-gray-800 border-gray-700 text-white text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 border-gray-700">
              {DAYS_OPTIONS.map(o => (
                <SelectItem key={o.value} value={o.value} className="text-white">{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={stepSize} onValueChange={setStepSize}>
            <SelectTrigger className="w-36 bg-gray-800 border-gray-700 text-white text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 border-gray-700">
              {STEP_OPTIONS.map(o => (
                <SelectItem key={o.value} value={o.value} className="text-white">{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            variant="outline"
            className="border-gray-600 text-gray-300 hover:text-white"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-gray-500 mb-1">Test Windows</p>
            <p className="text-xl font-bold text-white">
              {isLoading ? <Skeleton className="h-6 w-12 bg-gray-700" /> : steps.length}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-gray-500 mb-1">Total Samples</p>
            <p className="text-xl font-bold text-white">
              {isLoading ? <Skeleton className="h-6 w-16 bg-gray-700" /> : totalSamples.toLocaleString()}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-gray-500 mb-1">Best Model</p>
            <p className="text-sm font-bold text-green-400 truncate">
              {isLoading ? <Skeleton className="h-6 w-20 bg-gray-700" /> : (modelAvg[0]?.name ?? "—")}
            </p>
            <p className="text-xs text-gray-400">{modelAvg[0] ? pct(modelAvg[0].avg) : ""}</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-gray-500 mb-1">Weakest Model</p>
            <p className="text-sm font-bold text-orange-400 truncate">
              {isLoading ? <Skeleton className="h-6 w-20 bg-gray-700" /> : (modelAvg[modelAvg.length - 1]?.name ?? "—")}
            </p>
            <p className="text-xs text-gray-400">{modelAvg.length ? pct(modelAvg[modelAvg.length - 1]?.avg) : ""}</p>
          </CardContent>
        </Card>
      </div>

      {/* Chart */}
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-cyan-400" />
            Rolling Accuracy Over Time
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64 w-full bg-gray-800" />
          ) : isError || steps.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 gap-3 text-gray-500">
              <AlertCircle className="w-8 h-8" />
              <p className="text-sm">
                {data?.message ?? "No settled predictions found for this window. Run predictions and let matches settle to populate."}
              </p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 8, right: 8, Intelligence Agenttom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="label" tick={{ fill: "#9ca3af", fontSize: 11 }} tickLine={false} />
                <YAxis
                  tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  tickLine={false}
                  domain={[0.3, 0.8]}
                />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                  formatter={(v: any, name: string) => [`${(+v * 100).toFixed(1)}%`, name]}
                  labelStyle={{ color: "#e5e7eb", fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
                {modelNames.map((mn, idx) => (
                  <Line
                    key={mn}
                    type="monotone"
                    dataKey={mn}
                    stroke={LINE_COLORS[idx % LINE_COLORS.length]}
                    strokeWidth={1.5}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Per-model summary table */}
      {modelAvg.length > 0 && (
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-white">Model Performance Ranking</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-gray-800">
              {modelAvg.map((m, i) => (
                <div key={m.name} className="flex items-center gap-3 py-2.5 px-1">
                  <span className="text-xs text-gray-500 w-5 text-right">{i + 1}</span>
                  <span className="text-sm text-gray-200 font-mono flex-1 truncate">{m.name}</span>
                  <div className="w-28 bg-gray-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${Math.min(100, m.avg * 100 / 0.75 * 100)}%`, background: color(m.avg) }}
                    />
                  </div>
                  <Badge
                    className="text-xs font-mono w-14 text-right justify-end"
                    style={{ background: `${color(m.avg)}20`, color: color(m.avg), border: `1px solid ${color(m.avg)}40` }}
                  >
                    {pct(m.avg)}
                  </Badge>
                  {i === 0 ? <TrendingUp className="w-4 h-4 text-green-400 shrink-0" /> :
                   i === modelAvg.length - 1 ? <TrendingDown className="w-4 h-4 text-red-400 shrink-0" /> :
                   <span className="w-4" />}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
