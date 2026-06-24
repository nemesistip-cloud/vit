import { useState, useEffect, useMemo } from "react";
import { useListMatches, useListRecentMatches, useListCompletedMatches, useSyncFixtures, useListLeagues } from "@/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PremiumMatchCard } from "@/components/PremiumMatchCard";
import { EmptyState } from "@/components/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Zap, Clock, RefreshCw, CalendarDays, Radio, Info, Users, Activity, ChevronRight, Filter } from "lucide-react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import { vitWS } from "@/lib/websocket";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const DAY_OPTIONS = [
  { value: "3", label: "Next 3 Days" },
  { value: "7", label: "Next 7 Days" },
  { value: "14", label: "Next 14 Days" },
];

interface League {
  key: string;
  display: string;
}

function isMatchLive(m: any): boolean {
  const s = String(m.status ?? "").toLowerCase();
  if (s === "live" || s === "in_play" || s === "playing") return true;
  if (m.actual_outcome) return false;
  const ko = m.kickoff_time ? new Date(m.kickoff_time).getTime() : NaN;
  if (!Number.isFinite(ko)) return false;
  const now = Date.now();
  return ko <= now && now - ko <= 2.5 * 60 * 60 * 1000;
}

export default function MatchesPage() {
  const [activeTab, setActiveTab] = useState("matches");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [leagueFilter, setLeagueFilter] = useState<string>("all");
  const [daysFilter, setDaysFilter] = useState<string>("14");
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const queryClient = useQueryClient();

  const matchParams = { days: daysFilter };
  const { data: upcomingData, isLoading: upcomingLoading, isError: isErrorUpcoming, refetch } = useListMatches(matchParams);
  const { data: recentData, isLoading: recentLoading, isError: isErrorRecent } = useListRecentMatches();
  const { data: completedData, isLoading: completedLoading, isError: isErrorCompleted } = useListCompletedMatches();
  const { data: leaguesData } = useListLeagues();
  const syncMutation = useSyncFixtures();

  const { data: liveApiData } = useQuery<{ matches: any[] }>({
    queryKey: ["/api/matches/live"],
    queryFn: () => apiGet("/api/matches/live"),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  useEffect(() => {
    const id = setInterval(() => {
      queryClient.invalidateQueries({ predicate: (q) => {
        const k = String(q.queryKey?.[0] ?? "");
        return k.includes("/matches");
      }});
      setLastRefreshed(new Date());
    }, 60_000);
    return () => clearInterval(id);
  }, [queryClient]);

  useEffect(() => {
    const unsub1 = vitWS.on("live_score_update", () => {
      queryClient.invalidateQueries({ queryKey: ["/api/matches/live"] });
      setLastRefreshed(new Date());
    });
    const unsub2 = vitWS.on("match_update", () => {
      queryClient.invalidateQueries({ predicate: (q: any) => {
        const k = String(q.queryKey?.[0] ?? "");
        return k.includes("/matches");
      }});
    });
    return () => { unsub1(); unsub2(); };
  }, [queryClient]);

  const isLoading = upcomingLoading || recentLoading || completedLoading;

  const upcoming = upcomingData?.matches ?? [];
  const recent = recentData?.matches ?? [];
  const completed = completedData?.matches ?? [];
  const liveFromApi = liveApiData?.matches ?? [];

  const allMatches = useMemo(() => {
    const seen = new Set<string>();
    const merged: any[] = [];
    for (const m of [...liveFromApi, ...upcoming, ...recent, ...completed]) {
      const id = String((m as any).match_id ?? "");
      if (!id || seen.has(id)) continue;
      seen.add(id);
      merged.push(m);
    }
    return merged;
  }, [liveFromApi, upcoming, recent, completed]);

  const leagues: League[] = leaguesData?.leagues ?? Array.from(
    new Map(
      allMatches
        .map((m) => [(m as any).league_key ?? m.league, m.league] as [string, string])
        .filter(([k]) => !!k)
    ).entries()
  ).map(([key, display]) => ({ key: String(key), display: String(display ?? key) }));

  const matches = useMemo(() => {
    return allMatches.filter((m) => {
      const searchLower = search.toLowerCase();
      const matchesSearch = !search ||
        m.home_team?.toLowerCase().includes(searchLower) ||
        m.away_team?.toLowerCase().includes(searchLower) ||
        m.league?.toLowerCase().includes(searchLower);

      if (!matchesSearch) return false;

      if (leagueFilter !== "all") {
        const mKey = (m as any).league_key ?? m.league;
        if (mKey !== leagueFilter && m.league !== leagueFilter) return false;
      }

      if (statusFilter === "completed") return !!m.actual_outcome;
      if (statusFilter === "upcoming") return !m.actual_outcome && !isMatchLive(m);
      if (statusFilter === "live")     return isMatchLive(m);

      return true;
    });
  }, [allMatches, search, leagueFilter, statusFilter]);

  const sortedMatches = useMemo(() => {
    return [...matches].sort((a, b) => {
      const aLive = isMatchLive(a) ? 0 : 1;
      const bLive = isMatchLive(b) ? 0 : 1;
      if (aLive !== bLive) return aLive - bLive;
      const aKo = a.kickoff_time ? new Date(a.kickoff_time).getTime() : 0;
      const bKo = b.kickoff_time ? new Date(b.kickoff_time).getTime() : 0;
      return aKo - bKo;
    });
  }, [matches]);

  const teams = useMemo(() => {
    const stats = new Map<string, { count: number, sport: string, league: string }>();
    allMatches.forEach(m => {
      [m.home_team, m.away_team].forEach(name => {
        if (name) {
          const entry = stats.get(name) || { count: 0, sport: m.sport || "sports", league: m.league };
          entry.count += 1;
          stats.set(name, entry);
        }
      });
    });

    return Array.from(stats.entries()).map(([name, data]) => ({
      name,
      ...data
    })).filter(t => !search || t.name.toLowerCase().includes(search.toLowerCase()))
       .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  }, [allMatches, search]);

  const isSports = allMatches.some(m => m.market_type === "sports" || m.sport !== "niche");
  const liveCount = allMatches.filter(isMatchLive).length;

  const handleSync = async () => {
    try {
      const result = await syncMutation.mutateAsync({ days: parseInt(daysFilter) });
      if (result.stored > 0) {
        toast.success(`Synced ${result.stored} new fixtures (${result.source})`);
      } else {
        toast.info("All fixtures already up to date");
      }
      queryClient.invalidateQueries({ predicate: (q) => {
        const k = String(q.queryKey?.[0] ?? "");
        return k.startsWith("/matches") || k.startsWith("matches-");
      }});
      refetch();
      setLastRefreshed(new Date());
    } catch (e: any) {
      toast.error(e.message || "Sync failed");
    }
  };

  const hasActiveFilters = search !== "" || leagueFilter !== "all" || statusFilter !== "all";

  return (
    <div className="space-y-4">
      {/* ── Header ──────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">
            {isSports ? "Sports Analysis Hub" : "Niche Market Discovery"}
          </h1>
          <p className="text-muted-foreground font-mono text-sm mt-1 uppercase tracking-widest text-[10px]">
            Real-time match data & ML consensus
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="font-mono text-xs gap-1.5 flex-shrink-0 border-primary/30 hover:border-primary/60"
          onClick={handleSync}
          disabled={syncMutation.isPending}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
          {syncMutation.isPending ? "Syncing..." : "Sync Fixtures"}
        </Button>
      </div>

      {/* ── Tabs ────────────────────────────────────────── */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full max-w-[400px] grid-cols-2 font-mono bg-card/50 border border-border/40 p-1 rounded-xl">
          <TabsTrigger value="matches" className="gap-2 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            <Activity className="w-3.5 h-3.5" />
            Matches ({allMatches.length})
          </TabsTrigger>
          <TabsTrigger value="teams" className="gap-2 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            <Users className="w-3.5 h-3.5" />
            Teams ({teams.length})
          </TabsTrigger>
        </TabsList>

        <div className="mt-6 space-y-6">
          {/* Summary line EXACTLY matching user screenshots logic */}
          <div className="flex flex-col gap-1 border-b border-border/40 pb-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
                Found: {activeTab === "matches" ? sortedMatches.length : teams.length}
              </span>
              {hasActiveFilters && (
                 <Button
                   variant="ghost"
                   size="sm"
                   className="h-7 px-2 text-[10px] font-mono uppercase text-muted-foreground hover:text-primary"
                   onClick={() => {
                     setSearch("");
                     setLeagueFilter("all");
                     setStatusFilter("all");
                   }}
                 >
                   Clear Filters
                 </Button>
              )}
            </div>
            <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
              {activeTab === "matches" ? "Live & Upcoming Fixtures" : "Repository Contributors & Entities"}
              <span className="ml-2 opacity-50">· refreshed {formatDistanceToNow(lastRefreshed, { addSuffix: true })}</span>
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={activeTab === "matches" ? "Search teams, league or ID…" : "Search teams or players…"}
                  className="pl-10 font-mono bg-card/40 border-border/40 rounded-xl"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              {activeTab === "matches" && (
                <div className="flex gap-2">
                  <Select value={leagueFilter} onValueChange={setLeagueFilter}>
                    <SelectTrigger className="w-[140px] font-mono bg-card/40 border-border/40 rounded-xl text-xs">
                      <SelectValue placeholder="League" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Leagues</SelectItem>
                      {leagues.map((lg) => (
                        <SelectItem key={lg.key} value={lg.key}>{lg.display}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-[120px] font-mono bg-card/40 border-border/40 rounded-xl text-xs">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="upcoming">Upcoming</SelectItem>
                      <SelectItem value="live">Live</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={daysFilter} onValueChange={setDaysFilter}>
                    <SelectTrigger className="w-[130px] font-mono bg-card/40 border-border/40 rounded-xl text-xs">
                      <CalendarDays className="w-3 h-3 mr-1.5" />
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DAY_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            <TabsContent value="matches" className="mt-0 space-y-4">
              {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-72 rounded-xl" />
                  ))}
                </div>
              ) : sortedMatches.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {sortedMatches.map((match, i) => (
                    <PremiumMatchCard key={`${match.match_id}-${i}`} match={match} />
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={Search}
                  title={`No matches match your current filters.`}
                  description={hasActiveFilters ? "Try clearing filters to see more results." : "No matches currently loaded in the network."}
                />
              )}
            </TabsContent>

            <TabsContent value="teams" className="mt-0">
              {teams.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {teams.map((team, i) => (
                    <div key={i} className="p-4 rounded-2xl bg-card/40 border border-border/40 hover:border-primary/40 transition-all group cursor-pointer">
                      <div className="flex items-center gap-3">
                        <Avatar className="w-12 h-12 border border-border/20 group-hover:border-primary/30 transition-colors">
                          <AvatarFallback className="bg-primary/5 text-primary font-mono font-bold">
                            {team.name.substring(0, 2).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div className="min-w-0 flex-1">
                          <h3 className="text-sm font-mono font-bold truncate group-hover:text-primary transition-colors">{team.name}</h3>
                          <div className="flex flex-col gap-0.5 mt-0.5">
                             <div className="flex items-center gap-1.5">
                               <Badge variant="outline" className="text-[8px] font-mono py-0 h-3.5 uppercase tracking-tighter opacity-70">
                                 {team.sport}
                               </Badge>
                               <span className="text-[10px] font-mono text-muted-foreground truncate">{team.league}</span>
                             </div>
                             <p className="text-[10px] font-mono text-primary/80 font-bold uppercase tracking-tight">
                               {team.count} matches
                             </p>
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={Users}
                  title="No teams found"
                  description="Try a different search term or check back later."
                />
              )}
            </TabsContent>
          </div>
        </div>
      </Tabs>
    </div>
  );
}
