import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { TrendingUp, Activity, BarChart3, Ticket, ChevronRight, User as UserIcon, Users, Filter } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import { safeFormat } from "@/lib/utils";
import PredictionRow from "@/components/cards/PredictionRow";
import CategoryPills from "@/components/layout/CategoryPills";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import { EmptyState } from "@/components/empty-state";
import { useLocation } from "wouter";

export default function PredictionsPage() {
  const [, navigate] = useLocation();
  const [activeTab, setActiveTab] = useState("community");
  const [activeCategory, setActiveCategory] = useState("all");

  const { data: history, isLoading } = useQuery<any[]>({
    queryKey: [activeTab === "community" ? "/api/history?all_users=true" : "/api/history"],
    queryFn: async () => {
      const res = await apiGet(activeTab === "community" ? "/api/history?all_users=true" : "/api/history");
      return Array.isArray(res) ? res : (res?.predictions ?? res?.items ?? []);
    },
  });

  const safeHistory: any[] = Array.isArray(history) ? history : [];

  const categories = [
    { id: "all", label: "All Picks" },
    { id: "won", label: "Won", count: safeHistory.filter(h => h.outcome === h.prediction_side).length },
    { id: "lost", label: "Lost", count: safeHistory.filter(h => h.outcome && h.outcome !== h.prediction_side).length },
    { id: "pending", label: "Pending", count: safeHistory.filter(h => !h.outcome).length },
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
    <div className="space-y-4 pb-20">
      <div className="flex items-center justify-between px-1">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-auto">
          <TabsList className="bg-vit-surface-2 border border-vit-border p-1 h-9">
            <TabsTrigger value="community" className="px-4 py-1 text-[10px] font-bold data-[state=active]:bg-vit-surface-3">COMMUNITY</TabsTrigger>
            <TabsTrigger value="user" className="px-4 py-1 text-[10px] font-bold data-[state=active]:bg-vit-surface-3">MY PICKS</TabsTrigger>
          </TabsList>
        </Tabs>
        <Button variant="ghost" size="sm" className="h-8 px-2 text-[10px] font-mono uppercase tracking-widest text-vit-text-3">
          <Filter size={12} className="mr-1.5" /> Filter
        </Button>
      </div>

      <CategoryPills
        items={categories}
        activeId={activeCategory}
        onSelect={setActiveCategory}
      />

      <div className="bg-vit-surface border-y border-vit-border">
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
              oddsChange={item.outcome === item.prediction_side ? 2.5 : -1.5}
              badgeLabel={item.prediction_side?.toUpperCase()}
              onTap={() => navigate(`/matches/${item.match_id}`)}
            />
          ))
        ) : (
          <div className="p-20 text-center">
            <EmptyState
              icon={TrendingUp}
              title="No history found"
              description="Signals and predictions will appear here once settled."
            />
          </div>
        )}
      </div>
    </div>
  );
}
