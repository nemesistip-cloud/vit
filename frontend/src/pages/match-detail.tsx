import { useState } from "react";
import { useParams, useLocation } from "wouter";
import {
  useGetMatch, useGetConsensusPrediction, useStakeOnPrediction, useGetWallet,
  useGetOddsInjuries,
} from "@/api-client";
import { AIInsightComparison } from "@/components/AIInsightComparison";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { BrainCircuit, ShieldCheck, ChevronLeft, Zap, Coins, TrendingUp, Target, BarChart2, Radio } from "lucide-react";
import { format } from "date-fns";
import { Progress } from "@/components/ui/progress";

export default function MatchDetailPage() {
  const params = useParams();
  const [, setLocation] = useLocation();
  const matchId = params.id || "";

  const { data: match, isLoading } = useGetMatch(matchId);
  const { data: consensus } = useGetConsensusPrediction(matchId);
  const { data: wallet } = useGetWallet();
  const stake = useStakeOnPrediction();
  const { data: injuries } = useGetOddsInjuries({ team: match?.home_team });

  type StakeSide = "home" | "draw" | "away" | "over_25" | "under_25" | "btts_yes" | "btts_no";
  const [selectedSide, setSelectedSide] = useState<StakeSide | null>(null);
  const [stakeAmount, setStakeAmount] = useState("10");

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center font-mono text-muted-foreground">
        <div className="text-center space-y-2">
          <div className="text-2xl animate-pulse">⬡</div>
          <div>RETRIEVING_DATA...</div>
        </div>
      </div>
    );
  }

  if (!match) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4 font-mono">
          <div className="text-4xl text-muted-foreground">404</div>
          <div className="text-muted-foreground uppercase text-sm">Match not found in the intelligence network</div>
          <Button variant="outline" className="font-mono uppercase text-xs" onClick={() => setLocation("/matches")}>
            <ChevronLeft className="w-4 h-4 mr-2" /> Return to Feed
          </Button>
        </div>
      </div>
    );
  }

  const homeProb = match.home_prob ?? 0;
  const drawProb = match.draw_prob ?? 0;
  const awayProb = match.away_prob ?? 0;
  const confidence = match.confidence ?? 0;
  const modelContributions = (match as any).model_contributions ?? [];
  const consensusBreakdown = (match as any).consensus_breakdown;
  const recentForm = (match as any).recent_form;
  const headToHead = (match as any).head_to_head;

  const handleStake = async () => {
    if (!selectedSide) {
      toast.error("Select a prediction first");
      return;
    }
    const amount = parseFloat(stakeAmount);
    if (!amount || amount <= 0) {
      toast.error("Enter a valid stake amount");
      return;
    }
    try {
      await stake.mutateAsync({ matchId, prediction: selectedSide, amount });
      toast.success(`Staked ${amount} VITCoin on ${selectedSide}`);
      setSelectedSide(null);
    } catch (e: any) {
      toast.error(e.message || "Stake failed");
    }
  };

  return (
    <div className="space-y-6">
      <Button variant="ghost" className="font-mono text-xs uppercase tracking-wider mb-2" onClick={() => setLocation("/matches")}>
        <ChevronLeft className="w-4 h-4 mr-2" /> Back to Feed
      </Button>

      <Card className="bg-card/80 backdrop-blur border-primary/30 overflow-hidden relative">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-transparent to-primary/5 pointer-events-none" />
        <CardContent className="p-8 relative z-10">
          <div className="flex flex-col items-center justify-center space-y-4">
            <Badge variant="outline" className="font-mono border-primary/30 text-primary uppercase">{match.league}</Badge>
            <div className="flex items-center justify-center gap-4 sm:gap-8 w-full max-w-2xl">
              <div className="flex-1 text-right min-w-0">
                <h2 className="text-lg sm:text-3xl font-bold tracking-tight break-words hyphens-auto leading-tight">{match.home_team}</h2>
              </div>
              <div className="flex flex-col items-center px-2 sm:px-4 flex-shrink-0">
                {match.ft_score ? (
                  <div className="text-4xl font-bold font-mono text-primary bg-background/50 px-6 py-3 rounded-lg border border-primary/30">
                    {match.ft_score}
                  </div>
                ) : (
                  <div className="text-center font-mono bg-background/50 px-4 py-2 rounded-lg border border-border">
                    <span className="block text-xl font-bold text-primary">VS</span>
                    <span className="text-xs text-muted-foreground">
                      {format(new Date(match.kickoff_time), "HH:mm")}
                    </span>
                  </div>
                )}
                {(match as any).status === "live" ? (
                  <Badge variant="default" className="mt-4 font-mono bg-red-600 hover:bg-red-600 flex items-center gap-1.5">
                    <Radio className="w-3 h-3 animate-pulse" /> LIVE
                  </Badge>
                ) : match.actual_outcome ? (
                  <Badge variant="secondary" className="mt-4 font-mono">SETTLED</Badge>
                ) : (
                  <Badge variant="outline" className="mt-4 font-mono">UPCOMING</Badge>
                )}
              </div>
              <div className="flex-1 text-left min-w-0">
                <h2 className="text-lg sm:text-3xl font-bold tracking-tight break-words hyphens-auto leading-tight">{match.away_team}</h2>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="analysis" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
          <TabsTrigger value="injuries">Injuries</TabsTrigger>
          <TabsTrigger value="audit">Audit Log</TabsTrigger>
        </TabsList>

        <TabsContent value="analysis" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <AIInsightComparison matchId={matchId} />

              <Card className="bg-card/50 backdrop-blur border-border">
                <CardHeader className="border-b border-border/50 pb-4">
                  <CardTitle className="font-mono uppercase flex items-center">
                    <BrainCircuit className="w-5 h-5 mr-2 text-primary" />
                    Ensemble Intelligence</CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-6">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="space-y-2">
                  <div className="font-mono text-sm text-muted-foreground uppercase">Home Win</div>
                  <div className="text-2xl font-bold font-mono text-primary">{(homeProb * 100).toFixed(1)}%</div>
                </div>
                <div className="space-y-2">
                  <div className="font-mono text-sm text-muted-foreground uppercase">Draw</div>
                  <div className="text-2xl font-bold font-mono">{(drawProb * 100).toFixed(1)}%</div>
                </div>
                <div className="space-y-2">
                  <div className="font-mono text-sm text-muted-foreground uppercase">Away Win</div>
                  <div className="text-2xl font-bold font-mono">{(awayProb * 100).toFixed(1)}%</div>
                </div>
              </div>

              {/* Extended Market Probabilities */}
              <div>
                <div className="font-mono text-[10px] text-muted-foreground uppercase mb-2 flex items-center gap-1">
                  <Target className="w-3 h-3" /> Market Probabilities
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center">
                  {[
                    { label: "Over 2.5", val: match.over_25_prob },
                    { label: "Under 2.5", val: match.under_25_prob ?? (match.over_25_prob != null ? 1 - match.over_25_prob : null) },
                    { label: "Over 1.5", val: (match as any).over_15_prob },
                    { label: "Over 3.5", val: (match as any).over_35_prob },
                    { label: "BTTS Yes", val: match.btts_prob },
                    { label: "BTTS No",  val: match.no_btts_prob ?? (match.btts_prob != null ? 1 - match.btts_prob : null) },
                    {
                      label: "DNB Home",
                      val: (match as any).dnb_home_prob
                        ?? (homeProb + awayProb > 0 ? homeProb / (homeProb + awayProb) : null),
                    },
                    {
                      label: "DNB Away",
                      val: (match as any).dnb_away_prob
                        ?? (homeProb + awayProb > 0 ? awayProb / (homeProb + awayProb) : null),
                    },
                  ].map(({ label, val }) => (
                    <div key={label} className="rounded-lg border border-border bg-background/40 p-2">
                      <div className="font-mono text-[10px] text-muted-foreground uppercase">{label}</div>
                      <div className="font-mono text-base font-bold">{val != null ? `${(val * 100).toFixed(1)}%` : "—"}</div>
                    </div>
                  ))}
                </div>
                {match.recommended_stake != null && (
                  <div className="mt-3 flex items-center justify-between rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 font-mono text-xs">
                    <span className="text-muted-foreground uppercase">Kelly Recommended Stake</span>
                    <span className="font-bold text-primary">
                      {(match.recommended_stake * 100).toFixed(2)}% of bankroll
                    </span>
                  </div>
                )}
              </div>

              <div>
                <div className="flex justify-between mb-2 font-mono text-sm">
                  <span className="text-muted-foreground uppercase">Network Confidence</span>
                  <span className="text-primary">{(confidence * 100).toFixed(1)}%</span>
                </div>
                <Progress value={confidence * 100} className="h-2 bg-muted [&>div]:bg-primary" />
              </div>

              {match.bet_side && (
                <div className="bg-background/50 rounded-lg p-4 border border-border">
                  <h4 className="font-mono text-sm font-bold uppercase mb-2 flex items-center text-primary">
                    <Zap className="w-4 h-4 mr-2" /> AI Recommendation
                  </h4>
                  <div className="flex flex-wrap gap-4 font-mono text-sm">
                    <div>
                      <span className="text-muted-foreground uppercase text-xs">Bet Side: </span>
                      <span className="font-bold uppercase">{match.bet_side}</span>
                    </div>
                    {match.entry_odds && (
                      <div>
                        <span className="text-muted-foreground uppercase text-xs">Odds: </span>
                        <span className="font-bold">{match.entry_odds}</span>
                      </div>
                    )}
                    {match.edge != null && (
                      <div>
                        <span className="text-muted-foreground uppercase text-xs">Edge: </span>
                        <span className={`font-bold ${match.edge > 0 ? "text-primary" : "text-destructive"}`}>
                          {(match.edge * 100).toFixed(2)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
              {consensusBreakdown && (
                <div className="bg-background/50 rounded-lg p-4 border border-border">
                  <h4 className="font-mono text-sm font-bold uppercase mb-2">Consensus Breakdown</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                    <div>Leader: <span className="text-primary uppercase">{consensusBreakdown.leader}</span></div>
                    <div>Home: {(consensusBreakdown.home * 100).toFixed(1)}%</div>
                    <div>Draw: {(consensusBreakdown.draw * 100).toFixed(1)}%</div>
                    <div>Away: {(consensusBreakdown.away * 100).toFixed(1)}%</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-primary" /> Child Model Analysis
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              {modelContributions.length > 0 ? modelContributions.map((model: any, index: number) => {
                const h = Number(model.home_prob ?? 0);
                const d = Number(model.draw_prob ?? 0);
                const a = Number(model.away_prob ?? 0);
                const leader = h > d && h > a ? "home" : d > a ? "draw" : "away";
                const leaderColor = leader === "home" ? "text-primary" : leader === "draw" ? "text-muted-foreground" : "text-orange-400";
                const rawConf = model.confidence;
                const confidence = (typeof rawConf === "object" && rawConf !== null)
                  ? (rawConf["1x2"] ?? Math.max(h, d, a))
                  : (typeof rawConf === "number" && !isNaN(rawConf) ? rawConf : Math.max(h, d, a));
                const weight = model.model_weight ?? model.weight ?? (1 / Math.max(1, modelContributions.length));
                return (
                  <div key={`${model.model_name}-${index}`} className="rounded-lg border border-border bg-background/40 p-3 space-y-2">
                    <div className="flex items-center justify-between font-mono text-xs">
                      <div className="font-bold uppercase truncate">{model.model_name ?? model.model ?? `Model ${index + 1}`}</div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={`text-[9px] uppercase ${leaderColor}`}>{leader}</Badge>
                        <span className="text-muted-foreground">wt={((weight) * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-1 font-mono text-xs text-center">
                      <div className={`rounded p-1.5 ${leader === "home" ? "bg-primary/10 border border-primary/30" : "bg-background/60 border border-border/40"}`}>
                        <div className="text-[9px] text-muted-foreground uppercase">Home</div>
                        <div className="font-bold">{(h * 100).toFixed(1)}%</div>
                      </div>
                      <div className={`rounded p-1.5 ${leader === "draw" ? "bg-muted/20 border border-border" : "bg-background/60 border border-border/40"}`}>
                        <div className="text-[9px] text-muted-foreground uppercase">Draw</div>
                        <div className="font-bold">{(d * 100).toFixed(1)}%</div>
                      </div>
                      <div className={`rounded p-1.5 ${leader === "away" ? "bg-orange-400/10 border border-orange-400/30" : "bg-background/60 border border-border/40"}`}>
                        <div className="text-[9px] text-muted-foreground uppercase">Away</div>
                        <div className="font-bold">{(a * 100).toFixed(1)}%</div>
                      </div>
                    </div>
                    <Progress value={confidence * 100} className="h-1 bg-muted [&>div]:bg-primary/60" />
                    <div className="font-mono text-[9px] text-muted-foreground text-right">
                      confidence {(confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                );
              }) : (
                <div className="text-center py-6 space-y-2">
                  <div className="font-mono text-muted-foreground text-sm">No model breakdown available yet.</div>
                  <div className="font-mono text-muted-foreground text-xs">Run the ML ensemble for this match to see child model analysis.</div>
                </div>
              )}
            </CardContent>
          </Card>

          {headToHead && headToHead.count > 0 && (
            <Card className="bg-card/50 backdrop-blur border-border">
              <CardHeader className="border-b border-border/50 pb-4">
                <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-primary" /> Head to Head
                  <Badge variant="outline" className="font-mono text-[10px] ml-1">{headToHead.count} matches</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-2">
                {headToHead.matches?.map((h2h: any, i: number) => {
                  const isHome = h2h.home_team === match.home_team;
                  const outcome = h2h.outcome;
                  const resultLabel = outcome === "H" ? (isHome ? "W" : "L") : outcome === "A" ? (isHome ? "L" : "W") : "D";
                  const resultColor = resultLabel === "W" ? "text-primary" : resultLabel === "L" ? "text-destructive" : "text-muted-foreground";
                  return (
                    <div key={i} className="flex items-center justify-between font-mono text-xs rounded-lg border border-border bg-background/40 px-3 py-2 gap-2">
                      <div className="flex-1 text-right truncate text-muted-foreground">{h2h.home_team}</div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <span className="font-bold text-sm px-2 py-0.5 bg-background/60 border border-border rounded">{h2h.score ?? "?"}</span>
                        <span className={`font-bold text-[10px] uppercase ${resultColor}`}>{resultLabel}</span>
                      </div>
                      <div className="flex-1 text-left truncate text-muted-foreground">{h2h.away_team}</div>
                      <div className="text-[9px] text-muted-foreground flex-shrink-0">
                        {h2h.kickoff_time ? new Date(h2h.kickoff_time).getFullYear() : ""}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {consensus && (
            <Card className="bg-card/50 backdrop-blur border-border">
              <CardHeader className="border-b border-border/50 pb-4">
                <CardTitle className="font-mono uppercase flex items-center">
                  <ShieldCheck className="w-5 h-5 mr-2 text-secondary" />
                  Validator Consensus
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-background rounded-lg border border-border">
                    <div className="font-mono text-xs text-muted-foreground uppercase mb-1">Active Nodes</div>
                    <div className="text-xl font-bold font-mono">{consensus.validators?.count ?? 0}</div>
                  </div>
                  <div className="p-4 bg-background rounded-lg border border-border">
                    <div className="font-mono text-xs text-muted-foreground uppercase mb-1">Total Influence</div>
                    <div className="text-xl font-bold font-mono text-secondary">
                      {(consensus.validators?.total_influence ?? 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="p-4 bg-background rounded-lg border border-border">
                    <div className="font-mono text-xs text-muted-foreground uppercase mb-1">Status</div>
                    <Badge variant="outline" className="font-mono uppercase text-xs">{consensus.status}</Badge>
                  </div>
                  <div className="p-4 bg-background rounded-lg border border-border">
                    <div className="font-mono text-xs text-muted-foreground uppercase mb-1">Final Home%</div>
                    <div className="text-xl font-bold font-mono text-primary">
                      {((consensus.final?.p_home ?? 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card className="bg-card/50 backdrop-blur border-primary/20 shadow-[0_0_30px_rgba(0,255,255,0.05)]">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase flex items-center">
                <Coins className="w-5 h-5 mr-2 text-secondary" />
                Stake VITCoin
              </CardTitle>
              <CardDescription className="font-mono">
                Balance: {Number(wallet?.vitcoin_balance ?? 0).toLocaleString()} VIT
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              {match.actual_outcome ? (
                <div className="text-center p-4 bg-muted/30 rounded-lg border border-border font-mono text-sm text-muted-foreground">
                  MARKET_CLOSED
                </div>
              ) : (
                <>
                  <div className="space-y-3">
                    <div>
                      <p className="text-[10px] font-mono text-muted-foreground uppercase mb-2">1X2 — Match Result</p>
                      <div className="grid grid-cols-3 gap-2">
                        {([
                          { side: "home" as StakeSide, label: "1", sublabel: match.home_team, odds: match.odds?.home ?? 2.0 },
                          { side: "draw" as StakeSide, label: "X", sublabel: "Draw", odds: match.odds?.draw ?? 3.3 },
                          { side: "away" as StakeSide, label: "2", sublabel: match.away_team, odds: match.odds?.away ?? 3.5 },
                        ]).map(({ side, label, sublabel, odds }) => (
                          <button
                            key={side}
                            type="button"
                            onClick={() => setSelectedSide(side)}
                            className={`flex flex-col items-center gap-0.5 p-3 rounded-lg border font-mono transition-all ${
                              selectedSide === side
                                ? "border-primary bg-primary/10 shadow-[0_0_12px_rgba(0,255,255,0.15)]"
                                : "border-border bg-card/50 hover:border-primary/40"
                            }`}
                          >
                            <span className="text-base font-bold text-primary">{label}</span>
                            <span className="text-[9px] text-muted-foreground truncate w-full text-center">{sublabel}</span>
                            <span className="text-[10px] text-foreground font-semibold">{odds.toFixed(2)}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                    {(match as any).over_25_prob != null && (
                      <div>
                        <p className="text-[10px] font-mono text-muted-foreground uppercase mb-2">Over / Under 2.5 Goals</p>
                        <div className="grid grid-cols-2 gap-2">
                          {([
                            { side: "over_25" as StakeSide, label: "Over 2.5", prob: (match as any).over_25_prob },
                            { side: "under_25" as StakeSide, label: "Under 2.5", prob: (match as any).under_25_prob ?? (1 - ((match as any).over_25_prob ?? 0.5)) },
                          ]).map(({ side, label, prob }) => (
                            <button
                              key={side}
                              type="button"
                              onClick={() => setSelectedSide(side)}
                              className={`flex flex-col items-center gap-0.5 p-3 rounded-lg border font-mono transition-all ${
                                selectedSide === side
                                  ? "border-primary bg-primary/10 shadow-[0_0_12px_rgba(0,255,255,0.15)]"
                                  : "border-border bg-card/50 hover:border-primary/40"
                              }`}
                            >
                              <span className="text-sm font-bold text-foreground">{label}</span>
                              <span className="text-[10px] text-muted-foreground">{(prob * 100).toFixed(0)}% prob</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    {(match as any).btts_prob != null && (
                      <div>
                        <p className="text-[10px] font-mono text-muted-foreground uppercase mb-2">Both Teams to Score</p>
                        <div className="grid grid-cols-2 gap-2">
                          {([
                            { side: "btts_yes" as StakeSide, label: "BTTS Yes", prob: (match as any).btts_prob },
                            { side: "btts_no" as StakeSide, label: "BTTS No", prob: (match as any).no_btts_prob ?? (1 - ((match as any).btts_prob ?? 0.5)) },
                          ]).map(({ side, label, prob }) => (
                            <button
                              key={side}
                              type="button"
                              onClick={() => setSelectedSide(side)}
                              className={`flex flex-col items-center gap-0.5 p-3 rounded-lg border font-mono transition-all ${
                                selectedSide === side
                                  ? "border-primary bg-primary/10 shadow-[0_0_12px_rgba(0,255,255,0.15)]"
                                  : "border-border bg-card/50 hover:border-primary/40"
                              }`}
                            >
                              <span className="text-sm font-bold text-foreground">{label}</span>
                              <span className="text-[10px] text-muted-foreground">{(prob * 100).toFixed(0)}% prob</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div>
                    <label className="text-xs font-mono text-muted-foreground uppercase mb-1 block">Amount (VITCoin)</label>
                    <Input
                      type="number"
                      value={stakeAmount}
                      onChange={(e) => setStakeAmount(e.target.value)}
                      className="font-mono text-lg bg-background/50 border-primary/20 h-12"
                      min="1"
                    />
                  </div>
                  <Button
                    className="w-full h-12 font-mono uppercase tracking-widest text-sm"
                    onClick={handleStake}
                    disabled={stake.isPending || !selectedSide}
                  >
                    {stake.isPending ? "PROCESSING_TX..." : "EXECUTE_STAKE"}
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <TrendingUp className="w-4 h-4 mr-2" />
                Match Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3 font-mono text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground uppercase text-xs">Kickoff</span>
                <span>{format(new Date(match.kickoff_time), "yyyy-MM-dd HH:mm")}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground uppercase text-xs">League</span>
                <span className="truncate ml-4">{match.league}</span>
              </div>
              {match.over_25_prob != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">Over 2.5</span>
                  <span>{(match.over_25_prob * 100).toFixed(1)}%</span>
                </div>
              )}
              {match.btts_prob != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">BTTS Yes</span>
                  <span>{(match.btts_prob * 100).toFixed(1)}%</span>
                </div>
              )}
              {recentForm?.home?.form && recentForm.home.form !== "N/A" && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">Home Form</span>
                  <span>{recentForm.home.form}</span>
                </div>
              )}
              {recentForm?.away?.form && recentForm.away.form !== "N/A" && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">Away Form</span>
                  <span>{recentForm.away.form}</span>
                </div>
              )}
              {headToHead && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">H2H Matches</span>
                  <span>{headToHead.count ?? 0}</span>
                </div>
              )}
              {match.clv != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">CLV</span>
                  <span className={match.clv > 0 ? "text-primary" : "text-destructive"}>{match.clv.toFixed(3)}</span>
                </div>
              )}
              {match.profit != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">P&L</span>
                  <span className={match.profit >= 0 ? "text-primary" : "text-destructive"}>
                    {match.profit >= 0 ? "+" : ""}{match.profit.toFixed(2)}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
        </TabsContent>

        <TabsContent value="injuries" className="mt-6">
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader>
              <CardTitle className="font-mono uppercase">Injury Reports</CardTitle>
              <CardDescription>Latest injury updates for participating teams</CardDescription>
            </CardHeader>
            <CardContent>
              {injuries?.injuries?.length ? (
                <div className="space-y-4">
                  {injuries.injuries.map((injury: any) => (
                    <div key={injury.id} className="border border-border rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-semibold">{injury.player_name}</h4>
                          <p className="text-sm text-muted-foreground">{injury.team_name}</p>
                          <p className="text-sm">{injury.injury_type} - {injury.status}</p>
                        </div>
                        <Badge variant={injury.status === 'doubtful' ? 'destructive' : 'secondary'}>
                          {injury.status}
                        </Badge>
                      </div>
                      {injury.expected_return && (
                        <p className="text-xs text-muted-foreground mt-2">
                          Expected return: {injury.expected_return}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No injury reports available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit" className="mt-6">
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader>
              <CardTitle className="font-mono uppercase">Odds Audit Log</CardTitle>
              <CardDescription>Historical changes to odds and market data</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                Audit log feature coming soon
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
