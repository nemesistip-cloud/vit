/**
 * BetSlip — Slide-up accumulator builder panel.
 *
 * Users add predictions/matches to the slip from anywhere in the app.
 * The slip calculates combined odds and potential payout in real time.
 *
 * State is kept in a React context (module-level singleton) so any component
 * can call addToBetSlip({ matchId, match, pick, odds }) without prop-drilling.
 *
 * Usage:
 *   // Anywhere in the app:
 *   import { addToBetSlip } from "@/components/bet-slip";
 *   addToBetSlip({ matchId: 42, match: "Arsenal vs Chelsea", pick: "home", odds: 1.85 });
 *
 *   // Once at root (shows the panel + FAB):
 *   <BetSlipPanel />
 */

import { createContext, useCallback, useContext, useMemo, useReducer } from "react";
import { X, Trash2, ChevronUp, ChevronDown, Layers } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

// ── Types ────────────────────────────────────────────────────────────────────

export interface BetSlipItem {
  matchId: number;
  match:   string;         // "Team A vs Team B"
  pick:    string;         // "home" | "draw" | "away" | custom label
  odds:    number;         // Decimal odds for this selection
}

// ── Module-level add function (callable from any component) ──────────────────

let _dispatch: React.Dispatch<Action> | null = null;

export function addToBetSlip(item: BetSlipItem) {
  _dispatch?.({ type: "ADD", item });
}
export function removeFromBetSlip(matchId: number) {
  _dispatch?.({ type: "REMOVE", matchId });
}
export function clearBetSlip() {
  _dispatch?.({ type: "CLEAR" });
}

// ── Reducer ──────────────────────────────────────────────────────────────────

type Action =
  | { type: "ADD";    item: BetSlipItem }
  | { type: "REMOVE"; matchId: number }
  | { type: "CLEAR" };

function reducer(state: BetSlipItem[], action: Action): BetSlipItem[] {
  switch (action.type) {
    case "ADD":
      // Replace if same match already in slip, otherwise append
      return state.some((s) => s.matchId === action.item.matchId)
        ? state.map((s) => s.matchId === action.item.matchId ? action.item : s)
        : [...state, action.item];
    case "REMOVE":
      return state.filter((s) => s.matchId !== action.matchId);
    case "CLEAR":
      return [];
  }
}

// ── Context ──────────────────────────────────────────────────────────────────

const BetSlipContext = createContext<{ items: BetSlipItem[] }>({ items: [] });
export function useBetSlip() { return useContext(BetSlipContext); }

// ── Pick label formatter ─────────────────────────────────────────────────────
function pickLabel(pick: string) {
  if (pick === "home") return "1";
  if (pick === "draw") return "X";
  if (pick === "away") return "2";
  return pick.toUpperCase();
}

