import { useState } from "react";
import { useRoute, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  ChevronLeft, Share2, TrendingUp, BarChart3,
  Brain, Shield, Activity, Zap, Target, Flame
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";

function FormBadge({ result }: { result: string }) {
  const color =
    result === "W" ? "bg-green-500/20 text-green-400 border-green-500/30" :
    result === "L" ? "bg-red-500/20 text-red-400 border-red-500/30" :
    "bg-gray-500/20 text-gray-400 border-gray-500/30";
  return (
    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[10px] font-black border ${color}`}>
      {result}
    </span>
  );
}

export default function MatchDetailPage() {
  const [, params] = useRoute("/matches/:id");
  const [, navigate] = useLocation();
  const id = params?.id;

  const { data, isLoading } = useQuery<any>({
    queryKey: [`/api/matches/${id}`],
    queryFn: () => apiGet(`/api/matches/${id}`),
    enabled: !!id,
  });

  if (isLoading) return <div className="p-8"><RowSkeleton /><RowSkeleton /></div>;
  if (!data) return <div className="p-8 text-center text-vit-text-3">Match not found</div>;

  const match = data.match ?? data;
  const latestPred = data.predictions?.[0] ?? null;
  const consensus = data.consensus_breakdown ?? {};
  const modelSummary = data.model_summary ?? {};
  const modelContributions: any[] = data.model_contributions ?? [];
  const recentForm = data.recent_form ?? {};
  const h2h = data.head_to_head ?? {};

  const homeProb = consensus.home ?? match.home_prob ?? 0;
  const drawProb = consensus.draw ?? match.draw_prob ?? 0;
  const awayProb = consensus.away ?? match.away_prob ?? 0;
  const leader = consensus.leader ?? (homeProb >= awayProb ? "home" : "away");

  const aiConsensus = modelSummary.model_agreement_pct != null
    ? `${(modelSummary.model_agreement_pct * 100).toFixed(1)}%`
    : homeProb > 0
      ? `${(Math.max(homeProb, drawProb, awayProb) * 100).toFixed(1)}%`
      : "—";

  const marketEdge = latestPred?.edge != null
    ? (latestPred.edge >= 0 ? "+" : "") + (latestPred.edge * 100).toFixed(1) + "%"
    : match.home_prob > 0 && match.odds?.home
      ? (() => {
          const e = match.home_prob - (1 / match.odds.home);
          return (e >= 0 ? "+" : "") + (e * 100).toFixed(1) + "%";
        })()
      : "—";
  const edgePositive = latestPred?.edge != null ? latestPred.edge >= 0 : true;

  const betSide = latestPred?.bet_side ?? leader;
  const betLabel =
    betSide === "home" ? `${match.home_team} TO WIN` :
    betSide === "away" ? `${match.away_team} TO WIN` :
    "DRAW";
  const entryOdds = latestPred?.entry_odds ?? match.odds?.[betSide === "home" ? "home" : betSide === "away" ? "away" : "draw"];
  const confidence = latestPred?.confidence ?? match.confidence ?? 0;

  const kickoffDisplay = match.kickoff_time
    ? new Date(match.kickoff_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "TBD";

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({ title: `${match.home_team} vs ${match.away_team}`, url: window.location.href });
    } else {
      navigator.clipboard?.writeText(window.location.href);
    }
  };

  const handleBetSlip = () => {
    const provider = "betway";
    const selection = betSide === "home" ? "home" : betSide === "away" ? "away" : "draw";
    window.open(
      `/api/predictions/generate-slip?match_id=${id}&provider=${provider}&selection=${selection}&utm_source=vit_app`,
      "_blank"
    );
  };

  return (
    <div className="space-y-6 pb-20">
      <div className="flex items-center justify-between gap-4 px-1">
        <Button variant="ghost" size="icon" className="rounded-full bg-vit-surface-2" onClick={() => navigate("/matches")}>
          <ChevronLeft size={20} />
        </Button>
        <div className="text-center flex-1">
          <p className="text-[10px] font-bold text-vit-text-3 uppercase tracking-widest">{match.competition || match.league}</p>
          <h1 className="text-lg font-display font-bold text-vit-text-1">MATCH INTELLIGENCE</h1>
        </div>
        <Button variant="ghost" size="icon" className="rounded-full bg-vit-surface-2" onClick={handleShare}>
          <Share2 size={18} />
        </Button>
      </div>

      <Card className="bg-vit-surface border-vit-border overflow-hidden">
        <div className="p-6 text-center">
          <div className="flex items-center justify-around mb-6">
            <div className="w-20 space-y-2">
              <div className="w-16 h-16 mx-auto rounded-full bg-vit-surface-3 flex items-center justify-center border border-vit-border">
                <span className="text-xl font-bold">{match.home_team?.[0]}</span>
              </div>
              <p className="text-xs font-bold truncate">{match.home_team}</p>
            </div>
            <div className="text-center px-4">
              <div className="text-3xl font-display font-black text-vit-text-1 mb-1">
                {match.status === "live" ? `${match.home_goals ?? 0} : ${match.away_goals ?? 0}` : "VS"}
              </div>
              <Badge className={`text-[9px] ${match.status === "live" ? "bg-vit-negative/10 text-vit-negative border-vit-negative/20" : "bg-vit-surface-3 text-vit-text-3 border-vit-border"}`}>
                {match.status === "live" ? `${match.minute ?? ""}' LIVE` : "UPCOMING"}
              </Badge>
            </div>
            <div className="w-20 space-y-2">
              <div className="w-16 h-16 mx-auto rounded-full bg-vit-surface-3 flex items-center justify-center border border-vit-border">
                <span className="text-xl font-bold">{match.away_team?.[0]}</span>
              </div>
              <p className="text-xs font-bold truncate">{match.away_team}</p>
            </div>
          </div>

          {homeProb > 0 && (
            <div className="flex items-center gap-1 mb-4 rounded-xl overflow-hidden h-2">
              <div className="h-full bg-vit-green rounded-l-xl transition-all" style={{ width: `${homeProb * 100}%` }} />
              <div className="h-full bg-vit-text-3/40 transition-all" style={{ width: `${drawProb * 100}%` }} />
              <div className="h-full bg-blue-500/60 rounded-r-xl transition-all" style={{ width: `${awayProb * 100}%` }} />
            </div>
          )}
          {homeProb > 0 && (
            <div className="flex justify-between text-[9px] font-mono text-vit-text-3 px-1 mb-4">
              <span className="text-vit-green font-bold">{(homeProb * 100).toFixed(0)}% H</span>
              <span>{(drawProb * 100).toFixed(0)}% D</span>
              <span className="text-blue-400 font-bold">{(awayProb * 100).toFixed(0)}% A</span>
            </div>
          )}

          <div className="flex items-center justify-center gap-6 pt-4 border-t border-vit-border/50">
            <div className="text-center">
              <p className="text-[10px] text-vit-text-3 uppercase">Kickoff</p>
              <p className="text-xs font-mono font-bold">{kickoffDisplay}</p>
            </div>
            <div className="text-center">
              <p className="text-[10px] text-vit-text-3 uppercase">Venue</p>
              <p className="text-xs font-bold">{match.venue || "Neutral"}</p>
            </div>
            {modelSummary.models_used > 0 && (
              <div className="text-center">
                <p className="text-[10px] text-vit-text-3 uppercase">Models</p>
                <p className="text-xs font-mono font-bold">{modelSummary.models_used}</p>
              </div>
            )}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          label="AI CONSENSUS"
          value={aiConsensus}
          icon={<Brain size={16} className="text-vit-green" />}
        />
        <MetricCard
          label="MARKET EDGE"
          value={marketEdge}
          changePositive={edgePositive}
          icon={<TrendingUp size={16} className={edgePositive ? "text-vit-green" : "text-red-400"} />}
        />
      </div>

      <Tabs defaultValue="insights">
        <TabsList className="bg-vit-surface-2 border border-vit-border p-1 h-10 w-full grid grid-cols-3">
          <TabsTrigger value="insights" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">INSIGHTS</TabsTrigger>
          <TabsTrigger value="odds" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">ODDS</TabsTrigger>
          <TabsTrigger value="stats" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">STATS</TabsTrigger>
        </TabsList>

        <TabsContent value="insights" className="mt-4 space-y-4">
          {(latestPred || homeProb > 0) && (
            <Card className="bg-vit-surface border-vit-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-display font-bold flex items-center gap-2">
                  <Zap size={16} className="text-vit-green" /> ENSEMBLE SIGNAL
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="p-4 bg-vit-green-glow border border-vit-green/20 rounded-xl flex justify-between items-center">
                  <div>
                    <p className="text-[10px] font-bold text-vit-green uppercase tracking-widest">Recommended Selection</p>
                    <h3 className="text-lg font-bold text-vit-text-1">{betLabel}</h3>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-mono font-black text-vit-text-1">
                      {entryOdds ? Number(entryOdds).toFixed(2) : "—"}
                    </p>
                    <p className="text-[10px] text-vit-green font-bold">
                      CONFIDENCE: {confidence > 0 ? `${(confidence * 100).toFixed(0)}%` : "—"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {modelContributions.length > 0 ? (
            <div className="bg-vit-surface border border-vit-border rounded-xl p-4">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 mb-3">Model Breakdown</h4>
              <div className="space-y-2">
                {modelContributions.slice(0, 5).map((m: any, i: number) => {
                  const pct = Math.round(
                    ((m.home_prob ?? m.prob ?? 0) * (m.weight ?? 1)) * 100
                  ) || Math.round((m.home_prob ?? 0) * 100);
                  return (
                    <div key={i} className="flex items-center gap-4">
                      <span className="text-[10px] font-mono text-vit-text-2 w-32 truncate">
                        {m.model_name ?? m.name ?? `Model ${i + 1}`}
                      </span>
                      <div className="flex-1 h-1.5 bg-vit-surface-3 rounded-full overflow-hidden">
                        <div className="h-full bg-vit-green" style={{ width: `${Math.min(pct, 100)}%` }} />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-vit-text-1">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : homeProb > 0 ? (
            <div className="bg-vit-surface border border-vit-border rounded-xl p-4">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 mb-3">Probability Breakdown</h4>
              <div className="space-y-2">
                {[
                  { name: "Home Win", prob: Math.round(homeProb * 100) },
                  { name: "Draw", prob: Math.round(drawProb * 100) },
                  { name: "Away Win", prob: Math.round(awayProb * 100) },
                ].map((m, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <span className="text-[10px] font-mono text-vit-text-2 w-32 truncate">{m.name}</span>
                    <div className="flex-1 h-1.5 bg-vit-surface-3 rounded-full overflow-hidden">
                      <div className="h-full bg-vit-green" style={{ width: `${m.prob}%` }} />
                    </div>
                    <span className="text-[10px] font-mono font-bold text-vit-text-1">{m.prob}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-vit-surface border border-vit-border rounded-xl p-6 text-center text-vit-text-3 text-xs">
              AI analysis is being generated — check back soon
            </div>
          )}

          {modelSummary.ensemble_diversity != null && (
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-vit-surface border border-vit-border rounded-xl p-3 text-center">
                <p className="text-[9px] text-vit-text-3 uppercase font-bold mb-1">Ensemble Diversity</p>
                <p className="text-sm font-mono font-black text-vit-text-1">
                  {(modelSummary.ensemble_diversity * 100).toFixed(0)}%
                </p>
              </div>
              <div className="bg-vit-surface border border-vit-border rounded-xl p-3 text-center">
                <p className="text-[9px] text-vit-text-3 uppercase font-bold mb-1">Models Used</p>
                <p className="text-sm font-mono font-black text-vit-text-1">{modelSummary.models_used ?? "—"}</p>
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent value="odds" className="mt-4">
          <div className="bg-vit-surface border border-vit-border rounded-xl overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-vit-surface-2 border-b border-vit-border">
                <tr>
                  <th className="p-3 text-[10px] font-bold text-vit-text-3 uppercase">Bookmaker</th>
                  <th className="p-3 text-[10px] font-bold text-vit-text-3 uppercase text-center">1</th>
                  <th className="p-3 text-[10px] font-bold text-vit-text-3 uppercase text-center">X</th>
                  <th className="p-3 text-[10px] font-bold text-vit-text-3 uppercase text-center">2</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-vit-border">
                {(match.bookmaker_odds && match.bookmaker_odds.length > 0
                  ? match.bookmaker_odds
                  : match.odds?.home
                    ? [{ bookmaker: "Market", home: match.odds.home, draw: match.odds.draw, away: match.odds.away }]
                    : []
                ).map((b: any, i: number) => (
                  <tr key={i} className="hover:bg-vit-surface-2 transition-colors">
                    <td className="p-3 text-xs font-bold">{b.bookmaker}</td>
                    <td className="p-3 text-center font-mono text-xs text-vit-green">{b.home ?? "--"}</td>
                    <td className="p-3 text-center font-mono text-xs">{b.draw ?? "--"}</td>
                    <td className="p-3 text-center font-mono text-xs">{b.away ?? "--"}</td>
                  </tr>
                ))}
                {(!match.bookmaker_odds || match.bookmaker_odds.length === 0) && !match.odds?.home && (
                  <tr>
                    <td colSpan={4} className="p-6 text-center text-[11px] text-vit-text-3">
                      Live odds unavailable — check back closer to kickoff
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {latestPred && (
            <div className="mt-3 grid grid-cols-3 gap-2">
              {[
                { label: "Over 2.5", val: latestPred.over_25_prob },
                { label: "BTTS", val: latestPred.btts_prob },
                { label: "Under 2.5", val: latestPred.under_25_prob },
              ].filter(x => x.val != null).map((x, i) => (
                <div key={i} className="bg-vit-surface border border-vit-border rounded-xl p-3 text-center">
                  <p className="text-[9px] text-vit-text-3 uppercase font-bold">{x.label}</p>
                  <p className="text-sm font-mono font-black text-vit-text-1">{(x.val * 100).toFixed(0)}%</p>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="stats" className="mt-4 space-y-4">
          {(recentForm.home?.length > 0 || recentForm.away?.length > 0) && (
            <Card className="bg-vit-surface border-vit-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-display font-bold flex items-center gap-2">
                  <Flame size={16} className="text-orange-400" /> RECENT FORM
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-vit-text-2 w-24 truncate">{match.home_team}</span>
                  <div className="flex gap-1">
                    {(recentForm.home ?? []).slice(0, 5).map((r: string, i: number) => (
                      <FormBadge key={i} result={r} />
                    ))}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-vit-text-2 w-24 truncate">{match.away_team}</span>
                  <div className="flex gap-1">
                    {(recentForm.away ?? []).slice(0, 5).map((r: string, i: number) => (
                      <FormBadge key={i} result={r} />
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {h2h && (h2h.home_wins != null || h2h.total != null) && (
            <Card className="bg-vit-surface border-vit-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-display font-bold flex items-center gap-2">
                  <Shield size={16} className="text-vit-text-2" /> HEAD TO HEAD
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-vit-surface-2 rounded-xl p-3">
                    <p className="text-lg font-black text-vit-green">{h2h.home_wins ?? 0}</p>
                    <p className="text-[9px] text-vit-text-3 uppercase font-bold truncate">{match.home_team}</p>
                  </div>
                  <div className="bg-vit-surface-2 rounded-xl p-3">
                    <p className="text-lg font-black text-vit-text-1">{h2h.draws ?? 0}</p>
                    <p className="text-[9px] text-vit-text-3 uppercase font-bold">Draws</p>
                  </div>
                  <div className="bg-vit-surface-2 rounded-xl p-3">
                    <p className="text-lg font-black text-blue-400">{h2h.away_wins ?? 0}</p>
                    <p className="text-[9px] text-vit-text-3 uppercase font-bold truncate">{match.away_team}</p>
                  </div>
                </div>
                {h2h.total != null && (
                  <p className="text-center text-[10px] text-vit-text-3 mt-2">
                    From {h2h.total} meetings
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {match.over_25_prob != null && (
            <Card className="bg-vit-surface border-vit-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-display font-bold flex items-center gap-2">
                  <Activity size={16} className="text-vit-text-2" /> MARKET SIGNALS
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Over 2.5 Goals", val: match.over_25_prob },
                    { label: "Under 2.5 Goals", val: match.under_25_prob },
                    { label: "BTTS", val: match.btts_prob },
                    { label: "No BTTS", val: match.no_btts_prob },
                  ].filter(x => x.val != null).map((x, i) => (
                    <div key={i} className="bg-vit-surface-2 rounded-xl p-3">
                      <p className="text-[9px] text-vit-text-3 uppercase font-bold">{x.label}</p>
                      <div className="mt-1 h-1 bg-vit-surface-3 rounded-full overflow-hidden">
                        <div className="h-full bg-vit-green" style={{ width: `${(x.val * 100).toFixed(0)}%` }} />
                      </div>
                      <p className="text-xs font-mono font-black text-vit-text-1 mt-1">{(x.val * 100).toFixed(0)}%</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {!recentForm.home?.length && !h2h?.total && !match.over_25_prob && (
            <div className="bg-vit-surface border border-vit-border rounded-xl p-6 text-center text-vit-text-3 text-xs">
              Stats will populate as match data is collected
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Button
        className="w-full h-12 bg-vit-green text-vit-text-inverse font-black tracking-widest rounded-xl"
        onClick={handleBetSlip}
      >
        <Target size={16} className="mr-2" />
        GENERATE BET SLIP
      </Button>
    </div>
  );
}
