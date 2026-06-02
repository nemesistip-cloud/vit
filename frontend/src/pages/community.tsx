import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, MessageSquare, Shield, Star } from "lucide-react";

export default function CommunityPage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">Community Circles</h1>
        <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Collaborative Analytics & Social Proof</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card className="bg-card/50 border-border/40">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Users className="w-4 h-4 text-primary" />
              Trending Circles
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { name: "Lagos Arbitrage Squad", members: "1.2k", signal: "92%" },
              { name: "Naira Policy Analysts", members: "450", signal: "88%" },
              { name: "Elite Betting Shop Agents", members: "2k+", signal: "95%" },
            ].map((circle) => (
              <div key={circle.name} className="p-3 rounded-xl bg-background/40 border border-border/20 hover:border-primary/40 cursor-pointer transition-all">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-xs font-mono font-bold">{circle.name}</h3>
                  <Badge variant="outline" className="text-[8px] font-mono">{circle.members}</Badge>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-full bg-background/60 h-1 rounded-full overflow-hidden">
                    <div className="bg-primary h-full" style={{ width: circle.signal }} />
                  </div>
                  <span className="text-[9px] font-mono text-primary font-bold">{circle.signal}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
