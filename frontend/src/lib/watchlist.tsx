/**
 * Watchlist context — persists bookmarked match IDs in localStorage.
 *
 * Wrap the app once with <WatchlistProvider>.
 * Consume with useWatchlist() anywhere in the tree.
 *
 * API:
 *   isWatched(id)   → boolean
 *   toggle(id)      → void     (add if absent, remove if present)
 *   watchedIds      → number[] (sorted newest-first)
 *   count           → number
 */

import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";

const STORAGE_KEY = "vit_watchlist_v1";

interface WatchlistContextType {
  watchedIds:  number[];
  count:       number;
  isWatched:   (id: number) => boolean;
  toggle:      (id: number) => void;
}

const WatchlistContext = createContext<WatchlistContextType>({
  watchedIds:  [],
  count:       0,
  isWatched:   () => false,
  toggle:      () => {},
});

function loadIds(): number[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as number[];
  } catch {
    return [];
  }
}

export function WatchlistProvider({ children }: { children: React.ReactNode }) {
  const [ids, setIds] = useState<number[]>(loadIds);

  // Persist to localStorage whenever the list changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  }, [ids]);

  const isWatched = useCallback((id: number) => ids.includes(id), [ids]);

  const toggle = useCallback((id: number) => {
    setIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [id, ...prev]
    );
  }, []);

  const value = useMemo(() => ({
    watchedIds: ids,
    count:      ids.length,
    isWatched,
    toggle,
  }), [ids, isWatched, toggle]);

  return (
    <WatchlistContext.Provider value={value}>
      {children}
    </WatchlistContext.Provider>
  );
}

export function useWatchlist() {
  return useContext(WatchlistContext);
}
