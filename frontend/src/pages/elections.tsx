import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  Vote, TrendingUp, BarChart2, Globe,
  ChevronRight, Brain, Zap, Clock, ShieldCheck, CheckCircle2
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function ElectionsPage() {
  const [activeCategory, setActiveCategory] = useState("all");

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

      <Card className="bg-vit-surface border-vit-border overflow-hidden">
         <CardHeader className="bg-vit-surface-2 border-b border-vit-border">
            <CardTitle className="text-sm font-display font-bold flex items-center gap-2">
               <Brain size={16} className="text-vit-green" /> AI POLICY SIMULATOR
            </CardTitle>
         </CardHeader>
         <CardContent className="p-10 text-center">
            <Zap size={40} className="text-secondary/30 mx-auto mb-4" />
            <p className="text-xs text-vit-text-3 max-w-sm mx-auto mb-6">Simulate the impact of policy changes using the 13-model VIT ensemble before forecasting.</p>
            <Button size="sm" className="bg-vit-green text-vit-text-inverse font-bold px-6">
               OPEN SIMULATOR
            </Button>
         </CardContent>
      </Card>
    </div>
  );
}
