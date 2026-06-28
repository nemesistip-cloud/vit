import React from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity } from 'lucide-react';

interface TacticalRadarProps {
  homeTeam: string;
  awayTeam: string;
  data: any[];
}

export const TacticalRadar: React.FC<TacticalRadarProps> = ({ homeTeam, awayTeam, data }) => {
  if (!data || data.length === 0) return null;

  return (
    <Card className="border-white/5 bg-white/[0.01]">
      <CardHeader>
        <CardTitle className="text-[10px] font-mono uppercase tracking-[0.2em] flex items-center gap-2">
          <Activity size={14} className="text-primary" />
          Tactical Matrix Comparison
        </CardTitle>
      </CardHeader>
      <CardContent className="flex justify-center h-[250px] pt-0">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
            <PolarGrid stroke="#333" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: '#666', fontSize: 10 }} />
            <Radar
              name={homeTeam}
              dataKey="A"
              stroke="#00F5FF"
              fill="#00F5FF"
              fillOpacity={0.3}
            />
            <Radar
              name={awayTeam}
              dataKey="B"
              stroke="#F59E0B"
              fill="#F59E0B"
              fillOpacity={0.3}
            />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
      <div className="p-4 border-t border-white/5 flex justify-center gap-6">
         <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary" />
            <span className="text-[9px] font-mono text-muted-foreground uppercase">{homeTeam}</span>
         </div>
         <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-secondary" />
            <span className="text-[9px] font-mono text-muted-foreground uppercase">{awayTeam}</span>
         </div>
      </div>
    </Card>
  );
};
