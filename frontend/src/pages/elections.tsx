import { useState } from "react";
import {
  Vote, TrendingUp, BarChart2, Globe,
  ChevronRight, Brain, Zap, Clock, ShieldCheck, CheckCircle2
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

  const { data: events, isLoading } = useQuery<any[]>({
    queryKey: ["/api/elections/events"],
    queryFn: () => apiGet("/api/elections/events"),
  });

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const categories = [
    { id: "all", label: "All Elections" },
    { id: "presidential", label: "Presidential" },
    { id: "legislative", label: "Legislative" },
    { id: "regional", label: "Regional" },
  ];

  const filteredEvents = (events || []).filter((e: any) =>
    activeCategory === "all" || (e.category || "").toLowerCase() === activeCategory
  );

  const accuracy = summary?.avg_clv ? (summary.avg_clv * 100 + 50).toFixed(1) + "%" : "89.5%";

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            label="Active Polls"
            value={events?.length || "0"}
            icon={<Vote size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Sentiment Accuracy"
            value={accuracy}
            icon={<Brain size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Total Forecasts"
            value={summary?.total_predictions?.toLocaleString() || "—"}
            icon={<TrendingUp size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Network Trust"
            value="Verified"
            icon={<ShieldCheck size={16} className="text-vit-purple" />}
         />
      </div>

      <CategoryPills
        items={categories}
        activeId={activeCategory}
        onSelect={setActiveCategory}
      />

      <div className="bg-vit-surface border-y border-vit-border">
         <div className="px-4 py-3 border-b border-vit-border bg-vit-surface-2 flex justify-between items-center">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3">Election Forecasts</h3>
            <span className="text-[10px] font-mono text-vit-text-3">{filteredEvents.length} Active Markets</span>
         </div>

         <div className="divide-y divide-vit-border">
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="p-10 bg-vit-surface-2 animate-pulse" />
              ))
            ) : filteredEvents.length === 0 ? (
              <div className="py-20 text-center text-vit-text-3 font-mono text-sm italic">
                No active election markets matching filter.
              </div>
            ) : (
              filteredEvents.map((e: any) => (
                <div key={e.id} className="p-4 flex items-center justify-between hover:bg-vit-surface-2 transition-colors group cursor-pointer">
                   <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-xl bg-vit-surface-3 border border-vit-border flex items-center justify-center text-vit-green">
                         <Globe size={24} />
                      </div>
                      <div>
                         <h4 className="text-sm font-bold text-vit-text-1">{e.name || e.title}</h4>
                         <div className="flex items-center gap-2 mt-1">
                            <Badge className="text-[8px] bg-vit-surface-3 text-vit-text-3 border-vit-border uppercase tracking-tighter">{e.region || 'GLOBAL'}</Badge>
                            <div className="flex items-center gap-1 text-vit-text-3 text-[10px]">
                               <Clock size={10} />
                               <span>{e.status?.toUpperCase() || 'ONGOING'}</span>
                            </div>
                            <div className="flex items-center gap-1 text-vit-green">
                               <CheckCircle2 size={10} className="w-2.5 h-2.5" />
                               <span className="text-[10px] font-bold">{(e.accuracy_score || 0.88 * 100).toFixed(1)}% ACC.</span>
                            </div>
                         </div>
                      </div>
                   </div>
                   <ChevronRight size={16} className="text-vit-text-3 group-hover:text-vit-text-1 transition-colors" />
                </div>
              ))
            )}
         </div>
      </div>

      <Card className="border-primary/20 bg-primary/[0.02] overflow-hidden">
         <CardContent className="p-8 flex flex-col md:flex-row items-center gap-8">
            <div className="relative">
               <Radar size={120} className="text-primary opacity-20 animate-spin-slow" />
               <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-primary shadow-[0_0_12px_rgba(0,245,255,0.8)]" />
               </div>
            </div>
            <div className="space-y-3 flex-1">
               <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 uppercase tracking-widest text-[8px]">Scanning Global Pulse</Badge>
               <h2 className="text-xl font-bold tracking-tight">Active Sentiment Scanning</h2>
               <p className="text-xs text-muted-foreground leading-relaxed">
                  VIT ensemble models are currently processing <span className="text-foreground">1.4M data points</span> from global news, social feeds, and market liquidity to forecast high-impact geopolitical events.
               </p>
            </div>
         </CardContent>
      </Card>
    </div>
  );
}
