import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BrainCircuit, Info, Zap, ShieldAlert } from 'lucide-react';

interface TacticalIntelligenceProps {
  data: {
    summary: string;
    key_factors: string[];
    tactical_assessment: string;
    risk_level: string;
    value_assessment: string;
    scie_version: string;
    provider: string;
    confidence: number;
  };
}

export const TacticalIntelligence: React.FC<TacticalIntelligenceProps> = ({ data }) => {
  if (!data) return null;

  return (
    <Card className="border-white/5 bg-white/[0.01]">
      <CardHeader>
        <CardTitle className="text-[10px] font-mono uppercase tracking-[0.2em] flex items-center gap-2">
          <BrainCircuit size={14} className="text-primary" />
          Tactical Explanation Engine
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="bg-primary/5 border border-primary/10 rounded-sm p-4 relative overflow-hidden">
           <Zap size={40} className="absolute -right-4 -bottom-4 text-primary/5 rotate-12" />
           <p className="text-sm font-display font-bold leading-tight mb-2">"{data.summary}"</p>
           <p className="text-[11px] text-muted-foreground leading-relaxed italic">{data.tactical_assessment}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
           <div className="space-y-3">
              <h4 className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest flex items-center gap-2">
                 <Info size={12} className="text-primary" /> Contributing Factors
              </h4>
              <div className="space-y-2">
                 {data.key_factors.map((factor, i) => (
                    <div key={i} className="flex gap-2 items-start">
                       <div className="w-1 h-1 rounded-full bg-primary mt-1.5 flex-shrink-0" />
                       <p className="text-[10px] leading-normal text-foreground/80">{factor}</p>
                    </div>
                 ))}
              </div>
           </div>

           <div className="space-y-4">
              <div className="space-y-2">
                 <h4 className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest">Risk Classification</h4>
                 <div className="flex items-center gap-3">
                    <Badge className={`rounded-sm font-mono text-[10px] ${
                       data.risk_level === 'LOW' ? 'bg-vit-positive/10 text-vit-positive border-vit-positive/20' :
                       data.risk_level === 'MEDIUM' ? 'bg-secondary/10 text-secondary border-secondary/20' :
                       'bg-red-500/10 text-red-500 border-red-500/20'
                    }`}>
                       {data.risk_level} VOLATILITY
                    </Badge>
                    <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
                       <div
                          className={`h-full ${data.risk_level === 'LOW' ? 'bg-vit-positive' : data.risk_level === 'MEDIUM' ? 'bg-secondary' : 'bg-red-500'}`}
                          style={{ width: data.risk_level === 'LOW' ? '33%' : data.risk_level === 'MEDIUM' ? '66%' : '100%' }}
                       />
                    </div>
                 </div>
              </div>

              <div className="space-y-2">
                 <h4 className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest">Intelligence Grade</h4>
                 <div className="p-3 bg-white/5 border border-white/5 rounded-sm flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase">{data.value_assessment}</span>
                    <ShieldAlert size={16} className="text-primary" />
                 </div>
              </div>
           </div>
        </div>

        <div className="pt-4 border-t border-white/5 flex justify-between items-center opacity-40">
           <span className="text-[8px] font-mono uppercase tracking-tighter">Source: {data.provider}</span>
           <span className="text-[8px] font-mono uppercase tracking-tighter">Engine: {data.scie_version}</span>
        </div>
      </CardContent>
    </Card>
  );
};
