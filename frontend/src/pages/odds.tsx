import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "@/lib/apiClient";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { BarChart2, Gem, Activity, ClipboardList, RefreshCw, Plus, X, Radio, Clock, Zap } from "lucide-react";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { format, formatDistanceToNow } from "date-fns";

type Tab = "compare" | "arbitrage" | "injuries" | "audit";

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "compare",   label: "Odds Compare",     icon: BarChart2 },
  { id: "arbitrage", label: "Arbitrage Scanner", icon: Gem },
  { id: "injuries",  label: "Injury Notes",      icon: Activity },
  { id: "audit",     label: "Audit Log",         icon: ClipboardList },
];

const REFETCH_INTERVAL = 60_000;

function FreshnessBar({ fetchedAt, isFetching, requestsRemaining }: {
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
          <Radio className="w-3 h-3 animate-pulse" />
          FETCHING LIVE ODDS...
        </span>
      ) : fetchedAt ? (
        <>
          <span className="flex items-center gap-1.5 text-primary">
            <Radio className="w-3 h-3 text-primary" />
            LIVE
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
    rate_limited:  { label: "Rate Limited",    cls: "border-yellow-500/50 text-yellow-400" },
    invalid_sport: { label: "Invalid League",  cls: "border-orange-500/50 text-orange-400" },
    timeout:       { label: "API Timeout",     cls: "border-destructive/50 text-destructive" },
    fetch_error:   { label: "Fetch Error",     cls: "border-destructive/50 text-destructive" },
  };
  const entry = map[status] ?? { label: status, cls: "border-muted/50 text-muted-foreground" };
  return (
    <Badge variant="outline" className={`font-mono text-xs ${entry.cls}`}>
      {entry.label}
    </Badge>
  );
}

