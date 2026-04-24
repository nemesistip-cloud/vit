import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useGetAiPerformance, useGetAiReport } from "@/api-client/index";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  LineChart, Line, BarChart, Bar, ResponsiveContainer,
  XAxis, YAxis, Tooltip, Legend, ReferenceLine,
} from "recharts";
import {
  TrendingUp, Target, BarChart2, Brain, Download,
  Globe, Users, Trophy, ShieldCheck, Filter,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "";

function StatCard({ label, value, sub, icon: Icon, color = "text-primary" }: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; color?: string;
}) {
  return (
    <Card className="bg-card/50 backdrop-blur border-primary/10">
      <CardHeader className="flex flex-row items-center justify-between pb-1">
        <CardTitle className="text-xs font-mono uppercase text-muted-foreground">{label}</CardTitle>
        <Icon className={`w-4 h-4 ${color}`} />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
        {sub && <p className="text-xs text-muted-foreground font-mono mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function RankBadge({ rank }: { rank: number }) {
  const cls =
    rank === 1 ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/40" :
    rank === 2 ? "bg-slate-400/20 text-slate-300 border-slate-400/40" :
    rank === 3 ? "bg-amber-700/20 text-amber-600 border-amber-700/40" :
    "bg-muted/20 text-muted-foreground border-muted/30";
  return (
    <div className={`w-7 h-7 rounded flex items-center justify-center text-xs font-bold font-mono border ${cls}`}>
      #{rank}
    </div>
  );
}

export default function AnalyticsPage() {
  const [tab, setTab] = useState("accuracy");
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [dateTo, setDateTo] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split("T")[0];
  });
  const [lbSort, setLbSort] = useState<"trust_score" | "accuracy" | "stake">("trust_score");
  const [userSort, setUserSort] = useState<"roi" | "profit" | "win_rate" | "stake">("roi");

  function buildDateParams() {
    const params: string[] = [];
    if (dateFrom) params.push(`date_from=${dateFrom}`);
    if (dateTo) params.push(`date_to=${dateTo}`);
    return params.length ? `?${params.join("&")}` : "";
  }

  const dateParams = buildDateParams();

  const { data: summary } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: () => apiGet<any>("/analytics/summary"),
  });

  const { data: system } = useQuery({
    queryKey: ["analytics-system"],
    queryFn: () => apiGet<any>("/analytics/system"),
    refetchInterval: 60_000,
    enabled: tab === "system",
  });

  const { data: accuracy, isLoading: loadingAcc } = useQuery({
    queryKey: ["analytics-accuracy", dateParams],
    queryFn: () => apiGet<any>(`/analytics/accuracy${dateParams}`),
    enabled: tab === "accuracy",
  });

  const { data: roi, isLoading: loadingRoi } = useQuery({
    queryKey: ["analytics-roi", dateParams],
    queryFn: () => apiGet<any>(`/analytics/roi${dateParams}`),
    enabled: tab === "roi",
  });

  const { data: models, isLoading: loadingModels } = useQuery({
    queryKey: ["analytics-models", dateParams],
    queryFn: () => apiGet<any>(`/analytics/model-contribution${dateParams}`),
    enabled: tab === "models",
  });

  const { data: aiPerformance } = useGetAiPerformance();
  const { data: aiReport } = useGetAiReport();

  const { data: clv, isLoading: loadingClv } = useQuery({
    queryKey: ["analytics-clv", dateParams],
    queryFn: () => apiGet<any>(`/analytics/clv${dateParams}`),
    enabled: tab === "clv",
  });

  const { data: validatorLb, isLoading: loadingVLb } = useQuery({
    queryKey: ["analytics-lb-validators", lbSort],
    queryFn: () => apiGet<any>(`/analytics/leaderboard/validators?sort_by=${lbSort}`),
    enabled: tab === "leaderboard",
  });

  const { data: userLb, isLoading: loadingULb } = useQuery({
    queryKey: ["analytics-lb-users", userSort],
    queryFn: () => apiGet<any>(`/analytics/leaderboard/users?sort_by=${userSort}`),
    enabled: tab === "leaderboard",
  });

  const handleExport = () => {
    window.open('/api/exports/analytics/csv', "_blank");
  };

  const hasDates = dateFrom || dateTo;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-mono font-bold uppercase tracking-tight">Analytics Suite</h1>
          <p className="text-muted-foreground font-mono text-sm">Performance intelligence & edge tracking.</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-muted-foreground" />
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="font-mono text-xs h-8 w-36"
            placeholder="From"
          />
          <span className="text-muted-foreground text-xs font-mono">→</span>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="font-mono text-xs h-8 w-36"
            placeholder="To"
          />
          {hasDates && (
            <Button variant="ghost" size="sm" className="font-mono text-xs h-8 px-2 text-muted-foreground"
              onClick={() => { setDateFrom(""); setDateTo(""); }}>
              Clear
            </Button>
          )}
          <Button variant="outline" size="sm" className="font-mono text-xs gap-2 h-8" onClick={handleExport}>
            <Download className="w-3.5 h-3.5" /> Export
          </Button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Predictions" value={summary.total_predictions} icon={Target} />
          <StatCard label="Settled" value={summary.settled} icon={TrendingUp} color="text-primary" />
          <StatCard label="Avg CLV" value={`${(summary.avg_clv * 100).toFixed(2)}%`} icon={BarChart2} color={summary.avg_clv >= 0 ? "text-primary" : "text-destructive"} />
          <StatCard label="Avg Edge" value={`${(summary.avg_edge * 100).toFixed(2)}%`} icon={Brain} color="text-secondary" />
          {summary.total_predictions === 0 && (
            <div className="col-span-full text-center py-4 font-mono text-xs text-muted-foreground border border-border/30 rounded-lg">
              No prediction data for this period. Visit <a href="/matches" className="text-primary underline">Matches</a> to make your first prediction.
            </div>
          )}
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="font-mono text-xs flex-wrap">
          <TabsTrigger value="accuracy">Accuracy</TabsTrigger>
          <TabsTrigger value="roi">ROI & Equity</TabsTrigger>
          <TabsTrigger value="models">Models</TabsTrigger>
          <TabsTrigger value="clv">CLV</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
          <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
        </TabsList>

        {/* ACCURACY */}
        <TabsContent value="accuracy" className="space-y-4 mt-4">
          {loadingAcc ? (
            <div className="text-muted-foreground font-mono text-center py-12">Loading accuracy data...</div>
          ) : accuracy?.total === 0 ? (
            <Card className="bg-card/50 border-muted">
              <CardContent className="py-8 text-center font-mono text-muted-foreground text-sm">
                No settled predictions yet. Accuracy will populate once matches are settled.
              </CardContent>
            </Card>
          ) : accuracy ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-card/50 border-primary/20">
                  <CardHeader><CardTitle className="font-mono text-sm uppercase text-muted-foreground">Overall Accuracy</CardTitle></CardHeader>
                  <CardContent>
                    <div className="text-4xl font-bold font-mono text-primary">
                      {accuracy.overall ? `${(accuracy.overall.accuracy * 100).toFixed(1)}%` : "N/A"}
                    </div>
                    <p className="text-xs text-muted-foreground font-mono mt-1">
                      {accuracy.overall?.correct}/{accuracy.overall?.total} correct
                    </p>
                  </CardContent>
                </Card>
                {["low", "mid", "high"].map((bk) => (
                  <Card key={bk} className="bg-card/50 border-muted/50">
                    <CardHeader><CardTitle className="font-mono text-xs uppercase text-muted-foreground">{bk} Confidence</CardTitle></CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold font-mono">
                        {accuracy.by_confidence?.[bk]?.accuracy != null
                          ? `${(accuracy.by_confidence[bk].accuracy * 100).toFixed(1)}%`
                          : "—"}
                      </div>
                      <p className="text-xs text-muted-foreground font-mono">{accuracy.by_confidence?.[bk]?.total ?? 0} bets</p>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {accuracy.by_league?.length > 0 && (
                <Card className="bg-card/50 border-muted/50">
                  <CardHeader><CardTitle className="font-mono text-sm uppercase">By League</CardTitle></CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={accuracy.by_league} layout="vertical">
                        <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontFamily: "monospace", fontSize: 10 }} />
                        <YAxis type="category" dataKey="league" tick={{ fontFamily: "monospace", fontSize: 10 }} width={100} />
                        <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} contentStyle={{ background: "#0a0a0a", border: "1px solid #1a1a2e", fontFamily: "monospace", fontSize: 11 }} />
                        <Bar dataKey="accuracy" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}

              {accuracy.weekly_trend?.length > 0 && (
                <Card className="bg-card/50 border-muted/50">
                  <CardHeader><CardTitle className="font-mono text-sm uppercase">Weekly Trend</CardTitle></CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={180}>
                      <LineChart data={accuracy.weekly_trend}>
                        <XAxis dataKey="week" tick={{ fontFamily: "monospace", fontSize: 10 }} />
                        <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontFamily: "monospace", fontSize: 10 }} />
                        <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} contentStyle={{ background: "#0a0a0a", border: "1px solid #1a1a2e", fontFamily: "monospace", fontSize: 11 }} />
                        <Line type="monotone" dataKey="accuracy" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}
            </>
          ) : null}
        </TabsContent>

        {/* ROI */}
        <TabsContent value="roi" className="space-y-4 mt-4">
          {loadingRoi ? (
            <div className="text-muted-foreground font-mono text-center py-12">Loading ROI data...</div>
          ) : roi?.total === 0 || !roi ? (
            <Card className="bg-card/50 border-muted">
              <CardContent className="py-8 text-center font-mono text-muted-foreground text-sm">
                No settled bets yet. ROI tracking begins after first settlement.
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "ROI", value: `${(roi.summary.roi * 100).toFixed(2)}%`, color: roi.summary.roi >= 0 ? "text-primary" : "text-destructive" },
                  { label: "Win Rate", value: `${(roi.summary.win_rate * 100).toFixed(1)}%`, color: "text-foreground" },
                  { label: "Total Profit", value: `${roi.summary.total_profit >= 0 ? "+" : ""}${roi.summary.total_profit.toFixed(2)}`, color: roi.summary.total_profit >= 0 ? "text-primary" : "text-destructive" },
                  { label: "Max Drawdown", value: `${(roi.summary.max_drawdown * 100).toFixed(1)}%`, color: "text-destructive" },
                ].map((s) => (
                  <Card key={s.label} className="bg-card/50 border-muted/50">
                    <CardHeader className="pb-1"><CardTitle className="text-xs font-mono uppercase text-muted-foreground">{s.label}</CardTitle></CardHeader>
                    <CardContent><div className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</div></CardContent>
                  </Card>
                ))}
              </div>
              {roi.equity_curve?.length > 0 && (
                <Card className="bg-card/50 border-muted/50">
                  <CardHeader><CardTitle className="font-mono text-sm uppercase">Equity Curve</CardTitle></CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={roi.equity_curve}>
                        <XAxis dataKey="match" hide />
                        <YAxis tick={{ fontFamily: "monospace", fontSize: 10 }} />
                        <Tooltip contentStyle={{ background: "#0a0a0a", border: "1px solid #1a1a2e", fontFamily: "monospace", fontSize: 11 }} />
                        <ReferenceLine y={roi.equity_curve[0]?.bankroll || 1000} stroke="#333" strokeDasharray="3 3" />
                        <Line type="monotone" dataKey="bankroll" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>

        {/* MODELS */}
        <TabsContent value="models" className="space-y-4 mt-4">
          {loadingModels ? (
            <div className="text-muted-foreground font-mono text-center py-12">Loading model data...</div>
          ) : (
            <div className="space-y-4">
              <Card className="bg-card/50 border-muted/50">
                <CardHeader>
                  <CardTitle className="font-mono text-sm uppercase">12-Model Ensemble Breakdown</CardTitle>
                  {models?.data_source && (
                    <p className="text-xs text-muted-foreground font-mono">
                      Source: {models.data_source === "estimated" ? "estimated from prediction metadata" : "model insights"}
                    </p>
                  )}
                </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="min-w-[720px] w-full text-xs font-mono">
                    <thead>
                      <tr className="border-b border-muted/50">
                        {["Model", "Appearances", "Fail Rate", "Avg Weight", "Avg Conf", "Accuracy"].map((h) => (
                          <th key={h} className="text-left py-2 pr-4 text-muted-foreground uppercase">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {models?.models?.map((m: any) => (
                        <tr key={m.model_name} className="border-b border-muted/20 hover:bg-muted/10 transition-colors">
                          <td className="py-2 pr-4 text-primary font-bold">{m.model_name}</td>
                          <td className="py-2 pr-4">{m.appearances}</td>
                          <td className="py-2 pr-4 text-muted-foreground">
                            {m.failures > 0 ? <span className="text-destructive">{m.failures}</span> : "0"}
                          </td>
                          <td className="py-2 pr-4">{m.avg_weight?.toFixed(3) ?? "—"}</td>
                          <td className="py-2 pr-4">{m.avg_confidence != null ? `${(m.avg_confidence * 100).toFixed(1)}%` : "—"}</td>
                          <td className="py-2 pr-4">
                            {m.accuracy != null
                              ? <span className={m.accuracy > 0.6 ? "text-primary" : m.accuracy > 0.5 ? "text-secondary" : "text-destructive"}>
                                  {(m.accuracy * 100).toFixed(1)}%
                                </span>
                              : <span className="text-muted-foreground">—</span>
                            }
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!loadingModels && (!models?.models || models.models.length === 0) && (
                    <div className="text-center py-8 text-muted-foreground font-mono text-sm">
                      No model data yet. Run predictions to populate the model breakdown.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/50 border-muted/50">
              <CardHeader>
                <CardTitle className="font-mono text-sm uppercase">AI Source Performance</CardTitle>
                <p className="text-xs text-muted-foreground font-mono">
                  Performance metrics from external AI prediction sources
                </p>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="min-w-[720px] w-full text-xs font-mono">
                    <thead>
                      <tr className="border-b border-muted/50">
                        {["Source", "Sample Size", "Accuracy", "Avg Confidence", "Last Updated"].map((h) => (
                          <th key={h} className="text-left py-2 pr-4 text-muted-foreground uppercase">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {aiPerformance && Object.entries(aiPerformance).map(([source, data]: [string, any]) => (
                        <tr key={source} className="border-b border-muted/20 hover:bg-muted/10 transition-colors">
                          <td className="py-2 pr-4 text-primary font-bold">{source}</td>
                          <td className="py-2 pr-4">{data.sample_size || 0}</td>
                          <td className="py-2 pr-4">
                            {data.accuracy != null
                              ? <span className={data.accuracy > 0.6 ? "text-primary" : data.accuracy > 0.5 ? "text-secondary" : "text-destructive"}>
                                  {(data.accuracy * 100).toFixed(1)}%
                                </span>
                              : <span className="text-muted-foreground">—</span>
                            }
                          </td>
                          <td className="py-2 pr-4">{data.avg_confidence != null ? `${(data.avg_confidence * 100).toFixed(1)}%` : "—"}</td>
                          <td className="py-2 pr-4 text-muted-foreground">
                            {data.last_updated ? new Date(data.last_updated).toLocaleDateString() : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!aiPerformance || Object.keys(aiPerformance).length === 0 && (
                    <div className="text-center py-8 text-muted-foreground font-mono text-sm">
                      No AI performance data yet.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
            </div>
          )}
        </TabsContent>

        {/* CLV */}
        <TabsContent value="clv" className="space-y-4 mt-4">
          {loadingClv ? (
            <div className="text-muted-foreground font-mono text-center py-12">Loading CLV data...</div>
          ) : clv?.total === 0 || !clv || clv?.message ? (
            <Card className="bg-card/50 border-muted">
              <CardContent className="py-8 text-center font-mono text-muted-foreground text-sm">
                No CLV data yet. Closing line values are tracked after market close.
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Avg CLV", value: `${(clv.summary.avg_clv * 100).toFixed(2)}%`, color: clv.summary.avg_clv > 0 ? "text-primary" : "text-destructive" },
                  { label: "Positive CLV%", value: `${(clv.summary.positive_clv_pct * 100).toFixed(1)}%`, color: "text-foreground" },
                  { label: "Max CLV", value: `+${(clv.summary.max_clv * 100).toFixed(2)}%`, color: "text-primary" },
                  { label: "Min CLV", value: `${(clv.summary.min_clv * 100).toFixed(2)}%`, color: "text-destructive" },
                ].map((s) => (
                  <Card key={s.label} className="bg-card/50 border-muted/50">
                    <CardHeader className="pb-1"><CardTitle className="text-xs font-mono uppercase text-muted-foreground">{s.label}</CardTitle></CardHeader>
                    <CardContent><div className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</div></CardContent>
                  </Card>
                ))}
              </div>
              <Card className="bg-card/50 border-muted/50">
                <CardHeader><CardTitle className="font-mono text-sm uppercase">CLV Series</CardTitle></CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={clv.series}>
                      <XAxis dataKey="match" hide />
                      <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontFamily: "monospace", fontSize: 10 }} />
                      <Tooltip contentStyle={{ background: "#0a0a0a", border: "1px solid #1a1a2e", fontFamily: "monospace", fontSize: 11 }} />
                      <ReferenceLine y={0} stroke="#444" />
                      <Line type="monotone" dataKey="clv" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* SYSTEM */}
        <TabsContent value="system" className="space-y-4 mt-4">
          {!system ? (
            <div className="text-muted-foreground font-mono text-center py-12">Loading system metrics...</div>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Total Predictions" value={system.predictions?.total ?? 0} icon={Target} />
                <StatCard label="Accuracy" value={`${((system.predictions?.accuracy ?? 0) * 100).toFixed(1)}%`} icon={TrendingUp} color="text-primary" />
                <StatCard label="Active Matches" value={system.matches?.active ?? 0} icon={BarChart2} />
                <StatCard label="VIT Price" value={`$${Number(system.economy?.vitcoin_price_usd ?? 0.001).toFixed(6)}`} icon={Brain} color="text-secondary" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-card/50 border-muted/50">
                  <CardHeader className="pb-2">
                    <CardTitle className="font-mono text-sm uppercase flex items-center gap-2">
                      <Users className="w-4 h-4 text-primary" /> Users
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 font-mono text-sm">
                    {[
                      { label: "Total Users", value: system.users?.total ?? 0 },
                      { label: "Active (30d)", value: system.users?.active_30d ?? 0 },
                      { label: "Active Validators", value: system.users?.validators ?? 0 },
                    ].map(({ label, value }) => (
                      <div key={label} className="flex justify-between py-1 border-b border-muted/20">
                        <span className="text-muted-foreground text-xs uppercase">{label}</span>
                        <span className="font-bold">{value}</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card className="bg-card/50 border-muted/50">
                  <CardHeader className="pb-2">
                    <CardTitle className="font-mono text-sm uppercase flex items-center gap-2">
                      <Globe className="w-4 h-4 text-primary" /> Economy
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 font-mono text-sm">
                    {[
                      { label: "Total Staked (VIT)", value: Number(system.economy?.total_staked_vit ?? 0).toLocaleString() },
                      { label: "Platform Volume", value: `$${Number(system.economy?.platform_volume ?? 0).toFixed(2)}` },
                      { label: "Total Profit", value: `$${Number(system.economy?.total_profit ?? 0).toFixed(2)}` },
                    ].map(({ label, value }) => (
                      <div key={label} className="flex justify-between py-1 border-b border-muted/20">
                        <span className="text-muted-foreground text-xs uppercase">{label}</span>
                        <span className="font-bold">{value}</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card className="bg-card/50 border-muted/50">
                  <CardHeader className="pb-2">
                    <CardTitle className="font-mono text-sm uppercase flex items-center gap-2">
                      <Target className="w-4 h-4 text-primary" /> Matches
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 font-mono text-sm">
                    {[
                      { label: "Total Matches", value: system.matches?.total ?? 0 },
                      { label: "Settled", value: system.matches?.settled ?? 0 },
                      { label: "Predictions (Settled)", value: system.predictions?.settled ?? 0 },
                    ].map(({ label, value }) => (
                      <div key={label} className="flex justify-between py-1 border-b border-muted/20">
                        <span className="text-muted-foreground text-xs uppercase">{label}</span>
                        <span className="font-bold">{value}</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>

        {/* LEADERBOARD */}
        <TabsContent value="leaderboard" className="space-y-6 mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Validator Leaderboard */}
            <Card className="bg-card/50 border-muted/50">
              <CardHeader className="border-b border-muted/30 pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="font-mono text-sm uppercase flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-primary" /> Validators
                  </CardTitle>
                  <div className="flex gap-1">
                    {(["trust_score", "accuracy", "stake"] as const).map((s) => (
                      <Button key={s} variant={lbSort === s ? "default" : "ghost"} size="sm"
                        className="font-mono text-[10px] h-6 px-2 uppercase"
                        onClick={() => setLbSort(s)}>
                        {s === "trust_score" ? "Trust" : s === "accuracy" ? "Acc" : "Stake"}
                      </Button>
                    ))}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {loadingVLb ? (
                  <div className="py-8 text-center font-mono text-muted-foreground text-sm">Loading...</div>
                ) : (
                  <div className="divide-y divide-muted/20">
                    {validatorLb?.leaderboard?.slice(0, 10).map((v: any) => (
                      <div key={v.username} className="flex items-center justify-between px-4 py-3 hover:bg-muted/10 transition-colors">
                        <div className="flex items-center gap-3">
                          <RankBadge rank={v.rank} />
                          <div>
                            <div className="font-bold font-mono text-sm">{v.username}</div>
                            <div className="text-xs text-muted-foreground font-mono flex gap-2">
                              <span>{(v.accuracy_rate * 100).toFixed(1)}% ACC</span>
                              <span>·</span>
                              <span>{v.total_predictions} preds</span>
                            </div>
                          </div>
                        </div>
                        <div className="text-right font-mono">
                          <div className="font-bold text-sm text-primary">
                            {(v.trust_score * 100).toFixed(0)}/100
                          </div>
                          <div className="text-[10px] text-muted-foreground uppercase">Trust</div>
                        </div>
                      </div>
                    ))}
                    {(!validatorLb?.leaderboard?.length) && (
                      <div className="py-8 text-center font-mono text-muted-foreground text-sm">
                        No active validators yet.
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* User Leaderboard */}
            <Card className="bg-card/50 border-muted/50">
              <CardHeader className="border-b border-muted/30 pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="font-mono text-sm uppercase flex items-center gap-2">
                    <Trophy className="w-4 h-4 text-secondary" /> Top Stakers
                  </CardTitle>
                  <div className="flex gap-1">
                    {(["roi", "profit", "stake", "win_rate"] as const).map((s) => (
                      <Button key={s} variant={userSort === s ? "default" : "ghost"} size="sm"
                        className="font-mono text-[10px] h-6 px-2 uppercase"
                        onClick={() => setUserSort(s)}
                        data-testid={`button-userlb-sort-${s}`}>
                        {s === "roi" ? "ROI" : s === "profit" ? "Profit" : s === "stake" ? "Stake" : "W/R"}
                      </Button>
                    ))}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {loadingULb ? (
                  <div className="py-8 text-center font-mono text-muted-foreground text-sm">Loading...</div>
                ) : (
                  <div className="divide-y divide-muted/20">
                    {userLb?.leaderboard?.slice(0, 10).map((u: any) => {
                      const totalBets = Number(u.total_bets ?? u.settled ?? u.predictions ?? 0);
                      const winRate = Number.isFinite(Number(u.win_rate)) ? Number(u.win_rate) : 0;
                      const roi = Number.isFinite(Number(u.roi)) ? Number(u.roi) : 0;
                      const profit = Number.isFinite(Number(u.profit)) ? Number(u.profit) : 0;
                      const stake = Number.isFinite(Number(u.total_staked)) ? Number(u.total_staked) : 0;
                      const hasActivity = totalBets > 0;

                      let primaryLabel = "ROI";
                      let primaryValue = "—";
                      let primaryClass = "text-muted-foreground";
                      if (userSort === "roi") {
                        primaryLabel = "ROI";
                        if (hasActivity) {
                          primaryValue = `${roi >= 0 ? "+" : ""}${(roi * 100).toFixed(1)}%`;
                          primaryClass = roi >= 0 ? "text-primary" : "text-destructive";
                        }
                      } else if (userSort === "profit") {
                        primaryLabel = "Profit";
                        if (hasActivity) {
                          primaryValue = `${profit >= 0 ? "+" : ""}${profit.toFixed(2)}`;
                          primaryClass = profit >= 0 ? "text-primary" : "text-destructive";
                        }
                      } else if (userSort === "stake") {
                        primaryLabel = "Stake";
                        if (hasActivity) {
                          primaryValue = stake.toFixed(2);
                          primaryClass = "text-secondary";
                        }
                      } else {
                        primaryLabel = "W/R";
                        if (hasActivity) {
                          primaryValue = `${(winRate * 100).toFixed(1)}%`;
                          primaryClass = winRate >= 0.5 ? "text-primary" : "text-destructive";
                        }
                      }

                      return (
                        <div key={u.username} className="flex items-center justify-between px-4 py-3 hover:bg-muted/10 transition-colors" data-testid={`row-userlb-${u.username}`}>
                          <div className="flex items-center gap-3">
                            <RankBadge rank={u.rank} />
                            <div>
                              <div className="font-bold font-mono text-sm">{u.username}</div>
                              <div className="text-xs text-muted-foreground font-mono flex gap-2">
                                <span>{totalBets} {totalBets === 1 ? "bet" : "bets"}</span>
                                <span>·</span>
                                {hasActivity ? (
                                  <span className={winRate >= 0.5 ? "text-primary" : "text-destructive"}>
                                    {(winRate * 100).toFixed(1)}% W/R
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground">No settled bets</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="text-right font-mono">
                            <div className={`font-bold text-sm ${primaryClass}`} data-testid={`text-userlb-primary-${u.username}`}>
                              {primaryValue}
                            </div>
                            <div className="text-[10px] text-muted-foreground uppercase">{primaryLabel}</div>
                          </div>
                        </div>
                      );
                    })}
                    {(!userLb?.leaderboard?.length) && (
                      <div className="py-8 text-center font-mono text-muted-foreground text-sm">
                        No staking activity yet.
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
