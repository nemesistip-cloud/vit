import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  Database, Cloud, HardDrive, RefreshCw,
  ShieldCheck, Globe, Cpu, ChevronRight, Activity,
  Lock, Share2, Info, ArrowUpRight
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";
import type { StorageStats } from "@/api-client/schemas";

export default function StoragePage() {
  const { data: stats, isLoading } = useQuery<StorageStats>({
    queryKey: ["/api/storage/stats"],
    queryFn: () => apiGet("/api/storage/stats"),
  });

  const usedGb = stats?.total_stored_gb || 0;
  const totalGb = stats?.total_capacity_gb || 0;
  const util = stats?.utilization_pct || 0;

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Tachyon VESS</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Distributed Content Storage Swarm</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Swarm Capacity" value={`${totalGb.toFixed(1)} GB`} icon={<Database size={14} />} />
        <MetricCard label="Data Utilized" value={`${usedGb.toFixed(1)} GB`} icon={<Cloud size={14} />} />
        <MetricCard label="Active Nodes" value="14" icon={<Globe size={14} />} />
        <MetricCard label="Integrity" value="100%" icon={<ShieldCheck size={14} />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           <Card className="border-primary/20 bg-primary/[0.02]">
              <CardHeader className="flex flex-row items-center justify-between">
                 <CardTitle className="text-sm uppercase tracking-widest font-display text-primary">Network Load</CardTitle>
                 <Badge className="bg-primary/10 text-primary border-primary/20">{util.toFixed(1)}%</Badge>
              </CardHeader>
              <CardContent className="space-y-6">
                 <div className="space-y-2">
                    <div className="flex justify-between text-[10px] font-mono uppercase text-muted-foreground">
                       <span>Swarm Saturation</span>
                       <span>{usedGb.toFixed(1)} / {totalGb.toFixed(1)} GB</span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                       <div
                         className={cn(
                           "h-full transition-all duration-1000 shadow-[0_0_12px]",
                           util > 85 ? "bg-vit-negative shadow-vit-negative/40" :
                           util > 60 ? "bg-vit-warning shadow-vit-warning/40" : "bg-primary shadow-primary/40"
                         )}
                         style={{ width: `${util}%` }}
                       />
                    </div>
                 </div>
                 <div className="grid grid-cols-3 gap-4 pt-2">
                    <div className="text-center p-3 rounded bg-white/[0.02] border border-white/5">
                       <p className="text-[8px] font-mono text-muted-foreground uppercase">Data Shards</p>
                       <p className="font-mono text-sm font-bold">4</p>
                    </div>
                    <div className="text-center p-3 rounded bg-white/[0.02] border border-white/5">
                       <p className="text-[8px] font-mono text-muted-foreground uppercase">Parity</p>
                       <p className="font-mono text-sm font-bold">2</p>
                    </div>
                    <div className="text-center p-3 rounded bg-white/[0.02] border border-white/5">
                       <p className="text-[8px] font-mono text-muted-foreground uppercase">Redundancy</p>
                       <p className="font-mono text-sm font-bold text-primary">1.5x</p>
                    </div>
                 </div>
              </CardContent>
           </Card>

           <Card className="border-white/5 bg-white/[0.01] overflow-hidden">
              <CardHeader className="bg-white/[0.01] border-b border-white/5">
                 <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">Provider Clusters</CardTitle>
              </CardHeader>
              <div className="divide-y divide-white/5">
                 {[
                    { name: "Google Drive Cluster", nodes: 4, health: "Optimal" },
                    { name: "Dropbox Swarm", nodes: 6, health: "Stable" },
                    { name: "OneDrive Cluster", nodes: 4, health: "Optimal" },
                 ].map((cluster, i) => (
                    <div key={i} className="p-5 flex items-center justify-between hover:bg-white/[0.01]">
                       <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded border border-white/5 bg-white/5 flex items-center justify-center text-muted-foreground/40">
                             <HardDrive size={18} />
                          </div>
                          <div>
                             <p className="text-sm font-bold tracking-tight">{cluster.name}</p>
                             <p className="font-mono text-[8px] text-muted-foreground uppercase tracking-widest">{cluster.nodes} Active Nodes</p>
                          </div>
                       </div>
                       <Badge variant="outline" className="text-[8px] font-bold text-primary border-primary/20 uppercase">{cluster.health}</Badge>
                    </div>
                 ))}
              </div>
           </Card>
        </div>

        <div className="space-y-6">
           <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4 text-primary">
                 <Lock size={16} />
                 <h4 className="font-display text-[10px] font-bold uppercase tracking-[0.2em]">Encryption Layer</h4>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                 All swarm data is fragmented using <span className="text-foreground">Reed-Solomon</span> erasure coding and encrypted via AES-256 before distribution.
              </p>
              <Button variant="outline" className="w-full mt-4 h-9 text-[9px] uppercase tracking-widest border-white/10">
                 Rotate Keys
              </Button>
           </div>
        </div>
      </div>
    </div>
  );
}
