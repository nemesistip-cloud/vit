import { useState } from "react";
import { useParams, useLocation } from "wouter";
import {
  useGetMatch, useGetConsensusPrediction, useStakeOnPrediction, useGetWallet,
  useGetOddsInjuries, useGetOddsAuditLog, useGenerateSlip
} from "@/api-client";
import { AIInsightComparison } from "@/components/AIInsightComparison";
import { MatchAssistantCard } from "@/components/MatchAssistantCard";
import { PredictionFlow } from "@/components/PredictionFlow";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { shareToTelegram } from "@/lib/twa";
import { toast } from "sonner";
import { BrainCircuit, ShieldCheck, ChevronLeft, Zap, Coins, TrendingUp, Target, BarChart2, Radio, Hash, Grid3x3, Star } from "lucide-react";
import { format } from "date-fns";
import { Progress } from "@/components/ui/progress";

const gradeColor = (grade: string) => {
  if (grade === "A") return "text-emerald-400 border-emerald-400/40 bg-emerald-400/10";
  if (grade === "B") return "text-primary border-primary/40 bg-primary/10";
  if (grade === "C") return "text-yellow-400 border-yellow-400/40 bg-yellow-400/10";
  return "text-muted-foreground border-border bg-background/40";
};

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

  const { data: match, isLoading } = useGetMatch(matchId);
  const { data: consensus } = useGetConsensusPrediction(matchId);
  const { data: wallet } = useGetWallet();
  const stake = useStakeOnPrediction();
  const generateSlip = useGenerateSlip();
  const { data: injuries } = useGetOddsInjuries({ team: match?.home_team });
  const { data: auditLog } = useGetOddsAuditLog();

  type StakeSide = "home" | "draw" | "away" | "over_25" | "under_25" | "btts_yes" | "btts_no" | "ah_home" | "ah_away" | `cs_${string}`;
  const [selectedSide, setSelectedSide] = useState<StakeSide | null>(null);
  const [stakeAmount, setStakeAmount] = useState("10");
  const [ahLine, setAhLine] = useState<string>("0.0");
  const [stakeTab, setStakeTab] = useState<"1x2" | "goals" | "ah" | "cs">("1x2");
  const [showPredict, setShowPredict] = useState(false);

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

  if (!match) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4 font-mono">
          <div className="text-4xl text-muted-foreground">404</div>
          <div className="text-muted-foreground uppercase text-sm">Match not found in the analytics network</div>
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
  const matchQuality: { score: number; grade: string; label: string; home_advantage_bias?: number; components?: Record<string, number> } | null
    = (match as any).match_quality_rating ?? null;
  const marketConf: Record<string, number> | null = (match as any).market_confidence ?? null;

  const handleStake = async () => {
    if (!selectedSide) {
      toast.error("Select a prediction first");
      return;
    }
    try {
      await stake.mutateAsync({
        matchId,
        prediction: selectedSide,
        amount: parseFloat(stakeAmount),
        ah_line: (selectedSide === "ah_home" || selectedSide === "ah_away") ? ahLineNum : undefined
      });
      toast.success("Stake executed successfully");
    } catch (e: any) {
      toast.error(e.message || "Stake failed");
    }
  };

  const handleGenerateSlip = async (provider?: string) => {
    if (!selectedSide) {
      toast.error("Select a selection first");
      return;
    }
    try {
      const res = await generateSlip.mutateAsync({
        match_id: matchId,
        prediction: selectedSide,
        provider
      });

      toast.success("Affiliate slip generated successfully");

      // In a real app, we might open a modal or redirect.
      // For this prototype, we'll open the first available link.
      const links = Object.values(res.affiliate_links);
      if (links.length > 0) {
        window.open(links[0], "_blank");
      }
    } catch (e: any) {
      toast.error(e.message || "Failed to generate slip");
    }
  };

  const isSports = match?.market_type === "sports" || match?.sport !== "niche";

  return (
    <div className="space-y-6">
      <Button variant="ghost" className="font-mono text-xs uppercase tracking-wider mb-2" onClick={() => setLocation("/matches")}>
        <ChevronLeft className="w-4 h-4 mr-2" /> Back to Feed
      </Button>

      <Card className="bg-card/80  border-primary/30 overflow-hidden relative">
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

      <Tabs defaultValue="analytics" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="injuries">Injuries</TabsTrigger>
          <TabsTrigger value="audit">Audit Log</TabsTrigger>
        </TabsList>

        <TabsContent value="analytics" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <MatchAssistantCard match={match} consensus={consensus} />

              <AIInsightComparison
                matchId={matchId}
                homeTeam={match?.home_team}
                awayTeam={match?.away_team}
                league={match?.league ?? undefined}
              />

              <Card className="bg-card/50  border-border">
                <CardHeader className="border-b border-border/50 pb-4">
                  <CardTitle className="font-mono uppercase flex items-center">
                    <BrainCircuit className="w-5 h-5 mr-2 text-primary" />
                    Ensemble Analytics</CardTitle>
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

              {/* Match Quality Rating */}
              {matchQuality && (
                <div className={`rounded-lg border p-3 ${gradeColor(matchQuality.grade)}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-mono text-[10px] uppercase flex items-center gap-1">
                      <Star className="w-3 h-3" /> Match Quality Rating
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`font-mono text-lg font-bold`}>{matchQuality.score}</span>
                      <Badge variant="outline" className={`font-mono text-xs font-bold ${gradeColor(matchQuality.grade)}`}>
                        {matchQuality.grade} — {matchQuality.label}
                      </Badge>
                    </div>
                  </div>
                  <Progress
                    value={matchQuality.score}
                    className="h-1.5 bg-muted/30"
                  />
                  {matchQuality.components && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-1 mt-2">
                      {Object.entries(matchQuality.components).map(([k, v]) => (
                        <div key={k} className="text-center">
                          <div className="font-mono text-[9px] uppercase opacity-70">{k.replace(/_/g, " ")}</div>
                          <div className="font-mono text-xs font-bold">{v.toFixed(1)}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Extended Market Probabilities with per-market confidence */}
              <div>
                <div className="font-mono text-[10px] text-muted-foreground uppercase mb-2 flex items-center gap-1">
                  <Target className="w-3 h-3" /> Market Probabilities
                  {marketConf && <span className="ml-auto text-[9px] opacity-60">+ conf.</span>}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center">
                  {[
                    { label: "Over 2.5", val: match.over_25_prob, confKey: "over_under" },
                    { label: "Under 2.5", val: match.under_25_prob ?? (match.over_25_prob != null ? 1 - match.over_25_prob : null), confKey: "over_under" },
                    { label: "Over 1.5", val: (match as any).over_15_prob, confKey: "over_under" },
                    { label: "Over 3.5", val: (match as any).over_35_prob, confKey: "over_under" },
                    { label: "BTTS Yes", val: match.btts_prob, confKey: "btts" },
                    { label: "BTTS No",  val: match.no_btts_prob ?? (match.btts_prob != null ? 1 - match.btts_prob : null), confKey: "btts" },
                    {
                      label: "DNB Home",
                      val: (match as any).dnb_home_prob
                        ?? (homeProb + awayProb > 0 ? homeProb / (homeProb + awayProb) : null),
                      confKey: "1x2",
                    },
                    {
                      label: "DNB Away",
                      val: (match as any).dnb_away_prob
                        ?? (homeProb + awayProb > 0 ? awayProb / (homeProb + awayProb) : null),
                      confKey: "1x2",
                    },
                  ].map(({ label, val, confKey }) => {
                    const conf = marketConf?.[confKey];
                    return (
                      <div key={label} className="rounded-lg border border-border bg-background/40 p-2">
                        <div className="text-[10px] text-muted-foreground uppercase mb-1">{label}</div>
                        <div className="text-sm font-bold font-mono">
                          {val != null ? `${(val * 100).toFixed(1)}%` : "—"}
                        </div>
                        {conf != null && (
                          <div className="mt-1">
                            <div className="h-0.5 w-full bg-muted overflow-hidden rounded-full">
                              <div className="h-full bg-primary" style={{ width: `${conf * 100}%` }} />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {match.recommended_stake != null && (
                <div className="flex items-center justify-between p-3 rounded-lg border border-primary/20 bg-primary/5">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-primary" />
                    <span className="font-mono text-xs uppercase tracking-wider">Kelly Recommended Stake</span>
                  </div>
                  <span className="font-mono font-bold text-primary">{(match.recommended_stake * 100).toFixed(2)}% of bankroll</span>
                </div>
              )}

              <div>
                <div className="flex justify-between mb-2 font-mono text-sm">
                  <span className="text-muted-foreground uppercase">Network Confidence</span>
                  <span className="text-primary">{(confidence * 100).toFixed(1)}%</span>
                </div>
                <Progress value={confidence * 100} className="h-2" />
              </div>

              {match.bet_side && (
                <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 flex items-center justify-between">
                  <div>
                    <div className="font-mono text-[10px] text-primary uppercase mb-1">AI Recommendation</div>
                    <div className="font-mono text-lg font-bold uppercase tracking-widest flex items-center gap-2">
                      Position Side: <span className="text-primary">{match.bet_side}</span>
                    </div>
                    {match.entry_odds && <div className="font-mono text-xs text-muted-foreground uppercase">Odds: {match.entry_odds.toFixed(2)}</div>}
                    {match.edge != null && (
                      <div className={`font-mono text-xs uppercase ${match.edge > 0 ? "text-primary" : "text-destructive"}`}>
                        Edge: {(match.edge * 100).toFixed(2)}%
                      </div>
                    )}
                  </div>
                  <ShieldCheck className="w-10 h-10 text-primary/40" />
                </div>
              )}

              {consensusBreakdown && (
                <div className="space-y-2 pt-4 border-t border-border/50">
                  <div className="font-mono text-[10px] text-muted-foreground uppercase flex items-center gap-1">
                    <Hash className="w-3 h-3" /> Consensus Breakdown
                  </div>
                  <div className="grid grid-cols-4 gap-2 font-mono text-[10px] uppercase text-center">
                    <div className="text-primary font-bold">Leader: {consensusBreakdown.leader}</div>
                    <div>Home: {(consensusBreakdown.home * 100).toFixed(1)}%</div>
                    <div>Draw: {(consensusBreakdown.draw * 100).toFixed(1)}%</div>
                    <div>Away: {(consensusBreakdown.away * 100).toFixed(1)}%</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card/50  border-border">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-primary" /> Child Model Analytics
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
                const confidence = typeof rawConf === 'number' ? rawConf : (parseFloat(rawConf) || 0.5);

                return (
                  <div key={index} className="p-3 rounded-lg border border-border/50 bg-background/30 space-y-2">
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2">
                        {model.model_key ?? model.name ?? "Ensemble_Node"}
                        <Badge variant="outline" className={`text-[8px] h-4 ${leaderColor} border-current/20`}>{leader}</Badge>
                      </div>
                      {model.weight && <span className="font-mono text-[9px] text-muted-foreground">weight: {model.weight.toFixed(3)}</span>}
                    </div>
                    <div className="grid grid-cols-3 gap-2 font-mono text-[10px] text-center">
                      <div>
                        <div className="text-muted-foreground opacity-60">HOME</div>
                        <div className="font-bold">{(h * 100).toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground opacity-60">DRAW</div>
                        <div className="font-bold">{(d * 100).toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground opacity-60">AWAY</div>
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
                  <div className="font-mono text-muted-foreground text-xs">Run the ML ensemble for this match to see child model analytics.</div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="font-mono text-[10px] uppercase border-primary/30 hover:border-primary hover:bg-primary/10 text-primary transition-all mt-2"
                    onClick={() => setShowPredict(true)}
                  >
                    <Zap className="w-3 h-3 mr-1.5" />
                    Run ML Ensemble
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {headToHead && headToHead.count > 0 && (
            <Card className="bg-card/50  border-border">
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
                  const color = resultLabel === "W" ? "text-emerald-400" : resultLabel === "L" ? "text-red-400" : "text-yellow-400";

                  return (
                    <div key={i} className="flex items-center justify-between font-mono text-xs border-b border-border/20 pb-2 last:border-0 last:pb-0">
                      <div className="flex items-center gap-2">
                        <span className={`font-black w-4 ${color}`}>{resultLabel}</span>
                        <span className="text-muted-foreground truncate max-w-[100px]">{isHome ? h2h.away_team : h2h.home_team}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-bold">{h2h.score}</span>
                        <span className="text-[10px] opacity-40">{format(new Date(h2h.date), "MM/yy")}</span>
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card className="bg-card/50  border-border sticky top-6">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <Coins className="w-4 h-4 mr-2" />
                Affiliate Execution Layer
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              {!isSports && (
                <div className="space-y-4">
                  <div className="grid grid-cols-4 gap-2">
                    {(["1x2", "goals", "ah", "cs"] as const).map((t) => (
                      <button
                        key={t}
                        onClick={() => setStakeTab(t)}
                        className={`py-1.5 rounded border font-mono text-[10px] uppercase transition-all ${stakeTab === t ? "border-secondary bg-secondary/10 text-secondary" : "border-border text-muted-foreground hover:border-secondary/40"}`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between font-mono text-[10px] text-muted-foreground uppercase">
                      <span>Available: {wallet?.vitcoin_balance?.toFixed(2) ?? "0.00"} VIT</span>
                      <span>Min: 1 VIT</span>
                    </div>
                    <div className="relative group">
                      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                        <span className="text-muted-foreground font-mono text-xs">AMOUNT</span>
                      </div>
                      <Input
                        type="number"
                        value={stakeAmount}
                        onChange={(e) => setStakeAmount(e.target.value)}
                        className="pl-16 h-12 bg-background/50 border-secondary/30 focus:border-secondary/60 font-mono text-lg"
                        min="1"
                      />
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-3">
                <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <Zap className="w-3 h-3 text-primary/60" /> Execute Selection
                </p>
                {isSports && (
                  <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-tighter mb-4 opacity-70">
                    No wallet interaction. Predictions are fulfilled via external affiliate partners.
                  </p>
                )}

                <Tabs value={stakeTab} onValueChange={(v: any) => setStakeTab(v)} className="w-full">
                  <TabsList className="grid w-full grid-cols-4 h-9 bg-background/40">
                    <TabsTrigger value="1x2" className="text-[10px] font-mono uppercase">1X2</TabsTrigger>
                    <TabsTrigger value="goals" className="text-[10px] font-mono uppercase">Goals</TabsTrigger>
                    <TabsTrigger value="ah" className="text-[10px] font-mono uppercase">Asian HCP</TabsTrigger>
                    <TabsTrigger value="cs" className="text-[10px] font-mono uppercase">Correct Score</TabsTrigger>
                  </TabsList>

                  <div className="mt-4 space-y-2">
                    <TabsContent value="1x2" className="space-y-2 m-0">
                      {[
                        { id: "home", label: match.home_team, odds: match.odds?.home, prob: homeProb },
                        { id: "draw", label: "Draw", odds: match.odds?.draw, prob: drawProb },
                        { id: "away", label: match.away_team, odds: match.odds?.away, prob: awayProb }
                      ].filter(x => x.odds != null || x.id !== "draw").map((s) => (
                        <button
                          key={s.id}
                          onClick={() => setSelectedSide(s.id as StakeSide)}
                          className={`w-full p-3 rounded-lg border font-mono text-xs flex items-center justify-between transition-all ${selectedSide === s.id ? "border-primary bg-primary/10" : "border-border bg-background/20 hover:border-primary/40"}`}
                        >
                          <div className="flex items-center gap-3">
                            <span className={`w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-bold ${selectedSide === s.id ? "bg-primary text-background" : "text-muted-foreground"}`}>
                              {s.id === "home" ? "1" : s.id === "draw" ? "X" : "2"}
                            </span>
                            <span className="font-bold text-left truncate max-w-[120px]">{s.label}</span>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="font-black text-sm">{s.odds?.toFixed(2) ?? "—"}</span>
                            <span className="text-muted-foreground opacity-60 w-8">{(s.prob * 100).toFixed(0)}%</span>
                          </div>
                        </button>
                      ))}
                    </TabsContent>

                    <TabsContent value="goals" className="space-y-2 m-0">
                      {[
                        { id: "over_25", label: "Over 2.5", prob: match.over_25_prob },
                        { id: "under_25", label: "Under 2.5", prob: match.under_25_prob },
                        { id: "btts_yes", label: "BTTS Yes", prob: match.btts_prob },
                        { id: "btts_no", label: "BTTS No", prob: match.no_btts_prob }
                      ].map((s) => (
                        <button
                          key={s.id}
                          onClick={() => setSelectedSide(s.id as StakeSide)}
                          className={`w-full p-3 rounded-lg border font-mono text-xs flex items-center justify-between transition-all ${selectedSide === s.id ? "border-primary bg-primary/10" : "border-border bg-background/20 hover:border-primary/40"}`}
                        >
                          <span className="font-bold">{s.label}</span>
                          <span className="text-muted-foreground opacity-60">{(s.prob ? s.prob * 100 : 0).toFixed(0)}%</span>
                        </button>
                      ))}
                    </TabsContent>

                    <TabsContent value="ah" className="space-y-4 m-0">
                      <div className="grid grid-cols-2 gap-2">
                        {(["-1.5", "-0.75", "-0.5", "0.0", "+0.5", "+0.75", "+1.5"]).map(line => (
                          <button
                            key={line}
                            onClick={() => setAhLine(line)}
                            className={`py-1.5 rounded border font-mono text-[10px] transition-all ${ahLine === line ? "border-primary bg-primary/10" : "border-border text-muted-foreground"}`}
                          >
                            HCP {line}
                          </button>
                        ))}
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <Button
                          variant={selectedSide === "ah_home" ? "default" : "outline"}
                          className="font-mono text-[10px] uppercase"
                          onClick={() => setSelectedSide("ah_home")}
                        >
                          Home {ahLine} ({(ahHomeProb ? ahHomeProb * 100 : 0).toFixed(0)}%)
                        </Button>
                        <Button
                          variant={selectedSide === "ah_away" ? "default" : "outline"}
                          className="font-mono text-[10px] uppercase"
                          onClick={() => setSelectedSide("ah_away")}
                        >
                          Away {ahLine.startsWith("-") ? ahLine.replace("-", "+") : ahLine.startsWith("+") ? ahLine.replace("+", "-") : ahLine} ({(ahAwayProb ? ahAwayProb * 100 : 0).toFixed(0)}%)
                        </Button>
                      </div>
                    </TabsContent>

                    <TabsContent value="cs" className="m-0">
                      <div className="grid grid-cols-4 gap-2">
                        {CS_LINES.map(line => {
                          const prob = csProbs?.[line] ?? 0;
                          return (
                            <button
                              key={line}
                              onClick={() => setSelectedSide(`cs_${line}`)}
                              className={`flex flex-col items-center justify-center p-2 rounded border font-mono transition-all ${selectedSide === `cs_${line}` ? "border-primary bg-primary/10" : "border-border bg-background/20"}`}
                            >
                              <span className="text-[10px] font-bold">{line}</span>
                              <span className="text-[8px] opacity-60">{(prob * 100).toFixed(1)}%</span>
                            </button>
                          );
                        })}
                      </div>
                    </TabsContent>
                  </div>
                </Tabs>
              </div>

              {selectedSide && (
                <div className={`rounded-lg border px-3 py-2 font-mono text-xs flex items-center justify-between ${isSports ? "border-primary/40 bg-primary/10" : "border-secondary/30 bg-secondary/5"}`}>
                  <span className="text-muted-foreground uppercase">Selection</span>
                  <span className={`${isSports ? "text-primary" : "text-secondary"} font-bold uppercase`}>
                    {(selectedSide as string).startsWith("cs_")
                      ? `Score ${(selectedSide as string).replace("cs_", "").replace("-", " – ")}`
                      : (selectedSide as string).replace(/_/g, " ")}
                    {(selectedSide === "ah_home" || selectedSide === "ah_away") && ` (${ahLineNum > 0 ? "+" : ""}${ahLineNum})`}
                  </span>
                </div>
              )}

              {isSports ? (
                <div className="space-y-2">
                  <Button
                    className="w-full h-12 font-mono uppercase tracking-widest text-sm gap-2"
                    onClick={() => handleGenerateSlip()}
                    disabled={generateSlip.isPending || !selectedSide}
                  >
                    {generateSlip.isPending ? (
                      <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    ) : (
                      <><TrendingUp className="w-4 h-4" /> Generate Slip & Open Affiliate</>
                    )}
                  </Button>
                  <p className="text-[9px] font-mono text-center text-muted-foreground uppercase tracking-tighter">
                    Redirects to verified bookmaker partners (Betway, SportyBet, Bet9ja)
                  </p>
                </div>
              ) : (
                <Button
                  className="w-full h-12 font-mono uppercase tracking-widest text-sm bg-secondary hover:bg-secondary/90 text-secondary-foreground"
                  onClick={handleStake}
                  disabled={stake.isPending || !selectedSide}
                >
                  {stake.isPending ? "PROCESSING_TX..." : "EXECUTE_STAKE"}
                </Button>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card/50  border-border">
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
          <Card className="bg-card/50  border-border">
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
          <Card className="bg-card/50  border-border">
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

      {showPredict && (
        <PredictionFlow
          match={match}
          open={showPredict}
          onClose={() => setShowPredict(false)}
        />
      )}
    </div>
  );
}
