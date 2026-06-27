import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import {
  ShieldCheck, Cpu, Database, Activity, Trophy, Coins,
  Plus, ChevronRight, Info, CheckCircle2, XCircle, AlertTriangle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import MetricCard from "@/components/cards/MetricCard";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

export default function ValidatorsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [stakeInput, setStakeInput] = useState("100");

  const { data: status } = useQuery<any>({
    queryKey: ["/api/validators/me"],
    queryFn: () => apiGet("/api/validators/me"),
  });

  const { data: list } = useQuery<any>({
    queryKey: ["/api/validators/active"],
    queryFn: () => apiGet("/api/validators/active"),
  });

  const apply = useMutation({
    mutationFn: (vars: any) => apiPost("/api/validators/apply", vars),
    onSuccess: () => {
      toast.success("Application registered in the ledger.");
      queryClient.invalidateQueries({ queryKey: ["/api/validators/me"] });
    },
  });

  const isValidator = status?.is_validator;
  const validatorList = list?.validators || [];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Validator Network</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Distributed Infrastructure Ledger</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Active Nodes" value="124" icon={<Cpu size={14} />} />
        <MetricCard label="Network Stake" value="840k" icon={<Coins size={14} />} />
        <MetricCard label="Avg Uptime" value="99.9%" icon={<Activity size={14} />} />
        <MetricCard label="Slashing" value="0.02%" icon={<ShieldCheck size={14} />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           <Card className="border-primary/20 bg-primary/[0.02]">
              <CardHeader className="flex flex-row items-center justify-between">
                 <CardTitle className="text-sm uppercase tracking-widest font-display">Node Status</CardTitle>
                 <Badge variant="outline" className={cn(isValidator ? "text-primary border-primary/20" : "text-muted-foreground border-white/5")}>
                    {isValidator ? "ACTIVE" : "INACTIVE"}
                 </Badge>
              </CardHeader>
              <CardContent className="space-y-6">
                 {isValidator ? (
                    <div className="grid grid-cols-2 gap-4">
                       <div className="space-y-1">
                          <p className="font-mono text-[9px] text-muted-foreground uppercase">Influence</p>
                          <p className="font-mono text-xl font-bold text-primary">{status.influence_score?.toFixed(2)}</p>
                       </div>
                       <div className="space-y-1">
                          <p className="font-mono text-[9px] text-muted-foreground uppercase">Commission</p>
                          <p className="font-mono text-xl font-bold text-foreground">5.0%</p>
                       </div>
                    </div>
                 ) : (
                    <div className="space-y-4">
                       <p className="text-xs text-muted-foreground leading-relaxed">
                          Infrastructure nodes process neural consensus and secure the network ledger.
                          Requires a minimum stake of <span className="text-foreground">100 VIT</span> and Oracle reputation.
                       </p>
                       <Dialog>
                          <DialogTrigger asChild>
                             <Button className="w-full h-10 shadow-lg shadow-primary/20 uppercase tracking-widest text-[10px]">
                                Initialize Node Application
                             </Button>
                          </DialogTrigger>
                          <DialogContent className="bg-card border-white/10">
                             <DialogHeader>
                                <DialogTitle className="font-display uppercase tracking-widest">Node Provisioning</DialogTitle>
                             </DialogHeader>
                             <div className="space-y-4 pt-4">
                                <div className="space-y-2">
                                   <label className="text-[10px] font-mono text-muted-foreground uppercase">Collateral Stake (VIT)</label>
                                   <Input
                                      type="number"
                                      value={stakeInput}
                                      onChange={(e) => setStakeInput(e.target.value)}
                                      className="bg-white/5 border-white/5 font-mono"
                                   />
                                </div>
                                <Button className="w-full h-10" onClick={() => apply.mutate({ stake_amount: stakeInput })}>
                                   Confirm Stake & Deploy
                                </Button>
                             </div>
                          </DialogContent>
                       </Dialog>
                    </div>
                 )}
              </CardContent>
           </Card>

           <Card className="border-white/5 bg-white/[0.01] overflow-hidden">
              <CardHeader>
                 <CardTitle className="text-xs uppercase tracking-widest font-display">Global Registry</CardTitle>
              </CardHeader>
              <div className="divide-y divide-white/5">
                 {validatorList.slice(0, 6).map((v: any, i: number) => (
                    <div key={i} className="p-4 flex items-center justify-between hover:bg-white/[0.01]">
                       <div className="flex items-center gap-4">
                          <div className="w-8 h-8 rounded border border-white/5 bg-white/5 flex items-center justify-center font-mono text-[10px] font-bold text-muted-foreground">
                             {i + 1}
                          </div>
                          <div>
                             <p className="text-sm font-bold tracking-tight">{v.username}</p>
                             <p className="font-mono text-[8px] text-muted-foreground uppercase tracking-widest">Uptime: 99.9%</p>
                          </div>
                       </div>
                       <div className="text-right">
                          <p className="font-mono text-xs font-bold text-primary">{v.influence_score?.toFixed(2)}</p>
                          <p className="font-mono text-[8px] text-muted-foreground uppercase tracking-widest">Power</p>
                       </div>
                    </div>
                 ))}
              </div>
           </Card>
        </div>

        <div className="space-y-6">
           <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                 <ShieldCheck size={16} className="text-primary" />
                 <h4 className="font-display text-[10px] font-bold uppercase tracking-[0.2em]">Compliance Protocol</h4>
              </div>
              <ul className="space-y-4">
                 {[
                    { label: "Hardware SLA", status: "Required" },
                    { label: "Slashing Risk", status: "Active" },
                    { label: "Stake Lock", status: "21 Days" },
                 ].map((item, i) => (
                    <li key={i} className="flex justify-between items-center">
                       <span className="text-[11px] text-muted-foreground">{item.label}</span>
                       <span className="font-mono text-[10px] font-bold text-primary uppercase">{item.status}</span>
                    </li>
                 ))}
              </ul>
           </div>
        </div>
      </div>
    </div>
  );
}
