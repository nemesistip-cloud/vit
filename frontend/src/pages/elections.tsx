import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Vote, TrendingUp, Users, ShieldCheck } from "lucide-react";

export default function ElectionsPage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">Elections & Governance</h1>
        <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Verifiable Polling & Forecast Analytics</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Active Polls", value: "24", icon: Vote, color: "text-blue-400" },
          { label: "Accuracy Score", value: "94.2%", icon: TrendingUp, color: "text-emerald-400" },
          { label: "Total Participants", value: "1.2M", icon: Users, color: "text-purple-400" },
          { label: "On-Chain Verified", value: "100%", icon: ShieldCheck, color: "text-yellow-400" },
        ].map((stat) => (
          <Card key={stat.label} className="bg-card/50 border-border/40 backdrop-blur-sm">
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`p-2 rounded-lg bg-background/50 ${stat.color}`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[10px] font-mono text-muted-foreground uppercase">{stat.label}</p>
                <p className="text-lg font-bold font-mono">{stat.value}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-card/50 border-border/40 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Real-time Forecast: Nigeria 2027
            </CardTitle>
            <CardDescription className="text-xs font-mono">Aggregated AI ensemble of ground polling and economic sentiment</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center border-t border-border/20">
            <p className="text-xs font-mono text-muted-foreground/60 italic">Interactive forecast map loading...</p>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/40 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-mono">Recent Updates</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-3 pb-3 border-b border-border/20 last:border-0">
                <div className="w-1 h-8 bg-primary/40 rounded-full" />
                <div>
                  <p className="text-xs font-mono font-bold">Lagos State Polling Shift</p>
                  <p className="text-[10px] font-mono text-muted-foreground">+2.4% shift in youth engagement sentiment recorded.</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
