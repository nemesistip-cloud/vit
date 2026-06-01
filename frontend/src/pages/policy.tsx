import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, Scale, Zap, Globe } from "lucide-react";

export default function PolicyPage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">Policy Analytics</h1>
        <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Simulating the future of African policy</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-card/50 border-border/40">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Scale className="w-4 h-4 text-orange-400" />
              Policy Simulator v1.0
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="p-4 rounded-xl bg-background/50 border border-border/40">
              <h3 className="text-xs font-mono font-bold mb-2">Scenario: Central Bank Digital Currency (eNaira) Revamp</h3>
              <p className="text-[10px] font-mono text-muted-foreground leading-relaxed">
                Adjust variables like transaction limits, interest incentives, and offline capabilities to see predicted impact on inflation and adoption.
              </p>
              <div className="mt-4 h-32 flex items-center justify-center border-2 border-dashed border-border/20 rounded-lg">
                <span className="text-[10px] font-mono text-muted-foreground/40">Simulation Workspace</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="bg-card/50 border-border/40">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono flex items-center gap-2 uppercase tracking-wider">
                <Zap className="w-3 h-3 text-yellow-400" />
                Impact Alerts
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-2 rounded bg-rose-500/5 border border-rose-500/20 text-[10px] font-mono text-rose-400">
                New Finance Bill may impact startup tax exemptions.
              </div>
              <div className="p-2 rounded bg-emerald-500/5 border border-emerald-500/20 text-[10px] font-mono text-emerald-400">
                AfCFTA expansion projected to boost cross-border VIT utility.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
