import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar, Cell
} from "recharts";
import {
  TrendingUp, Activity, BarChart2, Zap, Globe, Brain,
  ShieldCheck, Cpu, Database, Target, Award, ArrowUpRight
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/cards/MetricCard";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import { cn } from "@/lib/utils";

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState("system");

  const { data: system, isLoading: loadingSystem } = useQuery<any>({
    queryKey: ["/api/admin/system/health"],
    queryFn: () => apiGet("/api/admin/system/health"),
  });

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const { data: leaderboard, isLoading: loadingLb } = useQuery<any>({
    queryKey: ["/api/leaderboard"],
    queryFn: () => apiGet("/api/leaderboard"),
  });

  const forecasts = summary?.total_predictions
    ? (summary.total_predictions >= 1000 ? (summary.total_predictions / 1000).toFixed(1) + "K" : summary.total_predictions)
    : "—";

  const networkRoi = summary?.avg_clv != null ? "+" + (summary.avg_clv * 100).toFixed(1) + "%" : "—";
  const communityXp = summary?.total_xp
    ? (summary.total_xp >= 1000000 ? (summary.total_xp / 1000000).toFixed(1) + "M" : (summary.total_xp / 1000).toFixed(1) + "K")
    : "—";

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Network Intelligence</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Institutional Analytics & Alpha Metrics</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            label="Nodes Online"
            value={system?.models_loaded ?? "—"}
            icon={<Globe size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Total Forecasts"
            value={forecasts}
            icon={<Activity size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Network ROI"
            value={networkRoi}
            changePositive={true}
            icon={<TrendingUp size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Community XP"
            value={communityXp}
            icon={<Zap size={16} className="text-vit-purple" />}
         />
      </div>

      <Tabs defaultValue="system" className="w-full">
         <TabsList className="w-full h-10 p-1 bg-white/[0.03]">
            <TabsTrigger value="system" className="flex-1 text-[10px]">NETWORK HEALTH</TabsTrigger>
            <TabsTrigger value="alpha" className="flex-1 text-[10px]">ALPHA LEADERBOARD</TabsTrigger>
         </TabsList>

         <TabsContent value="system" className="mt-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
               <Card className="border-white/5 bg-white/[0.01]">
                  <CardHeader className="flex flex-row items-center justify-between">
                     <CardTitle className="text-xs flex items-center gap-2">
                        <Brain size={14} className="text-primary" /> Neural Consensus Hub
                     </CardTitle>
                     <Badge variant="outline" className="text-[8px]">PROD-V5</Badge>
                  </CardHeader>
                  <CardContent className="p-0">
                     <div className="divide-y divide-vit-border">
                        {system?.ai_models && system.ai_models.length > 0 ? (
                          system.ai_models.slice(0, 6).map((model: any, i: number) => (
                             <div key={i} className="p-4 flex items-center justify-between">
                                <span className="text-xs font-medium">{model.name}</span>
                                <div className="flex items-center gap-3">
                                   <div className="w-24 h-1.5 bg-vit-surface-3 rounded-full overflow-hidden">
                                      <div className="h-full bg-vit-green" style={{ width: `${model.accuracy || 0}%` }} />
                                   </div>
                                   <span className="text-xs font-mono font-bold text-vit-green">{model.accuracy || 0}%</span>
                                </div>
                             </div>
                          ))
                        ) : (
                          <div className="p-10 text-center text-xs text-vit-text-3 italic font-mono">
                            Awaiting ensemble consensus...
                          </div>
                        )}
                     </div>
                  </CardContent>
               </Card>

               <Card className="border-white/5 bg-white/[0.01]">
                  <CardHeader>
                     <CardTitle className="text-xs flex items-center gap-2">
                        <ShieldCheck size={14} className="text-primary" /> Infrastructure Nodes
                     </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                     <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 rounded-xl bg-vit-surface-2 border border-vit-border">
                           <p className="text-[10px] font-bold text-vit-text-3 uppercase mb-1">Database</p>
                           <p className={`text-sm font-bold ${system?.database ? 'text-vit-green' : 'text-rose-400'}`}>
                             {system?.database ? 'SYNCHRONIZED' : 'OFFLINE'}
                           </p>
                        </div>
                        <div className="p-4 rounded-xl bg-vit-surface-2 border border-vit-border">
                           <p className="text-[10px] font-bold text-vit-text-3 uppercase mb-1">Cache Layer</p>
                           <p className={`text-sm font-bold ${system?.redis ? 'text-vit-green' : 'text-amber-400'}`}>
                             {system?.redis ? 'OPTIMIZED' : 'DEGRADED'}
                           </p>
                        </div>
                     </div>
                     <div className="space-y-2">
                        <p className="text-[10px] font-bold text-vit-text-3 uppercase">Memory Utilization</p>
                        <div className="h-2 bg-vit-surface-3 rounded-full overflow-hidden">
                           <div className="h-full bg-vit-green" style={{ width: `${system?.mem_pct || 0}%` }} />
                        </div>
                        <p className="text-[10px] text-right text-vit-text-3">
                          {system?.mem_pct ? (system.mem_pct * 0.1).toFixed(1) + "GB / 10GB" : "— / 10GB"}
                        </p>
                     </div>
                  </CardContent>
               </Card>
            </div>
         </TabsContent>

         <TabsContent value="alpha" className="mt-6">
            <Card className="border-white/5 bg-transparent overflow-hidden">
               <table className="w-full text-left">
                  <thead className="bg-white/[0.02] border-b border-white/5">
                     <tr>
                        <th className="px-6 py-4 font-display text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Rank</th>
                        <th className="px-6 py-4 font-display text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Analyst</th>
                        <th className="px-6 py-4 font-display text-[10px] font-bold text-muted-foreground uppercase tracking-widest text-right">Yield</th>
                     </tr>
                  </thead>
                  <tbody className="divide-y divide-vit-border">
                     {loadingLb ? (
                       Array.from({length: 5}).map((_, i) => <RowSkeleton key={i} />)
                     ) : leaderboard?.leaderboard?.length > 0 ? (
                       leaderboard.leaderboard.map((entry: any, i: number) => (
                          <tr key={i} className="hover:bg-vit-surface-2 transition-colors">
                             <td className="p-4 font-mono text-sm font-bold">#{i + 1}</td>
                             <td className="p-4">
                                <div className="flex items-center gap-2">
                                   <div className="w-6 h-6 rounded bg-vit-surface-3 flex items-center justify-center text-[10px] font-bold">U</div>
                                   <span className="text-sm font-medium">{entry?.username || `User ${entry?.user_id || (1000 + i)}`}</span>
                                </div>
                             </td>
                             <td className="p-4 text-center">
                                <Badge className="bg-vit-green-glow text-vit-green border-vit-green/20 text-[10px] font-bold">
                                  {entry?.win_rate != null ? (entry.win_rate * 100).toFixed(1) + "%" : entry?.accuracy_rate != null ? (entry.accuracy_rate * 100).toFixed(1) + "%" : "—"}
                                </Badge>
                             </td>
                             <td className="p-4 text-right font-mono text-sm font-bold text-vit-green">
                               {entry?.roi != null ? `+${(entry.roi * 100).toFixed(1)}%` : entry?.yield_pct != null ? `+${entry.yield_pct.toFixed(1)}%` : '--'}
                             </td>
                          </tr>
                       ))
                     ) : (
                       <tr>
                         <td colSpan={4} className="p-10 text-center text-xs text-vit-text-3 font-mono italic">
                           Calculating leaderboard rankings...
                         </td>
                       </tr>
                     )}
                  </tbody>
               </table>
            </Card>
         </TabsContent>
      </Tabs>
    </div>
  );
}