function OddsCompare() {
  const { data: cfg } = usePublicConfig();
  const LEAGUES = (cfg?.leagues ?? []).map((l) => ({ value: l.id, label: l.label }));
  const BK_LABELS = cfg?.bookmaker_labels ?? {};
  const [league, setLeague] = useState<string>("");

  useEffect(() => {
    if (!league && LEAGUES.length > 0) setLeague(LEAGUES[0].value);
  }, [LEAGUES.length]);

  const { data, isLoading, isFetching, refetch } = useQuery<any>({
    queryKey: ["odds-compare", league],
    queryFn: () => apiGet<any>(`/odds/compare?league=${league}`),
    enabled: !!league,
    refetchInterval: REFETCH_INTERVAL,
    staleTime: 30_000,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">League</Label>
          <Select value={league} onValueChange={setLeague}>
            <SelectTrigger className="w-48 font-mono bg-background/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LEAGUES.map((l) => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
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
          {[1,2,3].map(i => (
            <div key={i} className="h-28 bg-muted/20 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {data && (
        <div className="space-y-3">
          {data.sport_key && (
            <p className="text-xs font-mono text-muted-foreground/60">
              Sport key: <span className="text-muted-foreground">{data.sport_key}</span>
              {" · "}{data.total} fixture{data.total !== 1 ? "s" : ""}
            </p>
          )}
          {(data.events ?? []).length === 0 ? (
            <div className="text-center py-12 space-y-2">
              <p className="font-mono text-muted-foreground text-sm">
                {data.data_status === "invalid_sport"
                  ? "This league is not available on The Odds API for the current plan."
                  : data.data_status === "rate_limited"
                  ? "API rate limit reached. Try again shortly."
                  : "No fixtures found for this league right now. Check back closer to match day."}
              </p>
              <p className="font-mono text-xs text-muted-foreground/60">
                Status: {data.data_status ?? "unknown"}
              </p>
            </div>
          ) : (
            (data.events ?? []).map((ev: any, i: number) => (
              <Card key={i} className="bg-card/30 border-border overflow-hidden">
                <div className="flex justify-between items-center px-4 py-3 bg-muted/20 border-b border-border/50">
                  <div>
                    <p className="font-bold text-sm">
                      {ev.home_team} <span className="text-muted-foreground">vs</span> {ev.away_team}
                    </p>
                    {ev.kickoff && (
                      <p className="text-xs text-muted-foreground font-mono mt-0.5">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {(() => {
                          try { return format(new Date(ev.kickoff), "EEE d MMM · HH:mm"); } catch { return ev.kickoff?.slice(0, 16).replace("T", " "); }
                        })()}
                      </p>
                    )}
                  </div>
                  <Badge variant="outline" className="font-mono text-xs">
                    {ev.n_bookmakers} book{ev.n_bookmakers !== 1 ? "s" : ""}
                  </Badge>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="border-b border-border/50">
                        <th className="text-left p-2 pl-4 text-muted-foreground uppercase">Bookmaker</th>
                        {["Home", "Draw", "Away"].map((h) => (
                          <th key={h} className="text-center p-2 text-muted-foreground uppercase">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="bg-primary/5 border-b border-primary/20">
                        <td className="p-2 pl-4 font-bold text-primary">⭐ Best Available</td>
                        {["home", "draw", "away"].map((side) => (
                          <td key={side} className="p-2 text-center font-bold text-primary">
                            {ev.best_odds?.[side]?.toFixed(2) ?? "—"}
                          </td>
                        ))}
                      </tr>
                      {Object.entries(ev.bookmakers ?? {}).map(([bk, odds]: [string, any]) => (
                        <tr key={bk} className="border-b border-border/30 hover:bg-muted/10">
                          <td className="p-2 pl-4 text-muted-foreground capitalize">
                            {BK_LABELS[bk] || bk.replace(/_/g, " ")}
                          </td>
                          {["home", "draw", "away"].map((side) => {
                            const isBest = odds[side] === ev.best_odds?.[side];
                            return (
                              <td key={side} className={`p-2 text-center ${isBest ? "font-bold text-primary" : "text-muted-foreground"}`}>
                                {odds[side]?.toFixed(2) ?? "—"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function ArbitrageScanner() {
  const { data: cfg } = usePublicConfig();
  const BK_LABELS = cfg?.bookmaker_labels ?? {};
  const LEAGUES = (cfg?.leagues ?? []).map((l) => ({ value: l.id, label: l.label }));
  const [league, setLeague] = useState("premier_league");
  const [minProfit, setMinProfit] = useState("0.5");

  useEffect(() => {
    if (LEAGUES.length > 0 && !LEAGUES.find(l => l.value === league)) {
      setLeague(LEAGUES[0].value);
    }
  }, [LEAGUES.length]);

  const { data, isLoading, isFetching, refetch } = useQuery<any>({
    queryKey: ["arbitrage", league, minProfit],
    queryFn: () => apiGet<any>(`/odds/arbitrage?league=${league}&min_profit_pct=${minProfit}`),
    enabled: !!league,
    refetchInterval: REFETCH_INTERVAL,
    staleTime: 30_000,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">League</Label>
          <Select value={league} onValueChange={setLeague}>
            <SelectTrigger className="w-48 font-mono bg-background/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LEAGUES.map((l) => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">Min Profit %</Label>
          <Input type="number" step="0.1" min="0" className="w-28 font-mono bg-background/50"
            value={minProfit} onChange={(e) => setMinProfit(e.target.value)} />
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
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
          {[1,2,3].map(i => <div key={i} className="h-20 bg-muted/20 rounded-lg animate-pulse" />)}
        </div>
      )}

      {data && (
        <div className="space-y-3">
          <div className="flex gap-3 font-mono text-sm items-center">
            <span className="text-muted-foreground">
              Scanned: <span className="text-foreground font-bold">{data.scanned}</span>
            </span>
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
                  <div className="flex justify-between items-center mb-3">
                    <div>
                      <p className="font-bold text-sm">{arb.home_team} vs {arb.away_team}</p>
                      {arb.kickoff && (
                        <p className="text-xs text-muted-foreground font-mono mt-0.5">
                          {(() => { try { return format(new Date(arb.kickoff), "EEE d MMM · HH:mm"); } catch { return arb.kickoff?.slice(0, 16); } })()}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Badge className="bg-primary/10 text-primary border-primary/20 font-mono text-xs">
                        +{arb.profit_pct?.toFixed(3)}% profit
                      </Badge>
                      <Badge variant="outline" className="font-mono text-xs">
                        £{arb.guaranteed_profit?.toFixed(2)} / £100
                      </Badge>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(arb.legs ?? {}).map(([side, leg]: [string, any]) => (
                      <div key={side} className="bg-background/50 rounded p-2 border border-primary/20">
                        <p className="font-mono text-xs font-bold uppercase text-primary">{side}</p>
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

function InjuryNotes() {
  const qc = useQueryClient();
  const [form, setForm] = useState({ team: "", player: "", status: "out", note: "" });

  const { data, isLoading } = useQuery<{ injuries: any[] }>({
    queryKey: ["injuries"],
    queryFn: () => apiGet<{ injuries: any[] }>("/odds/injuries"),
  });

  const addMutation = useMutation({
    mutationFn: (d: typeof form) => apiPost("/odds/injuries", d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["injuries"] });
      setForm({ team: "", player: "", status: "out", note: "" });
      toast.success("Injury note added");
    },
    onError: (e: any) => toast.error(e.message),
  });

  const delMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/odds/injuries/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["injuries"] }); toast.success("Note removed"); },
  });

  const STATUS_COLORS: Record<string, string> = {
    out:       "bg-destructive/10 text-destructive border-destructive/30",
    doubtful:  "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
    returning: "bg-primary/10 text-primary border-primary/30",
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { key: "team",   label: "Team",   placeholder: "e.g. Arsenal" },
          { key: "player", label: "Player", placeholder: "e.g. Saka" },
        ].map(({ key, label, placeholder }) => (
          <div key={key} className="space-y-1.5">
            <Label className="font-mono text-xs uppercase">{label}</Label>
            <Input className="font-mono bg-background/50" placeholder={placeholder}
              value={form[key as keyof typeof form]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} />
          </div>
        ))}
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">Status</Label>
          <Select value={form.status} onValueChange={(v) => setForm((f) => ({ ...f, status: v }))}>
            <SelectTrigger className="font-mono bg-background/50"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="out">Out</SelectItem>
              <SelectItem value="doubtful">Doubtful</SelectItem>
              <SelectItem value="returning">Returning</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="font-mono text-xs uppercase">Note</Label>
          <Input className="font-mono bg-background/50" placeholder="Optional detail"
            value={form.note} onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))} />
        </div>
      </div>
      <Button className="font-mono uppercase" disabled={!form.team || !form.player || addMutation.isPending}
        onClick={() => addMutation.mutate(form)}>
        <Plus className="w-4 h-4 mr-2" />
        {addMutation.isPending ? "SAVING..." : "ADD NOTE"}
      </Button>

      <div className="space-y-2 mt-4">
        {isLoading ? (
          <div className="space-y-2">
            {[1,2].map(i => <div key={i} className="h-12 bg-muted/20 rounded-lg animate-pulse" />)}
          </div>
        ) : (data?.injuries ?? []).length === 0 ? (
          <p className="font-mono text-muted-foreground text-sm text-center py-6">No injury notes yet</p>
        ) : (
          (data?.injuries ?? []).map((n: any) => (
            <div key={n.id} className="flex items-center justify-between p-3 rounded-lg bg-card/30 border border-border/50">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-bold text-sm font-mono">{n.team} — {n.player}</span>
                <Badge variant="outline" className={`font-mono text-xs ${STATUS_COLORS[n.status] || ""}`}>
                  {n.status}
                </Badge>
                {n.note && <span className="text-xs text-muted-foreground font-mono">{n.note}</span>}
              </div>
              <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive flex-shrink-0"
                onClick={() => delMutation.mutate(n.id)}>
                <X className="w-3 h-3" />
              </Button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function AuditLog() {
  const { data, isLoading, refetch, isFetching } = useQuery<{ log: any[] }>({
    queryKey: ["odds-audit"],
    queryFn: () => apiGet<{ log: any[] }>("/odds/audit-log"),
    staleTime: 30_000,
  });

  const ACTION_COLORS: Record<string, string> = {
    odds_compare:   "border-primary/30 text-primary",
    arbitrage_scan: "border-secondary/30 text-secondary",
    injury_added:   "border-yellow-500/30 text-yellow-400",
    injury_deleted: "border-destructive/30 text-destructive",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="outline" className="font-mono uppercase text-xs border-primary/30 hover:border-primary" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          {isFetching ? "LOADING..." : "REFRESH LOG"}
        </Button>
        {data?.log && (
          <span className="text-xs font-mono text-muted-foreground">{data.log.length} entries</span>
        )}
      </div>

      {isLoading && (
        <div className="space-y-1">
          {[1,2,3,4].map(i => <div key={i} className="h-8 bg-muted/20 rounded animate-pulse" />)}
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
                {["ID", "Action", "Details", "Timestamp"].map((h) => (
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

export default function OddsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("compare");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-mono font-bold uppercase tracking-tight">Odds Intelligence</h1>
        <p className="text-muted-foreground font-mono text-sm mt-1">
          Real-time bookmaker odds, arbitrage detection, and injury tracking
        </p>
      </div>

      <Card className="bg-card/50 backdrop-blur border-border">
        <CardHeader className="pb-0">
          <div className="flex flex-wrap gap-2">
            {TABS.map((tab) => {
              const Icon = tab.icon;
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
          {activeTab === "compare"   && <OddsCompare />}
          {activeTab === "arbitrage" && <ArbitrageScanner />}
          {activeTab === "injuries"  && <InjuryNotes />}
          {activeTab === "audit"     && <AuditLog />}
        </CardContent>
      </Card>
    </div>
  );
}
