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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  Layers, AlertTriangle, Trophy, TrendingUp,
} from "lucide-react";
import { Link } from "wouter";
import { toast } from "sonner";

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
// Predictions ledger card (extracted so we can render in both tabs)
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

  const predictions = data?.predictions ?? [];

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
              <div className="p-5 md:w-1/3 border-b md:border-b-0 md:border-r border-border/50 bg-muted/10 flex flex-col justify-center">
                <div className="flex justify-between items-center mb-3">
                  <Badge variant="outline" className="font-mono text-[10px] border-primary/20 text-primary">
                    {prediction.league}
                  </Badge>
                  <Badge
                    variant={prediction.actual_outcome ? "secondary" : "outline"}
                    className="font-mono text-[10px] uppercase"
                  >
                    {prediction.actual_outcome ?? "PENDING"}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <div className="font-medium truncate">{prediction.home_team}</div>
                  <div className="font-medium truncate text-muted-foreground">{prediction.away_team}</div>
                </div>
                <div className="mt-3 flex items-center text-xs text-muted-foreground font-mono">
                  <Activity className="w-3 h-3 mr-1.5" />
                  {safeFormat(prediction.kickoff_time, "MMM dd HH:mm")}
                </div>
              </div>

              <div className="p-5 flex-1 grid grid-cols-2 md:grid-cols-4 gap-4 items-center">
                <div>
                  <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">Bet Side</div>
                  <div className="font-bold capitalize">{prediction.bet_side ?? "—"}</div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">Entry Odds</div>
                  <div className="font-mono font-bold flex items-center">
                    <Coins className="w-3.5 h-3.5 mr-1.5 text-secondary" />
                    {prediction.entry_odds ? prediction.entry_odds.toFixed(2) : "—"}
                  </div>
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
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">P&L</div>
                  <div className={`font-mono font-bold text-lg ${(prediction.profit ?? 0) > 0 ? "text-primary" : (prediction.profit ?? 0) < 0 ? "text-destructive" : ""}`}>
                    {prediction.profit != null ? `${prediction.profit >= 0 ? "+" : ""}${prediction.profit.toFixed(2)}` : "—"}
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
        min_combined_edge: -1, // we want to see best tickets even when combined edge is negative
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
          <p className="text-xs text-muted-foreground font-mono">
            High-confidence selections, combined into a single ticket.
          </p>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Controls */}
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

        {/* Candidates */}
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

        {/* Generated tickets */}
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
                            {leg.market_label} · {(leg.probability * 100).toFixed(1)}%
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
          <div className="text-[10px] font-mono text-muted-foreground/70 pt-1">
            Coming soon: {unsupported.map((u) => u.key).join(", ")}.
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-mono font-bold uppercase tracking-tight flex items-center gap-3">
          <TrendingUp className="w-7 h-7 text-primary" />
          Active Operations
        </h1>
        <p className="text-muted-foreground font-mono text-sm">
          Live prediction ledger across the network — and a ticket builder for high-confidence picks.
        </p>
      </div>

      <TicketBuilder />

      <div>
        <Tabs value={scope} onValueChange={(v) => setScope(v as "user" | "community")}>
          <TabsList className="grid grid-cols-2 w-full max-w-md font-mono">
            <TabsTrigger value="community" className="gap-2">
              <Users className="w-3.5 h-3.5" /> Community
            </TabsTrigger>
            <TabsTrigger value="user" className="gap-2">
              <UserIcon className="w-3.5 h-3.5" /> My Predictions
            </TabsTrigger>
          </TabsList>
          <TabsContent value="community" className="mt-4">
            <PredictionsLedger scope="community" />
          </TabsContent>
          <TabsContent value="user" className="mt-4">
            <PredictionsLedger scope="user" />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
