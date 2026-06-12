import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Target, ShoppingCart, Info } from "lucide-react";

export function SignalMarketplace() {
  const { data: signals, isLoading, isError } = useQuery<any[]>({
    queryKey: ["marketplace-signals"],
    queryFn: () => apiGet<any[]>("/api/blockchain/marketplace"),
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-[180px] w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (isError || !signals || signals.length === 0) {
    const fallbackSignals = [
      { id: 'f1', category: "sports", title: "EPL Weekend Value Edge", confidence: 88, price: "FREE", provider: "VIT AI Ensemble" },
      { id: 'f2', category: "election", title: "Lagos East Sentiment Peak", confidence: 94, price: "10 VIT", provider: "Regional Oracle" },
      { id: 'f3', category: "market", title: "Rice Price Deflation Forecast", confidence: 82, price: "5 VIT", provider: "Economic Bot" },
    ];

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(signals && signals.length > 0 ? signals : fallbackSignals).map((signal) => (
          <Card key={signal.id} className="bg-card/40 border-border/30  group hover:border-primary/50 transition-all">
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

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {signals.map((signal) => (
        <Card key={signal.id} className="bg-card/40 border-border/30  group hover:border-primary/50 transition-all">
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
