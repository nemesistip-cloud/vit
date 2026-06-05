import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import {
  Wallet, TrendingUp, TrendingDown, Activity, Target,
  Calculator, AlertTriangle, CheckCircle, ChevronUp, ChevronDown,
} from "lucide-react";
import { toast } from "sonner";

interface BankrollState {
  balance: {
    initial: number;
    current: number;
    peak: number;
    drawdown_pct: number;
  };
  stats: {
    all_time: { total: number; wins: number; losses: number; win_rate: number; profit: number; roi_pct: number };
    last_30d: { total: number; wins: number; losses: number; win_rate: number; profit: number };
    win_rate_decimal: number;
  };
  kelly: {
    full_kelly_pct: number;
    quarter_kelly_pct: number;
    suggested_stake: number;
    basis_win_rate: number;
    basis_avg_odds: number;
  };
  updated_at: string | null;
}

interface HistoryEntry {
  date: string;
  count: number;
  wins: number;
  profit: number;
  cumulative: number;
}

interface KellyResult {
  edge_pct: number;
  full_kelly_pct: number;
  quarter_kelly_pct: number;
  recommended_stake: number;
  bankroll: number;
  positive_ev: boolean;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs">
      <div className="text-zinc-400 mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-zinc-300">{p.name}:</span>
          <span className="text-white font-mono">{typeof p.value === "number" ? p.value.toFixed(4) : p.value}</span>
        </div>
      ))}
    </div>
  );
};

