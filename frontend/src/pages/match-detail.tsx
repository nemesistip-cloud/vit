import { useState } from "react";
import { useParams, useLocation } from "wouter";
import {
  useGetMatch, useGetConsensusPrediction, useStakeOnPrediction, useGetWallet,
  useGetOddsInjuries, useGetOddsAuditLog,
} from "@/api-client";
import { AIInsightComparison } from "@/components/AIInsightComparison";
import { MatchAssistantCard } from "@/components/MatchAssistantCard";
import { ProbabilityTrio } from "@/components/ProbabilityGauge";
import { ModelInterpretation } from "@/components/ModelInterpretation";
import { ModelVsMarket } from "@/components/ModelVsMarket";
import { AiSourceComparison } from "@/components/AiSourceComparison";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { BrainCircuit, ShieldCheck, ChevronLeft, Zap, Coins, TrendingUp, Target, BarChart2, Radio, Hash, Grid3x3, Syringe, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import { Progress } from "@/components/ui/progress";

const CS_LINES = [
  "1-0","2-0","2-1","3-0","3-1","3-2",
  "0-1","0-2","1-2","0-3","1-3","2-3",
  "0-0","1-1","2-2","3-3",
] as const;
type CSLine = typeof CS_LINES[number];

export default function MatchDetailPage() {
  const params = useParams();
  const [, setLocation] = useLocation();
  const matchId = params.id || "";

  const { data: match, isLoading, isError } = useGetMatch(matchId);
  const { data: consensus } = useGetConsensusPrediction(matchId);
  const { data: wallet } = useGetWallet();
  const stake = useStakeOnPrediction();
  const { data: injuries } = useGetOddsInjuries({ team: match?.home_team });
  const { data: auditLog } = useGetOddsAuditLog();

  type StakeSide = "home" | "draw" | "away" | "over_25" | "under_25" | "btts_yes" | "btts_no" | "ah_home" | "ah_away" | `cs_${string}`;
  const [selectedSide, setSelectedSide] = useState<StakeSide | null>(null);
  const [stakeAmount, setStakeAmount] = useState("10");
  const [ahLine, setAhLine] = useState<string>("0.0");
  const [stakeTab, setStakeTab] = useState<"1x2" | "goals" | "ah" | "cs">("1x2");

  const ahLineNum = parseFloat(ahLine) || 0;

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

  if (isError) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4 font-mono">
          <div className="text-4xl text-red-500">⚠</div>
          <div className="text-muted-foreground uppercase text-sm">Failed to load match data</div>
          <div className="text-xs text-red-400/70">The intelligence network could not retrieve this match.</div>
          <Button variant="outline" className="font-mono uppercase text-xs" onClick={() => setLocation("/matches")}>
            <ChevronLeft className="w-4 h-4 mr-2" /> Return to Feed
          </Button>
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

  const matchAhLine: number | null = (match as any).ah_line ?? null;
  const ahHomeProb: number | null = (match as any).ah_home_prob ?? null;
  const ahAwayProb: number | null = (match as any).ah_away_prob ?? null;
  const csProbs: Record<string, number> | null = (match as any).cs_probs ?? null;

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
    const isAH = selectedSide === "ah_home" || selectedSide === "ah_away";
    if (isAH && isNaN(ahLineNum)) {
      toast.error("Enter a valid AH line (e.g. -0.5)");
      return;
    }
    try {
      await stake.mutateAsync({
        matchId,
        prediction: selectedSide,
        amount,
        ...(isAH ? { ah_line: ahLineNum } : {}),
      });
      toast.success(`Staked ${amount} VITCoin on ${selectedSide.toUpperCase()}`);
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

      <Card className="bg-card/90 border-primary/30 overflow-hidden relative">
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
                      {match.kickoff_time
                        ? (() => { try { return format(new Date(match.kickoff_time), "HH:mm"); } catch { return "—"; } })()
                        : "—"}
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
              <MatchAssistantCard match={match} consensus={consensus} />

              <AIInsightComparison
                matchId={matchId}
                homeTeam={match?.home_team}
                awayTeam={match?.away_team}
                league={match?.league ?? undefined}
              />

              <Card className="bg-card/60 border-border">
                <CardHeader className="border-b border-border/50 pb-4">
                  <CardTitle className="font-mono uppercase flex items-center">
                    <BrainCircuit className="w-5 h-5 mr-2 text-primary" />
                    Ensemble Intelligence</CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-6">
              <ModelInterpretation
                homeProb={homeProb}
                drawProb={drawProb}
                awayProb={awayProb}
                homeTeam={match.home_team}
                awayTeam={match.away_team}
                confidence={confidence}
                edge={(match as any).edge ?? (match as any).normalized_edge}
                betSide={match.bet_side ?? null}
                entryOdds={match.entry_odds ?? null}
                modelCount={modelContributions.length || 13}
                vitScore={(match as any).vit_score ?? null}
                vitTier={(match as any).vit_tier ?? null}
                vitComponents={(match as any).vit_components ?? null}
                agreementPct={(match as any).model_consensus?.agreement_pct ?? null}
              />
              <ProbabilityTrio
                homeProb={homeProb}
                drawProb={drawProb}
                awayProb={awayProb}
                homeLabel={match.home_team}
                awayLabel={match.away_team}
              />

              <ModelVsMarket
                homeTeam={match.home_team}
                awayTeam={match.away_team}
                homeProb={homeProb || null}
                drawProb={drawProb || null}
                awayProb={awayProb || null}
                over25Prob={match.over_25_prob ?? null}
                under25Prob={match.under_25_prob ?? null}
                bttsProb={match.btts_prob ?? null}
                noBttsProb={match.no_btts_prob ?? null}
                ahLine={matchAhLine}
                ahHomeProb={ahHomeProb}
                ahAwayProb={ahAwayProb}
                oddsHome={match.odds?.home ?? null}
                oddsDraw={match.odds?.draw ?? null}
                oddsAway={match.odds?.away ?? null}
                betSide={match.bet_side ?? null}
              />

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

          <Card className="bg-card/60 border-border">
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
            <Card className="bg-card/60 border-border">
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
            <Card className="bg-card/60 border-border">
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
          <Card className="bg-card/60 border-primary/20 shadow-[0_0_30px_rgba(0,255,255,0.05)]">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase flex items-center">
                <Coins className="w-5 h-5 mr-2 text-secondary" />
                Stake VITCoin
              </CardTitle>
              <CardDescription className="font-mono">
                Balance: {Number(wallet?.vitcoin_balance ?? 0).toLocaleString()} VIT
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              {match.actual_outcome ? (
                <div className="text-center p-4 bg-muted/30 rounded-lg border border-border font-mono text-sm text-muted-foreground">
                  MARKET_CLOSED
                </div>
              ) : (
                <>
                  {/* Market selector tabs */}
                  <div className="flex gap-1 bg-background/60 rounded-lg p-1 border border-border/50">
                    {(["1x2", "goals", "ah", "cs"] as const).map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => { setStakeTab(t); setSelectedSide(null); }}
                        className={`flex-1 text-[10px] font-mono uppercase py-1.5 rounded transition-all ${
                          stakeTab === t
                            ? "bg-primary/20 text-primary border border-primary/40 shadow-[0_0_8px_rgba(0,255,255,0.1)]"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {t === "1x2" ? "1X2" : t === "goals" ? "Goals" : t === "ah" ? "Asian HCP" : "Correct Score"}
                      </button>
                    ))}
                  </div>

                  {/* 1X2 panel */}
                  {stakeTab === "1x2" && (
                    <div className="grid grid-cols-3 gap-2">
                      {([
                        { side: "home" as StakeSide, label: "1", sublabel: match.home_team, odds: match.odds?.home ?? 2.0, prob: homeProb },
                        { side: "draw" as StakeSide, label: "X", sublabel: "Draw", odds: match.odds?.draw ?? 3.3, prob: drawProb },
                        { side: "away" as StakeSide, label: "2", sublabel: match.away_team, odds: match.odds?.away ?? 3.5, prob: awayProb },
                      ]).map(({ side, label, sublabel, odds, prob }) => (
                        <button key={side} type="button" onClick={() => setSelectedSide(side)}
                          className={`flex flex-col items-center gap-0.5 p-3 rounded-lg border font-mono transition-all ${
                            selectedSide === side
                              ? "border-primary bg-primary/10 shadow-[0_0_12px_rgba(0,255,255,0.15)]"
                              : "border-border bg-card/50 hover:border-primary/40"
                          }`}
                        >
                          <span className="text-base font-bold text-primary">{label}</span>
                          <span className="text-[9px] text-muted-foreground truncate w-full text-center">{sublabel}</span>
                          <span className="text-[10px] text-foreground font-semibold">{odds.toFixed(2)}</span>
                          <span className="text-[9px] text-muted-foreground">{(prob * 100).toFixed(0)}%</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Goals panel */}
                  {stakeTab === "goals" && (
                    <div className="space-y-2">
                      {(match as any).over_25_prob != null && (
                        <div>
                          <p className="text-[10px] font-mono text-muted-foreground uppercase mb-2">Over / Under 2.5</p>
                          <div className="grid grid-cols-2 gap-2">
                            {([
                              { side: "over_25" as StakeSide, label: "Over 2.5", prob: (match as any).over_25_prob },
                              { side: "under_25" as StakeSide, label: "Under 2.5", prob: (match as any).under_25_prob ?? (1 - ((match as any).over_25_prob ?? 0.5)) },
                            ]).map(({ side, label, prob }) => (
                              <button key={side} type="button" onClick={() => setSelectedSide(side)}
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
                              <button key={side} type="button" onClick={() => setSelectedSide(side)}
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
                      {(match as any).over_25_prob == null && (match as any).btts_prob == null && (
                        <div className="text-center py-4 text-muted-foreground font-mono text-xs">
                          Goals market data not available for this fixture.
                        </div>
                      )}
                    </div>
                  )}

                  {/* Asian Handicap panel */}
                  {stakeTab === "ah" && (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <div className="flex-1">
                          <label className="text-[10px] font-mono text-muted-foreground uppercase mb-1 block">
                            AH Line (Home) {matchAhLine != null && <span className="text-primary">· AI: {matchAhLine > 0 ? "+" : ""}{matchAhLine}</span>}
                          </label>
                          <Input
                            type="number"
                            step="0.25"
                            value={ahLine}
                            onChange={(e) => setAhLine(e.target.value)}
                            className="font-mono h-9 text-sm bg-background/50 border-border"
                            placeholder="e.g. -0.5"
                          />
                        </div>
                        {matchAhLine != null && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="font-mono text-[10px] mt-5"
                            onClick={() => setAhLine(String(matchAhLine))}
                          >
                            Use AI Line
                          </Button>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        {([
                          { side: "ah_home" as StakeSide, label: `${match.home_team}`, sublabel: `AH ${ahLineNum > 0 ? "+" : ""}${ahLineNum}`, prob: ahHomeProb },
                          { side: "ah_away" as StakeSide, label: `${match.away_team}`, sublabel: `AH ${-ahLineNum > 0 ? "+" : ""}${-ahLineNum}`, prob: ahAwayProb },
                        ]).map(({ side, label, sublabel, prob }) => (
                          <button key={side} type="button" onClick={() => setSelectedSide(side)}
                            className={`flex flex-col items-center gap-1 p-3 rounded-lg border font-mono transition-all ${
                              selectedSide === side
                                ? "border-primary bg-primary/10 shadow-[0_0_12px_rgba(0,255,255,0.15)]"
                                : "border-border bg-card/50 hover:border-primary/40"
                            }`}
                          >
                            <span className="text-xs font-bold text-foreground truncate w-full text-center">{label}</span>
                            <span className="text-[10px] text-primary font-semibold">{sublabel}</span>
                            {prob != null && (
                              <span className="text-[9px] text-muted-foreground">{(prob * 100).toFixed(0)}% prob</span>
                            )}
                          </button>
                        ))}
                      </div>
                      <div className="text-[9px] font-mono text-muted-foreground bg-muted/20 rounded p-2 border border-border/40">
                        Asian Handicap: Push returns stake if margin equals the line. Positive line = underdog advantage.
                      </div>
                    </div>
                  )}

                  {/* Correct Score panel */}
                  {stakeTab === "cs" && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-[10px] font-mono text-muted-foreground uppercase flex items-center gap-1">
                          <Grid3x3 className="w-3 h-3" /> Select final score
                        </p>
                        {selectedSide?.startsWith("cs_") && (
                          <Badge variant="outline" className="font-mono text-[9px] text-primary border-primary/40">
                            {(selectedSide as string).replace("cs_", "").replace("-", " – ")}
                          </Badge>
                        )}
                      </div>
                      <div className="grid grid-cols-4 gap-1.5">
                        {CS_LINES.map((score) => {
                          const key = `cs_${score}` as StakeSide;
                          const prob = csProbs?.[`cs_${score}`] ?? csProbs?.[score] ?? null;
                          const isSelected = selectedSide === key;
                          const [h, a] = score.split("-").map(Number);
                          const isHome = h > a, isDraw = h === a, isAway = a > h;
                          const accentCls = isHome
                            ? "border-primary/50 text-primary"
                            : isDraw
                            ? "border-muted-foreground/40 text-muted-foreground"
                            : "border-orange-400/50 text-orange-400";
                          return (
                            <button key={score} type="button" onClick={() => setSelectedSide(key)}
                              className={`flex flex-col items-center p-2 rounded border font-mono text-xs transition-all ${
                                isSelected
                                  ? `bg-primary/10 border-primary shadow-[0_0_8px_rgba(0,255,255,0.12)]`
                                  : `bg-card/40 ${accentCls} hover:bg-muted/20`
                              }`}
                            >
                              <span className={`font-bold text-sm ${isSelected ? "text-primary" : ""}`}>{score}</span>
                              {prob != null && (
                                <span className="text-[8px] text-muted-foreground">{(prob * 100).toFixed(1)}%</span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                      <div className="text-[9px] font-mono text-muted-foreground bg-muted/20 rounded p-2 border border-border/40">
                        Correct Score pays out only if the exact final score matches. Higher odds, higher risk.
                      </div>
                    </div>
                  )}

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
                  {selectedSide && (
                    <div className="rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 font-mono text-xs flex items-center justify-between">
                      <span className="text-muted-foreground uppercase">Selected</span>
                      <span className="text-primary font-bold uppercase">
                        {(selectedSide as string).startsWith("cs_")
                          ? `Score ${(selectedSide as string).replace("cs_", "").replace("-", " – ")}`
                          : (selectedSide as string).replace(/_/g, " ")}
                        {(selectedSide === "ah_home" || selectedSide === "ah_away") && ` (${ahLineNum > 0 ? "+" : ""}${ahLineNum})`}
                      </span>
                    </div>
                  )}
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

          <Card className="bg-card/60 border-border">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <TrendingUp className="w-4 h-4 mr-2" />
                Match Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3 font-mono text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground uppercase text-xs">Kickoff</span>
                <span>
                  {match.kickoff_time
                    ? (() => { try { return format(new Date(match.kickoff_time), "yyyy-MM-dd HH:mm"); } catch { return match.kickoff_time; } })()
                    : "—"}
                </span>
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
          <Card className="bg-card/60 border-border">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase flex items-center gap-2">
                <Syringe className="w-4 h-4 text-primary" />
                Injury &amp; Team News
              </CardTitle>
              <CardDescription className="font-mono text-xs">
                Player availability updates for {match.home_team} vs {match.away_team}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              {injuries?.injuries?.length ? (
                <div className="space-y-3">
                  {injuries.injuries.map((injury: any) => {
                    const statusColor =
                      injury.status === "out"      ? "bg-red-500/10 border-red-500/25 text-red-400" :
                      injury.status === "doubtful" ? "bg-amber-500/10 border-amber-500/25 text-amber-400" :
                      "bg-emerald-500/10 border-emerald-500/25 text-emerald-400";
                    return (
                      <div key={injury.id} className="flex items-start gap-3 rounded-lg border border-border bg-background/40 p-3">
                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="font-mono text-sm font-bold text-foreground truncate">
                            {injury.player ?? injury.player_name ?? "Unknown Player"}
                          </div>
                          <div className="font-mono text-xs text-muted-foreground">
                            {injury.team ?? injury.team_name ?? ""}
                          </div>
                          {injury.note && (
                            <div className="font-mono text-[11px] text-muted-foreground/70 leading-relaxed">{injury.note}</div>
                          )}
                          {(injury.injury_type || injury.status) && !injury.note && (
                            <div className="font-mono text-[11px] text-muted-foreground/70">
                              {[injury.injury_type, injury.status].filter(Boolean).join(" — ")}
                            </div>
                          )}
                          {injury.added_at && (
                            <div className="font-mono text-[9px] text-muted-foreground/40 uppercase tracking-wide">
                              Added {new Date(injury.added_at).toLocaleDateString()}
                            </div>
                          )}
                        </div>
                        <Badge variant="outline" className={`font-mono text-[10px] uppercase flex-shrink-0 ${statusColor}`}>
                          {injury.status ?? "reported"}
                        </Badge>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 space-y-4 text-center">
                  <div className="w-12 h-12 rounded-full bg-muted/20 border border-border flex items-center justify-center">
                    <AlertCircle className="w-6 h-6 text-muted-foreground/50" />
                  </div>
                  <div className="space-y-1">
                    <p className="font-mono text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                      No Injury Reports
                    </p>
                    <p className="font-mono text-xs text-muted-foreground/60 max-w-xs">
                      No injuries or suspensions have been logged for this fixture. Admins can add team news via the Odds Intel panel.
                    </p>
                  </div>
                  <Button variant="outline" size="sm" className="font-mono text-xs uppercase" onClick={() => setLocation("/odds")}>
                    Go to Odds Intel
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit" className="mt-6">
          <Card className="bg-card/60 border-border">
            <CardHeader>
              <CardTitle className="font-mono uppercase">Odds Audit Log</CardTitle>
              <CardDescription className="font-mono text-xs">
                Historical admin actions on odds and market data
                {auditLog?.total != null && (
                  <span className="ml-2 text-muted-foreground/60">({auditLog.total} entries)</span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {!auditLog?.log?.length ? (
                <div className="text-center py-8 text-muted-foreground font-mono text-sm">
                  No audit entries found
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="border-b border-border/50 text-muted-foreground">
                        <th className="text-left px-4 py-2 uppercase">Time</th>
                        <th className="text-left px-4 py-2 uppercase">Action</th>
                        <th className="text-left px-4 py-2 uppercase">Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLog.log.map((entry: any, i: number) => (
                        <tr key={i} className="border-b border-border/20 hover:bg-muted/10 transition-colors">
                          <td className="px-4 py-2 text-muted-foreground whitespace-nowrap">
                            {entry.ts ? new Date(entry.ts).toLocaleString() : "—"}
                          </td>
                          <td className="px-4 py-2 text-primary font-bold uppercase">{entry.action ?? "—"}</td>
                          <td className="px-4 py-2 text-muted-foreground truncate max-w-[260px]">
                            {entry.details ? JSON.stringify(entry.details).slice(0, 80) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
