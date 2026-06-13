import { useState, useEffect, useMemo } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiPost } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  BrainCircuit,
  TrendingUp,
  Coins,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Zap,
  Brain,
  ShieldCheck,
  Activity,
  BarChart3,
  Clock,
  Layers,
  ChevronRight,
  Target,
  Trophy,
  ArrowRight
} from "lucide-react";

interface MatchInfo {
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff_time: string;
  odds?: {
    home?: number | null;
    draw?: number | null;
    away?: number | null;
    over_25?: number | null;
    under_25?: number | null;
    btts_yes?: number | null;
    btts_no?: number | null;
  };
  home_prob?: number | null;
  draw_prob?: number | null;
  away_prob?: number | null;
  confidence?: number | null;
  bet_side?: string | null;
  edge?: number | null;
  over_25_prob?: number | null;
  under_25_prob?: number | null;
  btts_prob?: number | null;
  no_btts_prob?: number | null;
  enabled_markets?: any[];
  sport?: string | null;
}

interface PredictionFlowProps {
  match: MatchInfo;
  open: boolean;
  onClose: () => void;
}

type Side = string;

const PRESETS = [5, 10, 25, 50, 100];

const PROCESSING_STEPS = [
  { label: "Initializing Neural Ensemble v4.2", icon: Layers },
  { label: "Querying Poisson Goals Engine", icon: Activity },
  { label: "Analyzing Dixon-Coles Distribution", icon: BarChart3 },
  { label: "Running Elo Rating Simulation", icon: Clock },
  { label: "Calculating Bayesian Value Edge", icon: TrendingUp },
  { label: "Aggregating Multi-Model Consensus", icon: Brain },
  { label: "Applying Entropy Calibration", icon: ShieldCheck },
  { label: "Finalizing Analytics Report", icon: CheckCircle2 }
];

