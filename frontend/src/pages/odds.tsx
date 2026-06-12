import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "@/lib/apiClient";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import {
  BarChart2, Gem, Activity, ClipboardList, RefreshCw,
  Plus, X, Radio, Zap, Layers, TrendingUp,
} from "lucide-react";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { format, formatDistanceToNow } from "date-fns";

type Tab = "markets" | "compare" | "arbitrage" | "audit";

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "markets",   label: "All Markets",       icon: Layers },
  { id: "compare",   label: "Odds Compare",       icon: BarChart2 },
  { id: "arbitrage", label: "Arbitrage Scanner",  icon: Gem },
  { id: "audit",     label: "Audit Log",          icon: ClipboardList },
];

const REFETCH_INTERVAL = 60_000;

// ── Shared UI ─────────────────────────────────────────────────────────

function FreshnessBar({
  fetchedAt,
  isFetching,
  requestsRemaining,
}: {
  fetchedAt?: string;
  isFetching: boolean;
  requestsRemaining?: number | null;
}) {
  const [secondsLeft, setSecondsLeft] = useState(REFETCH_INTERVAL / 1000);

  useEffect(() => {
    if (!fetchedAt) return;
    const interval = setInterval(() => {
      const elapsed = (Date.now() - new Date(fetchedAt).getTime()) / 1000;
      setSecondsLeft(Math.max(0, REFETCH_INTERVAL / 1000 - elapsed));
    }, 1000);
    return () => clearInterval(interval);
  }, [fetchedAt]);

  useEffect(() => {
    if (isFetching) setSecondsLeft(REFETCH_INTERVAL / 1000);
  }, [isFetching]);

  const pct = (secondsLeft / (REFETCH_INTERVAL / 1000)) * 100;

  return (
    <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
      {isFetching ? (
        <span className="flex items-center gap-1.5 text-primary">
          <Radio className="w-3 h-3 animate-pulse" /> FETCHING LIVE ODDS...
        </span>
      ) : fetchedAt ? (
        <>
          <span className="flex items-center gap-1.5 text-primary">
            <Radio className="w-3 h-3 text-primary" /> LIVE
          </span>
          <span>Updated {formatDistanceToNow(new Date(fetchedAt), { addSuffix: true })}</span>
          <span className="text-muted-foreground/60">· next in {Math.round(secondsLeft)}s</span>
          <div className="flex-1 max-w-24 h-1 bg-muted/30 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary/60 rounded-full transition-all duration-1000"
              style={{ width: `${pct}%` }}
            />
          </div>
        </>
      ) : null}
      {requestsRemaining != null && requestsRemaining >= 0 && (
        <span className="ml-auto text-muted-foreground/70">
          <Zap className="w-3 h-3 inline mr-0.5" />{requestsRemaining} API calls left
        </span>
      )}
    </div>
  );
}

function DataStatusBadge({ status }: { status?: string }) {
  if (!status || status === "ok") return null;
  const map: Record<string, { label: string; cls: string }> = {
    rate_limited:    { label: "Rate Limited",    cls: "border-yellow-500/50 text-yellow-400" },
    quota_exceeded:  { label: "Quota Exceeded",  cls: "border-yellow-500/50 text-yellow-400" },
    invalid_sport:   { label: "Invalid League",  cls: "border-orange-500/50 text-orange-400" },
    timeout:         { label: "API Timeout",     cls: "border-destructive/50 text-destructive" },
    fetch_error:     { label: "Fetch Error",     cls: "border-destructive/50 text-destructive" },
  };
  const entry = map[status] ?? { label: status, cls: "border-muted/50 text-muted-foreground" };
  return (
    <Badge variant="outline" className={`font-mono text-xs ${entry.cls}`}>
      {entry.label}
    </Badge>
  );
}

function LeagueSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const { data: cfg } = usePublicConfig();
  const LEAGUES = (cfg?.leagues ?? []).map((l: any) => ({ value: l.id, label: l.label }));
  useEffect(() => {
    if (!value && LEAGUES.length > 0) onChange(LEAGUES[0].value);
  }, [LEAGUES.length]);
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-52 font-mono bg-background/50">
        <SelectValue placeholder="Select league…" />
      </SelectTrigger>
      <SelectContent>
        {LEAGUES.map((l: any) => (
          <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function OddsCell({ label, value, highlight }: { label: string; value?: number | null; highlight?: boolean }) {
  if (!value) return (
    <div className="text-center">
      <p className="text-[10px] text-muted-foreground/50 font-mono uppercase">{label}</p>
      <p className="font-mono text-muted-foreground/30 text-sm">—</p>
    </div>
  );
  return (
    <div className="text-center">
      <p className="text-[10px] text-muted-foreground font-mono uppercase">{label}</p>
      <p className={`font-mono font-bold text-sm ${highlight ? "text-primary" : ""}`}>
        {value.toFixed(2)}
      </p>
    </div>
  );
}

// ── All Markets Tab ───────────────────────────────────────────────────

function AllMarketsTab() {
  const { data: cfg } = usePublicConfig();
  const BK_LABELS = cfg?.bookmaker_labels ?? {};
  const [league, setLeague] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading, isFetching, refetch } = useQuery<any>({
    queryKey: ["all-markets", league],
    queryFn:  () => apiGet<any>(`/api/odds/markets?league=${league}`),
    enabled:  !!league,
    refetchInterval: REFETCH_INTERVAL,
    staleTime: 30_000,
  });

  const events: any[] = data?.events ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">League</Label>
          <LeagueSelector value={league} onChange={setLeague} />
        </div>
        <Button
          variant="outline" size="sm"
          onClick={() => refetch()} disabled={isFetching}
          className="font-mono uppercase text-xs border-primary/30 hover:border-primary"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          {isFetching ? "FETCHING..." : "REFRESH"}
        </Button>
        {data && <DataStatusBadge status={data.data_status} />}
        {data?.markets_fetched && (
          <div className="flex gap-1 flex-wrap">
            {[...data.markets_fetched, ...data.markets_derived].map((m: string) => (
              <Badge key={m} variant="outline" className="font-mono text-[10px] border-primary/20 text-primary/70">
                {m}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {(data?.fetched_at || isFetching) && (
        <FreshnessBar
          fetchedAt={data?.fetched_at}
          isFetching={isFetching}
          requestsRemaining={data?.requests_remaining}
        />
      )}

      {isLoading && !data && (
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-28 bg-muted/20 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && events.length === 0 && data && (
        <div className="text-center py-10 text-muted-foreground font-mono text-sm">
          No upcoming fixtures found for this league.
        </div>
      )}

      <div className="space-y-3">
        {events.map((ev: any) => {
          const key      = ev.event_id || `${ev.home_team}-${ev.away_team}`;
          const isOpen   = expanded === key;
          const h2h      = ev.h2h?.best ?? {};
          const totals   = ev.totals?.best ?? {};
          const ahBest   = ev.spreads?.best ?? [];
          const derived  = ev.derived ?? {};
          const primaryAH = ahBest[0];

          return (
            <Card
              key={key}
              className={`border transition-colors cursor-pointer ${
                isOpen
                  ? "border-primary/40 bg-primary/5"
                  : "border-border/40 bg-card/40 hover:border-border"
              }`}
              onClick={() => setExpanded(isOpen ? null : key)}
            >
              <CardContent className="p-4">
                {/* Header row */}
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="font-bold text-sm font-mono">
                      {ev.home_team} <span className="text-muted-foreground">vs</span> {ev.away_team}
                    </p>
                    {ev.kickoff && (
                      <p className="text-xs text-muted-foreground font-mono mt-0.5">
                        {(() => {
                          try { return format(new Date(ev.kickoff), "EEE d MMM · HH:mm"); }
                          catch { return ev.kickoff?.slice(0, 16); }
                        })()}
                        <span className="ml-2 text-muted-foreground/60">{ev.n_bookmakers} books</span>
                      </p>
                    )}
                  </div>
                  {derived.overround != null && (
                    <Badge variant="outline" className="font-mono text-[10px] text-muted-foreground border-muted/40">
                      Vig {(derived.overround * 100).toFixed(1)}%
                    </Badge>
                  )}
                </div>

                {/* Summary grid — always visible */}
                <div className="grid grid-cols-3 sm:grid-cols-6 lg:grid-cols-10 gap-2 bg-muted/10 rounded p-2">
                  {/* 1X2 */}
                  <OddsCell label="1 (Home)"   value={h2h.home} highlight />
                  <OddsCell label="X (Draw)"   value={h2h.draw} />
                  <OddsCell label="2 (Away)"   value={h2h.away} />
                  {/* Totals */}
                  <OddsCell label="Ov 1.5"  value={totals.over_15} />
                  <OddsCell label="Ov 2.5"  value={totals.over_25} />
                  <OddsCell label="Ov 3.5"  value={totals.over_35} />
                  {/* AH */}
                  {primaryAH ? (
                    <>
                      <OddsCell label={`AH ${primaryAH.line > 0 ? "+" : ""}${primaryAH.line} H`} value={primaryAH.home} />
                      <OddsCell label={`AH ${primaryAH.line > 0 ? "+" : ""}${primaryAH.line} A`} value={primaryAH.away} />
                    </>
                  ) : (
                    <>
                      <OddsCell label="AH Home" value={null} />
                      <OddsCell label="AH Away" value={null} />
                    </>
                  )}
                  {/* Derived */}
                  <OddsCell label="1X (DC)"  value={derived.dc_1x} />
                  <OddsCell label="X2 (DC)"  value={derived.dc_x2} />
                </div>

                {/* Expanded detail */}
                {isOpen && (
                  <div className="mt-4 space-y-4" onClick={e => e.stopPropagation()}>
                    {/* Vig-free probabilities */}
                    {derived.vig_free && (
                      <div>
                        <p className="font-mono text-xs font-bold uppercase text-muted-foreground mb-2">
                          Vig-Free Probabilities
                        </p>
                        <div className="grid grid-cols-3 gap-2">
                          {["home", "draw", "away"].map(side => (
                            <div key={side} className="bg-muted/10 rounded p-2 text-center">
                              <p className="text-[10px] font-mono uppercase text-muted-foreground">{side}</p>
                              <p className="font-bold font-mono text-sm text-primary">
                                {((derived.vig_free[side] ?? 0) * 100).toFixed(1)}%
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Over / Under full table */}
                    {Object.keys(totals).length > 0 && (
                      <div>
                        <p className="font-mono text-xs font-bold uppercase text-muted-foreground mb-2">
                          Over / Under (Best Price)
                        </p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                          {(["15", "25", "35", "45"] as const).map(suffix => {
                            const ov = totals[`over_${suffix}`];
                            const un = totals[`under_${suffix}`];
                            if (!ov && !un) return null;
                            const label = `${suffix[0]}.${suffix[1]}`;
                            return (
                              <div key={suffix} className="bg-muted/10 rounded p-2">
                                <p className="text-[10px] font-mono uppercase text-muted-foreground mb-1">
                                  Goals {label}
                                </p>
                                <div className="flex gap-2 justify-between text-sm font-mono">
                                  <span className="text-primary">Ov {ov?.toFixed(2) ?? "—"}</span>
                                  <span className="text-muted-foreground">Un {un?.toFixed(2) ?? "—"}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Asian Handicap all lines */}
                    {ahBest.length > 0 && (
                      <div>
                        <p className="font-mono text-xs font-bold uppercase text-muted-foreground mb-2">
                          Asian Handicap — All Lines (Best Price)
                        </p>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs font-mono">
                            <thead>
                              <tr className="border-b border-border/40">
                                <th className="text-left p-1.5 text-muted-foreground uppercase">Line</th>
                                <th className="text-center p-1.5 text-muted-foreground uppercase">Home</th>
                                <th className="text-center p-1.5 text-muted-foreground uppercase">Away</th>
                              </tr>
                            </thead>
                            <tbody>
                              {ahBest.map((row: any, i: number) => (
                                <tr key={i} className={`border-b border-border/20 ${i === 0 ? "bg-primary/5" : ""}`}>
                                  <td className="p-1.5 font-bold">
                                    {row.line > 0 ? `+${row.line}` : row.line}
                                    {i === 0 && <Badge className="ml-1.5 text-[9px] bg-primary/10 text-primary border-primary/20 py-0">FAIR</Badge>}
                                  </td>
                                  <td className="p-1.5 text-center text-primary font-bold">{row.home?.toFixed(2)}</td>
                                  <td className="p-1.5 text-center">{row.away?.toFixed(2)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Derived markets */}
                    {(derived.dc_1x || derived.dc_x2 || derived.dc_12 || derived.dnb_home) && (
                      <div>
                        <p className="font-mono text-xs font-bold uppercase text-muted-foreground mb-2">
                          Derived Markets
                        </p>
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                          {[
                            { label: "1X (DC)", value: derived.dc_1x,    title: "Home or Draw" },
                            { label: "X2 (DC)", value: derived.dc_x2,    title: "Draw or Away" },
                            { label: "12 (DC)", value: derived.dc_12,    title: "Home or Away" },
                            { label: "DNB H",   value: derived.dnb_home, title: "Draw No Bet — Home" },
                            { label: "DNB A",   value: derived.dnb_away, title: "Draw No Bet — Away" },
                          ].map(({ label, value, title }) => (
                            value ? (
                              <div key={label} className="bg-muted/10 rounded p-2 text-center" title={title}>
                                <p className="text-[10px] font-mono uppercase text-muted-foreground">{label}</p>
                                <p className="font-bold font-mono text-sm">{value.toFixed(3)}</p>
                                <p className="text-[9px] text-muted-foreground/50 truncate">{title}</p>
                              </div>
                            ) : null
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Per-bookmaker 1X2 */}
                    {ev.h2h?.bookmakers && Object.keys(ev.h2h.bookmakers).length > 0 && (
                      <div>
                        <p className="font-mono text-xs font-bold uppercase text-muted-foreground mb-2">
                          1X2 — Per Bookmaker
                        </p>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs font-mono">
                            <thead>
                              <tr className="border-b border-border/40">
                                <th className="text-left p-1.5 text-muted-foreground uppercase">Bookmaker</th>
                                <th className="text-center p-1.5 text-muted-foreground uppercase">Home</th>
                                <th className="text-center p-1.5 text-muted-foreground uppercase">Draw</th>
                                <th className="text-center p-1.5 text-muted-foreground uppercase">Away</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(ev.h2h.bookmakers).map(([bk, odds]: [string, any]) => {
                                const isBestH = odds.home === h2h.home;
                                const isBestD = odds.draw === h2h.draw;
                                const isBestA = odds.away === h2h.away;
                                return (
                                  <tr key={bk} className="border-b border-border/20 hover:bg-muted/10">
                                    <td className="p-1.5 capitalize">
                                      {BK_LABELS[bk] || bk.replace(/_/g, " ")}
                                    </td>
                                    <td className={`p-1.5 text-center font-bold ${isBestH ? "text-primary" : ""}`}>
                                      {odds.home?.toFixed(2)}
                                    </td>
                                    <td className={`p-1.5 text-center ${isBestD ? "text-primary font-bold" : ""}`}>
                                      {odds.draw?.toFixed(2)}
                                    </td>
                                    <td className={`p-1.5 text-center font-bold ${isBestA ? "text-primary" : ""}`}>
                                      {odds.away?.toFixed(2)}
                                    </td>
                                  </tr>
                                );
                              })}
                              {/* Best row */}
                              <tr className="bg-primary/10 border-t border-primary/20">
                                <td className="p-1.5 font-bold text-primary uppercase text-[10px]">Best Price</td>
                                <td className="p-1.5 text-center font-bold text-primary">{h2h.home?.toFixed(2)}</td>
                                <td className="p-1.5 text-center font-bold text-primary">{h2h.draw?.toFixed(2)}</td>
                                <td className="p-1.5 text-center font-bold text-primary">{h2h.away?.toFixed(2)}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Click hint */}
                {!isOpen && (
                  <p className="text-[10px] text-muted-foreground/40 font-mono mt-2">
                    Click to expand all markets
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ── Odds Compare Tab ──────────────────────────────────────────────────

function OddsCompare() {
  const { data: cfg } = usePublicConfig();
  const BK_LABELS = cfg?.bookmaker_labels ?? {};
  const [league, setLeague] = useState("");

  const { data, isLoading, isFetching, refetch } = useQuery<any>({
    queryKey:        ["odds-compare", league],
    queryFn:         () => apiGet<any>(`/api/odds/compare?league=${league}`),
    enabled:         !!league,
    refetchInterval: REFETCH_INTERVAL,
    staleTime:       30_000,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">League</Label>
          <LeagueSelector value={league} onChange={setLeague} />
        </div>
        <Button
          variant="outline" size="sm"
          onClick={() => refetch()} disabled={isFetching}
          className="font-mono uppercase text-xs border-primary/30 hover:border-primary"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          {isFetching ? "FETCHING..." : "REFRESH"}
        </Button>
        {data && <DataStatusBadge status={data.data_status} />}
      </div>

      {(data?.fetched_at || isFetching) && (
        <FreshnessBar
          fetchedAt={data?.fetched_at}
          isFetching={isFetching}
          requestsRemaining={data?.requests_remaining}
        />
      )}

      {isLoading && !data && (
        <div className="space-y-2">
          {[1, 2, 3].map(i => <div key={i} className="h-28 bg-muted/20 rounded-lg animate-pulse" />)}
        </div>
      )}

      {(data?.events ?? []).length === 0 && !isLoading && data && (
        <div className="text-center py-10 text-muted-foreground font-mono text-sm">
          No fixtures found for this league.
        </div>
      )}

      <div className="space-y-3">
        {(data?.events ?? []).map((ev: any, idx: number) => (
          <Card key={idx} className="bg-card/40 border-border/40">
            <CardContent className="p-4">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <p className="font-bold text-sm font-mono">{ev.home_team} vs {ev.away_team}</p>
                  {ev.kickoff && (
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">
                      {(() => { try { return format(new Date(ev.kickoff), "EEE d MMM · HH:mm"); } catch { return ev.kickoff?.slice(0, 16); } })()}
                      <span className="ml-2 text-muted-foreground/60">{ev.n_bookmakers} bookmakers</span>
                    </p>
                  )}
                </div>
                <div className="flex gap-2 text-sm font-mono font-bold">
                  <span className="text-primary">{ev.best_odds?.home?.toFixed(2)}</span>
                  <span className="text-muted-foreground">{ev.best_odds?.draw?.toFixed(2)}</span>
                  <span className="text-primary">{ev.best_odds?.away?.toFixed(2)}</span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="border-b border-border/40">
                      {["Bookmaker", "Home", "Draw", "Away"].map(h => (
                        <th key={h} className="text-left p-1.5 text-muted-foreground uppercase">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(ev.bookmakers ?? {}).map(([bk, odds]: [string, any]) => {
                      const isBestH = odds.home === ev.best_odds?.home;
                      const isBestD = odds.draw === ev.best_odds?.draw;
                      const isBestA = odds.away === ev.best_odds?.away;
                      return (
                        <tr key={bk} className="border-b border-border/20 hover:bg-muted/10">
                          <td className="p-1.5 capitalize">{BK_LABELS[bk] || bk.replace(/_/g, " ")}</td>
                          <td className={`p-1.5 font-bold ${isBestH ? "text-primary" : ""}`}>{odds.home?.toFixed(2)}</td>
                          <td className={`p-1.5 ${isBestD ? "text-primary font-bold" : ""}`}>{odds.draw?.toFixed(2)}</td>
                          <td className={`p-1.5 font-bold ${isBestA ? "text-primary" : ""}`}>{odds.away?.toFixed(2)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Arbitrage Scanner Tab ─────────────────────────────────────────────

function ArbitrageScanner() {
  const { data: cfg } = usePublicConfig();
  const BK_LABELS = cfg?.bookmaker_labels ?? {};
  const [league, setLeague]       = useState("premier_league");
  const [minProfit, setMinProfit]  = useState("0.5");
  const [inclTotals, setInclTotals] = useState(true);

  const { data, isLoading, isFetching, refetch } = useQuery<any>({
    queryKey:        ["arbitrage", league, minProfit, inclTotals],
    queryFn:         () =>
      apiGet<any>(`/api/odds/arbitrage?league=${league}&min_profit_pct=${minProfit}&include_totals=${inclTotals}`),
    enabled:         !!league,
    refetchInterval: REFETCH_INTERVAL,
    staleTime:       30_000,
  });

  const MARKET_LABELS: Record<string, string> = {
    "1x2":           "1X2",
    "over_under_25": "O/U 2.5",
    "over_under_15": "O/U 1.5",
    "over_under_35": "O/U 3.5",
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">League</Label>
          <LeagueSelector value={league} onChange={setLeague} />
        </div>
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">Min Profit %</Label>
          <Input type="number" step="0.1" min="0" className="w-28 font-mono bg-background/50"
            value={minProfit} onChange={e => setMinProfit(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">Markets</Label>
          <Select value={inclTotals ? "all" : "h2h"} onValueChange={v => setInclTotals(v === "all")}>
            <SelectTrigger className="w-36 font-mono bg-background/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">1X2 + O/U</SelectItem>
              <SelectItem value="h2h">1X2 Only</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline" size="sm"
          onClick={() => refetch()} disabled={isFetching}
          className="font-mono uppercase text-xs border-primary/30 hover:border-primary"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          {isFetching ? "SCANNING..." : "REFRESH"}
        </Button>
        {data && <DataStatusBadge status={data.data_status} />}
      </div>

      {(data?.fetched_at || isFetching) && (
        <FreshnessBar
          fetchedAt={data?.fetched_at}
          isFetching={isFetching}
          requestsRemaining={data?.requests_remaining}
        />
      )}

      {isLoading && !data && (
        <div className="space-y-2">
          {[1, 2, 3].map(i => <div key={i} className="h-20 bg-muted/20 rounded-lg animate-pulse" />)}
        </div>
      )}

      {data && (
        <div className="space-y-3">
          <div className="flex gap-3 font-mono text-sm items-center flex-wrap">
            <span className="text-muted-foreground">
              Scanned: <span className="text-foreground font-bold">{data.scanned}</span>
            </span>
            {data.markets_scanned?.map((m: string) => (
              <Badge key={m} variant="outline" className="font-mono text-[10px] border-border/50">
                {m}
              </Badge>
            ))}
            <Badge variant="outline" className={`${data.total_found > 0 ? "border-primary text-primary" : "text-muted-foreground"}`}>
              {data.total_found} arb{data.total_found !== 1 ? "s" : ""} found
            </Badge>
          </div>

          {(data.opportunities ?? []).length === 0 ? (
            <div className="text-center py-8 space-y-1">
              <p className="text-muted-foreground font-mono text-sm">
                No arbitrage opportunities above {minProfit}% threshold right now.
              </p>
              <p className="text-xs text-muted-foreground/60 font-mono">Auto-refreshes every 60s</p>
            </div>
          ) : (
            (data.opportunities ?? []).map((arb: any, i: number) => (
              <Card key={i} className="bg-primary/5 border-primary/30">
                <CardContent className="p-4">
                  <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
                    <div>
                      <p className="font-bold text-sm">{arb.home_team} vs {arb.away_team}</p>
                      {arb.kickoff && (
                        <p className="text-xs text-muted-foreground font-mono mt-0.5">
                          {(() => { try { return format(new Date(arb.kickoff), "EEE d MMM · HH:mm"); } catch { return arb.kickoff?.slice(0, 16); } })()}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      <Badge variant="outline" className="font-mono text-xs border-muted/50 text-muted-foreground">
                        {MARKET_LABELS[arb.market_type] ?? arb.market_type ?? "1X2"}
                      </Badge>
                      <Badge className="bg-primary/10 text-primary border-primary/20 font-mono text-xs">
                        +{arb.profit_pct?.toFixed(3)}% profit
                      </Badge>
                      <Badge variant="outline" className="font-mono text-xs">
                        £{arb.guaranteed_profit?.toFixed(2)} / £100
                      </Badge>
                    </div>
                  </div>
                  <div className={`grid gap-2 ${Object.keys(arb.legs ?? {}).length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
                    {Object.entries(arb.legs ?? {}).map(([side, leg]: [string, any]) => (
                      <div key={side} className="bg-background/50 rounded p-2 border border-primary/20">
                        <p className="font-mono text-xs font-bold uppercase text-primary">{side.replace(/_/g, " ")}</p>
                        <p className="font-mono font-bold text-base">{leg.odds?.toFixed(2)}</p>
                        <p className="font-mono text-xs text-muted-foreground capitalize">
                          {BK_LABELS[leg.bookmaker] || leg.bookmaker?.replace(/_/g, " ")}
                        </p>
                        <p className="font-mono text-xs text-primary">Stake: £{leg.stake}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ── Audit Log Tab ─────────────────────────────────────────────────────

function AuditLog() {
  const { data, isLoading, refetch, isFetching } = useQuery<{ log: any[] }>({
    queryKey: ["odds-audit"],
    queryFn:  () => apiGet<{ log: any[] }>("/api/odds/audit-log"),
    staleTime: 30_000,
  });

  const ACTION_COLORS: Record<string, string> = {
    all_markets:    "border-primary/30 text-primary",
    odds_compare:   "border-blue-500/30 text-blue-400",
    arbitrage_scan: "border-secondary/30 text-secondary",
    event_markets:  "border-cyan-500/30 text-cyan-400",
    injury_added:   "border-yellow-500/30 text-yellow-400",
    injury_deleted: "border-destructive/30 text-destructive",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="outline"
          className="font-mono uppercase text-xs border-primary/30 hover:border-primary"
          onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          {isFetching ? "LOADING..." : "REFRESH LOG"}
        </Button>
        {data?.log && (
          <span className="text-xs font-mono text-muted-foreground">{data.log.length} entries</span>
        )}
      </div>
      {isLoading && (
        <div className="space-y-1">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-8 bg-muted/20 rounded animate-pulse" />)}
        </div>
      )}
      {!isLoading && (data?.log ?? []).length === 0 && (
        <p className="font-mono text-muted-foreground text-sm text-center py-6">No audit entries yet</p>
      )}
      {(data?.log ?? []).length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border/50">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-border bg-muted/10">
                {["ID", "Action", "Details", "Timestamp"].map(h => (
                  <th key={h} className="text-left p-2 px-3 font-bold uppercase text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.log ?? []).map((entry: any) => (
                <tr key={entry.id} className="border-b border-border/30 hover:bg-muted/10">
                  <td className="p-2 px-3 text-muted-foreground">{entry.id}</td>
                  <td className="p-2 px-3">
                    <Badge variant="outline" className={`text-[10px] ${ACTION_COLORS[entry.action] || ""}`}>
                      {entry.action}
                    </Badge>
                  </td>
                  <td className="p-2 px-3 text-muted-foreground max-w-xs truncate">
                    {Object.entries(entry.details ?? {}).map(([k, v]) => `${k}: ${v}`).join(", ")}
                  </td>
                  <td className="p-2 px-3 text-muted-foreground whitespace-nowrap">
                    {(() => { try { return format(new Date(entry.timestamp), "dd MMM HH:mm:ss"); } catch { return entry.timestamp; } })()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────

export default function OddsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("markets");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">Odds Analytics</h1>
        <p className="text-muted-foreground font-mono text-sm mt-1">
          Real-time odds across all markets — 1X2, Over/Under, Asian Handicap, Double Chance, Draw No Bet
        </p>
      </div>

      <Card className="bg-card/50  border-border">
        <CardHeader className="pb-0">
          <div className="flex flex-wrap gap-2">
            {TABS.map(tab => {
              const Icon     = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded font-mono text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted/30 text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {activeTab === "markets"   && <AllMarketsTab />}
          {activeTab === "compare"   && <OddsCompare />}
          {activeTab === "arbitrage" && <ArbitrageScanner />}
          {activeTab === "audit"     && <AuditLog />}
        </CardContent>
      </Card>
    </div>
  );
}
