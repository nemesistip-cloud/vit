import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from "recharts";
import {
  FlaskConical, TrendingUp, Sprout, Zap, SlidersHorizontal,
  RefreshCw, ChevronDown, ChevronUp, Info,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

// ─── API fetch helper ────────────────────────────────────────────────────────
const API = "/api/quant";

async function fetchJson(path: string, token: string) {
  const r = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

// ─── Stat chip ───────────────────────────────────────────────────────────────
function Chip({
  label, value, sub, positive,
}: { label: string; value: string; sub?: string; positive?: boolean }) {
  const colour =
    positive === undefined
      ? "text-foreground"
      : positive
      ? "text-emerald-400"
      : "text-rose-400";
  return (
    <div className="flex flex-col gap-0.5 min-w-[80px]">
      <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <span className={`text-lg font-mono font-bold leading-none ${colour}`}>{value}</span>
      {sub && <span className="text-[10px] font-mono text-muted-foreground">{sub}</span>}
    </div>
  );
}

// ─── Panel wrapper ───────────────────────────────────────────────────────────
function Panel({
  title, icon: Icon, children, className = "",
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-border bg-card/60  ${className}`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border/60">
        <Icon className="w-4 h-4 text-primary" />
        <span className="font-mono text-sm font-semibold tracking-tight">{title}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// ─── Loading spinner ─────────────────────────────────────────────────────────
function Loader() {
  return (
    <div className="flex items-center justify-center gap-2 text-muted-foreground py-6">
      <RefreshCw className="w-4 h-4 animate-spin" />
      <span className="font-mono text-xs">Computing…</span>
    </div>
  );
}

function Err({ msg }: { msg: string }) {
  return (
    <div className="flex items-center justify-center py-6 text-rose-400 font-mono text-xs text-center">
      {msg}
    </div>
  );
}

// ─── Custom tooltip for recharts ─────────────────────────────────────────────
function QuantTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-background border border-border rounded px-2 py-1 text-xs font-mono ">
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SECTION 1 — Backtester
// ════════════════════════════════════════════════════════════════════════════
function BacktestPanel({ token }: { token: string }) {
  const [bankroll, setBankroll] = useState(1000);
  const [flatPct, setFlatPct] = useState(0.01);
  const [trigger, setTrigger] = useState(0);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["quant-backtest", bankroll, flatPct, trigger],
    queryFn: () =>
      fetchJson(`${API}/backtest?initial_bankroll=${bankroll}&flat_pct=${flatPct}`, token),
    staleTime: 60_000,
  });

  const flatHistory  = data?.flat?.history  ?? [];
  const kellyHistory = data?.kelly?.history ?? [];
  const chartData = flatHistory.length > 0
    ? flatHistory
        .map((v: number, i: number) => ({
          bet: i,
          flat: v,
          kelly: kellyHistory[i] ?? null,
        }))
        .filter((_: any, i: number) => i % Math.max(1, Math.floor(flatHistory.length / 80)) === 0)
    : [];

  return (
    <Panel title="Strategy Backtester" icon={FlaskConical}>
      {/* Controls */}
      <div className="flex flex-wrap gap-4 mb-4">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">Bankroll ($)</span>
          <input
            type="number"
            value={bankroll}
            min={100}
            max={1_000_000}
            step={100}
            onChange={(e) => setBankroll(Number(e.target.value))}
            className="w-28 px-2 py-1 text-xs font-mono rounded border border-border bg-background"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">Flat stake %</span>
          <input
            type="number"
            value={flatPct}
            min={0.001}
            max={0.25}
            step={0.005}
            onChange={(e) => setFlatPct(Number(e.target.value))}
            className="w-24 px-2 py-1 text-xs font-mono rounded border border-border bg-background"
          />
        </label>
        <div className="flex items-end">
          <Button size="sm" onClick={() => setTrigger((t) => t + 1)} className="font-mono text-xs h-7">
            Run
          </Button>
        </div>
      </div>

      {isLoading && <Loader />}
      {isError && <Err msg="Failed to load backtest" />}
      {data && !data.error && (
        <>
          {/* Stats row */}
          <div className="flex flex-wrap gap-6 mb-4 pb-3 border-b border-border/50">
            <Chip label="Signals" value={data.count} />
            <Chip label="Win rate" value={`${data.win_rate_pct}%`} />
            <Chip
              label="Flat ROI"
              value={`${data.flat.roi_pct > 0 ? "+" : ""}${data.flat.roi_pct}%`}
              sub={`$${data.flat.final_bankroll.toLocaleString()}`}
              positive={data.flat.roi_pct > 0}
            />
            <Chip
              label="Kelly ROI"
              value={`${data.kelly.roi_pct > 0 ? "+" : ""}${data.kelly.roi_pct}%`}
              sub={`$${data.kelly.final_bankroll.toLocaleString()}`}
              positive={data.kelly.roi_pct > 0}
            />
            <Chip
              label="Flat DD"
              value={`${data.flat.max_drawdown_pct}%`}
              positive={data.flat.max_drawdown_pct < 15}
            />
            <Chip
              label="Kelly DD"
              value={`${data.kelly.max_drawdown_pct}%`}
              positive={data.kelly.max_drawdown_pct < 15}
            />
          </div>

          {/* Chart */}
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <XAxis
                dataKey="bet"
                tick={{ fontSize: 9, fontFamily: "monospace" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 9, fontFamily: "monospace" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `$${v.toFixed(0)}`}
                width={55}
              />
              <Tooltip content={<QuantTooltip />} />
              <ReferenceLine y={bankroll} stroke="#6b7280" strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="flat"
                stroke="#60a5fa"
                dot={false}
                strokeWidth={1.5}
                name="Flat"
              />
              <Line
                type="monotone"
                dataKey="kelly"
                stroke="#34d399"
                dot={false}
                strokeWidth={1.5}
                name="Kelly"
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-1 justify-center">
            <span className="text-[10px] font-mono text-blue-400">── Flat staking</span>
            <span className="text-[10px] font-mono text-emerald-400">── Kelly staking</span>
          </div>
        </>
      )}
      {data?.error && <Err msg={data.error} />}
    </Panel>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SECTION 2 — Monte Carlo
// ════════════════════════════════════════════════════════════════════════════
function MonteCarloPanel({ token }: { token: string }) {
  const [trials, setTrials] = useState(500);
  const [bets, setBets] = useState(100);
  const [staking, setStaking] = useState<"flat" | "kelly">("kelly");
  const [bankroll, setBankroll] = useState(1000);
  const [trigger, setTrigger] = useState(0);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["quant-mc", trials, bets, staking, bankroll, trigger],
    queryFn: () =>
      fetchJson(
        `${API}/monte-carlo?trials=${trials}&bets_per_trial=${bets}&staking=${staking}&initial_bankroll=${bankroll}`,
        token
      ),
    staleTime: 60_000,
  });

  const distData = (() => {
    if (!data?.distribution) return [];
    const dist: number[] = data.distribution;
    const min = dist[0];
    const max = dist[dist.length - 1];
    const buckets = 30;
    const step = (max - min) / buckets || 1;
    const bins: { range: string; count: number }[] = Array.from({ length: buckets }, (_, i) => ({
      range: `$${(min + i * step).toFixed(0)}`,
      count: 0,
    }));
    dist.forEach((v) => {
      const idx = Math.min(Math.floor((v - min) / step), buckets - 1);
      bins[idx].count++;
    });
    return bins;
  })();

  const pcts = data?.percentiles;

  return (
    <Panel title="Monte Carlo Simulator" icon={FlaskConical}>
      <div className="flex flex-wrap gap-4 mb-4">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">Trials</span>
          <select
            value={trials}
            onChange={(e) => setTrials(Number(e.target.value))}
            className="w-20 px-2 py-1 text-xs font-mono rounded border border-border bg-background"
          >
            {[100, 250, 500, 1000, 2000].map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">Signals/trial</span>
          <select
            value={bets}
            onChange={(e) => setBets(Number(e.target.value))}
            className="w-20 px-2 py-1 text-xs font-mono rounded border border-border bg-background"
          >
            {[50, 100, 200, 500].map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">Staking</span>
          <select
            value={staking}
            onChange={(e) => setStaking(e.target.value as "flat" | "kelly")}
            className="w-20 px-2 py-1 text-xs font-mono rounded border border-border bg-background"
          >
            <option value="kelly">Kelly</option>
            <option value="flat">Flat</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">Bankroll</span>
          <input
            type="number"
            value={bankroll}
            min={100}
            step={100}
            onChange={(e) => setBankroll(Number(e.target.value))}
            className="w-24 px-2 py-1 text-xs font-mono rounded border border-border bg-background"
          />
        </label>
        <div className="flex items-end">
          <Button size="sm" onClick={() => setTrigger((t) => t + 1)} className="font-mono text-xs h-7">
            Simulate
          </Button>
        </div>
      </div>

      {isLoading && <Loader />}
      {isError && <Err msg="Simulation failed" />}
      {data && !data.error && (
        <>
          <div className="flex flex-wrap gap-6 mb-4 pb-3 border-b border-border/50">
            <Chip label="Ruin risk" value={`${data.ruin_probability_pct}%`} positive={data.ruin_probability_pct < 5} />
            <Chip label="Profit prob" value={`${data.profit_probability_pct}%`} positive={data.profit_probability_pct > 50} />
            <Chip label="Median ROI" value={`${data.median_roi_pct > 0 ? "+" : ""}${data.median_roi_pct}%`} positive={data.median_roi_pct > 0} />
            <Chip label="Median ($)" value={`$${pcts?.p50?.toFixed(0) ?? "—"}`} />
            <Chip label="p5 floor" value={`$${pcts?.p5?.toFixed(0) ?? "—"}`} positive={(pcts?.p5 ?? 0) > bankroll * 0.5} />
            <Chip label="p95 ceil" value={`$${pcts?.p95?.toFixed(0) ?? "—"}`} positive />
          </div>

          {/* Percentile bar */}
          <div className="mb-4">
            <div className="text-[10px] font-mono uppercase text-muted-foreground mb-1">Distribution percentiles</div>
            <div className="relative h-6 rounded bg-muted/30 overflow-hidden">
              {pcts && (() => {
                const total = pcts.p95 - pcts.p5 || 1;
                const toX = (v: number) => `${Math.max(0, Math.min(100, ((v - pcts.p5) / total) * 100))}%`;
                return (
                  <>
                    <div className="absolute inset-y-0 bg-primary/20 rounded"
                      style={{ left: toX(pcts.p25), right: `${100 - parseFloat(toX(pcts.p75))}%` }} />
                    <div className="absolute inset-y-0 w-0.5 bg-primary" style={{ left: toX(pcts.p50) }} />
                    {[pcts.p5, pcts.p25, pcts.p50, pcts.p75, pcts.p95].map((v, i) => (
                      <span key={i} className="absolute top-0.5 text-[9px] font-mono -translate-x-1/2 text-muted-foreground"
                        style={{ left: toX(v) }}>
                        ${v.toFixed(0)}
                      </span>
                    ))}
                  </>
                );
              })()}
            </div>
            <div className="flex justify-between text-[9px] font-mono text-muted-foreground/60 mt-0.5">
              <span>p5</span><span>p25</span><span>p50</span><span>p75</span><span>p95</span>
            </div>
          </div>

          {/* Histogram */}
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={distData} barCategoryGap="2%">
              <XAxis dataKey="range" tick={false} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 9, fontFamily: "monospace" }} axisLine={false} tickLine={false} width={30} />
              <Tooltip content={<QuantTooltip />} />
              <Bar dataKey="count" name="Trials" radius={[2, 2, 0, 0]}>
                {distData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={
                      parseFloat(entry.range.replace("$", "")) >= bankroll
                        ? "#34d399"
                        : "#f87171"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-1 justify-center">
            <span className="text-[10px] font-mono text-emerald-400">■ Profitable</span>
            <span className="text-[10px] font-mono text-rose-400">■ Loss</span>
          </div>
        </>
      )}
      {data?.error && <Err msg={data.error} />}
    </Panel>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SECTION 3 — EV Scanner
// ════════════════════════════════════════════════════════════════════════════
function EVScannerPanel({ token }: { token: string }) {
  const [minEv, setMinEv] = useState(0);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["quant-ev", minEv],
    queryFn: () => fetchJson(`${API}/ev-scanner?min_ev=${minEv}&limit=20`, token),
    staleTime: 30_000,
  });

  const signals: any[] = data?.signals ?? [];

  return (
    <Panel title="EV Scanner" icon={Zap}>
      <div className="flex flex-wrap gap-4 mb-3 items-end">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">Min EV</span>
          <input
            type="number"
            value={minEv}
            step={0.01}
            onChange={(e) => setMinEv(Number(e.target.value))}
            className="w-20 px-2 py-1 text-xs font-mono rounded border border-border bg-background"
          />
        </label>
        <Button size="sm" variant="outline" onClick={() => refetch()} className="font-mono text-xs h-7">
          <RefreshCw className="w-3 h-3 mr-1" /> Refresh
        </Button>
        {data && (
          <span className="text-[10px] font-mono text-muted-foreground">
            {data.count} signal{data.count !== 1 ? "s" : ""} ·{" "}
            <span className="text-primary">{data.mode === "live_upcoming" ? "LIVE" : "HISTORICAL"}</span>
          </span>
        )}
      </div>

      {isLoading && <Loader />}
      {isError && <Err msg="EV scan failed" />}

      {!isLoading && !isError && (
        <div className="overflow-auto max-h-72">
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-[10px] uppercase tracking-widest text-muted-foreground border-b border-border/50">
                <th className="text-left pb-1 pr-3">Match</th>
                <th className="text-left pb-1 pr-3">Side</th>
                <th className="text-right pb-1 pr-3">Model P</th>
                <th className="text-right pb-1 pr-3">Odds</th>
                <th className="text-right pb-1 pr-3">Edge</th>
                <th className="text-right pb-1">EV</th>
              </tr>
            </thead>
            <tbody>
              {signals.length === 0 && (
                <tr>
                  <td colSpan={6} className="pt-4 text-center text-muted-foreground text-xs">
                    No signals at this threshold
                  </td>
                </tr>
              )}
              {signals.map((s, i) => (
                <tr key={i} className="border-b border-border/20 hover:bg-muted/20 transition-colors">
                  <td className="py-1 pr-3 truncate max-w-[150px]">
                    {s.home_team} v {s.away_team}
                  </td>
                  <td className="py-1 pr-3">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-bold ${
                        s.side === "home"
                          ? "bg-blue-500/20 text-blue-400"
                          : s.side === "away"
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-slate-500/20 text-slate-400"
                      }`}
                    >
                      {s.side}
                    </span>
                  </td>
                  <td className="py-1 pr-3 text-right">{(s.model_prob * 100).toFixed(1)}%</td>
                  <td className="py-1 pr-3 text-right">{s.market_odds}</td>
                  <td className={`py-1 pr-3 text-right ${s.edge_pct > 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {s.edge_pct > 0 ? "+" : ""}{s.edge_pct > 0 ? "▲" : "▼"}{s.edge_pct}%
                  </td>
                  <td className={`py-1 text-right font-bold ${s.ev > 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {s.ev > 0 ? "+" : ""}{s.ev}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SECTION 4 — Strategy Optimiser
// ════════════════════════════════════════════════════════════════════════════
function StrategyPanel({ token }: { token: string }) {
  const [minSamples, setMinSamples] = useState(5);
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["quant-strategy", minSamples],
    queryFn: () => fetchJson(`${API}/strategy-optimizer?min_samples=${minSamples}`, token),
    staleTime: 60_000,
  });

  const strategies: any[] = data?.strategies ?? [];

  return (
    <Panel title="Strategy Optimiser" icon={SlidersHorizontal}>
      <div className="flex flex-wrap gap-4 mb-3 items-end">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">Min samples</span>
          <select
            value={minSamples}
            onChange={(e) => setMinSamples(Number(e.target.value))}
            className="w-20 px-2 py-1 text-xs font-mono rounded border border-border bg-background"
          >
            {[3, 5, 10, 20].map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
        {data && (
          <span className="text-[10px] font-mono text-muted-foreground">
            {data.total_predictions} predictions · {strategies.length} strategies tested
          </span>
        )}
      </div>

      {isLoading && <Loader />}
      {isError && <Err msg="Strategy analytics failed" />}
      {!isLoading && !isError && data?.error && <Err msg={data.error} />}

      {!isLoading && !isError && !data?.error && (
        <div className="space-y-1 max-h-80 overflow-auto">
          {strategies.map((s, i) => {
            const isOpen = expanded === s.name;
            const roiColor =
              s.roi_pct > 5
                ? "text-emerald-400"
                : s.roi_pct > 0
                ? "text-sky-400"
                : "text-rose-400";
            return (
              <div
                key={i}
                className={`rounded border transition-colors ${
                  s.is_best
                    ? "border-primary/40 bg-primary/5"
                    : "border-border/40 bg-muted/10"
                }`}
              >
                <button
                  className="w-full flex items-center justify-between px-3 py-2 text-left"
                  onClick={() => setExpanded(isOpen ? null : s.name)}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {s.is_best && (
                      <span className="text-[9px] font-mono bg-primary text-primary-foreground px-1.5 py-0.5 rounded uppercase tracking-wide flex-shrink-0">
                        Best
                      </span>
                    )}
                    <span className="text-xs font-mono truncate">{s.name}</span>
                  </div>
                  <div className="flex items-center gap-4 flex-shrink-0 ml-2">
                    <span className={`text-xs font-mono font-bold ${roiColor}`}>
                      {s.roi_pct > 0 ? "+" : ""}{s.roi_pct}% ROI
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground">{s.count} bets</span>
                    {isOpen ? (
                      <ChevronUp className="w-3 h-3 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="w-3 h-3 text-muted-foreground" />
                    )}
                  </div>
                </button>
                {isOpen && (
                  <div className="px-3 pb-3 pt-0 flex flex-wrap gap-4 border-t border-border/30">
                    <Chip label="Win rate" value={`${s.win_rate_pct}%`} positive={s.win_rate_pct > 50} />
                    <Chip label="Signals" value={String(s.count)} />
                    <Chip
                      label="Net profit"
                      value={`${s.total_profit > 0 ? "+" : ""}${s.total_profit.toFixed(4)}`}
                      positive={s.total_profit > 0}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ════════════════════════════════════════════════════════════════════════════

// ════════════════════════════════════════════════════════════════════════════
// SECTION 5 — Strategy Vaults (Yield Farming)
// ════════════════════════════════════════════════════════════════════════════
function VaultPanel({ token }: { token: string }) {
  const { data: vaults, isLoading, refetch } = useQuery({
    queryKey: ["quant-vaults"],
    queryFn: () => fetchJson(`${API}/vaults`, token),
    staleTime: 60_000,
  });

  const [staking, setStaking] = useState<number | null>(null);
  const [harvesting, setHarvesting] = useState<number | null>(null);

  const handleStake = async (vaultId: number) => {
    const amount = prompt("Enter amount of VIT to stake:", "100");
    if (!amount || isNaN(Number(amount))) return;

    setStaking(vaultId);
    try {
      await fetchJson(`${API}/vaults/stake?vault_id=${vaultId}&amount=${amount}`, token, { method: "POST" });
      refetch();
      alert("Successfully staked into vault!");
    } catch (e: any) {
      alert(e.message);
    } finally {
      setStaking(null);
    }
  };

  const handleHarvest = async (vaultId: number) => {
    setHarvesting(vaultId);
    try {
      const res = await fetchJson(`${API}/vaults/harvest?vault_id=${vaultId}`, token, { method: "POST" });
      refetch();
      alert(`Harvested ${res.amount} VIT from strategy yield!`);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setHarvesting(null);
    }
  };

  return (
    <Panel title="Strategy Vaults (Farming)" icon={Sprout}>
      <div className="space-y-3">
        {isLoading && <Loader />}
        {vaults?.map((v: any) => (
          <div key={v.id} className="p-3 rounded-lg border border-border bg-card/50 flex flex-col gap-3">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-sm font-bold font-mono">{v.name}</h3>
                <p className="text-[10px] text-muted-foreground font-mono">{v.description || "Automated strategy execution vault."}</p>
              </div>
              <div className="text-right">
                <div className="text-emerald-400 text-sm font-bold font-mono">+{v.historical_roi_pct}% APY</div>
                <div className="text-[10px] text-muted-foreground font-mono">TVL: {v.total_staked} VIT</div>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => handleStake(v.id)}
                disabled={staking === v.id}
                className="flex-1 px-3 py-1.5 bg-primary text-primary-foreground text-xs font-bold font-mono rounded hover:opacity-90 disabled:opacity-50"
              >
                {staking === v.id ? "STAKING..." : "STAKE VIT"}
              </button>
              <button
                onClick={() => handleHarvest(v.id)}
                disabled={harvesting === v.id}
                className="px-3 py-1.5 border border-primary/30 text-primary text-xs font-bold font-mono rounded hover:bg-primary/5 disabled:opacity-50"
              >
                {harvesting === v.id ? "..." : "HARVEST"}
              </button>
            </div>
          </div>
        ))}
        {vaults?.length === 0 && <p className="text-center py-4 text-xs text-muted-foreground font-mono">No vaults active.</p>}
      </div>
    </Panel>
  );
}

export default function ResearchPage() {
  const { user } = useAuth();
  const token = localStorage.getItem("vit_token") ?? "";

  const { data: summary } = useQuery({
    queryKey: ["quant-summary"],
    queryFn: () => fetchJson(`${API}/summary`, token),
    staleTime: 60_000,
    enabled: !!token,
  });

  if (!user) return null;

  return (
    <div className="space-y-6">
      {/* ── Header ─────────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <TrendingUp className="w-5 h-5 text-primary" />
          <h1 className="text-xl font-bold font-mono tracking-tight">Research Terminal</h1>
          <span className="text-[10px] font-mono bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-full ml-1">
            QUANT ENGINE
          </span>
        </div>
        <p className="text-xs text-muted-foreground font-mono">
          Professional backtesting, simulation and signal scanning powered by{" "}
          {summary?.count ?? "—"} settled predictions.
        </p>
      </div>

      {/* ── Headline stats strip ───────────────────────────── */}
      {summary && summary.count > 0 && (
        <div className="flex flex-wrap gap-6 p-4 rounded-xl border border-border bg-card/40">
          <Chip label="Settled bets" value={String(summary.count)} />
          <Chip label="Win rate" value={`${summary.win_rate_pct}%`} positive={summary.win_rate_pct > 50} />
          <Chip
            label="Portfolio ROI"
            value={`${summary.roi_pct > 0 ? "+" : ""}${summary.roi_pct}%`}
            positive={summary.roi_pct > 0}
          />
          <Chip label="Avg odds" value={`${summary.avg_odds}×`} />
          <Chip label="Avg confidence" value={`${(summary.avg_confidence * 100).toFixed(1)}%`} />
          <Chip
            label="Avg EV"
            value={`${summary.avg_ev > 0 ? "+" : ""}${summary.avg_ev.toFixed(4)}`}
            positive={summary.avg_ev > 0}
          />
        </div>
      )}

      {/* ── Info banner ────────────────────────────────────── */}
      <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-blue-500/5 border border-blue-500/20 text-[11px] font-mono text-blue-400">
        <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
        All analytics uses live prediction data from your database. EV Scanner shows live upcoming
        fixtures where available, or historical signals when no upcoming matches are scheduled.
      </div>

      {/* ── 2-column grid (desktop), stacked (mobile) ─────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <BacktestPanel token={token} />
        <MonteCarloPanel token={token} />
        <EVScannerPanel token={token} />
        <StrategyPanel token={token} />
        <VaultPanel token={token} />
      </div>
    </div>
  );
}
