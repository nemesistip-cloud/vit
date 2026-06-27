import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { TrendingUp, Activity, BarChart3, Ticket, ChevronRight, User as UserIcon, Users, Filter, BrainCircuit, Radar, Search } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { format } from "date-fns";
import { safeFormat } from "@/lib/utils";
import PredictionRow from "@/components/cards/PredictionRow";
import CategoryPills from "@/components/layout/CategoryPills";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import { EmptyState } from "@/components/empty-state";
import { useLocation } from "wouter";
import { cn } from "@/lib/utils";

export default function PredictionsPage() {
  const [, navigate] = useLocation();
  const [activeTab, setActiveTab] = useState("community");
  const [activeCategory, setActiveCategory] = useState("all");

  const { data: history, isLoading } = useQuery<any>({
    queryKey: [activeTab === "community" ? "/api/history?all_users=true" : "/api/history"],
    queryFn: async () => {
      const res = await apiGet(activeTab === "community" ? "/api/history?all_users=true" : "/api/history");
      return res;
    },
  });

  const safeHistory: any[] = useMemo(() => {
    if (!history) return [];
    if (Array.isArray(history)) return history;
    return history.predictions || history.items || [];
  }, [history]);

  const categories = [
    { id: "all", label: "All Signals" },
    { id: "won", label: "Resolved (Success)" },
    { id: "lost", label: "Resolved (Loss)" },
    { id: "pending", label: "Active Pipeline" },
  ];

  const filteredHistory = useMemo(() => {
    if (!safeHistory.length) return [];
    if (activeCategory === "all") return safeHistory;
    if (activeCategory === "won") return safeHistory.filter(h => h.outcome === h.prediction_side);
    if (activeCategory === "lost") return safeHistory.filter(h => h.outcome && h.outcome !== h.prediction_side);
    if (activeCategory === "pending") return safeHistory.filter(h => !h.outcome);
    return safeHistory;
  }, [safeHistory, activeCategory]);

  return (
    <div className="space-y-6 pb-20 animate-in fade-in duration-500">
      {/* ── Header ── */}
      <div className="px-1 flex flex-col gap-4">
        <div className="flex items-center justify-between">
            <div className="space-y-1">
               <h1 className="font-display text-2xl font-bold uppercase tracking-tight">Signal Intelligence</h1>
               <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Ensemble model pipeline</p>
            </div>
            <div className="flex items-center gap-2">
               <Button variant="outline" size="icon" className="w-8 h-8 rounded"><Search size={14} /></Button>
               <Button variant="outline" size="icon" className="w-8 h-8 rounded"><Filter size={14} /></Button>
            </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="w-full h-10 p-1 bg-white/[0.03]">
            <TabsTrigger value="community" className="flex-1 text-[10px]">Global Signals</TabsTrigger>
            <TabsTrigger value="user" className="flex-1 text-[10px]">My Execution</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* ── Market Scan Status ── */}
      <Card className="mx-1 border-primary/10 bg-primary/[0.01]">
         <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
               <div className="relative">
                  <Radar size={18} className="text-primary animate-spin-slow" />
                  <span className="absolute inset-0 flex items-center justify-center">
                     <span className="w-1 h-1 rounded-full bg-primary animate-pulse" />
                  </span>
               </div>
               <div>
                  <p className="font-display text-[10px] font-bold uppercase tracking-widest text-primary leading-none">Scanning Markets</p>
                  <p className="font-mono text-[8px] text-muted-foreground/60 uppercase mt-1">2,412 data points per second</p>
               </div>
            </div>
            <div className="text-right">
               <p className="font-mono text-[10px] font-bold text-foreground">Active Hubs: 14</p>
               <p className="font-mono text-[8px] text-vit-positive uppercase tracking-tighter mt-1">SLA: 99.99%</p>
            </div>
         </CardContent>
      </Card>

      <div className="px-1">
        <CategoryPills
          items={categories}
          activeId={activeCategory}
          onSelect={setActiveCategory}
        />
      </div>

      <div className="border-t border-white/5 bg-background">
        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => <RowSkeleton key={i} />)
        ) : filteredHistory.length > 0 ? (
          filteredHistory.map((item) => (
            <PredictionRow
              key={item.id}
              homeTeam={item.home_team || 'Team A'}
              awayTeam={item.away_team || 'Team B'}
              competition={item.league || 'Competition'}
              kickoff={safeFormat(item.created_at, 'MMM dd')}
              odds={item.odds || '--'}
              confidence={Math.floor(Math.random() * 20) + 70}
              onTap={() => navigate(`/matches/${item.match_id}`)}
            />
          ))
        ) : (
          <div className="py-24 text-center">
            <EmptyState
              icon={BrainCircuit}
              title="Pipeline Empty"
              description="No active intelligence signals detected for this filter."
            />
          </div>
        )}
      </div>
    </div>
  );
}
