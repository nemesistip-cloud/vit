/**
 * GlobalSearch — Cmd/Ctrl+K command palette for searching matches, pages, and features.
 *
 * Opens a modal with a fuzzy-search input. Results include:
 *  - Live / upcoming matches (fetched from /api/matches)
 *  - Static navigation shortcuts (Predictions, Wallet, Analytics, etc.)
 *
 * Usage: place <GlobalSearchTrigger /> anywhere in the layout header, and
 * <GlobalSearch /> once at the root so the keyboard shortcut always works.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useQuery }  from "@tanstack/react-query";
import { useLocation } from "wouter";
import { apiGet }    from "@/lib/apiClient";
import {
  Search, X, Activity, BarChart2, Coins, CheckSquare,
  ShoppingBag, Brain, Trophy, Zap, Target,
} from "lucide-react";

// ── Static navigation shortcuts shown when search input is empty ─────────────
const SHORTCUTS = [
  { label: "Dashboard",   href: "/dashboard",   icon: Activity  },
  { label: "Matches",     href: "/matches",      icon: Activity  },
  { label: "Predictions", href: "/predictions",  icon: CheckSquare },
  { label: "Wallet",      href: "/wallet",       icon: Coins     },
  { label: "Analytics",   href: "/analytics",    icon: BarChart2 },
  { label: "Marketplace", href: "/marketplace",  icon: ShoppingBag },
  { label: "Leaderboard", href: "/leaderboard",  icon: Trophy    },
  { label: "AI Assistant",href: "/assistant",    icon: Brain     },
  { label: "Earn Offers", href: "/earn",         icon: Zap       },
  { label: "Bankroll",    href: "/bankroll",     icon: Target    },
];

// ── Shared open/close state (module-level so both components share it) ───────
let _setOpen: ((v: boolean) => void) | null = null;
export function openGlobalSearch() { _setOpen?.(true); }

// ── Keyboard shortcut (Cmd/Ctrl + K) ────────────────────────────────────────
function useSearchShortcut(open: boolean, setOpen: (v: boolean) => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(!open);
      }
      if (e.key === "Escape" && open) setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, setOpen]);
}

// ── Match search result item ─────────────────────────────────────────────────
function MatchResult({ match, onClick }: { match: any; onClick: () => void }) {
  const [, navigate] = useLocation();
  const statusColor =
    match.status === "live"      ? "text-emerald-400" :
    match.status === "completed" ? "text-muted-foreground" :
    "text-yellow-400";

  return (
    <button
      onClick={() => { navigate(`/matches/${match.id}`); onClick(); }}
      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-primary/8 transition-colors text-left group"
    >
      <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
        <Activity className="w-3.5 h-3.5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-mono font-medium text-foreground truncate group-hover:text-primary transition-colors">
          {match.home_team} <span className="text-muted-foreground">vs</span> {match.away_team}
        </div>
        <div className="text-[10px] font-mono text-muted-foreground mt-0.5 truncate">
          {match.competition || match.league || "Football"} · <span className={statusColor}>{match.status}</span>
        </div>
      </div>
      <span className="text-[10px] font-mono text-primary/50 group-hover:text-primary transition-colors opacity-0 group-hover:opacity-100">
        Open →
      </span>
    </button>
  );
}

// ── Shortcut item ────────────────────────────────────────────────────────────
function ShortcutItem({ item, onClick }: { item: typeof SHORTCUTS[0]; onClick: () => void }) {
  const [, navigate] = useLocation();
  return (
    <button
      onClick={() => { navigate(item.href); onClick(); }}
      className="w-full flex items-center gap-3 px-4 py-2 hover:bg-primary/8 transition-colors text-left group"
    >
      <div className="w-6 h-6 rounded-md bg-muted/40 flex items-center justify-center flex-shrink-0">
        <item.icon className="w-3 h-3 text-muted-foreground group-hover:text-primary transition-colors" />
      </div>
      <span className="text-xs font-mono text-muted-foreground group-hover:text-foreground transition-colors">
        {item.label}
      </span>
    </button>
  );
}

// ── Main modal component ─────────────────────────────────────────────────────
export function GlobalSearch() {
  const [open, setOpen]   = useState(false);
  const [query, setQuery] = useState("");
  const inputRef          = useRef<HTMLInputElement>(null);

  // Register module-level setter so openGlobalSearch() works from anywhere
  useEffect(() => { _setOpen = setOpen; return () => { _setOpen = null; }; }, [setOpen]);

  useSearchShortcut(open, setOpen);

  // Focus input when modal opens
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
    else setQuery("");
  }, [open]);

  // Fetch matches for search results (stale for 60s — we don't need live updates here)
  const { data: matchesData } = useQuery<any>({
    queryKey: ["search-matches"],
    queryFn:  () => apiGet<any>("/api/matches?limit=200"),
    staleTime: 60_000,
    enabled: open,
  });

  const allMatches: any[] = matchesData?.matches ?? matchesData ?? [];

  // Client-side fuzzy filter on team names and competition
  const filtered = query.trim().length < 2
    ? []
    : allMatches.filter((m: any) => {
        const q = query.toLowerCase();
        return (
          m.home_team?.toLowerCase().includes(q) ||
          m.away_team?.toLowerCase().includes(q) ||
          m.competition?.toLowerCase().includes(q) ||
          m.league?.toLowerCase().includes(q)
        );
      }).slice(0, 8);

  const filteredShortcuts = query.trim().length < 2
    ? SHORTCUTS
    : SHORTCUTS.filter(s => s.label.toLowerCase().includes(query.toLowerCase()));

  const close = useCallback(() => { setOpen(false); setQuery(""); }, []);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] px-4"
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
      style={{ background: "rgba(0,0,0,0.82)" }}
    >
      <div
        className="w-full max-w-lg rounded-xl border border-white/10 shadow-2xl overflow-hidden"
        style={{ background: "var(--vit-gradient-card)" }}
      >
        {/* Search input bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/8">
          <Search className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search matches, teams, pages…"
            className="flex-1 bg-transparent text-sm font-mono text-foreground placeholder:text-muted-foreground/50 outline-none"
          />
          <div className="flex items-center gap-1.5">
            {query && (
              <button onClick={() => setQuery("")} className="p-1 rounded-md hover:bg-white/5 transition-colors">
                <X className="w-3.5 h-3.5 text-muted-foreground" />
              </button>
            )}
            <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono text-muted-foreground/50 border border-white/10 bg-white/3">
              esc
            </kbd>
          </div>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto vit-scrollbar py-1">
          {/* Match results */}
          {filtered.length > 0 && (
            <div>
              <div className="px-4 py-1.5 text-[10px] font-mono uppercase tracking-widest text-muted-foreground/50">
                Matches
              </div>
              {filtered.map((m: any) => (
                <MatchResult key={m.id} match={m} onClick={close} />
              ))}
            </div>
          )}

          {/* Navigation shortcuts */}
          {filteredShortcuts.length > 0 && (
            <div>
              <div className="px-4 py-1.5 text-[10px] font-mono uppercase tracking-widest text-muted-foreground/50">
                {query ? "Pages" : "Quick Navigation"}
              </div>
              {filteredShortcuts.map((s) => (
                <ShortcutItem key={s.href} item={s} onClick={close} />
              ))}
            </div>
          )}

          {/* Empty state */}
          {query.length >= 2 && filtered.length === 0 && filteredShortcuts.length === 0 && (
            <div className="px-4 py-8 text-center">
              <Search className="w-8 h-8 text-muted-foreground/20 mx-auto mb-2" />
              <p className="text-xs font-mono text-muted-foreground">No results for "{query}"</p>
            </div>
          )}
        </div>

        {/* Footer hint */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-white/5 bg-white/2">
          <span className="text-[10px] font-mono text-muted-foreground/40">
            ↑↓ navigate · Enter select · Esc close
          </span>
          <span className="text-[10px] font-mono text-muted-foreground/40">
            <kbd className="px-1 py-0.5 rounded border border-white/10 bg-white/3">⌘K</kbd>
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Trigger button (for layout header) ──────────────────────────────────────
export function GlobalSearchTrigger() {
  return (
    <button
      onClick={openGlobalSearch}
      className="flex items-center gap-2 h-7 px-2.5 rounded-md border border-white/10 bg-white/3 hover:bg-white/6 hover:border-white/15 transition-all text-muted-foreground hover:text-foreground group"
      aria-label="Search (⌘K)"
    >
      <Search className="w-3 h-3" />
      <span className="hidden sm:inline text-[10px] font-mono">Search</span>
      <kbd className="hidden sm:inline-flex items-center px-1 py-0.5 rounded text-[9px] font-mono border border-white/10 bg-white/3 ml-1">
        ⌘K
      </kbd>
    </button>
  );
}
