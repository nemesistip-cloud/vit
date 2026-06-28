import React from 'react';
import { useRoute, useLocation } from 'wouter';
import { useAuth } from '@/lib/auth';
import { apiGet as apiClient } from '@/lib/apiClient';
import { Layout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Zap, Clock, MapPin, User, Trophy,
  ChevronLeft, Share2, Target, BarChart3,
  TrendingUp, Users, DollarSign
} from 'lucide-react';
import { format } from 'date-fns';
import { useToast } from '@/hooks/use-toast';
import { RowSkeleton } from '@/components/skeletons/RowSkeleton';
import { ConsensusPanel } from '@/components/match-intelligence/ConsensusPanel';
import { TacticalIntelligence } from '@/components/match-intelligence/TacticalIntelligence';
import { ModelBreakdown } from '@/components/match-intelligence/ModelBreakdown';
import { MarketEdgeTable } from '@/components/match-intelligence/MarketEdgeTable';
import { TacticalRadar } from '@/components/match-intelligence/TacticalRadar';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card';
import { useQuery } from "@tanstack/react-query";

export default function MatchDetailPage() {
  const [, params] = useRoute('/matches/:id');
  const [, setLocation] = useLocation();
  const { id } = params || {};
  const { user } = useAuth();
  const { toast } = useToast();

  const { data: match, isLoading: loading, error } = useQuery<any>({
    queryKey: ['match', id],
    queryFn: () => apiClient(`/matches/${id}`),
    enabled: !!id,
  });

  if (loading) {
    return (
      <Layout>
        <div className="p-6 space-y-6">
          <RowSkeleton count={5} />
        </div>
      </Layout>
    );
  }

  if (error || !match) {
    return (
       <Layout>
          <div className="p-6 text-center space-y-4">
             <p className="text-red-500 font-mono text-sm">FAILED TO SYNCHRONIZE INTELLIGENCE FEED</p>
             <Button variant="outline" onClick={() => window.location.reload()}>RETRY CONNECTION</Button>
          </div>
       </Layout>
    );
  }

  const handleBetSlip = () => {
    toast({
      title: 'Success',
      description: 'Selection added to intelligence slip.',
    });
  };

  const safeFormat = (dateStr: string, formatStr: string) => {
    try {
      return format(new Date(dateStr), formatStr);
    } catch {
      return 'N/A';
    }
  };

  const intel = match.intelligence;

  return (
    <Layout>
      <div className="min-h-screen bg-[#0C0E12] pb-32">
        {/* ── Header ── */}
        <div className="sticky top-0 z-40 bg-[#0C0E12]/80 backdrop-blur-md border-b border-white/5 p-4 flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setLocation('/matches')} className="text-muted-foreground hover:text-foreground">
            <ChevronLeft size={20} />
          </Button>
          <div className="flex-1 min-w-0">
            <p className="font-mono text-[9px] text-primary uppercase tracking-[0.2em]">{match.league}</p>
            <h1 className="text-sm font-display font-bold uppercase truncate tracking-tight">Intelligence Terminal</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="text-muted-foreground"><Share2 size={16} /></Button>
            <Badge variant="outline" className="font-mono text-[9px] border-white/10 text-muted-foreground">NODE: {id?.toString().slice(0, 8)}</Badge>
          </div>
        </div>

        <div className="max-w-4xl mx-auto p-4 space-y-6">
          {/* ── Hero Match Section ── */}
          <div className="relative overflow-hidden rounded-sm border border-white/5 bg-gradient-to-br from-white/[0.03] to-transparent p-8 text-center">
             <div className="absolute top-0 right-0 p-4 opacity-20">
                <Trophy size={64} className="text-primary" />
             </div>

             <div className="flex items-center justify-between gap-4 relative z-10">
                <div className="flex-1 space-y-4">
                   <div className="w-20 h-20 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mx-auto shadow-2xl">
                      <span className="text-3xl font-black text-primary">{match.home_team?.[0]}</span>
                   </div>
                   <p className="text-sm font-display font-bold uppercase tracking-widest">{match.home_team}</p>
                </div>

                <div className="flex flex-col items-center gap-2">
                   <span className="font-mono text-xs text-muted-foreground opacity-50 uppercase tracking-widest italic">V/S</span>
                   <div className="h-px w-12 bg-primary/20" />
                   <Badge className="bg-primary/10 text-primary border-primary/20 text-[9px] font-mono">LIVE FEED</Badge>
                </div>

                <div className="flex-1 space-y-4">
                   <div className="w-20 h-20 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mx-auto shadow-2xl">
                      <span className="text-3xl font-black text-secondary">{match.away_team?.[0]}</span>
                   </div>
                   <p className="text-sm font-display font-bold uppercase tracking-widest">{match.away_team}</p>
                </div>
             </div>

             <div className="mt-10 flex flex-wrap justify-center gap-6 border-t border-white/5 pt-6">
                <div className="flex items-center gap-2 text-muted-foreground">
                   <Clock size={14} className="text-primary" />
                   <span className="font-mono text-[10px] uppercase tracking-wider">{safeFormat(match.kickoff_time, 'MMM dd, yyyy • HH:mm')}</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                   <MapPin size={14} />
                   <span className="font-mono text-[10px] uppercase tracking-wider">Global Arena</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                   <User size={14} />
                   <span className="font-mono text-[10px] uppercase tracking-wider">Ref: Certified AI</span>
                </div>
             </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
             <div className="lg:col-span-8 space-y-6">
                <ConsensusPanel data={intel.consensus} homeTeam={match.home_team} awayTeam={match.away_team} />
                <TacticalIntelligence data={intel.tactical} />
                <TacticalRadar homeTeam={match.home_team} awayTeam={match.away_team} data={intel.radar_data} />
                <MarketEdgeTable odds={match.odds} match={match} edge={intel.market_edge} />
             </div>

             <div className="lg:col-span-4 space-y-6">
                {/* ── Institutional Analytics ── */}
                <div className="p-4 rounded-sm border border-primary/20 bg-primary/[0.03] space-y-4">
                   <h3 className="text-[10px] font-mono uppercase text-primary font-bold tracking-widest flex items-center gap-2">
                      <Target size={14} /> Executive Summary
                   </h3>
                   <div className="space-y-4">
                      <div>
                         <p className="text-[9px] text-muted-foreground uppercase font-mono mb-1">Primary Prediction</p>
                         <p className="text-lg font-bold text-foreground">
                            {intel.consensus.home_prob > intel.consensus.away_prob ? match.home_team : match.away_team} Win
                         </p>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                         <div>
                            <p className="text-[9px] text-muted-foreground uppercase font-mono mb-1">Edge</p>
                            <p className="text-sm font-bold text-vit-positive">{(intel.market_edge.edge * 100).toFixed(1)}%</p>
                         </div>
                         <div>
                            <p className="text-[9px] text-muted-foreground uppercase font-mono mb-1">Confidence</p>
                            <p className="text-sm font-bold">{(intel.consensus.confidence * 100).toFixed(0)}%</p>
                         </div>
                      </div>
                      <div className="pt-2">
                         <Badge className="w-full justify-center bg-white/5 border-white/10 text-[10px] font-mono py-1 rounded-sm">
                            INVESTMENT GRADE: {intel.market_edge.edge > 0.04 ? 'AAA' : 'BBB+'}
                         </Badge>
                      </div>
                   </div>
                </div>

                {/* ── Detailed Metrics ── */}
                <Card className="border-white/5 bg-white/[0.01]">
                   <CardHeader className="pb-2 border-b border-white/5">
                      <CardTitle className="text-[10px] font-mono uppercase tracking-widest flex items-center gap-2">
                         <TrendingUp size={14} className="text-primary" /> Institutional Metrics
                      </CardTitle>
                   </CardHeader>
                   <CardContent className="space-y-4 pt-4">
                      <div className="flex justify-between items-center">
                         <div className="flex items-center gap-2">
                            <Zap size={12} className="text-muted-foreground" />
                            <span className="text-[10px] font-mono text-muted-foreground uppercase">Elo Differential</span>
                         </div>
                         <span className={`text-[10px] font-mono font-bold ${intel.consensus.elo_diff > 0 ? 'text-vit-positive' : 'text-secondary'}`}>
                            {intel.consensus.elo_diff > 0 ? '+' : ''}{intel.consensus.elo_diff.toFixed(0)}
                         </span>
                      </div>
                      <div className="flex justify-between items-center">
                         <div className="flex items-center gap-2">
                            <DollarSign size={12} className="text-muted-foreground" />
                            <span className="text-[10px] font-mono text-muted-foreground uppercase">Squad Value Delta</span>
                         </div>
                         <span className="text-[10px] font-mono font-bold text-foreground">
                            {intel.consensus.squad_value_diff > 0 ? '+' : ''}{intel.consensus.squad_value_diff}%
                         </span>
                      </div>
                      <div className="flex justify-between items-center">
                         <div className="flex items-center gap-2">
                            <BarChart3 size={12} className="text-muted-foreground" />
                            <span className="text-[10px] font-mono text-muted-foreground uppercase">Volatility Index</span>
                         </div>
                         <span className="text-[10px] font-mono font-bold">{(intel.consensus.risk_score * 10).toFixed(1)}/10</span>
                      </div>
                      <div className="flex justify-between items-center">
                         <div className="flex items-center gap-2">
                            <Users size={12} className="text-muted-foreground" />
                            <span className="text-[10px] font-mono text-muted-foreground uppercase">Model Agreement</span>
                         </div>
                         <span className="text-[10px] font-mono font-bold text-vit-positive">{(intel.consensus.model_agreement * 100).toFixed(0)}%</span>
                      </div>
                   </CardContent>
                </Card>

                <ModelBreakdown attribution={intel.attribution} />
             </div>
          </div>
        </div>

        {/* ── Fixed Footer CTA ── */}
        <div className="fixed bottom-0 inset-x-0 z-50 p-4 bg-[#0C0E12]/95 backdrop-blur-xl border-t border-white/5">
           <div className="max-w-4xl mx-auto flex items-center justify-between gap-6">
              <div className="hidden sm:block">
                 <p className="text-[9px] font-mono text-muted-foreground uppercase">Execution Metrics</p>
                 <div className="flex gap-4 mt-1">
                    <span className="text-xs font-mono font-bold text-primary">EDGE: {(intel.market_edge.edge * 100).toFixed(1)}%</span>
                    <span className="text-xs font-mono font-bold text-vit-positive">ROI: {intel.market_edge.expected_roi.toFixed(1)}%</span>
                 </div>
              </div>
              <Button
                className="flex-1 h-12 bg-primary hover:bg-primary/90 text-primary-foreground font-display font-black uppercase tracking-[0.2em] shadow-lg shadow-primary/20 rounded-sm"
                onClick={handleBetSlip}
              >
                <Zap size={18} className="mr-2 fill-current" />
                Execute Intelligence Slip
              </Button>
           </div>
        </div>
      </div>
    </Layout>
  );
}
