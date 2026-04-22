import { useState } from "react";
import { Link } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { format } from "date-fns";
import { Activity, BrainCircuit, TrendingUp, Zap, Brain, ChevronDown, ChevronUp } from "lucide-react";
import type { Match } from "@/api-client/schemas";
import { PredictionFlow } from "@/components/PredictionFlow";

function ConfidenceMeter({ confidence, risk }: { confidence: number; risk: number }) {
  const riskLevel = risk > 0.7 ? "HIGH" : risk > 0.4 ? "MED" : "LOW";
  const riskColor = riskLevel === "HIGH" ? "text-destructive" : riskLevel === "MED" ? "text-yellow-400" : "text-primary";
  const riskBg   = riskLevel === "HIGH" ? "bg-destructive" : riskLevel === "MED" ? "bg-yellow-400" : "bg-primary";

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="text-muted-foreground w-20 uppercase">Confidence</span>
        <div className="flex-1 h-1.5 bg-muted/40 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all"
            style={{ width: `${Math.max(0, Math.min(100, confidence * 100))}%` }}
          />
        </div>
        <span className="text-primary font-bold w-8 text-right">{(confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="text-muted-foreground w-20 uppercase">Risk</span>
        <div className="flex-1 flex gap-0.5">
          {[0.2, 0.4, 0.6, 0.8, 1.0].map((t, i) => (
            <div key={i} className={`flex-1 h-1.5 rounded-sm transition-all ${risk >= t ? riskBg : "bg-muted/30"}`} />
          ))}
        </div>
        <span className={`font-bold w-8 text-right ${riskColor}`}>{riskLevel}</span>
      </div>
    </div>
  );
}

function AIInsightPanel({ match }: { match: any }) {
  const confidence = match.confidence ?? match.avg_1x2_confidence ?? 0.65;
  const edge = match.edge;
  const betSide = match.bet_side;
  const overProb = match.over_25_prob;
  const bttsProb = match.btts_prob;
  const stake = match.recommended_stake;

  const insights: { label: string; value: string; accent?: string }[] = [];

  if (betSide) {
    const sideLabel = betSide === "home" ? match.home_team : betSide === "away" ? match.away_team : "Draw";
    insights.push({ label: "ML Signal", value: `Back ${sideLabel}`, accent: "text-primary" });
  }

  if (edge != null) {
    const edgeStr = `${(edge * 100).toFixed(2)}% edge`;
    insights.push({ label: "Value Edge", value: edgeStr, accent: edge > 0.03 ? "text-green-400" : edge > 0 ? "text-yellow-400" : "text-destructive" });
  }

  if (confidence > 0) {
    const tier = confidence >= 0.75 ? "HIGH" : confidence >= 0.65 ? "MED" : "LOW";
    insights.push({ label: "Confidence", value: `${(confidence * 100).toFixed(0)}% (${tier})`, accent: confidence >= 0.75 ? "text-green-400" : confidence >= 0.65 ? "text-yellow-400" : "text-orange-400" });
  }

  if (overProb != null) {
    const overSide = overProb > 0.5 ? `Over 2.5 (${(overProb * 100).toFixed(0)}%)` : `Under 2.5 (${((1 - overProb) * 100).toFixed(0)}%)`;
    insights.push({ label: "Goals Mkt", value: overSide });
  }

  if (bttsProb != null) {
    insights.push({ label: "BTTS", value: bttsProb > 0.5 ? `YES (${(bttsProb * 100).toFixed(0)}%)` : `NO (${((1 - bttsProb) * 100).toFixed(0)}%)` });
  }

  if (stake != null) {
    insights.push({ label: "Kelly %", value: `${(stake * 100).toFixed(1)}%` });
  }

  if (insights.length === 0) {
    return (
      <p className="text-xs font-mono text-muted-foreground text-center py-1">
        Run the ML ensemble for insights
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
      {insights.map((ins) => (
        <div key={ins.label} className="flex items-center gap-1.5 text-xs font-mono">
          <span className="text-muted-foreground shrink-0 w-[72px]">{ins.label}</span>
          <span className={`font-medium ${ins.accent ?? "text-foreground"}`}>{ins.value}</span>
        </div>
      ))}
    </div>
  );
}

export function PremiumMatchCard({ match }: { match: Match & { [key: string]: any } }) {
  const [showPredict, setShowPredict] = useState(false);
  const [showInsights, setShowInsights] = useState(false);
  const confidence = match.confidence ?? match.avg_1x2_confidence ?? 0.65;
  const risk = Math.max(0, 1 - confidence);
  const homeProb = match.home_prob ?? match.model_consensus_probs?.home ?? 0;
  const drawProb = match.draw_prob ?? match.model_consensus_probs?.draw ?? 0;
  const awayProb = match.away_prob ?? match.model_consensus_probs?.away ?? 0;
  const isSettled = !!match.actual_outcome;

  return (
    <>
      <PredictionFlow
        match={{
          match_id: match.match_id,
          home_team: match.home_team,
          away_team: match.away_team,
          league: match.league,
          kickoff_time: match.kickoff_time,
          odds: match.odds ?? undefined,
          home_prob: homeProb || undefined,
          draw_prob: drawProb || undefined,
          away_prob: awayProb || undefined,
          confidence: confidence || undefined,
          bet_side: match.bet_side,
          edge: match.edge,
          over_25_prob: match.over_25_prob,
          under_25_prob: match.under_25_prob,
          btts_prob: match.btts_prob,
          no_btts_prob: match.no_btts_prob,
          enabled_markets: match.enabled_markets,
        }}
        open={showPredict}
        onClose={() => setShowPredict(false)}
      />

      <Card className="bg-card/50 backdrop-blur border-border hover:border-primary/50 transition-all duration-200 group hover:-translate-y-0.5 hover:shadow-[0_4px_20px_rgba(0,255,255,0.08)] h-full flex flex-col">
        <CardContent className="p-0 flex flex-col h-full">
          <Link href={`/matches/${match.match_id}`} className="flex flex-col flex-1">
            {/* Header */}
            <div className="p-4 border-b border-border/50">
              <div className="flex justify-between items-start mb-3">
                <Badge variant="outline" className="font-mono text-xs border-primary/20 text-muted-foreground">
                  {match.league?.replace(/_/g, " ")}
                </Badge>
                <div className="flex gap-1.5">
                  {match.bet_side && (
                    <Badge className="font-mono text-[10px] uppercase bg-primary/10 text-primary border border-primary/20">
                      {match.bet_side}
                    </Badge>
                  )}
                  <Badge variant={isSettled ? "secondary" : "outline"} className="font-mono text-[10px]">
                    {isSettled ? "SETTLED" : match.status === "live" ? "LIVE" : "UPCOMING"}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-base truncate leading-tight">{match.home_team}</p>
                  <p className="text-sm text-muted-foreground truncate mt-0.5">vs {match.away_team}</p>
                </div>
                {match.ft_score ? (
                  <div className="font-mono font-bold text-xl text-primary bg-primary/10 px-3 py-1.5 rounded border border-primary/20 ml-3">
                    {match.ft_score}
                  </div>
                ) : match.entry_odds ? (
                  <div className="text-right ml-3">
                    <div className="font-mono font-bold text-primary">{Number(match.entry_odds).toFixed(2)}</div>
                    <div className="text-[10px] text-muted-foreground font-mono">odds</div>
                  </div>
                ) : null}
              </div>
            </div>

            {/* Probability row */}
            <div className="grid grid-cols-3 gap-px bg-border/30 flex-1">
              {[
                { label: "Home", prob: homeProb },
                { label: "Draw", prob: drawProb },
                { label: "Away", prob: awayProb },
              ].map(({ label, prob }) => (
                <div key={label} className="bg-card/30 p-3 text-center">
                  <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1">{label}</div>
                  <div className="text-lg font-bold font-mono text-primary">{(prob * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>

            {/* Confidence + risk meters */}
            <div className="p-4 border-t border-border/50">
              <ConfidenceMeter confidence={confidence} risk={risk} />
              <div className="grid grid-cols-3 gap-2 mt-3 text-[10px] font-mono text-muted-foreground">
                <div>O2.5 <span className="text-foreground">{match.over_25_prob != null ? `${(match.over_25_prob * 100).toFixed(0)}%` : "—"}</span></div>
                <div>BTTS <span className="text-foreground">{match.btts_prob != null ? `${(match.btts_prob * 100).toFixed(0)}%` : "—"}</span></div>
                <div>Stake <span className="text-foreground">{match.recommended_stake != null ? `${(match.recommended_stake * 100).toFixed(1)}%` : "—"}</span></div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-4 pb-3 flex justify-between items-center text-xs font-mono text-muted-foreground border-t border-border/30 pt-2">
              <span className="flex items-center gap-1">
                <Activity className="w-3 h-3" />
                {format(new Date(match.kickoff_time), "MMM dd HH:mm")}
              </span>
              {match.edge != null && (
                <span className={`flex items-center gap-1 font-bold ${match.edge > 0 ? "text-primary" : "text-destructive"}`}>
                  <TrendingUp className="w-3 h-3" />
                  {(match.edge * 100).toFixed(1)}% edge
                </span>
              )}
              <span className="flex items-center gap-1 text-primary/60 group-hover:text-primary transition-colors">
                <BrainCircuit className="w-3 h-3" />
                View →
              </span>
            </div>
          </Link>

          <div className="px-4 pb-4 pt-0 space-y-2">
            {/* AI Insights toggle */}
            <button
              className="w-full flex items-center justify-between text-xs font-mono text-muted-foreground hover:text-foreground transition-colors py-1 border-t border-border/20 pt-2"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); setShowInsights((s) => !s); }}
            >
              <span className="flex items-center gap-1.5">
                <Brain className="w-3 h-3 text-primary/70" />
                AI Insights
              </span>
              {showInsights ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {showInsights && (
              <div className="bg-background/40 border border-border/30 rounded-md p-3">
                <AIInsightPanel match={match} />
              </div>
            )}

            {!isSettled && (
              <Button
                size="sm"
                variant="outline"
                className="w-full font-mono text-xs uppercase border-primary/30 hover:border-primary hover:bg-primary/10 text-primary transition-all"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowPredict(true);
                }}
              >
                <Zap className="w-3 h-3 mr-1.5" />
                Run ML Ensemble
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  );
}
