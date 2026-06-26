import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Search, Activity, Users, RefreshCw, Filter, CalendarDays, ChevronRight, Globe, BarChart3 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import PredictionRow from "@/components/cards/PredictionRow";
import CategoryPills from "@/components/layout/CategoryPills";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import { EmptyState } from "@/components/empty-state";
import { useLocation } from "wouter";
import { cn } from "@/lib/utils";

export default function MatchesPage() {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data: matchesData, isLoading, refetch } = useQuery<any>({
    queryKey: ["/api/matches?limit=100"],
    queryFn: () => apiGet("/api/matches?limit=100"),
    refetchInterval: 30_000,
  });

  const hasLiveMatches = (matchesData?.matches ?? matchesData ?? []).some(
    (m: any) => m.status === "live" || m.status === "in_progress"
  );

  const syncMutation = useMutation({
    mutationFn: (vars: { days: number }) => apiPost("/api/admin/sync/fixtures", vars),
  });

  const allMatches: any[] = matchesData?.matches ?? matchesData ?? [];

  const categories = useMemo(() => {
    const base = [{ id: "all", label: "Global Hub", count: allMatches.length }];
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
      toast.success("Intelligence hub updated");
      refetch();
    } catch (e: any) {
      toast.error("Update failed: " + e.message);
    }
  };

  return (
    <div className="space-y-6 pb-20 animate-in fade-in duration-500">
      <div className="px-1 space-y-4">
        <div className="flex items-center justify-between">
           <div className="space-y-1">
              <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Market Intelligence</h1>
              <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Active Analytics Hub</p>
           </div>
           <Button
              variant="outline"
              size="icon"
              className="rounded bg-white/[0.02] border-white/5 w-9 h-9"
              onClick={handleSync}
              disabled={syncMutation.isPending}
            >
              <RefreshCw size={14} className={cn("text-muted-foreground", syncMutation.isPending ? "animate-spin text-primary" : "")} />
            </Button>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
          <Input
            placeholder="Search markets, teams, or assets..."
            className="pl-9 bg-white/[0.02] border-white/5 rounded-md h-10 text-xs font-mono"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="px-1">
        <CategoryPills
          items={categories.slice(0, 8)}
          activeId={activeCategory}
          onSelect={setActiveCategory}
        />
      </div>

      <div className="flex items-center justify-between px-1">
        <Tabs value={statusFilter} onValueChange={setStatusFilter} className="w-auto">
          <TabsList className="bg-white/[0.02] border-white/5 p-1 h-9">
            <TabsTrigger value="all" className="px-4 text-[10px]">ALL</TabsTrigger>
            <TabsTrigger value="live" className="px-4 text-[10px]">
              <span className="flex items-center gap-1.5">
                {hasLiveMatches && <span className="w-1 h-1 rounded-full bg-vit-negative animate-pulse" />}
                LIVE
              </span>
            </TabsTrigger>
            <TabsTrigger value="upcoming" className="px-4 text-[10px]">UPCOMING</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="text-right">
          <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
            {filteredMatches.length} MATCHES FOUND
          </span>
        </div>
      </div>

      <div className="border-t border-white/5 bg-background">
        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => <RowSkeleton key={i} />)
        ) : filteredMatches.length > 0 ? (
          filteredMatches.map((match) => {
            const matchId = match.match_id ?? match.id;
            return (
            <PredictionRow
              key={matchId}
              homeTeam={match.home_team}
              awayTeam={match.away_team}
              competition={match.competition || match.league}
              kickoff={match.status === 'live' ? (match.minute ? `${match.minute}'` : 'LIVE') : match.kickoff_time ? new Date(match.kickoff_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--'}
              odds={match.odds?.home || '--'}
              onTap={() => navigate(`/matches/${matchId}`)}
            />
            );
          })
        ) : (
          <div className="py-24 text-center">
             <EmptyState
                icon={Globe}
                title="No Nodes Detected"
                description="The intelligence hub is currently quiet. Try adjusting scan parameters."
              />
          </div>
        )}
      </div>
    </div>
  );
}