export function PredictionFlow({ match, open, onClose }: PredictionFlowProps) {
  const [selectedSide, setSelectedSide] = useState<Side | null>(match.bet_side || null);
  const [stake, setStake] = useState("10");
  const [processingStep, setProcessingStep] = useState(0);
  const [predictionResult, setPredictionResult] = useState<any>(null);
  const queryClient = useQueryClient();

  // Reset state when opening — auto-select bet_side or default to "home" (1x2 Home)
  // so the Run Strategic Ensemble button is never stuck in disabled state
  useEffect(() => {
    if (open) {
      setProcessingStep(0);
      setPredictionResult(null);
      // Prefer the model's recommended side; fall back to "home" so the button is enabled
      const autoSide: Side = match.bet_side || "home";
      setSelectedSide(autoSide);
    }
  }, [open, match.bet_side]);

  const mutation = useMutation({
    mutationFn: async () => {
      // Simulate processing time for professional feel
      for (let i = 0; i < PROCESSING_STEPS.length; i++) {
        setProcessingStep(i);
        const delay = i === 0 ? 600 : i === PROCESSING_STEPS.length - 1 ? 800 : 350 + Math.random() * 300;
        await new Promise(r => setTimeout(r, delay));
      }

      const kickoff = match.kickoff_time?.endsWith("Z")
        ? match.kickoff_time
        : match.kickoff_time + "Z";

      const homeOdds = match.odds?.home ?? null;
      const drawOdds = match.odds?.draw ?? null;
      const awayOdds = match.odds?.away ?? null;

      const market_odds: Record<string, number> = {};
      if (match.odds) {
        for (const [k, v] of Object.entries(match.odds as Record<string, any>)) {
          const num = Number(v);
          if (!isNaN(num) && num > 1) market_odds[k] = num;
        }
      }
      if (homeOdds != null) market_odds.home = Number(homeOdds);
      if (drawOdds != null) market_odds.draw = Number(drawOdds);
      if (awayOdds != null) market_odds.away = Number(awayOdds);

      let market_id = "1x2";
      for (const g of marketGroups) {
        if (g.sides.find((s) => s.side === selectedSide)) {
          market_id = g.id;
          break;
        }
      }

      const stakeVal = parseFloat(stake) || 0;

      return apiPost("/api/predict", {
        home_team: match.home_team,
        away_team: match.away_team,
        league: match.league,
        kickoff_time: kickoff,
        fixture_id: String(match.match_id),
        sport: match.sport || "football",
        market_odds,
        market_id,
        selected_side: selectedSide,
        stake: stakeVal,
      });
    },
    onSuccess: (result: any) => {
      setPredictionResult(result);
      queryClient.invalidateQueries({ predicate: (q) => {
        const k = String(q.queryKey?.[0] ?? "");
        return k.startsWith("/matches") || k.startsWith("matches-") || k.startsWith("/history");
      }});
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.detail || e?.message || "Prediction failed";
      toast.error(msg, { className: "font-mono text-xs" });
    },
  });

  const enabledMarkets = match.enabled_markets || [];

  // ── Normalize backend market IDs (e.g. "over_under_25") to frontend keys
  // (e.g. "over_under_2.5"). Handles all documented mismatches.
  const MARKET_ID_ALIASES: Record<string, string> = {
    "over_under_25":    "over_under_2.5",
    "over_under_15":    "over_under_1.5",
    "over_under_35":    "over_under_3.5",
    "over_under":       "over_under_2.5",
    "btts_ht":          "btts_half_time",
    "clean_sheet_home": "home_clean_sheet",
    "clean_sheet_away": "away_clean_sheet",
    "win_to_nil":       "win_to_nil",
    "correct_score":    "correct_score",
    "htft":             "htft",
    "match_winner_ht":  "match_winner_ht",
  };

  // Build a normalized set of active market IDs — union of raw IDs + normalized aliases
  const activeMarketIds = new Set<string>();
  for (const m of enabledMarkets) {
    const raw = String(m.id);
    activeMarketIds.add(raw);
    if (MARKET_ID_ALIASES[raw]) activeMarketIds.add(MARKET_ID_ALIASES[raw]);
  }
  // If no markets configured at all, activate everything (fallback to defaults)
  const noMarketsConfigured = enabledMarkets.length === 0;

  const isActiveGroup = (gid: string): boolean => {
    if (noMarketsConfigured) return true;
    if (activeMarketIds.has(gid)) return true;
    // Check alias map in reverse (frontend key → backend ID)
    for (const [backendId, frontendKey] of Object.entries(MARKET_ID_ALIASES)) {
      if (frontendKey === gid && activeMarketIds.has(backendId)) return true;
    }
    return false;
  };

  const KNOWN_MARKETS: Record<string, { title: string; sides: Array<{ side: Side; label: string }> }> = {
    "1x2": {
      title: "Match Result",
      sides: [
        { side: "home", label: "Home" },
        { side: "draw", label: "Draw" },
        { side: "away", label: "Away" }
      ]
    },
    "double_chance": {
      title: "Double Chance",
      sides: [
        { side: "dc_home_draw", label: "Home or Draw" },
        { side: "dc_home_away", label: "Home or Away" },
        { side: "dc_draw_away", label: "Draw or Away" }
      ]
    },
    "over_under_1.5": {
      title: "Over/Under 1.5 Goals",
      sides: [
        { side: "over_15", label: "Over 1.5" },
        { side: "under_15", label: "Under 1.5" }
      ]
    },
    "over_under_2.5": {
      title: "Over/Under 2.5 Goals",
      sides: [
        { side: "over_25", label: "Over 2.5" },
        { side: "under_25", label: "Under 2.5" }
      ]
    },
    "over_under_3.5": {
      title: "Over/Under 3.5 Goals",
      sides: [
        { side: "over_35", label: "Over 3.5" },
        { side: "under_35", label: "Under 3.5" }
      ]
    },
    "draw_no_bet": {
      title: "Draw No Bet (DNB)",
      sides: [
        { side: "dnb_home", label: "Home DNB" },
        { side: "dnb_away", label: "Away DNB" }
      ]
    },
    "asian_handicap": {
      title: "Asian Handicap",
      sides: [
        { side: "ah_home", label: "AH Home" },
        { side: "ah_away", label: "AH Away" }
      ]
    },
    "btts": {
      title: "BTTS - Both Teams To Score",
      sides: [
        { side: "btts_yes", label: "YES" },
        { side: "btts_no", label: "NO" }
      ]
    },
    "btts_half_time": {
      title: "BTTS - Half Time",
      sides: [
        { side: "btts_ht_yes", label: "YES" },
        { side: "btts_ht_no", label: "NO" }
      ]
    },
    "home_clean_sheet": {
      title: "Home Clean Sheet",
      sides: [
        { side: "home_cs_yes", label: "YES" },
        { side: "home_cs_no", label: "NO" }
      ]
    },
    "away_clean_sheet": {
      title: "Away Clean Sheet",
      sides: [
        { side: "away_cs_yes", label: "YES" },
        { side: "away_cs_no", label: "NO" }
      ]
    },
    "win_to_nil": {
      title: "Win To Nil",
      sides: [
        { side: "wtn_home", label: "Home Win To Nil" },
        { side: "wtn_away", label: "Away Win To Nil" }
      ]
    },
  };

  const twoWay = (match.sport || '').toLowerCase() === 'tennis' || (match.sport || '').toLowerCase() === 'basketball';

  const marketGroups: Array<{ id: string; title: string; sides: Array<{ side: Side; label: string }> }> = [];
  for (const gid of Object.keys(KNOWN_MARKETS)) {
    if (isActiveGroup(gid)) {
      const sides = twoWay ? KNOWN_MARKETS[gid].sides.filter(s => s.side !== 'draw') : KNOWN_MARKETS[gid].sides;
      marketGroups.push({ id: gid, title: KNOWN_MARKETS[gid].title, sides });
    }
  }

  const probMap: Record<string, number> = {
    home: match.home_prob || 0,
    draw: match.draw_prob || 0,
    away: match.away_prob || 0,
    over_25: match.over_25_prob || 0,
    under_25: match.under_25_prob || 0,
    btts_yes: match.btts_prob || 0,
    btts_no: match.btts_prob != null ? 1 - match.btts_prob : 0,
  };

  const oddsMap: Record<string, number> = match.odds || {};

  const potentialPayout = useMemo(() => {
    if (!selectedSide || !stake) return 0;
    const odds = oddsMap[selectedSide] || 0;
    return parseFloat(stake) * odds;
  }, [selectedSide, stake, oddsMap]);

  if (mutation.isPending) {
    return (
      <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
        <DialogContent className="max-w-md bg-[#0a0a0b] border-[#1a1a1c] font-mono p-8 overflow-hidden">
          <div className="flex flex-col items-center justify-center space-y-10 py-6">
            <div className="relative">
              <div className="absolute inset-0 bg-primary/20  rounded-full animate-pulse" />
              <div className="relative bg-[#0d0d0e] border border-primary/40 rounded-3xl p-8 ">
                <BrainCircuit className="w-14 h-14 text-primary animate-pulse" />
                <div className="absolute -top-1 -right-1">
                  <span className="relative flex h-4 w-4">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-4 w-4 bg-primary"></span>
                  </span>
                </div>
              </div>
            </div>

            <div className="text-center space-y-3">
              <h3 className="text-xl font-black tracking-widest uppercase text-white">Neural Processing</h3>
              <div className="flex items-center justify-center gap-2">
                <Loader2 className="w-3 h-3 text-primary animate-spin" />
                <p className="text-[10px] text-primary font-bold uppercase tracking-[0.2em] animate-pulse">
                  {PROCESSING_STEPS[processingStep].label}
                </p>
              </div>
            </div>

            <div className="w-full space-y-2.5 bg-[#0d0d0e] p-5 rounded-2xl border border-[#1a1a1c]">
              {PROCESSING_STEPS.map((step, idx) => {
                const Icon = step.icon;
                const isCurrent = idx === processingStep;
                const isPast = idx < processingStep;
                return (
                  <div
                    key={idx}
                    className={`flex items-center justify-between transition-all duration-500 ${
                      isCurrent ? "opacity-100 translate-x-1" : isPast ? "opacity-40" : "opacity-5"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-1 rounded ${isCurrent ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}>
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className="text-[9px] font-bold uppercase tracking-wider">{step.label}</span>
                    </div>
                    {isPast ? (
                      <CheckCircle2 className="w-3 h-3 text-primary" />
                    ) : isCurrent ? (
                      <div className="flex gap-0.5">
                        <div className="w-1 h-1 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]" />
                        <div className="w-1 h-1 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]" />
                        <div className="w-1 h-1 bg-primary rounded-full animate-bounce" />
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>

            <div className="w-full space-y-2">
              <div className="flex justify-between text-[8px] font-black text-muted-foreground uppercase tracking-widest">
                <span>System Stability: 99.9%</span>
                <span>Progress: {Math.round(((processingStep + 1) / PROCESSING_STEPS.length) * 100)}%</span>
              </div>
              <div className="w-full bg-[#1a1a1c] h-1.5 rounded-full overflow-hidden p-[2px]">
                <div
                  className="bg-gradient-to-r from-primary/50 to-primary h-full rounded-full transition-all duration-700 ease-in-out "
                  style={{ width: `${((processingStep + 1) / PROCESSING_STEPS.length) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  if (predictionResult) {
    return (
      <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
        <DialogContent className="max-w-md bg-[#0a0a0b] border-[#1a1a1c] font-mono p-0 overflow-hidden ">
          <div className="bg-primary/10 border-b border-primary/20 p-6 flex flex-col items-center gap-2">
            <div className="bg-primary text-[#0a0a0b] p-2 rounded-2xl ">
              <ShieldCheck className="w-8 h-8" />
            </div>
            <h2 className="text-lg font-black uppercase tracking-[0.2em] text-white mt-2">Analytics Report</h2>
            <p className="text-[10px] text-primary font-bold uppercase tracking-widest">Analytics v4.2 Finalized</p>
          </div>

          <div className="p-6 space-y-6">
            {/* Primary Rating */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#0d0d0e] border border-[#1a1a1c] rounded-2xl p-4 space-y-1">
                <span className="text-[9px] text-muted-foreground font-black uppercase tracking-widest">Signal Rating</span>
                <p className={`text-xl font-black ${
                  predictionResult.analytics_rating === "EXCELLENT" ? "text-primary" :
                  predictionResult.analytics_rating === "VERY GOOD" ? "text-green-400" : "text-yellow-400"
                }`}>
                  {predictionResult.analytics_rating}
                </p>
              </div>
              <div className="bg-[#0d0d0e] border border-[#1a1a1c] rounded-2xl p-4 space-y-1">
                <span className="text-[9px] text-muted-foreground font-black uppercase tracking-widest">Accuracy Est.</span>
                <p className="text-2xl font-black text-white">
                  {predictionResult.prediction_accuracy_estimate}%
                </p>
              </div>
            </div>

            {/* Metrics Breakdown */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-3 h-3 text-primary" />
                <span className="text-[10px] text-muted-foreground font-black uppercase tracking-widest">Ensemble Metrics</span>
              </div>
              <div className="bg-[#0d0d0e] border border-[#1a1a1c] rounded-2xl divide-y divide-[#1a1a1c]">
                <div className="p-4 flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">Neural Consensus</span>
                  <span className="text-sm font-black text-primary">{predictionResult.neural_consensus_score.toFixed(1)}%</span>
                </div>
                <div className="p-4 flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">Models Participating</span>
                  <span className="text-sm font-black text-white">{predictionResult.models_used}/{predictionResult.models_total}</span>
                </div>
                <div className="p-4 flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">Detected Edge</span>
                  <span className="text-sm font-black text-green-400">+{(predictionResult.edge * 100).toFixed(2)}%</span>
                </div>
              </div>
            </div>

            {/* Recommendation */}
            <div className="bg-primary/5 border border-primary/20 rounded-2xl p-5 space-y-3 relative overflow-hidden">
               <div className="absolute -bottom-2 -right-2 opacity-10">
                 <Target className="w-16 h-16 text-primary" />
               </div>
               <span className="text-[9px] text-primary font-black uppercase tracking-widest">Consensus Recommendation</span>
               <div className="flex items-center justify-between">
                 <div>
                   <p className="text-xl font-black text-white uppercase">{predictionResult.bet_side?.replace(/_/g, " ")}</p>
                   <p className="text-[10px] text-muted-foreground font-bold">Recommended Stake: {predictionResult.recommended_stake.toFixed(1)}%</p>
                 </div>
                 <div className="bg-primary px-3 py-1 rounded-lg text-[#0a0a0b] font-black text-xs">
                   {predictionResult.entry_odds?.toFixed(2)}
                 </div>
               </div>
            </div>

            <Button
              className="w-full h-14 bg-white text-[#0a0a0b] hover:bg-white/90 rounded-2xl font-black uppercase tracking-[0.2em] text-xs "
              onClick={onClose}
            >
              Confirm & Continue
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md bg-[#0a0a0b] border-[#1a1a1c] font-mono max-h-[92vh] overflow-y-auto p-0 gap-0 ">
        <div className="sticky top-0 z-20 bg-[#0a0a0b]/80  border-b border-[#1a1a1c] p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 p-2 rounded-xl border border-primary/20">
              <BrainCircuit className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xs font-black uppercase tracking-[0.2em] text-white">ML Ensemble v4.2</h2>
              <p className="text-[9px] text-muted-foreground font-bold uppercase">Strategic Analytics Suite</p>
            </div>
          </div>
          <Badge className="bg-primary/10 text-primary border-primary/20 text-[9px] px-2 py-1 rounded-lg animate-pulse">
            HIGH_ACCURACY_MODE
          </Badge>
        </div>

        <div className="p-6 space-y-8">
          {/* Match Context Card */}
          <div className="relative overflow-hidden rounded-2xl border border-[#1a1a1c] bg-[#0d0d0e] p-5 group">
            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
              <Activity className="w-16 h-16 text-white" />
            </div>
            <div className="relative flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="text-[9px] text-muted-foreground font-black uppercase tracking-[0.3em]">{match.league?.replace(/_/g, " ")}</span>
                <span className="text-[9px] text-primary font-black uppercase">LIVE_CONTEXT_ACTIVE</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-black text-white truncate">{match.home_team}</p>
                  <p className="text-[10px] text-muted-foreground font-bold uppercase">Home</p>
                </div>
                <div className="bg-[#1a1a1c] px-3 py-1.5 rounded-lg border border-[#2a2a2c] text-[10px] font-black text-white">VS</div>
                <div className="flex-1 text-right space-y-1">
                  <p className="text-sm font-black text-white truncate">{match.away_team}</p>
                  <p className="text-[10px] text-muted-foreground font-bold uppercase">Away</p>
                </div>
              </div>
            </div>
          </div>

          {/* Market Analytics Grid */}
          <div className="space-y-6">
            {marketGroups.map((group) => (
              <div key={group.id} className="space-y-3">
                <div className="flex items-center gap-2 px-1">
                  <div className="w-1 h-3 bg-primary rounded-full" />
                  <span className="text-[10px] text-muted-foreground font-black uppercase tracking-widest">{group.title}</span>
                </div>
                <div className={`grid gap-3 ${group.sides.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
                  {group.sides.map(({ side, label }) => {
                    const isSelected = selectedSide === side;
                    const isRecommended = match.bet_side === side;
                    const prob = probMap[side];
                    const odds = oddsMap[side];

                    return (
                      <button
                        key={side}
                        onClick={() => setSelectedSide(side)}
                        className={`group relative flex flex-col items-center justify-center gap-2 p-5 rounded-2xl border transition-all duration-300 ${
                          isSelected
                            ? "border-primary bg-primary/10  ring-1 ring-primary/50"
                            : "border-[#1a1a1c] bg-[#0d0d0e] hover:border-[#2a2a2c] hover:bg-[#0f0f10]"
                        }`}
                      >
                        {isRecommended && (
                          <div className="absolute -top-2 left-1/2 -translate-x-1/2 bg-primary text-[#0a0a0b] text-[8px] font-black px-2.5 py-0.5 rounded-full uppercase  z-10 flex items-center gap-1">
                            <Zap className="w-2.5 h-2.5 fill-current" />
                            ALPHA
                          </div>
                        )}

                        <span className={`text-[10px] font-black uppercase tracking-widest ${isSelected ? "text-primary" : "text-muted-foreground"}`}>
                          {label}
                        </span>

                        <div className="text-center">
                          <span className={`text-2xl font-black block ${isSelected ? "text-primary" : "text-white"}`}>
                            {odds != null ? odds.toFixed(2) : "—"}
                          </span>
                          {prob != null && prob > 0 ? (
                            <span className="text-[9px] text-muted-foreground/60 font-bold tracking-tighter">
                              {(prob * 100).toFixed(0)}% PROBABILITY
                            </span>
                          ) : (
                            <div className="w-4 h-0.5 bg-[#1a1a1c] mx-auto mt-1" />
                          )}
                        </div>

                        {isSelected && (
                          <div className="absolute bottom-2 right-2">
                            <div className="bg-primary p-0.5 rounded-full ">
                              <CheckCircle2 className="w-3 h-3 text-[#0a0a0b]" />
                            </div>
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Capital Allocation */}
          <div className="bg-[#0d0d0e] rounded-2xl border border-[#1a1a1c] p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Coins className="w-4 h-4 text-primary" />
                <span className="text-[11px] text-white font-black uppercase tracking-widest">Stake Allocation</span>
              </div>
              {match.edge != null && match.edge > 0 && (
                <div className="bg-green-500/10 border border-green-500/20 px-2 py-1 rounded-lg flex items-center gap-1.5">
                  <div className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-[9px] text-green-400 font-black uppercase">Edge: {(match.edge * 100).toFixed(1)}%</span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-5 gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p}
                  onClick={() => setStake(String(p))}
                  className={`py-2.5 text-[10px] font-black rounded-xl border transition-all ${
                    stake === String(p)
                      ? "border-primary bg-primary/10 text-primary "
                      : "border-[#1a1a1c] bg-[#0a0a0b] text-muted-foreground hover:border-[#2a2a2c]"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>

            <div className="relative group">
              <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                <span className="text-muted-foreground font-black text-xs">VIT</span>
              </div>
              <Input
                type="number"
                value={stake}
                onChange={(e) => setStake(e.target.value)}
                className="pl-12 h-14 bg-[#0a0a0b] border-[#1a1a1c] border-2 rounded-2xl font-black text-xl text-white focus:border-primary/50 transition-all focus:ring-0"
                placeholder="0.00"
              />
            </div>
          </div>

          {/* Execution Summary */}
          {selectedSide && potentialPayout > 0 && (
            <div className="relative overflow-hidden rounded-2xl border-2 border-primary/30 bg-primary/5 p-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="absolute top-0 right-0 p-4 opacity-5">
                <ShieldCheck className="w-20 h-20 text-white" />
              </div>
              <div className="relative grid grid-cols-2 gap-6">
                <div className="space-y-1">
                  <p className="text-[9px] text-muted-foreground font-black uppercase tracking-widest">Potential Return</p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-black text-primary tracking-tighter">{potentialPayout.toFixed(2)}</span>
                    <span className="text-[10px] text-primary font-black uppercase">VIT</span>
                  </div>
                </div>
                <div className="space-y-1 text-right border-l border-[#1a1a1c] pl-6">
                  <p className="text-[9px] text-muted-foreground font-black uppercase tracking-widest">Market Strategy</p>
                  <p className="text-sm font-black text-white truncate uppercase">{selectedSide.replace(/_/g, " ")}</p>
                  <p className="text-[10px] text-muted-foreground font-bold uppercase">@{oddsMap[selectedSide]?.toFixed(2)} Odds</p>
                </div>
              </div>
            </div>
          )}

          {/* Strategic Action */}
          <div className="flex flex-col gap-3 pb-8">
            <Button
              className={`h-16 rounded-2xl font-black uppercase tracking-[0.3em] text-xs transition-all duration-300  relative overflow-hidden group ${
                !selectedSide || !stake
                  ? "bg-[#1a1a1c] text-muted-foreground cursor-not-allowed"
                  : "bg-primary text-[#0a0a0b] hover:scale-[1.02] hover:brightness-110 active:scale-[0.98]"
              }`}
              disabled={!selectedSide || !stake || mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
              <Zap className="w-4 h-4 mr-3 fill-current" />
              Run Strategic Ensemble
            </Button>
            <button
              className="text-[10px] font-black text-muted-foreground uppercase tracking-widest hover:text-white transition-colors py-2"
              onClick={onClose}
            >
              Abort Mission
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
