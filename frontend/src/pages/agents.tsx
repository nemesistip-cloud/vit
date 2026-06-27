import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  Cpu, Zap, Activity, Shield,
  ChevronRight, Search, Plus, Terminal,
  Brain, Radio, Settings, Power
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function SentinelHub() {
  const agents = [
    { id: "SNT-1", name: "Market Liquidity Sentinel", type: "Monitoring", status: "Active", throughput: "142 req/s" },
    { id: "SNT-2", name: "Neural Arbitrage Scout", type: "Execution", status: "Idle", throughput: "0 req/s" },
    { id: "SNT-3", name: "Sentiment Analysis Drone", type: "Data Hub", status: "Active", throughput: "840 req/s" },
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="flex items-end justify-between">
         <div className="space-y-1">
            <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Sentinel Hub</h1>
            <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Autonomous Neural Agent Management</p>
         </div>
         <Button size="sm" className="h-9 px-4 rounded shadow-lg shadow-primary/20 uppercase tracking-widest text-[10px] font-bold">
            <Plus size={14} className="mr-2" /> Deploy Agent
         </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Active Agents" value="3" icon={<Cpu size={14} />} />
        <MetricCard label="Total Compute" value="1.2 TFLOPS" icon={<Zap size={14} />} />
        <MetricCard label="System Uptime" value="100%" icon={<Activity size={14} />} />
        <MetricCard label="Network Security" value="Optimal" icon={<Shield size={14} />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           <div className="space-y-4">
              <h3 className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground pl-1">Provisioned Sentinels</h3>
              <div className="grid grid-cols-1 gap-3">
                 {agents.map((agent, i) => (
                    <Card key={i} className="border-white/5 bg-white/[0.01] hover:bg-white/[0.02] transition-all group overflow-hidden">
                       <div className="p-6 flex items-center justify-between">
                          <div className="flex items-center gap-6">
                             <div className="relative">
                                <div className="w-12 h-12 rounded border border-white/5 bg-white/5 flex items-center justify-center text-primary">
                                   <Terminal size={20} />
                                </div>
                                {agent.status === 'Active' && (
                                   <div className="absolute -top-1 -right-1 w-3 h-3 bg-vit-positive rounded-full border-2 border-background animate-pulse" />
                                )}
                             </div>
                             <div className="space-y-1">
                                <div className="flex items-center gap-3">
                                   <Badge variant="outline" className="text-[8px] border-white/10 uppercase tracking-tighter">{agent.type}</Badge>
                                   <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">ID: {agent.id}</span>
                                </div>
                                <h3 className="text-base font-bold text-foreground tracking-tight group-hover:text-primary transition-colors">{agent.name}</h3>
                             </div>
                          </div>
                          <div className="flex items-center gap-8">
                             <div className="text-right hidden sm:block">
                                <p className="font-mono text-xs font-bold text-foreground">{agent.throughput}</p>
                                <p className="font-mono text-[8px] text-muted-foreground uppercase mt-1">Throughput</p>
                             </div>
                             <Button variant="outline" size="icon" className="w-9 h-9 border-white/5 hover:border-primary transition-all">
                                <Settings size={14} className="text-muted-foreground" />
                             </Button>
                          </div>
                       </div>
                    </Card>
                 ))}
              </div>
           </div>
        </div>

        <div className="space-y-6">
           <Card className="bg-white/[0.02] border border-white/5">
              <CardHeader>
                 <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">Sentinel Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                 <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Neural Engine</span>
                    <Badge className="bg-vit-positive/10 text-vit-positive border-none font-bold uppercase text-[9px]">ONLINE</Badge>
                 </div>
                 <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Execution Hub</span>
                    <Badge className="bg-primary/10 text-primary border-none font-bold uppercase text-[9px]">STANDBY</Badge>
                 </div>
                 <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Telemetry Stream</span>
                    <Badge className="bg-vit-positive/10 text-vit-positive border-none font-bold uppercase text-[9px]">ACTIVE</Badge>
                 </div>
                 <Button variant="outline" className="w-full mt-4 h-10 border-white/10 uppercase tracking-widest text-[9px] font-bold">
                    <Power size={12} className="mr-2" /> Global Shutdown
                 </Button>
              </CardContent>
           </Card>
        </div>
      </div>
    </div>
  );
}