export default function BankrollPage() {
  const [kellyWinProb, setKellyWinProb] = useState("0.55");
  const [kellyOdds, setKellyOdds] = useState("2.10");
  const [kellyResult, setKellyResult] = useState<KellyResult | null>(null);
  const [historyDays, setHistoryDays] = useState(30);

  const { data: state, isLoading: stateLoading } = useQuery<BankrollState>({
    queryKey: ["bankroll-state"],
    queryFn: () => apiGet("/api/bankroll/state"),
    staleTime: 30_000,
  });

  const { data: historyData } = useQuery<{ history: HistoryEntry[] }>({
    queryKey: ["bankroll-history", historyDays],
    queryFn: () => apiGet(`/api/bankroll/history?days=${historyDays}`),
    staleTime: 60_000,
  });

  const kellyMutation = useMutation({
    mutationFn: (body: { win_probability: number; decimal_odds: number }) =>
      apiPost<KellyResult>("/api/bankroll/kelly", body),
    onSuccess: (data) => setKellyResult(data),
    onError: () => toast.error("Kelly calculation failed"),
  });

  const handleKelly = () => {
    const wp = parseFloat(kellyWinProb);
    const od = parseFloat(kellyOdds);
    if (isNaN(wp) || isNaN(od) || wp <= 0 || wp >= 1 || od <= 1) {
      toast.error("Enter valid win probability (0–1) and odds (> 1)");
      return;
    }
    kellyMutation.mutate({ win_probability: wp, decimal_odds: od });
  };

  const bal = state?.balance;
  const stats = state?.stats;
  const kelly = state?.kelly;
  const history = historyData?.history ?? [];

  const profitColor = (v: number) => (v >= 0 ? "text-emerald-400" : "text-red-400");
  const profitSign = (v: number) => (v >= 0 ? "+" : "");

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground flex items-center gap-2">
          <Wallet className="w-6 h-6 text-cyan-400" />
          Bankroll Management
        </h1>
        <p className="text-zinc-400 text-sm mt-1">
          Kelly Criterion staking, P&L tracking, and drawdown protection
        </p>
      </div>

      {/* Balance Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Current Balance",
            value: `$${(bal?.current ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
            sub: `Initial: $${(bal?.initial ?? 0).toLocaleString()}`,
            icon: <Wallet className="w-4 h-4 text-cyan-400" />,
            color: "text-cyan-400",
          },
          {
            label: "Peak Balance",
            value: `$${(bal?.peak ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
            sub: `Drawdown: ${(bal?.drawdown_pct ?? 0).toFixed(1)}%`,
            icon: <ChevronUp className="w-4 h-4 text-emerald-400" />,
            color: "text-emerald-400",
          },
          {
            label: "All-Time ROI",
            value: `${profitSign(stats?.all_time.roi_pct ?? 0)}${(stats?.all_time.roi_pct ?? 0).toFixed(1)}%`,
            sub: `${stats?.all_time.total ?? 0} signals settled`,
            icon: <Activity className="w-4 h-4 text-purple-400" />,
            color: profitColor(stats?.all_time.roi_pct ?? 0),
          },
          {
            label: "30d Win Rate",
            value: `${stats?.last_30d.win_rate ?? 0}%`,
            sub: `${stats?.last_30d.wins ?? 0}W / ${stats?.last_30d.losses ?? 0}L`,
            icon: <Target className="w-4 h-4 text-yellow-400" />,
            color: (stats?.last_30d.win_rate ?? 0) >= 50 ? "text-emerald-400" : "text-red-400",
          },
        ].map((card) => (
          <Card key={card.label} className="bg-zinc-900 border-zinc-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                {card.icon}
                <span className="text-zinc-400 text-xs uppercase tracking-wider">{card.label}</span>
              </div>
              <div className={`text-xl font-bold font-mono ${card.color}`}>
                {stateLoading ? "…" : card.value}
              </div>
              <div className="text-zinc-500 text-xs mt-1">{card.sub}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* P&L Chart */}
        <Card className="md:col-span-2 bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2 flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm font-medium text-zinc-300">Cumulative P&L</CardTitle>
              <CardDescription className="text-xs text-zinc-500">Running profit/loss over time</CardDescription>
            </div>
            <div className="flex gap-1">
              {[7, 30, 90].map((d) => (
                <button
                  key={d}
                  onClick={() => setHistoryDays(d)}
                  className={`px-2 py-1 rounded text-xs font-mono transition-colors ${historyDays === d ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30" : "text-zinc-500 hover:text-zinc-300"}`}
                >
                  {d}d
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            {history.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-zinc-500 text-sm">
                No settled predictions yet — P&L will appear here as matches settle
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={history} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="date" tick={{ fill: "#71717a", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#71717a", fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <ReferenceLine y={0} stroke="#52525b" strokeDasharray="4 2" />
                  <Area
                    type="monotone"
                    dataKey="cumulative"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    fill="url(#profitGrad)"
                    name="Cumulative P&L"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Kelly Calculator */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
              <Calculator className="w-4 h-4 text-purple-400" />
              Kelly Calculator
            </CardTitle>
            <CardDescription className="text-xs text-zinc-500">
              Optimal stake sizing for any signal
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-zinc-400 text-xs">Win Probability (0–1)</Label>
              <Input
                value={kellyWinProb}
                onChange={(e) => setKellyWinProb(e.target.value)}
                placeholder="e.g. 0.55"
                className="mt-1 bg-zinc-800 border-zinc-700 text-white font-mono text-sm"
              />
            </div>
            <div>
              <Label className="text-zinc-400 text-xs">Decimal Odds</Label>
              <Input
                value={kellyOdds}
                onChange={(e) => setKellyOdds(e.target.value)}
                placeholder="e.g. 2.10"
                className="mt-1 bg-zinc-800 border-zinc-700 text-white font-mono text-sm"
              />
            </div>
            <Button
              className="w-full bg-cyan-600 hover:bg-cyan-500 text-white"
              onClick={handleKelly}
              disabled={kellyMutation.isPending}
            >
              Calculate Kelly
            </Button>

            {kellyResult && (
              <div className="space-y-2 pt-2 border-t border-zinc-800">
                <div className="flex items-center gap-2 mb-2">
                  {kellyResult.positive_ev ? (
                    <><CheckCircle className="w-4 h-4 text-emerald-400" /><span className="text-emerald-400 text-xs font-medium">Positive EV Signal</span></>
                  ) : (
                    <><AlertTriangle className="w-4 h-4 text-red-400" /><span className="text-red-400 text-xs font-medium">Negative EV — Avoid</span></>
                  )}
                </div>
                {[
                  { label: "Edge", value: `${kellyResult.edge_pct >= 0 ? "+" : ""}${kellyResult.edge_pct >= 0 ? "▲" : "▼"}{kellyResult.edge_pct.toFixed(2)}%`, color: kellyResult.positive_ev ? "text-emerald-400" : "text-red-400" },
                  { label: "Full Kelly", value: `${kellyResult.full_kelly_pct.toFixed(2)}%`, color: "text-white" },
                  { label: "¼ Kelly (safe)", value: `${kellyResult.quarter_kelly_pct.toFixed(2)}%`, color: "text-cyan-400" },
                  { label: "Recommended Stake", value: `$${kellyResult.recommended_stake.toFixed(2)}`, color: "text-cyan-400" },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between items-center">
                    <span className="text-zinc-400 text-xs">{row.label}</span>
                    <span className={`font-mono text-sm font-medium ${row.color}`}>{row.value}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Current Kelly from state */}
            {kelly && !kellyResult && (
              <div className="space-y-2 pt-2 border-t border-zinc-800">
                <div className="text-zinc-400 text-xs mb-2">Based on your prediction history:</div>
                {[
                  { label: "Win Rate", value: `${kelly.basis_win_rate}%` },
                  { label: "¼ Kelly", value: `${kelly.quarter_kelly_pct.toFixed(2)}%`, color: "text-cyan-400" },
                  { label: "Suggested Stake", value: `$${kelly.suggested_stake.toFixed(2)}`, color: "text-cyan-400" },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between items-center">
                    <span className="text-zinc-400 text-xs">{row.label}</span>
                    <span className={`font-mono text-sm ${(row as any).color ?? "text-white"}`}>{row.value}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Stats Table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-zinc-300">Performance Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { title: "All Time", data: stats?.all_time },
              { title: "Last 30 Days", data: stats?.last_30d },
            ].map(({ title, data: d }) => (
              <div key={title}>
                <div className="text-zinc-400 text-xs uppercase tracking-wider mb-3">{title}</div>
                <div className="space-y-2">
                  {[
                    { label: "Total Signals", value: (d?.total ?? 0).toString() },
                    { label: "Wins", value: (d?.wins ?? 0).toString(), color: "text-emerald-400" },
                    { label: "Losses", value: (d?.losses ?? 0).toString(), color: "text-red-400" },
                    { label: "Win Rate", value: `${d?.win_rate ?? 0}%`, color: (d?.win_rate ?? 0) >= 50 ? "text-emerald-400" : "text-red-400" },
                    { label: "Profit", value: `${profitSign(d?.profit ?? 0)}${(d?.profit ?? 0).toFixed(4)}`, color: profitColor(d?.profit ?? 0) },
                  ].map((row) => (
                    <div key={row.label} className="flex justify-between items-center py-1 border-b border-zinc-800/50">
                      <span className="text-zinc-400 text-xs">{row.label}</span>
                      <span className={`font-mono text-sm ${(row as any).color ?? "text-white"}`}>{row.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
