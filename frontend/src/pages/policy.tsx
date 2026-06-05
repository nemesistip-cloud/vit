import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BookOpen, Scale, Zap, Globe, RefreshCw, Play, ShieldCheck, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

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
  const [impacts, setImpacts] = useState<PolicyImpact[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);

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
      // For now, simulate against a fixed scenario ID 1 if it exists or just trigger
      await fetch("/api/policy/simulate/1", { method: "POST" });
      await fetchImpacts();
    } catch (err) {
      console.error("Simulation failed", err);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-Intelligence Agenttom-4 duration-500">
      <header className="flex justify-between items-start">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground uppercase">Policy Intelligence</h1>
          <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Simulating the future of economic & digital policy</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchImpacts} disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-card/50 border-border/40 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2 uppercase">
              <Scale className="w-4 h-4 text-orange-400" />
              Verifiable Policy Simulator
            </CardTitle>
            <CardDescription className="text-xs font-mono tracking-tighter uppercase">
              Running native AI simulations on regulatory & macroeconomic shifts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="p-6 rounded-xl bg-background/40 border border-border/20">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-sm font-mono font-bold">Scenario: VIT Network Staking Incentives Expansion</h3>
                  <p className="text-[10px] font-mono text-muted-foreground mt-1 uppercase tracking-widest">
                    Adjusting reward parameters to optimize long-term network security
                  </p>
                </div>
                <Badge variant="secondary" className="font-mono text-[9px]">ACTIVE SCENARIO</Badge>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4">
                {[
                  { label: "Reward Cap", value: "15%" },
                  { label: "Slash Rate", value: "2.5%" },
                  { label: "Bond Period", value: "21d" },
                  { label: "Min Stake", value: "100 VIT" },
                ].map(param => (
                  <div key={param.label} className="bg-background/60 p-2 rounded border border-border/10 text-center">
                    <div className="text-[9px] font-mono text-muted-foreground uppercase">{param.label}</div>
                    <div className="text-xs font-mono font-bold text-primary">{param.value}</div>
                  </div>
                ))}
              </div>

              <div className="mt-4 h-32 flex flex-col items-center justify-center border-2 border-dashed border-border/20 rounded-lg group hover:border-primary/40 transition-colors">
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
                {impacts.map((impact) => (
                  <Card key={impact.id} className="bg-background/20 border-border/10">
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <h5 className="text-xs font-mono font-bold">{impact.title}</h5>
                        <Badge className="text-[8px] font-mono uppercase" variant={impact.severity === 'high' ? 'destructive' : 'outline'}>
                          {impact.severity} IMPACT
                        </Badge>
                      </div>
                      <p className="text-[10px] font-mono text-muted-foreground mb-3">{impact.description}</p>
                      <div className="p-3 bg-primary/5 rounded border border-primary/10">
                        <p className="text-[11px] font-mono leading-relaxed italic text-foreground">
                          "{impact.predicted_impact}"
                        </p>
                      </div>
                      <div className="mt-3 flex justify-between items-center text-[9px] font-mono text-muted-foreground uppercase">
                        <span>Category: {impact.category}</span>
                        <span>{new Date(impact.created_at).toLocaleString()}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {!loading && impacts.length === 0 && (
                  <p className="text-center py-10 text-xs font-mono text-muted-foreground">No simulation history found.</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="bg-card/50 border-border/40 backdrop-blur-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono flex items-center gap-2 uppercase tracking-wider">
                <Zap className="w-3 h-3 text-yellow-400" />
                Live Policy Alerts
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-3 rounded-lg bg-rose-500/5 border border-rose-500/20">
                <div className="flex items-center gap-2 mb-1">
                  <AlertCircle className="w-3 h-3 text-rose-400" />
                  <span className="text-[10px] font-mono font-bold text-rose-400 uppercase">High Priority</span>
                </div>
                <p className="text-[10px] font-mono text-rose-300/80 leading-snug">
                  New regional digital asset regulation proposed. Analyzing impact on VIT-Remittance corridors.
                </p>
              </div>
              <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                <div className="flex items-center gap-2 mb-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-400" />
                  <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase">Opportunity</span>
                </div>
                <p className="text-[10px] font-mono text-emerald-300/80 leading-snug">
                  Cross-border data sharing agreement finalized. Enhancing AI training accuracy across 4 new territories.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-background/20 border-border/40">
            <CardHeader>
              <CardTitle className="text-xs font-mono flex items-center gap-2 uppercase">
                <Globe className="w-4 h-4 text-primary" />
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
                    <div className="flex justify-between text-[10px] font-mono uppercase">
                      <span>{r.region}</span>
                      <span>{r.progress}%</span>
                    </div>
                    <Progress value={r.progress} className="h-1" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
