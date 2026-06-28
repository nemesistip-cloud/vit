import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Microscope, ChevronRight } from 'lucide-react';

interface ModelBreakdownProps {
  attribution: any[];
}

export const ModelBreakdown: React.FC<ModelBreakdownProps> = ({ attribution }) => {
  if (!attribution || attribution.length === 0) return null;

  return (
    <Card className="border-white/5 bg-white/[0.01]">
      <CardHeader>
        <CardTitle className="text-[10px] font-mono uppercase tracking-[0.2em] flex items-center gap-2">
          <Microscope size={14} className="text-primary" />
          Individual Model Performance
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-white/5">
          {attribution.map((model, i) => (
            <div key={i} className="p-4 hover:bg-white/[0.02] transition-colors flex items-center justify-between group">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-sm bg-white/5 border border-white/5 flex items-center justify-center font-mono text-[10px] font-bold text-primary">
                  {model.model_name?.[0] || 'M'}
                </div>
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-tight">{model.model_name || 'Neural Engine'}</p>
                  <p className="text-[9px] text-muted-foreground font-mono">WEIGHT: {((model.model_weight || 1.0) * 10).toFixed(1)}x</p>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <p className="text-[10px] font-mono font-bold">{( (model.home_prob || 0.33) * 100).toFixed(1)}%</p>
                  <p className="text-[8px] text-muted-foreground uppercase font-mono">HOME</p>
                </div>
                <div className="text-right hidden sm:block">
                  <p className="text-[10px] font-mono font-bold">{( (model.draw_prob || 0.33) * 100).toFixed(1)}%</p>
                  <p className="text-[8px] text-muted-foreground uppercase font-mono">DRAW</p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-mono font-bold">{( (model.away_prob || 0.33) * 100).toFixed(1)}%</p>
                  <p className="text-[8px] text-muted-foreground uppercase font-mono">AWAY</p>
                </div>
                <ChevronRight size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
