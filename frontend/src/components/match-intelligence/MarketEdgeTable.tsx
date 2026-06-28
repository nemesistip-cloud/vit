import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowUpRight, Scale, Coins } from 'lucide-react';

interface MarketEdgeTableProps {
  odds: any;
  match: any;
  edge: {
    ai_prob: number;
    bookmaker_prob: number | null;
    edge: number;
    expected_roi: number;
    kelly_stake: number;
  };
}

export const MarketEdgeTable: React.FC<MarketEdgeTableProps> = ({ odds, match, edge }) => {
  return (
    <Card className="border-white/5 bg-white/[0.01]">
      <CardHeader>
        <CardTitle className="text-[10px] font-mono uppercase tracking-[0.2em] flex items-center gap-2">
          <Scale size={14} className="text-primary" />
          Market Intelligence & Edge analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
           <div className="p-3 bg-white/5 border border-white/5 rounded-sm space-y-1">
              <p className="text-[8px] font-mono text-muted-foreground uppercase">Estimated Edge</p>
              <div className="flex items-center gap-1">
                 <p className={`text-lg font-display font-bold ${edge.edge > 0 ? 'text-vit-positive' : 'text-muted-foreground'}`}>
                    {(edge.edge * 100).toFixed(2)}%
                 </p>
                 {edge.edge > 0.05 && <ArrowUpRight size={14} className="text-vit-positive" />}
              </div>
           </div>
           <div className="p-3 bg-white/5 border border-white/5 rounded-sm space-y-1">
              <p className="text-[8px] font-mono text-muted-foreground uppercase">Expected ROI</p>
              <p className="text-lg font-display font-bold">
                 {edge.expected_roi.toFixed(1)}%
              </p>
           </div>
           <div className="p-3 bg-white/5 border border-white/5 rounded-sm space-y-1">
              <p className="text-[8px] font-mono text-muted-foreground uppercase">Kelly Stake</p>
              <p className="text-lg font-display font-bold text-primary">
                 {(edge.kelly_stake * 100).toFixed(1)}%
              </p>
           </div>
           <div className="p-3 bg-white/5 border border-white/5 rounded-sm space-y-1">
              <p className="text-[8px] font-mono text-muted-foreground uppercase">Efficiency</p>
              <p className="text-lg font-display font-bold">
                 {edge.bookmaker_prob ? ((1 - Math.abs(edge.ai_prob - edge.bookmaker_prob)) * 100).toFixed(0) : '--'}
              </p>
           </div>
        </div>

        <div className="overflow-x-auto">
           <table className="w-full text-left">
              <thead className="border-b border-white/5">
                 <tr>
                    <th className="pb-3 text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Market Metric</th>
                    <th className="pb-3 text-center text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Home</th>
                    <th className="pb-3 text-center text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Draw</th>
                    <th className="pb-3 text-center text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Away</th>
                 </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                 <tr className="group">
                    <td className="py-4 text-[10px] font-mono uppercase text-muted-foreground">Bookmaker Odds</td>
                    <td className="py-4 text-center font-mono text-xs font-bold">{odds?.home || '--'}</td>
                    <td className="py-4 text-center font-mono text-xs font-bold text-muted-foreground">{odds?.draw || '--'}</td>
                    <td className="py-4 text-center font-mono text-xs font-bold">{odds?.away || '--'}</td>
                 </tr>
                 <tr className="bg-primary/[0.02]">
                    <td className="py-4 text-[10px] font-mono uppercase text-primary font-bold">AI Probability</td>
                    <td className="py-4 text-center font-mono text-xs font-bold text-primary">
                       {(match.intelligence.consensus.home_prob * 100).toFixed(1)}%
                    </td>
                    <td className="py-4 text-center font-mono text-xs font-bold text-primary">
                       {(match.intelligence.consensus.draw_prob * 100).toFixed(1)}%
                    </td>
                    <td className="py-4 text-center font-mono text-xs font-bold text-primary">
                       {(match.intelligence.consensus.away_prob * 100).toFixed(1)}%
                    </td>
                 </tr>
              </tbody>
           </table>
        </div>

        <div className="pt-4 space-y-4">
           <h4 className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest">Secondary Markets</h4>
           <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 bg-white/5 border border-white/5 rounded-sm flex justify-between items-center">
                 <div>
                    <p className="text-[10px] font-mono font-bold uppercase tracking-tight">Over 2.5 Goals</p>
                    <p className="text-[9px] text-muted-foreground font-mono">CONVICTION: HIGH</p>
                 </div>
                 <span className="text-sm font-mono font-bold text-vit-positive">
                    {( (match.over_25_prob || 0.5) * 100).toFixed(1)}%
                 </span>
              </div>
              <div className="p-4 bg-white/5 border border-white/5 rounded-sm flex justify-between items-center">
                 <div>
                    <p className="text-[10px] font-mono font-bold uppercase tracking-tight">Both Teams to Score</p>
                    <p className="text-[9px] text-muted-foreground font-mono">CONVICTION: MEDIUM</p>
                 </div>
                 <span className="text-sm font-mono font-bold">
                    {( (match.btts_prob || 0.5) * 100).toFixed(1)}%
                 </span>
              </div>
           </div>
        </div>

        <div className="flex items-center gap-2 p-3 bg-white/[0.02] border border-dashed border-white/10 rounded-sm">
           <Coins size={14} className="text-primary" />
           <p className="text-[9px] font-mono text-muted-foreground uppercase leading-relaxed">
              Sharp money indicates <span className="text-foreground font-bold">HEAVY VOLUME</span> on {edge.edge > 0 ? 'FAVORED SIDE' : 'MARKET EQUILIBRIUM'}
           </p>
        </div>
      </CardContent>
    </Card>
  );
};
