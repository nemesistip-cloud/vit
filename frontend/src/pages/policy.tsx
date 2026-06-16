import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BookOpen, Scale, Zap, Globe, RefreshCw, Play, ShieldCheck, AlertCircle, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

interface PolicyImpact {
  id: number;
  title: string;
  description: string;
  category: string;
  severity: string;
  predicted_impact: string;
  created_at: string;
}

export default function PolicyPage() {
  const { data: config } = usePublicConfig();
  const [impacts, setImpacts] = useState<PolicyImpact[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);

  const { data: systemStats } = useQuery<any>({
    queryKey: ["system-analytics"],
    queryFn: () => apiGet("/api/analytics/system"),
  });

  const fetchImpacts = async () => {
    try {
      const resp = await fetch("/api/policy/impacts");
      const data = await resp.json();
      setImpacts(data);
    } catch (err) {
      console.error("Failed to fetch policy impacts", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchImpacts();
  }, []);

  const runSimulation = async () => {
    setSimulating(true);
    try {
      await fetch("/api/policy/simulate/1", { method: "POST" });
      await fetchImpacts();
    } catch (err) {
      console.error("Simulation failed", err);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="flex justify-between items-start">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground uppercase">Policy Intelligence</h1>
          <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Simulating the future of economic & digital policy</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchImpacts} disabled={loading} className="font-mono text-xs uppercase tracking-wider">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-card/50 border-border/40 ">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2 uppercase tracking-wider">
              <Scale className="w-4 h-4 text-orange-400" />
              Verifiable Policy Simulator
            </CardTitle>
            <CardDescription className="text-xs font-mono tracking-tighter uppercase opacity-70">
              Running native AI simulations on regulatory & macroeconomic shifts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="p-6 rounded-xl bg-background/40 border border-border/20">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-sm font-mono font-bold uppercase tracking-tight">Scenario: VIT Network Staking Incentives Expansion</h3>
                  <p className="text-[10px] font-mono text-muted-foreground mt-1 uppercase tracking-widest">
                    Adjusting reward parameters to optimize long-term network security
                  </p>
                </div>
                <Badge variant="secondary" className="font-mono text-[9px] tracking-widest bg-emerald-500/10 text-emerald-400 border-emerald-500/20">ACTIVE SCENARIO</Badge>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4">
                {[
                  { label: "Reward Cap", value: "15%" },
                  { label: "Slash Rate", value: "2.5%" },
                  { label: "Bond Period", value: "21d" },
                  { label: "Min Stake", value: "100 VIT" },
                ].map(param => (
                  <div key={param.label} className="bg-background/60 p-2 rounded border border-border/10 text-center">
                    <div className="text-[9px] font-mono text-muted-foreground uppercase tracking-wider">{param.label}</div>
                    <div className="text-xs font-mono font-bold text-primary">{param.value}</div>
                  </div>
                ))}
              </div>

              <div className="mt-4 h-32 flex flex-col items-center justify-center border-2 border-dashed border-border/20 rounded-lg group hover:border-primary/40 transition-colors bg-muted/5">
                <Button
                  size="sm"
                  className="font-mono text-xs uppercase tracking-widest"
                  onClick={runSimulation}
                  disabled={simulating}
                >
                  {simulating ? <RefreshCw className="w-3 h-3 mr-2 animate-spin" /> : <Play className="w-3 h-3 mr-2" />}
                  {simulating ? "Simulating..." : "Execute Impact Simulation"}
                </Button>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="text-xs font-mono font-bold uppercase tracking-widest flex items-center gap-2">
                <ShieldCheck className="w-3 h-3 text-emerald-400" /> Recent Simulation Results
              </h4>
              <div className="space-y-3">
                {loading ? (
                  <Skeleton className="h-32 w-full rounded-xl" />
                ) : impacts.map((impact) => (
                  <Card key={impact.id} className="bg-background/20 border-border/10 hover:border-primary/20 transition-all">
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <h5 className="text-xs font-mono font-bold uppercase tracking-tight">{impact.title}</h5>
                        <Badge className="text-[8px] font-mono uppercase tracking-widest" variant={impact.severity === 'high' ? 'destructive' : 'outline'}>
                          {impact.severity} IMPACT
                        </Badge>
                      </div>
                      <p className="text-[10px] font-mono text-muted-foreground mb-3 uppercase tracking-tight">{impact.description}</p>
                      <div className="p-3 bg-primary/5 rounded border border-primary/10">
                        <p className="text-[11px] font-mono leading-relaxed italic text-foreground opacity-90">
                          "{impact.predicted_impact}"
                        </p>
                      </div>
                      <div className="mt-3 flex justify-between items-center text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
                        <span>Category: {impact.category}</span>
                        <span>{new Date(impact.created_at).toLocaleString()}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {!loading && impacts.length === 0 && (
                  <p className="text-center py-12 text-xs font-mono text-muted-foreground uppercase tracking-widest">No simulation history found.</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="bg-card/50 border-border/40 ">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono flex items-center gap-2 uppercase tracking-[0.2em]">
                <Zap className="w-3 h-3 text-yellow-400" />
                Live Policy Alerts
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-3 rounded-lg bg-rose-500/5 border border-rose-500/20">
                <div className="flex items-center gap-2 mb-1">
                  <AlertCircle className="w-3 h-3 text-rose-400" />
                  <span className="text-[10px] font-mono font-bold text-rose-400 uppercase tracking-widest">High Priority</span>
                </div>
                <p className="text-[10px] font-mono text-rose-300/80 leading-snug uppercase tracking-tight">
                  New regional digital asset regulation proposed. Analyzing impact on VIT-Remittance corridors.
                </p>
              </div>
              <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                <div className="flex items-center gap-2 mb-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-400" />
                  <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-widest">Opportunity</span>
                </div>
                <p className="text-[10px] font-mono text-emerald-300/80 leading-snug uppercase tracking-tight">
                  Cross-border data sharing agreement finalized. Enhancing AI training accuracy across {config?.platform?.model_count || systemStats?.models?.active_count || 22} network nodes.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-background/20 border-border/40">
            <CardHeader>
              <CardTitle className="text-xs font-mono flex items-center gap-2 uppercase tracking-widest text-primary">
                <Globe className="w-4 h-4" />
                Network Coverage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { region: "Western Africa", progress: 85 },
                  { region: "Eastern Africa", progress: 62 },
                  { region: "Southern Africa", progress: 44 },
                  { region: "Northern Africa", progress: 31 },
                ].map(r => (
                  <div key={r.region} className="space-y-1">
                    <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
                      <span>{r.region}</span>
                      <span className="text-primary font-bold">{r.progress}%</span>
                    </div>
                    <Progress value={r.progress} className="h-1" />
                  </div>
                ))}
              </div>
              <div className="mt-6 pt-4 border-t border-border/10">
                <div className="flex justify-between items-center text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                  <span>Global Nodes Active</span>
                  <span className="text-foreground font-bold">{systemStats?.models?.active_count || 22}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
