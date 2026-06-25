/**
 * WatchlistPage — Shows all matches bookmarked by the user.
 *
 * Matches are stored in localStorage (via WatchlistProvider).
 * This page fetches the full list of matches then cross-references
 * the saved IDs to show enriched match cards.
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet }   from "@/lib/apiClient";
import { useWatchlist } from "@/lib/watchlist";
import { Link }     from "wouter";
import { Bookmark, Activity, ChevronRight, Trash2 } from "lucide-react";
import { Button }   from "@/components/ui/button";
import { Badge }    from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

// ── Status colour helper ─────────────────────────────────────────────────────
function statusColor(status: string) {
  if (status === "live")      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  if (status === "completed") return "bg-muted/30 text-muted-foreground border-border";
  return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
}

// ── Match card ───────────────────────────────────────────────────────────────
function WatchedMatchCard({ match, onRemove }: { match: any; onRemove: () => void }) {
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl border border-border/40 bg-card/40 hover:border-primary/25 hover:bg-card/60 transition-all group">
      <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
        <Activity className="w-4 h-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-mono font-semibold text-foreground truncate">
          {match.home_team} <span className="text-muted-foreground">vs</span> {match.away_team}
        </div>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className="text-[10px] font-mono text-muted-foreground">{match.competition || match.league || "Football"}</span>
          {match.kickoff_time && (
            <span className="text-[10px] font-mono text-muted-foreground/60">
              {new Date(match.kickoff_time).toLocaleDateString()}
            </span>
          )}
          <Badge className={`text-[9px] font-mono px-1.5 py-0 border ${statusColor(match.status)}`}>
            {match.status === "live" ? "● LIVE" : match.status?.toUpperCase() ?? "UPCOMING"}
          </Badge>
        </div>
        {match.status === "live" && match.home_goals != null && (
          <div className="mt-1.5 text-base font-bold font-mono text-foreground">
            {match.home_goals} – {match.away_goals}
          </div>
        )}
      </div>
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <Link href={`/matches/${match.match_id ?? match.id}`}>
          <Button variant="ghost" size="icon" className="h-7 w-7" aria-label="View match details">
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
          </Button>
        </Link>
        <Button
          variant="ghost" size="icon" className="h-7 w-7"
          onClick={onRemove}
          title="Remove from watchlist"
          aria-label="Remove from watchlist"
        >
          <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-rose-400 transition-colors" />
        </Button>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function WatchlistPage() {
  const { watchedIds, toggle } = useWatchlist();

  const { data: allMatchesData, isLoading } = useQuery<any>({
    queryKey: ["all-matches-watchlist"],
    queryFn:  () => apiGet<any>("/api/matches?limit=500"),
    staleTime: 30_000,
  });

  const allMatches: any[] = allMatchesData?.matches ?? allMatchesData ?? [];

  // Filter to only the bookmarked matches
  const watched = allMatches.filter((m: any) => watchedIds.includes(m.id));

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Page header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
            <Bookmark className="w-4.5 h-4.5 text-primary" style={{ width: 18, height: 18 }} />
          </div>
          <div>
            <h1 className="text-xl font-bold font-mono text-foreground">Watchlist</h1>
            <p className="text-xs font-mono text-muted-foreground">
              {watchedIds.length} saved match{watchedIds.length !== 1 ? "es" : ""}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-4 rounded-xl border border-border/30">
              <Skeleton className="w-9 h-9 rounded-lg" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-48" />
                <Skeleton className="h-2 w-24" />
              </div>
            </div>
          ))}
        </div>
      ) : watchedIds.length === 0 ? (
        <div className="text-center py-16">
          <Bookmark className="w-12 h-12 text-muted-foreground/20 mx-auto mb-4" />
          <h3 className="text-base font-bold font-mono text-foreground mb-2">No saved matches</h3>
          <p className="text-sm font-mono text-muted-foreground mb-6">
            Tap the bookmark icon on any match card to save it here for quick access.
          </p>
          <Link href="/matches">
            <Button variant="outline" className="font-mono text-xs">
              Browse Matches
            </Button>
          </Link>
        </div>
      ) : watched.length === 0 && watchedIds.length > 0 ? (
        /* IDs saved but no matching data (old/expired matches) */
        <div className="space-y-2">
          {watchedIds.map((id) => (
            <div key={id} className="flex items-center justify-between p-4 rounded-xl border border-border/30 bg-card/30">
              <span className="text-xs font-mono text-muted-foreground">Match #{id}</span>
              <Button variant="ghost" size="sm" onClick={() => toggle(id)} className="font-mono text-xs text-rose-400 hover:text-rose-300">
                Remove
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {watched.map((m: any) => (
            <WatchedMatchCard key={m.id} match={m} onRemove={() => toggle(m.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
