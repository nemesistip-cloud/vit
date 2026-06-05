import { useMemo, useState } from "react";
import {
  useListPredictions,
  useSyncFixtures,
  useGetTicketMarkets,
  useGetTicketCandidates,
  useBuildTicket,
  type TicketCandidate,
  type BuiltTicket,
} from "@/api-client";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { format, isValid, parseISO } from "date-fns";
import {
  Activity, Coins, RefreshCw, Ticket, Sparkles, Users, User as UserIcon,
  Layers, AlertTriangle, Trophy, TrendingUp, Download, CheckCircle2,
  XCircle, Clock, BarChart3, Target,
} from "lucide-react";
import { Link } from "wouter";
import { toast } from "sonner";

const MARKET_LABEL: Record<string, string> = {
  "1x2": "1X2",
  home_win: "Home Win",
  away_win: "Away Win",
  draw: "Draw",
  btts: "h Teams to Score",
  btts_yes: "BTTS – Yes",
  btts_no: "BTTS – No",
  over_2_5: "Over 2.5 Goals",
  under_2_5: "Under 2.5 Goals",
  over_1_5: "Over 1.5 Goals",
  under_1_5: "Under 1.5 Goals",
  over_3_5: "Over 3.5 Goals",
  under_3_5: "Under 3.5 Goals",
  ah_home: "Asian Handicap – Home",
  ah_away: "Asian Handicap – Away",
  double_chance_1x: "Double Chance 1X",
  double_chance_x2: "Double Chance X2",
  double_chance_12: "Double Chance 12",
  correct_score: "Correct Score",
  ht_ft: "Half-Time / Full-Time",
  first_half_result: "First-Half Result",
  second_half_result: "Second-Half Result",
  clean_sheet: "Clean Sheet",
  win_to_nil: "Win to Nil",
};

function prettifyMarketKey(key: string): string {
  if (!key) return "—";
  return key
    .split(/[_\s]+/)
    .map((p) => (p.length <= 3 ? p.toUpperCase() : p.charAt(0).toUpperCase() + p.slice(1)))
    .join(" ");
}

function safeFormat(dateStr: string | null | undefined, fmt: string): string {
  if (!dateStr) return "—";
  try {
    const d = typeof dateStr === "string" ? parseISO(dateStr) : new Date(dateStr);
    return isValid(d) ? format(d, fmt) : "Invalid date";
  } catch {
    return "—";
  }
}

