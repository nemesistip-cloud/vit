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
import { cn } from "@/lib/utils";

export default function AnalyticsPage() {
  const { data: leaderboard } = useQuery<any>({
    queryKey: ["/api/leaderboard"],
    queryFn: () => apiGet("/api/leaderboard"),
  });

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Network Intelligence</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Institutional Analytics & Alpha Metrics</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Network Reliability"
          value="99.98%"
          icon={<Globe size={14} />}
          className="border-primary/20"
        />
        <MetricCard
          label="Total Liquidity"
          value="4.2M"
          change="+12.4%"
          changePositive={true}
          icon={<TrendingUp size={14} />}
        />
        <MetricCard
          label="Ensemble Load"
          value="42%"
          subtitle="Processing 1.2k req/s"
          icon={<Cpu size={14} />}
        />
        <MetricCard
          label="Alpha Consensus"
          value="84.2%"
          change="+1.1%"
          changePositive={true}
          icon={<Brain size={14} />}
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
                  <CardContent className="space-y-5">
                     {[
                        { name: "Ensemble XGB-13", accuracy: 88.4, status: "Optimized" },
                        { name: "Neural LSTM-04", accuracy: 82.1, status: "Training" },
                        { name: "Alpha Bayesian-02", accuracy: 85.7, status: "Active" },
                     ].map((model, i) => (
                        <div key={i} className="space-y-2">
                           <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
                              <span className="text-muted-foreground">{model.name}</span>
                              <span className="text-primary font-bold">{model.accuracy}%</span>
                           </div>
                           <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                              <div className="h-full bg-primary" style={{ width: `${model.accuracy}%` }} />
                           </div>
                        </div>
                     ))}
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
                        <div className="p-4 rounded bg-white/[0.02] border border-white/5">
                           <p className="text-[9px] font-mono text-muted-foreground uppercase mb-1">Compute Hubs</p>
                           <p className="text-lg font-bold text-primary">14 <span className="text-[10px] font-normal text-muted-foreground">Active</span></p>
                        </div>
                        <div className="p-4 rounded bg-white/[0.02] border border-white/5">
                           <p className="text-[9px] font-mono text-muted-foreground uppercase mb-1">Storage Swarm</p>
                           <p className="text-lg font-bold text-primary">2.4 TB <span className="text-[10px] font-normal text-muted-foreground">Used</span></p>
                        </div>
                     </div>
                     <div className="pt-2">
                        <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Sync Progress</p>
                        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                           <div className="h-full bg-primary" style={{ width: '94%' }} />
                        </div>
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
                  <tbody className="divide-y divide-white/5">
                     {leaderboard?.leaderboard?.slice(0, 10).map((entry: any, i: number) => (
                        <tr key={i} className="hover:bg-white/[0.01]">
                           <td className="px-6 py-4 font-mono text-xs font-bold text-muted-foreground/60">#{i+1}</td>
                           <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                 <div className="w-7 h-7 rounded bg-primary/10 border border-primary/20 flex items-center justify-center text-[10px] font-bold text-primary">
                                    {entry.username?.[0] || 'U'}
                                 </div>
                                 <span className="text-sm font-bold">{entry.username || `User ${entry.user_id?.slice(0,6)}`}</span>
                              </div>
                           </td>
                           <td className="px-6 py-4 text-right font-mono text-sm font-bold text-vit-positive">
                              +{((entry.yield_pct || entry.roi || 0)).toFixed(1)}%
                           </td>
                        </tr>
                     ))}
                  </tbody>
               </table>
            </Card>
         </TabsContent>
      </Tabs>
    </div>
  );
}