// ── Bet Slip Panel ───────────────────────────────────────────────────────────
export function BetSlipPanel() {
  const [items, dispatch] = useReducer(reducer, []);
  const [open, setOpen]   = useState(false);
  const [stake, setStake] = useState("100");

  // Register dispatch globally so addToBetSlip() works from anywhere.
  // dispatch from useReducer is referentially stable, so this runs exactly once.
  useEffect(() => {
    _dispatch = dispatch;
    return () => { _dispatch = null as any; };
  }, [dispatch]);

  const combinedOdds = useMemo(
    () => items.reduce((acc, i) => acc * i.odds, 1),
    [items]
  );
  const stakeAmt      = parseFloat(stake) || 0;
  const potentialWin  = Math.round(combinedOdds * stakeAmt * 100) / 100;
  const profit        = Math.round((potentialWin - stakeAmt) * 100) / 100;

  const hasItems = items.length > 0;

  return (
    <BetSlipContext.Provider value={{ items }}>
      {/* FAB — fixed bottom-right */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-24 left-5 z-50 lg:bottom-6 flex items-center gap-1.5 h-10 px-3 rounded-full bg-gradient-to-r from-secondary/80 to-yellow-500/60 shadow-lg border border-secondary/40 hover:scale-105 active:scale-95 transition-transform font-mono text-xs font-bold text-black"
        title="Bet Slip"
      >
        <Layers className="w-4 h-4" />
        <span>Slip</span>
        {hasItems && (
          <span className="w-4 h-4 rounded-full bg-black/30 text-[9px] flex items-center justify-center">
            {items.length}
          </span>
        )}
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-[4.5rem] left-2 right-2 lg:left-auto lg:right-6 lg:bottom-20 lg:w-80 z-50 rounded-xl border border-white/10 shadow-2xl overflow-hidden"
          style={{ background: "var(--vit-gradient-card)" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/8">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-secondary" />
              <span className="text-sm font-bold font-mono text-foreground">Bet Slip</span>
              {hasItems && (
                <span className="text-[10px] font-mono text-secondary bg-secondary/10 px-1.5 py-0.5 rounded border border-secondary/20">
                  {items.length} sel.
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              {hasItems && (
                <button
                  onClick={() => dispatch({ type: "CLEAR" })}
                  className="text-[10px] font-mono text-muted-foreground hover:text-rose-400 transition-colors"
                >
                  Clear all
                </button>
              )}
              <button onClick={() => setOpen(false)} className="p-1 rounded hover:bg-white/5 transition-colors">
                <X className="w-3.5 h-3.5 text-muted-foreground" />
              </button>
            </div>
          </div>

          {/* Selections */}
          <div className="max-h-48 overflow-y-auto vit-scrollbar">
            {!hasItems ? (
              <div className="px-4 py-8 text-center">
                <Layers className="w-8 h-8 text-muted-foreground/20 mx-auto mb-2" />
                <p className="text-xs font-mono text-muted-foreground">
                  No selections yet. Add predictions to build an accumulator.
                </p>
              </div>
            ) : (
              items.map((item) => (
                <div key={item.matchId} className="flex items-center gap-3 px-4 py-2.5 border-b border-white/5 last:border-0">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-mono text-foreground truncate">{item.match}</div>
                    <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
                      Pick: <span className="text-secondary font-bold">{pickLabel(item.pick)}</span>
                      <span className="ml-2 text-foreground">{item.odds.toFixed(2)}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => dispatch({ type: "REMOVE", matchId: item.matchId })}
                    className="p-1 rounded hover:bg-white/5 transition-colors flex-shrink-0"
                  >
                    <Trash2 className="w-3 h-3 text-muted-foreground hover:text-rose-400 transition-colors" />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Footer — stake + payout */}
          {hasItems && (
            <div className="px-4 py-3 border-t border-white/8 space-y-3">
              <div className="flex items-center gap-3">
                <label className="text-[10px] font-mono text-muted-foreground flex-shrink-0">Stake (VIT)</label>
                <input
                  type="number" min="1"
                  value={stake}
                  onChange={(e) => setStake(e.target.value)}
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs font-mono text-foreground outline-none focus:border-primary/40 transition-all text-right"
                />
              </div>
              <div className="rounded-lg bg-primary/5 border border-primary/15 px-3 py-2.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-muted-foreground">Combined odds</span>
                  <span className="text-xs font-bold font-mono text-primary">{combinedOdds.toFixed(2)}x</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-muted-foreground">Potential win</span>
                  <span className="text-xs font-bold font-mono text-emerald-400">{potentialWin.toLocaleString()} VIT</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-muted-foreground">Profit</span>
                  <span className="text-xs font-bold font-mono text-emerald-400">+{profit.toLocaleString()} VIT</span>
                </div>
              </div>
              <Button
                size="sm"
                className="w-full font-mono text-xs font-bold bg-gradient-to-r from-secondary to-yellow-500 text-black hover:opacity-90 border-0"
                onClick={() => { alert("Connect wallet to place accumulator bets. Feature coming soon!"); }}
              >
                Place Accumulator ({items.length} selections)
              </Button>
            </div>
          )}
        </div>
      )}
    </BetSlipContext.Provider>
  );
}
