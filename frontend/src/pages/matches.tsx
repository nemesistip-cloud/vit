import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Search, Activity, Users, RefreshCw, Filter, CalendarDays, ChevronRight, Globe, BarChart3, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import PredictionRow from "@/components/cards/PredictionRow";
import CategoryPills from "@/components/layout/CategoryPills";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import { EmptyState } from "@/components/empty-state";
import { useLocation } from "wouter";
import { cn, formatTime } from "@/lib/utils";

export default function MatchesPage() {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sportFilter, setSportFilter] = useState("all");

  const { data: matchesData, isLoading, refetch } = useQuery<any>({
    queryKey: ["/api/matches?limit=100"],
    queryFn: () => apiGet("/api/matches?limit=100"),
    refetchInterval: 30_000,
  });

  const allMatches: any[] = matchesData?.matches ?? matchesData ?? [];

  const hasLiveMatches = allMatches.some(
    (m: any) => m.status === "live" || m.status === "in_progress"
  );

  const syncMutation = useMutation({
    mutationFn: (vars: { days: number }) => apiPost("/api/admin/sync/fixtures", vars),
  });

  const categories = useMemo(() => {
    // Calculate counts based on current status and search, but NOT activeCategory itself
    const baseMatches = allMatches.filter(m => {
      const matchSearch = (m.home_team + m.away_team + (m.competition || m.league)).toLowerCase();
      const matchesSearch = matchSearch.includes(search.toLowerCase());
      const matchesStatus = statusFilter === "all" ||
                           (statusFilter === "live" ? (m.status === "live" || m.status === "in_progress") : m.status === statusFilter);
      const matchesSport = sportFilter === "all" || (m.sport || "football") === sportFilter;
      return matchesSearch && matchesStatus && matchesSport;
    });

    const base = [{ id: "all", label: "Global Hub", count: baseMatches.length }];

    const leagueCounts = baseMatches.reduce((acc: any, m: any) => {
      const l = m.competition || m.league || "Unknown";
      acc[l] = (acc[l] || 0) + 1;
      return acc;
    }, {});

    const leagues = Object.entries(leagueCounts).map(([label, count]) => ({
      id: label,
      label,
      count: count as number
    })).sort((a, b) => b.count - a.count);

    return [...base, ...leagues];
  }, [allMatches, search, statusFilter, sportFilter]);

  const filteredMatches = useMemo(() => {
    return allMatches.filter(m => {
      const matchSearch = (m.home_team + m.away_team + (m.competition || m.league)).toLowerCase();
      const matchesSearch = matchSearch.includes(search.toLowerCase());
      const matchesStatus = statusFilter === "all" ||
                           (statusFilter === "live" ? (m.status === "live" || m.status === "in_progress") : m.status === statusFilter);
      const matchesSport = sportFilter === "all" || (m.sport || "football") === sportFilter;
      const matchesCategory = activeCategory === "all" || (m.competition || m.league) === activeCategory;

      return matchesSearch && matchesStatus && matchesSport && matchesCategory;
    });
  }, [allMatches, search, activeCategory, statusFilter, sportFilter]);

  const handleSync = async () => {
    try {
      await syncMutation.mutateAsync({ days: 3 });
      toast.success("Intelligence hub updated");
      refetch();
    } catch (e: any) {
      toast.error("Update failed: " + e.message);
    }
  };

  const resetFilters = () => {
    setSearch("");
    setActiveCategory("all");
    setStatusFilter("all");
    setSportFilter("all");
  };

  const isFiltered = search !== "" || activeCategory !== "all" || statusFilter !== "all" || sportFilter !== "all";

  return (
    <div className="space-y-6 pb-20 animate-in fade-in duration-500">
      <div className="px-1 space-y-4">
        <div className="flex items-center justify-between">
           <div className="space-y-1">
              <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Market Intelligence</h1>
              <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Active Analytics Hub</p>
           </div>
           <div className="flex items-center gap-2">
             {isFiltered && (
               <Button variant="ghost" size="icon" className="w-9 h-9 text-muted-foreground hover:text-foreground" onClick={resetFilters}>
                 <X size={14} />
               </Button>
             )}
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
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
            <Input
              placeholder="Search markets, teams, or assets..."
              className="pl-9 bg-white/[0.02] border-white/5 rounded-md h-10 text-xs font-mono"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon" className="h-10 w-10 bg-white/[0.02] border-white/5">
                <Filter size={14} className={cn(sportFilter !== 'all' ? "text-primary" : "text-muted-foreground")} />
              </Button>
            </SheetTrigger>
            <SheetContent side="bottom" className="h-[40vh] bg-[#0C0E12] border-white/5 rounded-t-2xl">
              <SheetHeader className="text-left">
                <SheetTitle className="text-sm font-display uppercase tracking-widest text-white">Advanced Scan Filters</SheetTitle>
                <SheetDescription className="text-[10px] font-mono uppercase text-muted-foreground">Fine-tune your intelligence feed</SheetDescription>
              </SheetHeader>

              <div className="mt-8 space-y-6">
                <div className="space-y-3">
                  <Label className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Sport Type</Label>
                  <RadioGroup value={sportFilter} onValueChange={setSportFilter} className="flex flex-wrap gap-2">
                    {['all', 'football', 'basketball', 'tennis'].map((s) => (
                      <div key={s} className="flex items-center">
                        <RadioGroupItem value={s} id={s} className="peer sr-only" />
                        <Label
                          htmlFor={s}
                          className="px-4 py-2 bg-white/[0.02] border border-white/5 rounded-md text-[10px] uppercase font-bold peer-data-[state=checked]:border-primary peer-data-[state=checked]:text-primary cursor-pointer transition-all text-muted-foreground"
                        >
                          {s === 'all' ? 'All Sports' : s}
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                </div>

                <Button className="w-full uppercase tracking-widest font-display text-xs h-12" onClick={() => {}}>
                  Apply Parameters
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>

      <div className="px-1">
        <CategoryPills
          items={categories}
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
            const isLive = match.status === 'live' || match.status === 'in_progress';
            return (
            <PredictionRow
              key={matchId}
              homeTeam={match.home_team}
              awayTeam={match.away_team}
              competition={match.competition || match.league}
              kickoff={isLive ? (match.minute ? `${match.minute}'` : 'LIVE') : formatTime(match.kickoff_time)}
              isLive={isLive}
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
