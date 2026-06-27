/**
 * VIT Network — Intelligence Slip & Accumulator Manager
 * Provides global state for selections and a floating panel for placement.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useState } from "react";
import { X, Trash2, ChevronUp, ChevronDown, Layers, Wallet, ExternalLink, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";
import { apiPost } from "@/lib/apiClient";

// ── Types ────────────────────────────────────────────────────────────────────

export interface IntelligenceSlipItem {
  matchId: number;
  match:   string;         // "Team A vs Team B"
  pick:    string;         // "home" | "draw" | "away" | custom label
  odds:    number;         // Decimal odds for this selection
}

// ── Module-level add function (callable from any component) ──────────────────

let _dispatch: React.Dispatch<Action> | null = null;

export function addToBetSlip(item: IntelligenceSlipItem) {
  _dispatch?.({ type: "ADD", item });
  toast.success(`Added ${item.match} to slip`);
}
export function removeFromBetSlip(matchId: number) {
  _dispatch?.({ type: "REMOVE", matchId });
}
export function clearBetSlip() {
  _dispatch?.({ type: "CLEAR" });
}

// ── Reducer ──────────────────────────────────────────────────────────────────

type Action =
  | { type: "ADD";    item: IntelligenceSlipItem }
  | { type: "REMOVE"; matchId: number }
  | { type: "CLEAR" };

function reducer(state: IntelligenceSlipItem[], action: Action): IntelligenceSlipItem[] {
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

const BetSlipContext = createContext<{ items: IntelligenceSlipItem[] }>({ items: [] });
export function useBetSlip() { return useContext(BetSlipContext); }

// ── Pick label formatter ─────────────────────────────────────────────────────
function pickLabel(pick: string) {
  if (pick === "home") return "1";
  if (pick === "draw") return "X";
  if (pick === "away") return "2";
  return pick.toUpperCase();
}

// ── Intelligence Slip Panel ───────────────────────────────────────────────────────────
export function BetSlipPanel() {
  const [items, dispatch] = useReducer(reducer, []);
  const [open, setOpen]   = useState(false);
  const [stake, setStake] = useState("100");
  const [isPlacing, setIsPlacing] = useState(false);

  // Register dispatch globally so addToBetSlip() works from anywhere.
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

  const handlePlaceAccumulator = async () => {
    if (items.length === 0) return;
    setIsPlacing(true);
    try {
      const payload = {
        provider: "betway", // Defaulting to betway, could be a selector
        selections: items.map(i => ({
          match_id: i.matchId,
          selection: i.pick
        }))
      };

      const res = await apiPost("/api/predictions/generate-slip", payload);
      if (res.redirect_url) {
        toast.success("Slip generated! Redirecting to bookmaker...");
        window.open(res.redirect_url, "_blank");
      } else {
        throw new Error("No redirect URL received");
      }
    } catch (err) {
      console.error("Accumulator placement failed:", err);
      toast.error("Failed to generate betting slip. Please try again.");
    } finally {
      setIsPlacing(false);
    }
  };

  return (
    <BetSlipContext.Provider value={{ items }}>
      {/* FAB — fixed bottom-right */}
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={() => setOpen((v) => !v)}
            className="fixed bottom-24 left-5 z-50 lg:bottom-6 flex items-center gap-1.5 h-10 px-3 rounded-full bg-gradient-to-r from-secondary/80 to-yellow-500/60  border border-secondary/40 hover:scale-105 active:scale-95 transition-transform font-mono text-xs font-bold text-black shadow-lg"
            aria-label={`Intelligence Slip${hasItems ? `, ${items.length} selections` : ""}`}
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
        </TooltipTrigger>
        <TooltipContent side="right">
          Intelligence Slip {hasItems ? `(${items.length} selections)` : "(Empty)"}
        </TooltipContent>
      </Tooltip>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-[4.5rem] left-2 right-2 lg:left-auto lg:right-6 lg:bottom-20 lg:w-80 z-50 rounded-xl border border-white/10 overflow-hidden shadow-2xl animate-in slide-in-from-bottom-4 duration-300"
          style={{ background: "rgba(10, 10, 15, 0.95)", backdropFilter: "blur(20px)" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/8">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-secondary" />
              <span className="text-sm font-bold font-mono text-foreground">Intelligence Slip</span>
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
          <div className="max-h-64 overflow-y-auto vit-scrollbar">
            {!hasItems ? (
              <div className="px-4 py-12 text-center">
                <Layers className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
                <p className="text-xs font-mono text-muted-foreground">
                  No selections yet.<br/>Add predictions to build an accumulator.
                </p>
              </div>
            ) : (
              items.map((item) => (
                <div key={item.matchId} className="flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-mono font-bold text-foreground truncate">{item.match}</div>
                    <div className="text-[10px] font-mono text-muted-foreground mt-1 flex items-center gap-2">
                      <span className="bg-white/5 px-1.5 py-0.5 rounded">Pick: <span className="text-secondary font-bold">{pickLabel(item.pick)}</span></span>
                      <span className="text-foreground/70">@ {item.odds.toFixed(2)}</span>
                    </div>
                  </div>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => dispatch({ type: "REMOVE", matchId: item.matchId })}
                        className="p-1.5 rounded-lg hover:bg-rose-500/10 transition-colors flex-shrink-0"
                        aria-label="Remove selection"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-rose-400 transition-colors" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Remove selection</TooltipContent>
                  </Tooltip>
                </div>
              ))
            )}
          </div>

          {/* Footer — stake + payout */}
          {hasItems && (
            <div className="px-4 py-4 border-t border-white/8 space-y-4 bg-white/[0.01]">
              <div className="flex items-center gap-3">
                <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider flex-shrink-0">Stake (VIT)</label>
                <input
                  type="number" min="1"
                  value={stake}
                  onChange={(e) => setStake(e.target.value)}
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-foreground outline-none focus:border-secondary/40 transition-all text-right"
                />
              </div>
              <div className="rounded-xl bg-secondary/5 border border-secondary/15 px-4 py-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase">Combined odds</span>
                  <span className="text-xs font-bold font-mono text-secondary">{combinedOdds.toFixed(2)}x</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase">Potential win</span>
                  <span className="text-sm font-bold font-mono text-emerald-400">{potentialWin.toLocaleString()} VIT</span>
                </div>
              </div>
              <Button
                size="sm"
                onClick={handlePlaceAccumulator}
                disabled={isPlacing}
                className="w-full font-mono text-xs font-bold bg-gradient-to-r from-secondary to-yellow-500 hover:from-secondary/90 hover:to-yellow-500/90 text-black border-0 h-10 shadow-[0_0_15px_rgba(212,175,55,0.2)]"
              >
                {isPlacing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <ExternalLink className="w-3.5 h-3.5 mr-2" />
                    Place Accumulator
                  </>
                )}
              </Button>
              <p className="text-[9px] text-center text-muted-foreground font-mono">
                Redirects to bookmaker via affiliate link
              </p>
            </div>
          )}
        </div>
      )}
    </BetSlipContext.Provider>
  );
}
