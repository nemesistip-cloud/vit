import { useState } from "react";
import { useListMatches, useListRecentMatches, useSyncFixtures, useListLeagues } from "@/api-client";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PremiumMatchCard } from "@/components/PremiumMatchCard";
import { Search, Zap, Clock, RefreshCw, CalendarDays, Radio, Info } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

const DAY_OPTIONS = [
  { value: "3", label: "Next 3 Days" },
  { value: "7", label: "Next 7 Days" },
  { value: "14", label: "Next 14 Days" },
];

export default function MatchesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [leagueFilter, setLeagueFilter] = useState<string>("all");
  const [daysFilter, setDaysFilter] = useState<string>("14");
  const queryClient = useQueryClient();

  const matchParams = { days: daysFilter };
  const { data: upcomingData, isLoading: upcomingLoading, refetch } = useListMatches(matchParams);
  const { data: recentData, isLoading: recentLoading } = useListRecentMatches();
  const { data: leaguesData } = useListLeagues();
  const syncMutation = useSyncFixtures();

  const isLoading = upcomingLoading;

  const upcoming = upcomingData?.matches ?? [];
  const recent = recentData?.matches ?? [];

  const allMatches = statusFilter === "completed" ? recent : upcoming.length > 0 ? upcoming : recent;
  const hasSynced = upcoming.length > 0 || recent.length > 0;
  const isSynthetic = hasSynced && !upcoming.some((m: any) => m.external_id);

  const leagues = leaguesData?.leagues ?? [
    ...new Set(allMatches.map((m) => m.league).filter(Boolean)),
  ].map((l: any) => typeof l === "string" ? { key: l, display: l } : l);

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
    if (statusFilter === "upcoming") return !m.actual_outcome;
    if (statusFilter === "live") return m.status === "live" || m.status === "IN_PLAY" || m.status === "LIVE";

    return true;
  });

  const liveCount = allMatches.filter((m) =>
    m.status === "live" || m.status === "IN_PLAY" || m.status === "LIVE"
  ).length;

  const handleSync = async () => {
    try {
      const result = await syncMutation.mutateAsync({ days: parseInt(daysFilter) });
      if (result.stored > 0) {
        toast.success(`Synced ${result.stored} new fixtures (${result.source})`);
      } else {
        toast.info("All fixtures already up to date");
      }
      queryClient.invalidateQueries({ queryKey: ["matches-upcoming"] });
      queryClient.invalidateQueries({ queryKey: ["matches-recent"] });
      refetch();
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
          <p className="text-muted-foreground font-mono text-sm">
            {upcoming.length > 0
              ? `${upcoming.length} upcoming fixtures loaded`
              : recent.length > 0
              ? `${recent.length} fixtures available`
              : "Real-time match data & ML consensus"}
            {liveCount > 0 && (
              <span className="ml-2 inline-flex items-center gap-1 text-green-400">
                <Radio className="w-3 h-3 animate-pulse" />
                {liveCount} live
              </span>
            )}
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

      {/* ── Synthetic data notice ────────────────────────── */}
      {isSynthetic && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30 border border-border/40 text-xs font-mono text-muted-foreground">
          <Info className="w-3.5 h-3.5 flex-shrink-0 text-yellow-500/70" />
          <span>Showing synthetic fixtures — configure <span className="font-semibold text-foreground/70">FOOTBALL_DATA_API_KEY</span> for real match data</span>
        </div>
      )}

      {/* ── Filters ─────────────────────────────────────── */}
      <div className="space-y-2">
        {/* Search — always full width */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search teams or league…"
            className="pl-9 font-mono bg-card/50"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {/* Filter row — three dropdowns */}
        <div className="flex gap-2">
          <Select value={leagueFilter} onValueChange={setLeagueFilter}>
            <SelectTrigger className="flex-1 font-mono bg-card/50 text-xs min-w-0">
              <SelectValue placeholder="All Leagues" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Leagues</SelectItem>
              {(Array.isArray(leagues) ? leagues : []).map((lg: any) => {
                const key = typeof lg === "string" ? lg : lg.key;
                const display = typeof lg === "string" ? lg : lg.display;
                return (
                  <SelectItem key={key} value={key}>{display}</SelectItem>
                );
              })}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="flex-1 font-mono bg-card/50 text-xs min-w-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Matches</SelectItem>
              <SelectItem value="upcoming">Upcoming</SelectItem>
              <SelectItem value="live">
                <span className="flex items-center gap-1.5">
                  <Radio className="w-3 h-3 text-green-400" /> Live
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
            <Skeleton key={i} className="h-64 rounded-xl" />
          ))}
        </div>
      ) : upcoming.length === 0 && recent.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-8 text-center space-y-4">
          <Clock className="w-10 h-10 text-muted-foreground mx-auto" />
          <p className="font-mono text-sm text-muted-foreground uppercase tracking-wider">No match data loaded yet.</p>
          <p className="font-mono text-xs text-muted-foreground max-w-sm mx-auto">
            Click "Sync Fixtures" to load upcoming matches for the next {daysFilter} days.
          </p>
          <Button
            size="sm"
            className="font-mono gap-2 mx-auto"
            onClick={handleSync}
            disabled={syncMutation.isPending}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
            {syncMutation.isPending ? "Loading fixtures..." : "Load Fixtures Now"}
          </Button>
        </div>
      ) : matches.length > 0 ? (
        <>
          {statusFilter !== "completed" && upcoming.length > 0 && (
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-primary" />
              <span className="font-mono text-xs text-muted-foreground uppercase tracking-widest">
                {statusFilter === "live" ? "Live Matches" : "Upcoming Fixtures"}
              </span>
              <Badge variant="outline" className="font-mono text-[10px]">{matches.length}</Badge>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {matches.map((match, i) => (
              <PremiumMatchCard key={`${match.match_id}-${i}`} match={match} />
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-lg border border-dashed border-border p-6 text-center space-y-2">
          <Search className="w-8 h-8 text-muted-foreground mx-auto" />
          <p className="font-mono text-sm text-muted-foreground">No matches for the selected filters.</p>
          <p className="font-mono text-xs text-muted-foreground/60">Try adjusting the league, status, or date range filter.</p>
        </div>
      )}
    </div>
  );
}
