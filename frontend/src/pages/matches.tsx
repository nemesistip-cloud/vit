import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Search, Activity, Users, RefreshCw, Filter, CalendarDays, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import PredictionRow from "@/components/cards/PredictionRow";
import CategoryPills from "@/components/layout/CategoryPills";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import EmptyState from "@/components/empty-state";
import { useLocation } from "wouter";

export default function MatchesPage() {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [lastRefreshed, setLastRefreshed] = useState(new Date());

  const { data: matchesData, isLoading, refetch } = useQuery<any>({
    queryKey: ["/api/matches?limit=100"],
    queryFn: () => apiGet("/api/matches?limit=100"),
  });

  const syncMutation = useMutation({
    mutationFn: (vars: { days: number }) => apiPost("/api/admin/sync/fixtures", vars),
  });

  const allMatches: any[] = matchesData?.matches ?? matchesData ?? [];

  const categories = useMemo(() => {
    const base = [{ id: "all", label: "All Markets", count: allMatches.length }];
    const leagues = Array.from(new Set(allMatches.map(m => m.competition || m.league))).filter(Boolean);
    return [
      ...base,
      ...leagues.map(l => ({
        id: l,
        label: l,
        count: allMatches.filter(m => (m.competition || m.league) === l).length
      }))
    ];
  }, [allMatches]);

  const filteredMatches = useMemo(() => {
    return allMatches.filter(m => {
      const matchSearch = (m.home_team + m.away_team + (m.competition || m.league)).toLowerCase();
      const matchesSearch = matchSearch.includes(search.toLowerCase());
      const matchesCategory = activeCategory === "all" || (m.competition || m.league) === activeCategory;
      const matchesStatus = statusFilter === "all" || m.status === statusFilter;
      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [allMatches, search, activeCategory, statusFilter]);

  const handleSync = async () => {
    try {
      await syncMutation.mutateAsync({ days: 3 });
      toast.success("Fixtures synchronized successfully");
      refetch();
      setLastRefreshed(new Date());
    } catch (e: any) {
      toast.error("Sync failed: " + e.message);
    }
  };

  return (
    <div className="space-y-4 pb-20">
      <div className="flex items-center justify-between gap-4 px-1">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-vit-text-3" />
          <Input
            placeholder="Search teams or leagues..."
            className="pl-10 bg-vit-surface-2 border-vit-border rounded-full h-10 text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button
          variant="outline"
          size="icon"
          className="rounded-full border-vit-border bg-vit-surface-2 w-10 h-10 flex-shrink-0"
          onClick={handleSync}
          disabled={syncMutation.isPending}
        >
          <RefreshCw size={18} className={syncMutation.isPending ? "animate-spin" : ""} />
        </Button>
      </div>

      <CategoryPills
        items={categories.slice(0, 8)}
        activeId={activeCategory}
        onSelect={setActiveCategory}
      />

      <div className="flex items-center justify-between px-1">
        <Tabs value={statusFilter} onValueChange={setStatusFilter} className="w-auto">
          <TabsList className="bg-transparent gap-4 h-auto p-0">
            <TabsTrigger value="all" className="p-0 text-xs font-bold data-[state=active]:text-vit-green border-b-2 border-transparent data-[state=active]:border-vit-green rounded-none bg-transparent">ALL</TabsTrigger>
            <TabsTrigger value="live" className="p-0 text-xs font-bold data-[state=active]:text-vit-green border-b-2 border-transparent data-[state=active]:border-vit-green rounded-none bg-transparent">LIVE</TabsTrigger>
            <TabsTrigger value="upcoming" className="p-0 text-xs font-bold data-[state=active]:text-vit-green border-b-2 border-transparent data-[state=active]:border-vit-green rounded-none bg-transparent">UPCOMING</TabsTrigger>
          </TabsList>
        </Tabs>
        <span className="text-[10px] font-mono text-vit-text-3 uppercase">
          {filteredMatches.length} Matches Found
        </span>
      </div>

      <div className="bg-vit-surface border-y border-vit-border">
        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => <RowSkeleton key={i} />)
        ) : filteredMatches.length > 0 ? (
          filteredMatches.map((match) => (
            <PredictionRow
              key={match.id}
              homeTeam={match.home_team}
              awayTeam={match.away_team}
              competition={match.competition || match.league}
              kickoff={match.status === 'live' ? (match.minute ? `${match.minute}'` : 'LIVE') : new Date(match.kickoff_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              isLive={match.status === 'live'}
              odds={match.odds?.home || '--'}
              oddsChange={Math.random() > 0.5 ? 1.2 : -0.8} // Mock change for terminal look
              onTap={() => navigate(`/matches/${match.id}`)}
              badgeLabel={match.market_type === 'sports' ? 'PRO' : undefined}
            />
          ))
        ) : (
          <div className="p-20">
             <EmptyState
                icon={Activity}
                title="No matches found"
                description="Try adjusting your filters or search query."
              />
          </div>
        )}
      </div>
    </div>
  );
}
