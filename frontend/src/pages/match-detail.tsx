import { useState, useMemo } from "react";
import { useRoute, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  ChevronLeft, Share2, TrendingUp, BarChart3, Info,
  Brain, Shield, Users, Activity, Clock, Zap
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";

export default function MatchDetailPage() {
  const [, params] = useRoute("/matches/:id");
  const [, navigate] = useLocation();
  const id = params?.id;

  const { data: match, isLoading } = useQuery<any>({
    queryKey: [`/api/matches/${id}`],
    queryFn: () => apiGet(`/api/matches/${id}`),
    enabled: !!id,
  });

  const { data: predictions } = useQuery<any>({
    queryKey: [`/api/predictions/${id}`],
    queryFn: () => apiGet(`/api/predictions/${id}`),
    enabled: !!id,
  });

  if (isLoading) return <div className="p-8"><RowSkeleton /><RowSkeleton /></div>;
  if (!match) return <div className="p-8 text-center text-vit-text-3">Match not found</div>;

  return (
    <div className="space-y-6 pb-20">
      <div className="flex items-center justify-between gap-4 px-1">
        <Button variant="ghost" size="icon" className="rounded-full bg-vit-surface-2" onClick={() => navigate('/matches')}>
          <ChevronLeft size={20} />
        </Button>
        <div className="text-center flex-1">
          <p className="text-[10px] font-bold text-vit-text-3 uppercase tracking-widest">{match.competition || match.league}</p>
          <h1 className="text-lg font-display font-bold text-vit-text-1">MATCH INTELLIGENCE</h1>
        </div>
        <Button variant="ghost" size="icon" className="rounded-full bg-vit-surface-2">
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
                    {match.status === 'live' ? `${match.home_score} : ${match.away_score}` : 'VS'}
                 </div>
                 <Badge className="bg-vit-negative/10 text-vit-negative border-vit-negative/20 text-[9px]">
                    {match.status === 'live' ? `${match.minute}'` : 'UPCOMING'}
                 </Badge>
              </div>
              <div className="w-20 space-y-2">
                 <div className="w-16 h-16 mx-auto rounded-full bg-vit-surface-3 flex items-center justify-center border border-vit-border">
                    <span className="text-xl font-bold">{match.away_team?.[0]}</span>
                 </div>
                 <p className="text-xs font-bold truncate">{match.away_team}</p>
              </div>
           </div>
           <div className="flex items-center justify-center gap-6 pt-4 border-t border-vit-border/50">
              <div className="text-center">
                 <p className="text-[10px] text-vit-text-3 uppercase">Kickoff</p>
                 <p className="text-xs font-mono font-bold">{new Date(match.kickoff_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
              </div>
              <div className="text-center">
                 <p className="text-[10px] text-vit-text-3 uppercase">Venue</p>
                 <p className="text-xs font-bold">{match.venue || 'Neutral'}</p>
              </div>
           </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4">
         <MetricCard
            label="AI CONSENSUS"
            value="84.2%"
            icon={<Brain size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="MARKET EDGE"
            value="+4.5%"
            changePositive={true}
            icon={<TrendingUp size={16} className="text-vit-green" />}
         />
      </div>

      <Tabs defaultValue="insights">
        <TabsList className="bg-vit-surface-2 border border-vit-border p-1 h-10 w-full grid grid-cols-3">
          <TabsTrigger value="insights" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">INSIGHTS</TabsTrigger>
          <TabsTrigger value="odds" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">ODDS</TabsTrigger>
          <TabsTrigger value="stats" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">STATS</TabsTrigger>
        </TabsList>

        <TabsContent value="insights" className="mt-4 space-y-4">
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
                       <h3 className="text-lg font-bold text-vit-text-1">{match.home_team} TO WIN</h3>
                    </div>
                    <div className="text-right">
                       <p className="text-sm font-mono font-black text-vit-text-1">2.45</p>
                       <p className="text-[10px] text-vit-green font-bold">CONFIDENCE: 82%</p>
                    </div>
                 </div>
              </CardContent>
           </Card>

           <div className="bg-vit-surface border border-vit-border rounded-xl p-4">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 mb-3">Model Breakdown</h4>
              <div className="space-y-2">
                 {[
                   { name: "Neural Network V2", prob: 88, weight: 0.4 },
                   { name: "XGBoost Consensus", prob: 76, weight: 0.3 },
                   { name: "Poisson Goals", prob: 82, weight: 0.3 },
                 ].map((m, i) => (
                   <div key={i} className="flex items-center gap-4">
                      <span className="text-[10px] font-mono text-vit-text-2 w-28 truncate">{m.name}</span>
                      <div className="flex-1 h-1.5 bg-vit-surface-3 rounded-full overflow-hidden">
                         <div className="h-full bg-vit-green" style={{ width: `${m.prob}%` }} />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-vit-text-1">{m.prob}%</span>
                   </div>
                 ))}
              </div>
           </div>
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
                      : (match.odds
                          ? [{ bookmaker: 'Market', home: match.odds.home, draw: match.odds.draw, away: match.odds.away }]
                          : []
                        )
                    ).map((b: any) => (
                      <tr key={b.bookmaker} className="hover:bg-vit-surface-2 transition-colors">
                         <td className="p-3 text-xs font-bold">{b.bookmaker}</td>
                         <td className="p-3 text-center font-mono text-xs text-vit-green">{b.home ?? '--'}</td>
                         <td className="p-3 text-center font-mono text-xs">{b.draw ?? '--'}</td>
                         <td className="p-3 text-center font-mono text-xs">{b.away ?? '--'}</td>
                      </tr>
                    ))}
                    {(!match.bookmaker_odds || match.bookmaker_odds.length === 0) && !match.odds && (
                      <tr>
                        <td colSpan={4} className="p-6 text-center text-[11px] text-vit-text-3">
                          Live odds unavailable — check back closer to kickoff
                        </td>
                      </tr>
                    )}
                 </tbody>
              </table>
           </div>
        </TabsContent>
      </Tabs>

      <Button className="w-full h-12 bg-vit-green text-vit-text-inverse font-black tracking-widest rounded-xl">
         GENERATE BET SLIP
      </Button>
    </div>
  );
}
