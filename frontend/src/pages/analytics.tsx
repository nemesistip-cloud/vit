import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  BarChart2, TrendingUp, ShieldCheck, Trophy,
  Target, Activity, Zap, Users, Brain, Globe
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import { Badge } from "@/components/ui/badge";

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
    <div className="space-y-6 pb-20">
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

      <Tabs value={activeTab} onValueChange={setActiveTab}>
         <TabsList className="bg-vit-surface-2 border border-vit-border p-1 h-10 w-full grid grid-cols-2">
            <TabsTrigger value="system" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">NETWORK HEALTH</TabsTrigger>
            <TabsTrigger value="leaderboard" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">ALPHA LEADERBOARD</TabsTrigger>
         </TabsList>

         <TabsContent value="system" className="mt-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
               <Card className="bg-vit-surface border-vit-border">
                  <CardHeader className="pb-3 border-b border-vit-border bg-vit-surface-2">
                     <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 flex items-center gap-2">
                        <Brain size={14} className="text-vit-green" /> Neural Consensus Engine
                     </CardTitle>
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

               <Card className="bg-vit-surface border-vit-border">
                  <CardHeader className="pb-3 border-b border-vit-border bg-vit-surface-2">
                     <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 flex items-center gap-2">
                        <ShieldCheck size={14} className="text-vit-green" /> Infrastructure Nodes
                     </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6">
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

         <TabsContent value="leaderboard" className="mt-6">
            <div className="bg-vit-surface border border-vit-border rounded-xl overflow-hidden">
               <table className="w-full text-left">
                  <thead className="bg-vit-surface-2 border-b border-vit-border">
                     <tr>
                        <th className="p-4 text-[10px] font-bold text-vit-text-3 uppercase">Rank</th>
                        <th className="p-4 text-[10px] font-bold text-vit-text-3 uppercase">Contributor</th>
                        <th className="p-4 text-[10px] font-bold text-vit-text-3 uppercase text-center">Accuracy</th>
                        <th className="p-4 text-[10px] font-bold text-vit-text-3 uppercase text-right">Yield</th>
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
            </div>
         </TabsContent>
      </Tabs>
    </div>
  );
}
