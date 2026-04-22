import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "sonner";
import { BrainCircuit, TrendingUp, Coins, CheckCircle2, AlertTriangle } from "lucide-react";

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
}

interface PredictionFlowProps {
  match: MatchInfo;
  open: boolean;
  onClose: () => void;
}

type Side = "home" | "draw" | "away" | "over_25" | "under_25" | "btts_yes" | "btts_no";

const PRESETS = [5, 10, 25, 50, 100];

export function PredictionFlow({ match, open, onClose }: PredictionFlowProps) {
  const [selectedSide, setSelectedSide] = useState<Side | null>(
    (match.bet_side as Side) ?? null
  );
  const [stake, setStake] = useState("10");
  const queryClient = useQueryClient();
  const { data: marketData } = useQuery<{ markets: any[] }>({
    queryKey: ["enabled-markets"],
    queryFn: () => apiGet("/matches/markets/enabled"),
  });
  const enabledMarkets = match.enabled_markets ?? marketData?.markets ?? [];
  // Real enabled-markets only — no invented fallback list. If the backend
  // returns an empty array, the UI shows just the markets it actually has.
  const activeMarketIds = new Set(enabledMarkets.map((m: any) => m.id));
  const stakeMarket = enabledMarkets.find((m: any) => activeMarketIds.has(m.id));
  const minStake = Number(stakeMarket?.min_stake ?? 1);

  // Real odds only. If a side's odds are missing, that side is disabled
  // (selectedOdds becomes 0 → submit button stays disabled). We never
  // render fabricated 2.0 / 3.3 / 3.5 numbers as if they were market prices.
  const homeOdds = match.odds?.home ?? null;
  const drawOdds = match.odds?.draw ?? null;
  const awayOdds = match.odds?.away ?? null;

  const oddsMap: Record<Side, number | null> = {
    home: homeOdds,
    draw: drawOdds,
    away: awayOdds,
    over_25: match.odds?.over_25 ?? null,
    under_25: match.odds?.under_25 ?? null,
    btts_yes: match.odds?.btts_yes ?? null,
    btts_no:  match.odds?.btts_no  ?? null,
  };

  // Probabilities default to null when the model hasn't run for that market —
  // UI hides the row instead of showing a fake 33% / 50% split.
  const probMap: Record<Side, number | null> = {
    home: match.home_prob ?? null,
    draw: match.draw_prob ?? null,
    away: match.away_prob ?? null,
    over_25: match.over_25_prob ?? null,
    under_25: match.under_25_prob ?? (match.over_25_prob != null ? 1 - match.over_25_prob : null),
    btts_yes: match.btts_prob ?? null,
    btts_no: match.no_btts_prob ?? (match.btts_prob != null ? 1 - match.btts_prob : null),
  };

  const selectedOdds = (selectedSide && oddsMap[selectedSide]) || 0;
  const potentialPayout = selectedOdds > 0 ? parseFloat(stake || "0") * selectedOdds : 0;

  const mutation = useMutation({
    mutationFn: async () => {
      if (!selectedSide) throw new Error("Select a prediction");
      const stakeVal = parseFloat(stake);
      if (!stakeVal || stakeVal < minStake) throw new Error(`Minimum stake is ${minStake} VIT`);

      const kickoff = match.kickoff_time?.endsWith("Z")
        ? match.kickoff_time
        : match.kickoff_time + "Z";

      // Only send odds that are real — omit unknowns so the backend
      // doesn't get bogus data.
      const market_odds: Record<string, number> = {};
      if (homeOdds != null) market_odds.home = homeOdds;
      if (drawOdds != null) market_odds.draw = drawOdds;
      if (awayOdds != null) market_odds.away = awayOdds;

      return apiPost("/predict", {
        home_team: match.home_team,
        away_team: match.away_team,
        league: match.league,
        kickoff_time: kickoff,
        fixture_id: String(match.match_id),
        market_odds,
      });
    },
    onSuccess: (result: any) => {
      toast.success(
        `Prediction submitted: ${selectedSide?.toUpperCase()} @ ${selectedOdds.toFixed(2)}`,
        { description: `Edge: ${((result?.edge ?? 0) * 100).toFixed(2)}% | Confidence: ${((result?.confidence ?? 0) * 100).toFixed(1)}%` }
      );
      queryClient.invalidateQueries({ queryKey: ["matches-recent"] });
      queryClient.invalidateQueries({ queryKey: ["/history"] });
      onClose();
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.detail || e?.message || "Prediction failed";
      if (msg.includes("duplicate")) {
        toast.warning("Already predicted — run the ML ensemble to get an updated prediction");
      } else {
        toast.error(msg);
      }
    },
  });

  const sideLabel = { home: match.home_team, draw: "Draw", away: match.away_team, over_25: "Over 2.5", under_25: "Under 2.5", btts_yes: "BTTS Yes", btts_no: "BTTS No" };
  const marketGroups = [
    {
      id: "1x2",
      title: "1X2",
      sides: [
        { side: "home" as Side, label: "Home" },
        { side: "draw" as Side, label: "Draw" },
        { side: "away" as Side, label: "Away" },
      ],
    },
    {
      id: "over_under",
      title: "Over/Under 2.5",
      sides: [
        { side: "over_25" as Side, label: "Over" },
        { side: "under_25" as Side, label: "Under" },
      ],
    },
    {
      id: "btts",
      title: "BTTS",
      sides: [
        { side: "btts_yes" as Side, label: "Yes" },
        { side: "btts_no" as Side, label: "No" },
      ],
    },
  ].filter((group) => activeMarketIds.has(group.id));

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md bg-card border-border font-mono">
        <DialogHeader>
          <DialogTitle className="font-mono uppercase text-sm tracking-widest flex items-center gap-2">
            <BrainCircuit className="w-4 h-4 text-primary" />
            Submit Prediction
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          <div className="text-center space-y-1">
            <p className="text-xs text-muted-foreground uppercase">{match.league?.replace(/_/g, " ")}</p>
            <div className="flex items-center justify-center gap-3 text-sm font-bold">
              <span>{match.home_team}</span>
              <span className="text-muted-foreground text-xs">vs</span>
              <span>{match.away_team}</span>
            </div>
            {match.edge != null && Math.abs(match.edge) > 0.01 && (
              <Badge variant="outline" className="text-[10px] border-primary/30 text-primary">
                <TrendingUp className="w-3 h-3 mr-1" />
                ML Edge: {(match.edge * 100).toFixed(1)}%
              </Badge>
            )}
          </div>

          <div className="space-y-3">
            {marketGroups.map((group) => (
              <div key={group.id} className="space-y-2">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{group.title}</div>
                <div className={`grid gap-2 ${group.sides.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
                  {group.sides.map(({ side, label }) => {
                    const isSelected = selectedSide === side;
                    const isRecommended = match.bet_side === side;
                    const prob = probMap[side];
                    const odds = oddsMap[side];
                    return (
                      <button
                        key={side}
                        onClick={() => setSelectedSide(side)}
                        className={`relative flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all ${
                          isSelected
                            ? "border-primary bg-primary/10 shadow-[0_0_12px_rgba(0,255,255,0.1)]"
                            : "border-border bg-card/50 hover:border-primary/40"
                        }`}
                      >
                        {isRecommended && (
                          <span className="absolute -top-2 left-1/2 -translate-x-1/2 text-[9px] font-mono bg-primary text-primary-foreground px-1.5 rounded uppercase">
                            ML Pick
                          </span>
                        )}
                        <span className="text-[10px] text-muted-foreground uppercase">{label}</span>
                        <span className="text-lg font-bold text-primary">
                          {odds != null ? odds.toFixed(2) : "—"}
                        </span>
                        {prob != null && prob > 0 && (
                          <span className="text-[10px] text-muted-foreground">{(prob * 100).toFixed(0)}% prob</span>
                        )}
                        {isSelected && <CheckCircle2 className="w-3 h-3 text-primary absolute top-2 right-2" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div>
            <label className="text-xs text-muted-foreground uppercase mb-2 block">Stake (VITCoin)</label>
            <div className="flex gap-2 mb-2">
              {PRESETS.map((p) => (
                <button
                  key={p}
                  onClick={() => setStake(String(p))}
                  className={`flex-1 py-1 text-xs font-mono rounded border transition-colors ${
                    stake === String(p)
                      ? "border-primary text-primary bg-primary/10"
                      : "border-border text-muted-foreground hover:border-primary/40"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            <Input
              type="number"
              value={stake}
              onChange={(e) => setStake(e.target.value)}
              className="font-mono bg-card/50"
              placeholder="Enter stake amount"
              min={1}
            />
            <p className="text-[10px] text-muted-foreground mt-1 uppercase">Admin minimum: {minStake} VIT</p>
          </div>

          {selectedSide && potentialPayout > 0 && (
            <Card className="bg-muted/10 border-primary/10">
              <CardContent className="p-3 space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground uppercase">Prediction</span>
                  <span className="font-bold text-primary uppercase">{sideLabel[selectedSide]}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground uppercase">Stake</span>
                  <span className="font-mono">{parseFloat(stake || "0").toFixed(2)} VIT</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground uppercase">Odds</span>
                  <span className="font-mono">{selectedOdds.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm font-bold border-t border-border/50 pt-1 mt-1">
                  <span className="text-muted-foreground uppercase">Potential Return</span>
                  <span className="text-primary flex items-center gap-1">
                    <Coins className="w-3 h-3" />
                    {potentialPayout.toFixed(2)} VIT
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          {!selectedSide && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertTriangle className="w-3 h-3" />
              Select an enabled market outcome to continue
            </div>
          )}

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1 font-mono uppercase text-xs" onClick={onClose}>
              Cancel
            </Button>
            <Button
              className="flex-1 font-mono uppercase text-xs"
              disabled={!selectedSide || !stake || mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? "SUBMITTING..." : "RUN ML ENSEMBLE"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
