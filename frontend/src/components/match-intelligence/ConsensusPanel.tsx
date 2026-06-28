import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Cpu, TrendingUp } from 'lucide-react';

interface ConsensusPanelProps {
  data: {
    home_prob: number;
    draw_prob: number;
    away_prob: number;
    confidence: number;
    risk_score: number;
    model_agreement: number;
    models_active: number;
    timestamp?: string;
  };
  homeTeam: string;
  awayTeam: string;
}

export const ConsensusPanel: React.FC<ConsensusPanelProps> = ({ data, homeTeam, awayTeam }) => {
  const leader = Math.max(data.home_prob, data.draw_prob, data.away_prob);
  const leaderLabel = leader === data.home_prob ? homeTeam : (leader === data.away_prob ? awayTeam : 'Draw');

  return (
    <Card className="border-white/5 bg-white/[0.01] backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-[10px] font-mono uppercase tracking-[0.2em] flex items-center gap-2">
          <Cpu size={14} className="text-primary animate-pulse" />
          AI Ensemble Consensus
        </CardTitle>
        <Badge variant="outline" className="font-mono text-[9px] border-primary/20 text-primary">
          {data.models_active} MODELS ACTIVE
        </Badge>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-3 gap-4 py-4">
          <div className="text-center space-y-1">
            <p className="text-[9px] text-muted-foreground uppercase font-mono tracking-tighter">Confidence</p>
            <p className="text-xl font-display font-bold text-vit-positive">{(data.confidence * 100).toFixed(0)}%</p>
          </div>
          <div className="text-center space-y-1 border-x border-white/5">
            <p className="text-[9px] text-muted-foreground uppercase font-mono tracking-tighter">Risk Score</p>
            <p className="text-xl font-display font-bold text-secondary">{(data.risk_score * 100).toFixed(0)}</p>
          </div>
          <div className="text-center space-y-1">
            <p className="text-[9px] text-muted-foreground uppercase font-mono tracking-tighter">Agreement</p>
            <p className="text-xl font-display font-bold text-primary">{(data.model_agreement * 100).toFixed(0)}%</p>
          </div>
        </div>

        <div className="space-y-5">
          {[
            { label: homeTeam, prob: data.home_prob, color: 'bg-primary' },
            { label: 'Market Equilibrium', prob: data.draw_prob, color: 'bg-muted-foreground/30' },
            { label: awayTeam, prob: data.away_prob, color: 'bg-secondary' },
          ].map((item, i) => (
            <div key={i} className="group">
              <div className="flex justify-between items-end mb-2">
                <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground group-hover:text-foreground transition-colors">
                  {item.label}
                </span>
                <span className="text-sm font-mono font-bold">{(item.prob * 100).toFixed(1)}%</span>
              </div>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <div
                  className={`h-full ${item.color} transition-all duration-1000 ease-out`}
                  style={{ width: `${item.prob * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="pt-4 mt-4 border-t border-white/5 flex items-center justify-between">
           <div className="flex items-center gap-2">
              <TrendingUp size={12} className="text-vit-positive" />
              <span className="text-[9px] font-mono text-muted-foreground uppercase">Primary Signal: <span className="text-foreground font-bold">{leaderLabel}</span></span>
           </div>
           <span className="text-[8px] font-mono text-muted-foreground uppercase opacity-50">v5.5.0-ensemble</span>
        </div>
      </CardContent>
    </Card>
  );
};
