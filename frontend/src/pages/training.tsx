import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import {
  Brain, Cpu, Database, Activity, RefreshCw, Play,
  CheckCircle2, AlertCircle, Clock, ChevronRight, BarChart3,
  Layers, Zap, Shield
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import MetricCard from "@/components/cards/MetricCard";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export default function TrainingPage() {
  const queryClient = useQueryClient();

  const { data: jobs, isLoading: jobsLoading } = useQuery<any[]>({
    queryKey: ["/api/training/jobs"],
    queryFn: () => apiGet("/api/training/jobs"),
  });

  const trigger = useMutation({
    mutationFn: (type: string) => apiPost("/api/training/trigger", { type }),
    onSuccess: () => {
      toast.success("Neural training cycle initialized.");
      queryClient.invalidateQueries({ queryKey: ["/api/training/jobs"] });
    },
  });

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Neural Center</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Ensemble Model Training & Calibration</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Model Drift" value="0.04%" icon={<Activity size={14} />} />
        <MetricCard label="Calibration" value="94.2%" icon={<Zap size={14} />} />
        <MetricCard label="Data Shards" value="1.2k" icon={<Database size={14} />} />
        <MetricCard label="Uptime" value="100%" icon={<Shield size={14} />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           <Card className="border-primary/20 bg-primary/[0.02]">
              <CardHeader className="flex flex-row items-center justify-between">
                 <CardTitle className="text-sm uppercase tracking-widest font-display">Provision Training</CardTitle>
                 <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">READY</Badge>
              </CardHeader>
              <CardContent className="space-y-6">
                 <p className="text-xs text-muted-foreground leading-relaxed">
                    Initialize a new neural calibration cycle using the latest market telemetry.
                    Ensemble weights will be re-balanced across 13 active model shards.
                 </p>
                 <div className="flex flex-col sm:flex-row gap-3">
                    <Button
                       className="flex-1 h-12 uppercase tracking-widest text-[10px] font-bold"
                       onClick={() => trigger.mutate("ensemble")}
                       disabled={trigger.isPending}
                    >
                       <Play size={14} className="mr-2" /> Start Ensemble Cycle
                    </Button>
                    <Button
                       variant="outline"
                       className="flex-1 h-12 uppercase tracking-widest text-[10px] border-white/10"
                       onClick={() => trigger.mutate("bootstrap")}
                       disabled={trigger.isPending}
                    >
                       <RefreshCw size={14} className={cn("mr-2", trigger.isPending && "animate-spin")} /> Re-Bootstrap Shards
                    </Button>
                 </div>
              </CardContent>
           </Card>

           <Card className="border-white/5 bg-white/[0.01] overflow-hidden">
              <CardHeader className="bg-white/[0.01] border-b border-white/5">
                 <CardTitle className="text-[10px] uppercase tracking-widest">Active Job Pipeline</CardTitle>
              </CardHeader>
              <div className="divide-y divide-white/5">
                 {jobsLoading ? (
                    <div className="p-12 text-center text-muted-foreground/30 font-mono text-[10px] uppercase">Scanning Pipeline...</div>
                 ) : !jobs?.length ? (
                    <div className="p-12 text-center text-muted-foreground/30 font-mono text-[10px] uppercase">No active training jobs</div>
                 ) : (
                    jobs.map((job: any) => (
                       <div key={job.id} className="p-6 space-y-4">
                          <div className="flex justify-between items-start">
                             <div className="space-y-1">
                                <h4 className="text-sm font-bold uppercase tracking-tight">{job.type} CALIBRATION</h4>
                                <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-widest">ID: {job.id.slice(0,8)}</p>
                             </div>
                             <Badge className={cn(
                                "text-[9px] font-bold uppercase",
                                job.status === 'completed' ? "bg-vit-positive/10 text-vit-positive" :
                                job.status === 'failed' ? "bg-vit-negative/10 text-vit-negative" : "bg-primary/10 text-primary animate-pulse"
                             )}>
                                {job.status}
                             </Badge>
                          </div>
                          <div className="space-y-2">
                             <div className="flex justify-between text-[9px] font-mono uppercase text-muted-foreground">
                                <span>Progress</span>
                                <span>{job.progress}%</span>
                             </div>
                             <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                                <div className="h-full bg-primary" style={{ width: `${job.progress}%` }} />
                             </div>
                          </div>
                       </div>
                    ))
                 )}
              </div>
           </Card>
        </div>

        <div className="space-y-6">
           <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4 text-primary">
                 <Layers size={16} />
                 <h4 className="font-display text-[10px] font-bold uppercase tracking-[0.2em]">Cluster Metrics</h4>
              </div>
              <ul className="space-y-5">
                 {[
                    { label: "Neural Entropy", value: "0.12", trend: "Stable" },
                    { label: "Gradient Norm", value: "1.45", trend: "Optimal" },
                    { label: "Shard Sync", value: "99.9%", trend: "Active" },
                 ].map((item, i) => (
                    <li key={i} className="flex justify-between items-end border-b border-white/5 pb-2 last:border-0">
                       <div className="space-y-1">
                          <p className="text-[9px] text-muted-foreground uppercase font-mono">{item.label}</p>
                          <p className="font-mono text-sm font-bold">{item.value}</p>
                       </div>
                       <p className="text-[8px] font-bold text-primary uppercase">{item.trend}</p>
                    </li>
                 ))}
              </ul>
           </div>
        </div>
      </div>
    </div>
  );
}