// ────────────────────────────────────────────────────────────────────────
// Result badge helper
// ────────────────────────────────────────────────────────────────────────
function ResultBadge({
  wasCorrect,
  actualOutcome,
  betSide,
  ftScore,
}: {
  wasCorrect: boolean | null | undefined;
  actualOutcome: string | null | undefined;
  betSide: string | null | undefined;
  ftScore: string | null | undefined;
}) {
  if (!actualOutcome) {
    return (
      <Badge variant="outline" className="font-mono text-[10px] text-muted-foreground gap-1">
        <Clock className="w-2.5 h-2.5" />
        PENDING
      </Badge>
    );
  }

  const correct = wasCorrect ?? (betSide && actualOutcome
    ? betSide.toLowerCase() === actualOutcome.toLowerCase()
    : null);

  if (correct === true) {
    return (
      <div className="flex items-center gap-1.5">
        <Badge className="font-mono text-[10px] bg-emerald-500/20 text-emerald-400 border-emerald-500/30 gap-1">
          <CheckCircle2 className="w-2.5 h-2.5" />
          WIN
        </Badge>
        {ftScore && (
          <span className="font-mono text-[10px] text-muted-foreground">{ftScore}</span>
        )}
      </div>
    );
  }
  if (correct === false) {
    return (
      <div className="flex items-center gap-1.5">
        <Badge className="font-mono text-[10px] bg-red-500/20 text-red-400 border-red-500/30 gap-1">
          <XCircle className="w-2.5 h-2.5" />
          LOSS
        </Badge>
        {ftScore && (
          <span className="font-mono text-[10px] text-muted-foreground">{ftScore}</span>
        )}
      </div>
    );
  }
  return (
    <Badge variant="secondary" className="font-mono text-[10px]">
      {actualOutcome.toUpperCase()}
    </Badge>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Predictions ledger card
// ────────────────────────────────────────────────────────────────────────
function PredictionsLedger({ scope }: { scope: "user" | "community" }) {
  const { data, isLoading, isError } = useListPredictions({
    all_users: scope === "community",
    limit: 50,
  });
  const syncMutation = useSyncFixtures();

  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center font-mono text-muted-foreground">
        LOADING_LEDGER...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12 space-y-4">
        <p className="font-mono text-destructive">Failed to load predictions.</p>
        <Link href="/matches">
          <Button variant="outline" className="font-mono">Go to Matches</Button>
        </Link>
      </div>
    );
  }

  const rawPredictions = data?.predictions ?? [];
  const predictions = rawPredictions.filter((p) => {
    if (p.actual_outcome) return true;
    const statusNorm = String(p.status ?? "").toLowerCase();
    if (statusNorm === "live" || statusNorm === "in_play") return true;
    if (!p.kickoff_time) return true;
    try {
      const ko = new Date(p.kickoff_time).getTime();
      if (!Number.isFinite(ko)) return true;
      return Date.now() - ko <= 90 * 60 * 1000;
    } catch {
      return true;
    }
  });

  if (predictions.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground font-mono border border-dashed border-border rounded-lg space-y-4">
        <p className="text-sm">
          {scope === "community"
            ? "No community predictions yet."
            : "You have no predictions yet."}
        </p>
        <p className="text-xs text-muted-foreground/70">
          Visit Matches to run a prediction, or sync fixtures to load upcoming games.
        </p>
        <div className="flex justify-center gap-3">
          <Link href="/matches">
            <Button size="sm" className="font-mono gap-2">Browse Matches</Button>
          </Link>
          <Button
            size="sm"
            variant="outline"
            className="font-mono gap-2"
            onClick={() => syncMutation.mutate({ days: 14 })}
            disabled={syncMutation.isPending}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
            {syncMutation.isPending ? "Syncing..." : "Sync Fixtures"}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3">
      {predictions.map((prediction, i) => (
        <Link key={`${prediction.match_id}-${i}`} href={`/matches/${prediction.match_id}`}>
          <Card className="bg-card/50 backdrop-blur border-border hover:border-primary/50 transition-colors cursor-pointer overflow-hidden">
            <CardContent className="p-0 flex flex-col md:flex-row">
              {/* Left: fixture identity + result */}
              <div className="p-5 md:w-1/3 border-b md:border-b-0 md:border-r border-border/50 bg-muted/10 flex flex-col justify-center gap-2">
                <div className="flex justify-between items-center">
                  <Badge variant="outline" className="font-mono text-[10px] border-primary/20 text-primary">
                    {prediction.league}
                  </Badge>
                  <ResultBadge
                    wasCorrect={(prediction as any).was_correct}
                    actualOutcome={prediction.actual_outcome}
                    betSide={prediction.bet_side}
                    ftScore={(prediction as any).ft_score}
                  />
                </div>
                <div className="space-y-0.5">
                  <div className="font-medium truncate">{prediction.home_team}</div>
                  <div className="font-medium truncate text-muted-foreground">{prediction.away_team}</div>
                </div>
                <div className="flex items-center text-xs text-muted-foreground font-mono">
                  <Activity className="w-3 h-3 mr-1.5" />
                  {safeFormat(prediction.kickoff_time, "MMM dd HH:mm")}
                </div>
              </div>

              {/* Right: prediction metrics */}
              <div className="p-5 flex-1 grid grid-cols-2 md:grid-cols-4 gap-4 items-center">
                <div>
                  <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">Predicted</div>
                  <div className="font-bold capitalize">{prediction.bet_side ?? "—"}</div>
                  {(prediction as any).actual_outcome && prediction.bet_side && (
                    <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
                      actual: <span className="capitalize">{prediction.actual_outcome}</span>
                    </div>
                  )}
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">Entry Odds</div>
                  <div className="font-mono font-bold flex items-center">
                    <Coins className="w-3.5 h-3.5 mr-1.5 text-secondary" />
                    {prediction.entry_odds ? prediction.entry_odds.toFixed(2) : "—"}
                  </div>
                  {(prediction as any).clv != null && (
                    <div className={`text-[10px] font-mono mt-0.5 ${(prediction as any).clv > 0 ? "text-emerald-400" : "text-muted-foreground"}`}>
                      CLV: {((prediction as any).clv * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">Stake %</div>
                  <div className={`font-mono font-bold ${(prediction.recommended_stake ?? 0) > 0 ? "text-primary" : "text-muted-foreground"}`}>
                    {prediction.recommended_stake != null
                      ? `${(prediction.recommended_stake * 100).toFixed(1)}%`
                      : prediction.edge != null
                      ? `${(prediction.edge * 100).toFixed(2)}%`
                      : "—"}
                  </div>
                  <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
                    edge: {prediction.edge != null ? `${(prediction.edge * 100).toFixed(2)}%` : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">P&amp;L</div>
                  <div className={`font-mono font-bold text-lg ${(prediction.profit ?? 0) > 0 ? "text-emerald-400" : (prediction.profit ?? 0) < 0 ? "text-red-400" : ""}`}>
                    {prediction.profit != null
                      ? `${prediction.profit >= 0 ? "+" : ""}${prediction.profit.toFixed(2)}u`
                      : prediction.actual_outcome
                      ? "—"
                      : <span className="text-xs text-muted-foreground">awaiting result</span>}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Results Comparison Tab
// ────────────────────────────────────────────────────────────────────────
interface ComparisonItem {
  match_id: number;
  fixture: string;
  home_team: string;
  away_team: string;
  league: string;
  kickoff_time: string;
  predicted_side: string | null;
  model_probability: number;
  entry_odds: number | null;
  edge: number | null;
  recommended_stake: number | null;
  actual_outcome: string | null;
  ft_score: string | null;
  was_correct: boolean | null;
  result_status: "WIN" | "LOSS" | "PENDING" | "NO_BET";
  profit: number | null;
  clv: number | null;
  has_gap: boolean;
}

interface ComparisonData {
  total: number;
  summary: {
    total_returned: number;
    settled: number;
    pending: number;
    correct: number;
    accuracy_pct: number;
    total_profit: number;
    gaps: number;
  };
  predictions: ComparisonItem[];
}

function ResultsComparison() {
  const [settledOnly, setSettledOnly] = useState(false);

  const { data, isLoading, isError } = useQuery<ComparisonData>({
    queryKey: ["results-comparison", settledOnly],
    queryFn: () => apiGet(`/api/history/results-comparison?limit=100&settled_only=${settledOnly}`),
    staleTime: 20_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const summary = data?.summary;
  const items = data?.predictions ?? [];

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Card className="bg-card/50 border-border">
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold font-mono text-primary">{summary.settled}</div>
              <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Settled</div>
            </CardContent>
          </Card>
          <Card className="bg-emerald-500/5 border-emerald-500/20">
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold font-mono text-emerald-400">{summary.correct}</div>
              <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Correct</div>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-border">
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold font-mono">{summary.accuracy_pct.toFixed(1)}%</div>
              <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Accuracy</div>
            </CardContent>
          </Card>
          <Card className={`border ${summary.total_profit >= 0 ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}>
            <CardContent className="p-4 text-center">
              <div className={`text-2xl font-bold font-mono ${summary.total_profit >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {summary.total_profit >= 0 ? "+" : ""}{summary.total_profit.toFixed(2)}u
              </div>
              <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Total P&amp;L</div>
            </CardContent>
          </Card>
          <Card className={summary.gaps > 0 ? "bg-amber-500/5 border-amber-500/20" : "bg-card/50 border-border"}>
            <CardContent className="p-4 text-center">
              <div className={`text-2xl font-bold font-mono ${summary.gaps > 0 ? "text-amber-400" : "text-muted-foreground"}`}>
                {summary.gaps}
              </div>
              <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">
                {summary.gaps > 0 ? "Pending Results" : "No Gaps"}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-3">
        <Button
          size="sm"
          variant={settledOnly ? "default" : "outline"}
          className="font-mono text-xs"
          onClick={() => setSettledOnly(!settledOnly)}
        >
          <Target className="w-3.5 h-3.5 mr-1.5" />
          {settledOnly ? "Showing Settled Only" : "Show All"}
        </Button>
        {summary && summary.gaps > 0 && !settledOnly && (
          <span className="text-xs text-amber-400 font-mono flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            {summary.gaps} prediction{summary.gaps !== 1 ? "s" : ""} awaiting match result
          </span>
        )}
      </div>

      {isLoading && (
        <div className="h-32 flex items-center justify-center text-muted-foreground font-mono text-sm">
          Loading comparison data...
        </div>
      )}
      {isError && (
        <div className="text-center py-8 text-destructive font-mono text-sm">
          Failed to load results comparison.
        </div>
      )}

      {!isLoading && !isError && items.length === 0 && (
        <EmptyState title="No predictions with a selected side yet." />
      )}

      {/* Table */}
      {items.length > 0 && (
        <div className="space-y-2">
          {items.map((item, i) => (
            <Link key={`${item.match_id}-${i}`} href={`/matches/${item.match_id}`}>
              <Card className={`border transition-colors cursor-pointer hover:border-primary/50 ${
                item.has_gap
                  ? "border-amber-500/20 bg-amber-500/5"
                  : item.result_status === "WIN"
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : item.result_status === "LOSS"
                  ? "border-red-500/15 bg-red-500/5"
                  : "border-border bg-card/50"
              }`}>
                <CardContent className="p-4">
                  <div className="flex flex-col md:flex-row md:items-center gap-3">
                    {/* Fixture */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-sm truncate">
                          {item.home_team} vs {item.away_team}
                        </span>
                        <Badge variant="outline" className="font-mono text-[9px] border-primary/20 text-primary shrink-0">
                          {item.league}
                        </Badge>
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                        {safeFormat(item.kickoff_time, "MMM dd, yyyy HH:mm")}
                      </div>
                    </div>

                    {/* Prediction vs Result */}
                    <div className="flex items-center gap-4 font-mono text-sm flex-wrap">
                      <div className="text-center">
                        <div className="text-[9px] text-muted-foreground uppercase mb-0.5">Predicted</div>
                        <div className="font-bold capitalize">{item.predicted_side ?? "—"}</div>
                        <div className="text-[9px] text-muted-foreground">
                          {item.model_probability ? `${(item.model_probability * 100).toFixed(1)}%` : ""}
                        </div>
                      </div>

                      <div className="text-center">
                        <div className="text-[9px] text-muted-foreground uppercase mb-0.5">Result</div>
                        {item.actual_outcome ? (
                          <div className="font-bold capitalize">{item.actual_outcome}</div>
                        ) : (
                          <div className="text-muted-foreground text-xs">TBD</div>
                        )}
                        {item.ft_score && (
                          <div className="text-[9px] text-muted-foreground">{item.ft_score}</div>
                        )}
                      </div>

                      <div className="text-center min-w-[52px]">
                        <div className="text-[9px] text-muted-foreground uppercase mb-1">Verdict</div>
                        {item.result_status === "WIN" && (
                          <Badge className="text-[9px] bg-emerald-500/20 text-emerald-400 border-emerald-500/30">WIN</Badge>
                        )}
                        {item.result_status === "LOSS" && (
                          <Badge className="text-[9px] bg-red-500/20 text-red-400 border-red-500/30">LOSS</Badge>
                        )}
                        {item.result_status === "PENDING" && (
                          <Badge variant="outline" className="text-[9px] text-amber-400 border-amber-400/30">PENDING</Badge>
                        )}
                      </div>

                      <div className="text-center min-w-[60px]">
                        <div className="text-[9px] text-muted-foreground uppercase mb-0.5">P&amp;L</div>
                        <div className={`font-bold ${
                          item.profit != null && item.profit > 0
                            ? "text-emerald-400"
                            : item.profit != null && item.profit < 0
                            ? "text-red-400"
                            : "text-muted-foreground"
                        }`}>
                          {item.profit != null
                            ? `${item.profit >= 0 ? "+" : ""}${item.profit.toFixed(2)}u`
                            : "—"}
                        </div>
                      </div>

                      {item.clv != null && (
                        <div className="text-center min-w-[48px]">
                          <div className="text-[9px] text-muted-foreground uppercase mb-0.5">CLV</div>
                          <div className={`font-bold ${item.clv > 0 ? "text-emerald-400" : "text-muted-foreground"}`}>
                            {(item.clv * 100).toFixed(1)}%
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Ticket Builder
// ────────────────────────────────────────────────────────────────────────
function TicketBuilder() {
  const { data: marketsData } = useGetTicketMarkets();
  const markets = marketsData?.markets ?? [];
  const unsupported = marketsData?.unsupported ?? [];

  const [market, setMarket] = useState<string>("home");
  const [minConfidence, setMinConfidence] = useState<number>(0.55);
  const [minEdge, setMinEdge] = useState<number>(0.02);
  const [legs, setLegs] = useState<number>(3);
  const [topN] = useState<number>(5);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const candidatesQ = useGetTicketCandidates({
    market,
    min_confidence: minConfidence,
    min_edge: minEdge,
    limit: 30,
  });
  const candidates = candidatesQ.data?.candidates ?? [];
  const totalFound = candidatesQ.data?.total_found ?? 0;

  const buildMutation = useBuildTicket();
  const tickets: BuiltTicket[] = buildMutation.data?.tickets ?? [];

  const selectedCandidates = useMemo(
    () => candidates.filter((c) => selectedIds.has(c.match_id)),
    [candidates, selectedIds],
  );

  const activeMarket = markets.find((m) => m.key === market);
  const isSyntheticOdds = activeMarket && !activeMarket.uses_real_odds;

  function toggleCandidate(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectTopN() {
    const top = candidates.slice(0, Math.min(legs * 2, candidates.length));
    setSelectedIds(new Set(top.map((c) => c.match_id)));
  }

  function clearSelection() {
    setSelectedIds(new Set());
    buildMutation.reset();
  }

  function handleBuild() {
    const pool = selectedCandidates.length >= legs ? selectedCandidates : candidates.slice(0, Math.max(legs * 2, legs));
    if (pool.length < legs) {
      toast.error(`Need at least ${legs} candidates. Found ${pool.length}. Loosen filters or pick a different market.`);
      return;
    }
    buildMutation.mutate(
      {
        candidates: pool,
        legs,
        top_n: topN,
        min_combined_edge: -1,
        same_match_allowed: false,
      },
      {
        onError: (e) => toast.error(`Build failed: ${e.message}`),
        onSuccess: (d) => {
          if (d.tickets.length === 0) toast.warning("No tickets could be built with the current pool.");
        },
      },
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur border-border">
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Ticket className="w-5 h-5 text-primary" />
            <CardTitle className="font-mono uppercase tracking-tight text-lg">Ticket Builder</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open('/api/exports/predictions/csv', '_blank')}
              className="font-mono text-xs"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
            <p className="text-xs text-muted-foreground font-mono">
              High-confidence selections, combined into a single ticket.
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label className="text-[10px] uppercase font-mono text-muted-foreground">Market</Label>
            <Select
              value={market}
              onValueChange={(v) => {
                setMarket(v);
                setSelectedIds(new Set());
                buildMutation.reset();
              }}
            >
              <SelectTrigger className="font-mono"><SelectValue /></SelectTrigger>
              <SelectContent>
                {markets.map((m) => (
                  <SelectItem key={m.key} value={m.key} className="font-mono text-sm">
                    {m.label} {m.uses_real_odds ? "" : " (model-priced)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-[10px] uppercase font-mono text-muted-foreground">
              Legs: <span className="text-primary font-bold">{legs}</span>
            </Label>
            <Slider value={[legs]} min={2} max={8} step={1} onValueChange={(v) => setLegs(v[0])} />
          </div>

          <div className="space-y-2">
            <Label className="text-[10px] uppercase font-mono text-muted-foreground">
              Min Confidence: <span className="text-primary font-bold">{(minConfidence * 100).toFixed(0)}%</span>
            </Label>
            <Slider
              value={[minConfidence]}
              min={0.5}
              max={0.85}
              step={0.01}
              onValueChange={(v) => setMinConfidence(v[0])}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-[10px] uppercase font-mono text-muted-foreground">
              Min Edge: <span className="text-primary font-bold">{(minEdge * 100).toFixed(1)}%</span>
            </Label>
            <Slider
              value={[minEdge]}
              min={0}
              max={0.15}
              step={0.005}
              onValueChange={(v) => setMinEdge(v[0])}
              disabled={isSyntheticOdds}
            />
          </div>
        </div>

        {isSyntheticOdds && (
          <div className="flex items-start gap-2 text-xs text-muted-foreground font-mono p-2 border border-dashed border-border rounded">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-secondary shrink-0" />
            <span>
              {activeMarket?.label} uses model-fair odds (1 / probability). Edge is reported as 0
              because we don't yet capture live bookmaker prices for this market — combine the
              ticket and shop the actual price at your book.
            </span>
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-secondary" />
              <span className="font-mono text-sm uppercase tracking-tight">
                Candidates
                <span className="ml-2 text-muted-foreground">
                  ({selectedIds.size} picked / {candidates.length} shown / {totalFound} total)
                </span>
              </span>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" className="font-mono text-xs" onClick={selectTopN}>
                Auto-pick top {Math.min(legs * 2, candidates.length)}
              </Button>
              <Button size="sm" variant="ghost" className="font-mono text-xs" onClick={clearSelection}>
                Clear
              </Button>
            </div>
          </div>

          {candidatesQ.isLoading ? (
            <div className="text-xs font-mono text-muted-foreground">Loading candidates...</div>
          ) : candidates.length === 0 ? (
            <div className="text-xs font-mono text-muted-foreground border border-dashed border-border rounded p-4 text-center">
              No candidates match the current filters. Try lowering Min Confidence or Min Edge.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-80 overflow-y-auto pr-1">
              {candidates.map((c) => {
                const checked = selectedIds.has(c.match_id);
                return (
                  <label
                    key={`${c.match_id}-${c.market}`}
                    htmlFor={`cand-${c.match_id}`}
                    className={`flex items-start gap-3 p-3 rounded border cursor-pointer transition-colors ${
                      checked ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"
                    }`}
                  >
                    <Checkbox
                      id={`cand-${c.match_id}`}
                      checked={checked}
                      onCheckedChange={() => toggleCandidate(c.match_id)}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-sm truncate">
                          {c.home_team} vs {c.away_team}
                        </span>
                        <Badge variant="outline" className="font-mono text-[9px] shrink-0">
                          {c.market_label}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-muted-foreground font-mono mt-1">
                        <span>{c.league}</span>
                        <span>·</span>
                        <span>{safeFormat(c.kickoff_time, "MMM dd HH:mm")}</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs font-mono mt-2">
                        <span>
                          P: <span className="text-primary font-bold">{(c.probability * 100).toFixed(1)}%</span>
                        </span>
                        <span>
                          Odds: <span className="font-bold">{c.odds.toFixed(2)}</span>
                        </span>
                        <span className={c.edge > 0 ? "text-primary" : "text-muted-foreground"}>
                          Edge: <span className="font-bold">{(c.edge * 100).toFixed(2)}%</span>
                        </span>
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <Separator />

        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="text-xs font-mono text-muted-foreground">
            {selectedIds.size > 0
              ? `Building from ${selectedIds.size} selected pick(s).`
              : `Building from top ${Math.min(legs * 2, candidates.length)} auto-picked candidates.`}
          </div>
          <Button
            onClick={handleBuild}
            disabled={buildMutation.isPending || candidates.length < legs}
            className="font-mono gap-2"
          >
            <Sparkles className={`w-4 h-4 ${buildMutation.isPending ? "animate-pulse" : ""}`} />
            {buildMutation.isPending ? "Building..." : `Generate ${legs}-Leg Ticket`}
          </Button>
        </div>

        {tickets.length > 0 && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center gap-2">
              <Trophy className="w-4 h-4 text-primary" />
              <span className="font-mono text-sm uppercase tracking-tight">
                Top {tickets.length} Ticket{tickets.length === 1 ? "" : "s"}
              </span>
            </div>
            {tickets.map((t, i) => (
              <Card key={i} className="bg-muted/20 border-primary/20">
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-3 font-mono text-xs">
                      <Badge variant="default" className="font-bold">#{i + 1}</Badge>
                      <span>
                        Combined Odds: <span className="text-primary font-bold text-base">
                          {t.combined_odds.toFixed(2)}
                        </span>
                      </span>
                      <span>
                        Hit Prob: <span className="font-bold">{(t.combined_prob * 100).toFixed(2)}%</span>
                      </span>
                      <span className={t.adjusted_edge > 0 ? "text-primary" : "text-muted-foreground"}>
                        Edge: <span className="font-bold">{(t.adjusted_edge * 100).toFixed(2)}%</span>
                      </span>
                    </div>
                    <div className="font-mono text-xs">
                      Kelly: <span className="font-bold">{(t.kelly_stake * 100).toFixed(2)}%</span>
                      <span className="text-muted-foreground"> / bankroll</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {t.legs.map((leg, j) => (
                      <div key={j} className="flex items-center justify-between border border-border/50 rounded p-2 text-xs font-mono">
                        <div className="min-w-0">
                          <div className="truncate font-medium text-foreground">
                            {leg.home_team} vs {leg.away_team}
                          </div>
                          <div className="text-[10px] text-muted-foreground">
                            {leg.market_label || MARKET_LABEL[leg.market] || prettifyMarketKey(leg.market)} · {(leg.probability * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div className="text-right shrink-0 ml-2">
                          <div className="font-bold">{leg.odds.toFixed(2)}</div>
                          <div className="text-[10px] text-muted-foreground">
                            {leg.odds_source === "bookmaker_opening" ? "book" : "fair"}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {t.correlation_penalty > 0 && (
                    <div className="text-[10px] text-muted-foreground font-mono">
                      Correlation penalty: −{(t.correlation_penalty * 100).toFixed(2)}% (same-league legs)
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {unsupported.length > 0 && (
          <div className="text-[10px] font-mono text-muted-foreground/60 pt-1 flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400/70 shrink-0" />
            Model coverage expanding:{" "}
            {unsupported.map((u) => MARKET_LABEL[u.key] ?? prettifyMarketKey(u.key)).join(", ")} — available in a future release.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Page
// ────────────────────────────────────────────────────────────────────────
export default function PredictionsPage() {
  const [scope, setScope] = useState<"user" | "community">("community");
  const [mainTab, setMainTab] = useState<"ledger" | "results" | "tickets">("results");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground flex items-center gap-3">
          <TrendingUp className="w-7 h-7 text-primary" />
          Signal History
        </h1>
        <p className="text-muted-foreground font-mono text-sm">
          Signal ledger, results comparison, and ticket builder — track every call against the actual outcome.
        </p>
      </div>

      <Tabs value={mainTab} onValueChange={(v) => setMainTab(v as any)}>
        <TabsList className="font-mono">
          <TabsTrigger value="results" className="gap-2">
            <BarChart3 className="w-3.5 h-3.5" /> Results vs Predictions
          </TabsTrigger>
          <TabsTrigger value="ledger" className="gap-2">
            <Activity className="w-3.5 h-3.5" /> Live Ledger
          </TabsTrigger>
          <TabsTrigger value="tickets" className="gap-2">
            <Ticket className="w-3.5 h-3.5" /> Ticket Builder
          </TabsTrigger>
        </TabsList>

        <TabsContent value="results" className="mt-4">
          <ResultsComparison />
        </TabsContent>

        <TabsContent value="ledger" className="mt-4">
          <div className="mb-4">
            <Tabs value={scope} onValueChange={(v) => setScope(v as "user" | "community")}>
              <TabsList className="grid grid-cols-2 w-full max-w-md font-mono">
                <TabsTrigger value="community" className="gap-2">
                  <Users className="w-3.5 h-3.5" /> Community
                </TabsTrigger>
                <TabsTrigger value="user" className="gap-2">
                  <UserIcon className="w-3.5 h-3.5" /> My Predictions
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
          <PredictionsLedger scope={scope} />
        </TabsContent>

        <TabsContent value="tickets" className="mt-4">
          <TicketBuilder />
        </TabsContent>
      </Tabs>
    </div>
  );
}
