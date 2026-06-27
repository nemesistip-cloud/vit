import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  Trophy, Medal, Target, Zap, ChevronRight,
  TrendingUp, Activity, Award, Star, Search
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function LeaderboardPage() {
  const { data: leaderboard, isLoading } = useQuery<any>({
    queryKey: ["/api/leaderboard"],
    queryFn: () => apiGet("/api/leaderboard"),
  });

  const lb = leaderboard?.leaderboard || [];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Alpha Ranking</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Global Performance Index</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Global Rank" value="#42" icon={<Trophy size={14} />} />
        <MetricCard label="Avg Yield" value="18.4%" icon={<TrendingUp size={14} />} />
        <MetricCard label="Percentile" value="TOP 5%" icon={<Target size={14} />} />
        <MetricCard label="Network Power" value="1.2k" icon={<Zap size={14} />} />
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
        <Input
          placeholder="Filter analysts by UID or alias..."
          className="pl-9 bg-white/[0.02] border-white/5 h-10 text-xs font-mono"
        />
      </div>

      <Card className="border-white/5 bg-transparent overflow-hidden">
         <table className="w-full text-left">
            <thead className="bg-white/[0.02] border-b border-white/5">
               <tr>
                  <th className="px-6 py-4 font-display text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Rank</th>
                  <th className="px-6 py-4 font-display text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Analyst</th>
                  <th className="px-6 py-4 font-display text-[10px] font-bold text-muted-foreground uppercase tracking-widest text-right">Yield</th>
               </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
               {lb.slice(0, 10).map((entry: any, i: number) => (
                  <tr key={i} className="hover:bg-white/[0.01] group cursor-pointer transition-colors">
                     <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                           <span className="font-mono text-xs font-bold text-muted-foreground/60 w-4">#{i+1}</span>
                           {i < 3 && <Medal size={12} className={cn(i === 0 ? "text-primary" : i === 1 ? "text-secondary" : "text-orange-400")} />}
                        </div>
                     </td>
                     <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                           <div className="w-7 h-7 rounded bg-primary/10 border border-primary/20 flex items-center justify-center text-[10px] font-bold text-primary">
                              {entry.username?.[0]?.toUpperCase() || 'U'}
                           </div>
                           <div>
                              <span className="text-sm font-bold group-hover:text-primary transition-colors">{entry.username || `Node ${entry.user_id?.slice(0,6)}`}</span>
                              <p className="font-mono text-[8px] text-muted-foreground uppercase tracking-widest">{entry.tier || 'PRO'}</p>
                           </div>
                        </div>
                     </td>
                     <td className="px-6 py-4 text-right">
                        <span className="font-mono text-xs font-bold text-vit-positive">+{((entry.yield_pct || entry.roi || 0)).toFixed(1)}%</span>
                     </td>
                  </tr>
               ))}
            </tbody>
         </table>
      </Card>
    </div>
  );
}
