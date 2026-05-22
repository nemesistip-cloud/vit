import { useState, useEffect } from "react";
import { useListMatches, useListRecentMatches, useListCompletedMatches, useSyncFixtures, useListLeagues } from "@/api-client";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PremiumMatchCard } from "@/components/PremiumMatchCard";
import { EmptyState } from "@/components/empty-state";
import { Search, Zap, Clock, RefreshCw, CalendarDays, Radio, Info, Activity } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { vitWS } from "@/lib/websocket";

const DAY_OPTIONS = [
  { value: "3", label: "Next 3 Days" },
  { value: "7", label: "Next 7 Days" },
  { value: "14", label: "Next 14 Days" },
];

interface League {
  key: string;
  display: string;
}

// Detect if a match is currently live
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

  // Live match poll — fetch live endpoint every 30s
  const { data: liveApiData } = useQuery<{ matches: any[] }>({
    queryKey: ["/api/matches/live"],
    queryFn: () => apiGet("/api/matches/live"),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  // Auto-refresh upcoming data every 60s to pick up newly seeded predictions
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

  // Subscribe to live score WebSocket events — trigger a lightweight refetch
  // when the live-match-tracker agent broadcasts a score update.
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

  // Merge: live (from dedicated endpoint) → upcoming → recent → completed, deduped
  const allMatches = (() => {
    const seen = new Set<string>();
    const merged: any[] = [];
    for (const m of [...liveFromApi, ...upcoming, ...recent, ...completed]) {
      const id = String((m as any).match_id ?? "");
      if (!id || seen.has(id)) continue;
      seen.add(id);
      merged.push(m);
    }
    return merged;
  })();

  const hasSynced = allMatches.length > 0;
  const isSynthetic = hasSynced && !allMatches.some((m: any) => m.external_id);

  const leagues: League[] = leaguesData?.leagues ?? Array.from(
    new Map(
      allMatches
        .map((m) => [(m as any).league_key ?? m.league, m.league] as [string, string])
        .filter(([k]) => !!k)
    ).entries()
  ).map(([key, display]) => ({ key: String(key), display: String(display ?? key) }));

  const matches = allMatches.filter((m) => {
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

  // Sort: live first, then by kickoff time
  const sortedMatches = [...matches].sort((a, b) => {
    const aLive = isMatchLive(a) ? 0 : 1;
    const bLive = isMatchLive(b) ? 0 : 1;
    if (aLive !== bLive) return aLive - bLive;
    const aKo = a.kickoff_time ? new Date(a.kickoff_time).getTime() : 0;
    const bKo = b.kickoff_time ? new Date(b.kickoff_time).getTime() : 0;
    return aKo - bKo;
  });

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

  return (
    <div className="space-y-4">
      {/* ── Header ──────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-mono font-bold uppercase tracking-tight">Intelligence Feed</h1>
          <p className="text-muted-foreground font-mono text-sm flex items-center gap-2 flex-wrap">
            {statusFilter === "completed"
              ? `${sortedMatches.length} of ${completed.length} completed fixtures`
              : statusFilter === "live"
              ? `${sortedMatches.length} live now`
              : statusFilter === "upcoming"
              ? `${sortedMatches.length} upcoming fixtures`
              : hasSynced
              ? `${sortedMatches.length} of ${allMatches.length} fixtures`
              : "Real-time match data & ML consensus"}
            {liveCount > 0 && (
              <span className="inline-flex items-center gap-1 text-green-400 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                {liveCount} live
              </span>
            )}
            <span className="text-muted-foreground/50 text-xs hidden sm:inline">
              · refreshed {formatDistanceToNow(lastRefreshed, { addSuffix: true })}
            </span>
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

      {/* ── Live banner ─────────────────────────────────── */}
      {liveCount > 0 && statusFilter !== "completed" && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 border border-green-500/20 text-xs font-mono text-green-400">
          <Radio className="w-3.5 h-3.5 animate-pulse" />
          <span>
            <strong>{liveCount} match{liveCount !== 1 ? "es" : ""} in progress</strong>
            {" — "}live scores update every 30 seconds automatically
          </span>
        </div>
      )}

      {/* ── Synthetic data notice ────────────────────────── */}
      {isSynthetic && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30 border border-border/40 text-xs font-mono text-muted-foreground">
          <Info className="w-3.5 h-3.5 flex-shrink-0 text-yellow-500/70" />
          <span>Showing synthetic fixtures — configure <span className="font-semibold text-foreground/70">FOOTBALL_DATA_API_KEY</span> for live match data, or click Sync Fixtures</span>
        </div>
      )}

      {/* ── Filters ─────────────────────────────────────── */}
      <div className="space-y-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <label htmlFor="match-search" className="sr-only">Search teams or league</label>
          <Input
            id="match-search"
            placeholder="Search teams or league…"
            className="pl-9 font-mono bg-card/50"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <Select value={leagueFilter} onValueChange={setLeagueFilter}>
            <SelectTrigger className="flex-1 font-mono bg-card/50 text-xs min-w-0">
              <SelectValue placeholder="All Leagues" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Leagues</SelectItem>
              {(Array.isArray(leagues) ? leagues : []).map((lg: League) => (
                <SelectItem key={lg.key} value={lg.key}>{lg.display}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="flex-1 font-mono bg-card/50 text-xs min-w-0">
              <SelectValue placeholder="All Matches" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Matches</SelectItem>
              <SelectItem value="upcoming">Upcoming</SelectItem>
              <SelectItem value="live">
                <span className="flex items-center gap-1.5">
                  <Radio className="w-3 h-3 text-green-400" /> Live
                  {liveCount > 0 && <Badge className="text-[9px] h-3.5 px-1 bg-green-500/20 text-green-400 border-green-500/30">{liveCount}</Badge>}
                </span>
              </SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
            </SelectContent>
          </Select>
          <Select value={daysFilter} onValueChange={setDaysFilter}>
            <SelectTrigger className="font-mono bg-card/50 text-xs w-[120px] flex-shrink-0">
              <CalendarDays className="w-3 h-3 mr-1 text-muted-foreground" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DAY_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-72 rounded-xl" />
          ))}
        </div>
      ) : isErrorUpcoming && isErrorRecent && isErrorCompleted ? (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center space-y-3">
          <p className="font-mono text-sm text-destructive">Could not load match data. The API may be temporarily unavailable.</p>
          <Button size="sm" variant="outline" className="font-mono text-xs gap-1.5" onClick={() => { refetch(); }}>
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </Button>
        </div>
      ) : upcoming.length === 0 && recent.length === 0 && completed.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="No match data loaded yet."
          description={`Click "Load Fixtures Now" to fetch upcoming matches for the next ${daysFilter} days.`}
          action={{
            label: syncMutation.isPending ? "Loading fixtures..." : "Load Fixtures Now",
            onClick: handleSync,
            loading: syncMutation.isPending,
          }}
        />
      ) : sortedMatches.length > 0 ? (
        <>
          {/* Section labels */}
          {liveCount > 0 && statusFilter !== "completed" && statusFilter !== "upcoming" && (
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <span className="font-mono text-xs text-muted-foreground uppercase tracking-widest">
                Live matches first
              </span>
            </div>
          )}
          {statusFilter === "completed" && (
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-green-500" />
              <span className="font-mono text-xs text-muted-foreground uppercase tracking-widest">
                Completed Matches
              </span>
              <Badge variant="outline" className="font-mono text-[10px]">{sortedMatches.length}</Badge>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {sortedMatches.map((match, i) => (
              <PremiumMatchCard key={`${match.match_id}-${i}`} match={match} />
            ))}
          </div>
        </>
      ) : (
        <EmptyState
          icon={Search}
          title="No matches for the selected filters."
          description="Try adjusting the league, status, or date range filter."
        />
      )}
    </div>
  );
}
