import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Target, TrendingUp, ShoppingCart, Info } from "lucide-react";

const SIGNALS = [
  { id: 1, type: "sports", title: "EPL Weekend Value Edge", category: "Football", confidence: 88, price: "FREE", provider: "VIT AI Ensemble" },
  { id: 2, type: "election", title: "Lagos East Sentiment Peak", category: "Election", confidence: 94, price: "10 VIT", provider: "Regional Oracle" },
  { id: 3, type: "market", title: "Rice Price Deflation Forecast", category: "Commodity", confidence: 82, price: "5 VIT", provider: "Economic Bot" },
];

export function SignalMarketplace() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {SIGNALS.map((signal) => (
        <Card key={signal.id} className="bg-card/40 border-border/30 backdrop-blur-sm group hover:border-primary/50 transition-all">
          <CardHeader className="pb-2">
            <div className="flex justify-between items-start mb-2">
              <Badge variant="outline" className="text-[9px] font-mono uppercase tracking-widest">{signal.category}</Badge>
              <div className="flex items-center gap-1 text-emerald-400">
                <Target className="w-3 h-3" />
                <span className="text-[10px] font-mono font-bold">{signal.confidence}%</span>
              </div>
            </div>
            <CardTitle className="text-sm font-mono leading-tight">{signal.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-muted-foreground">Provider: {signal.provider}</span>
              <span className="text-xs font-bold font-mono text-primary">{signal.price}</span>
            </div>
            <Button size="sm" className="w-full font-mono text-[10px] uppercase gap-2 h-8">
              <ShoppingCart className="w-3 h-3" /> Get Signal
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
