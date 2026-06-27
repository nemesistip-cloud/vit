/**
 * AllocationCalculatorModal — Quick Capital Allocation Strategy stake calculator.
 *
 * The Capital Allocation Strategy answers: "What fraction of my bankroll should I stake
 * to maximise long-run growth?" given:
 *   f* = (bp - q) / b
 *   where b = decimal_odds - 1, p = win_probability, q = 1 - p
 *
 * Also calls the backend /api/bankroll/kelly endpoint for the server's
 * recommendation (which respects the user's configured max-stake limit).
 *
 * Usage:
 *   import { AllocationCalculatorModal, AllocationFAB } from "@/components/kelly-calculator-modal";
 *   <AllocationCalculatorModal />   — place once near root
 *   <AllocationFAB />               — floating trigger button
 *   openAllocationCalculator()      — programmatic open (e.g. from prediction card)
 */

import { useEffect, useRef, useState } from "react";
import { apiPost } from "@/lib/apiClient";
import { Calculator, X, TrendingUp, AlertTriangle, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// ── Module-level open/close signal ──────────────────────────────────────────
let _setOpen: ((v: boolean) => void) | null = null;
export function openAllocationCalculator() { _setOpen?.(true); }

// ── Local allocation formula (instant feedback without a network round-trip) ───────
function localKelly(winProb: number, decimalOdds: number): number {
  const b = decimalOdds - 1;
  const p = winProb / 100;
  const q = 1 - p;
  const f = (b * p - q) / b;
  return Math.max(0, Math.round(f * 100 * 100) / 100); // percentage, 2dp
}

// ── Confidence level badge ───────────────────────────────────────────────────
function ConfidenceBadge({ stake }: { stake: number }) {
  if (stake === 0)  return <span className="text-rose-400 text-[10px] font-mono">No edge — skip this signal</span>;
  if (stake <= 2)   return <span className="text-yellow-400 text-[10px] font-mono">Low edge — small stake only</span>;
  if (stake <= 7)   return <span className="text-emerald-400 text-[10px] font-mono">Good edge — confident signal</span>;
  return               <span className="text-primary text-[10px] font-mono">Very high edge — consider full Kelly</span>;
}

// ── Main modal ───────────────────────────────────────────────────────────────
export function AllocationCalculatorModal() {
  const [open, setOpen]             = useState(false);
  const [prob, setProb]             = useState(55);        // Win probability %
  const [odds, setOdds]             = useState("2.10");   // Decimal odds string
  const [bankroll, setBankroll]     = useState("1000");   // Bankroll amount
  const [serverResult, setServer]   = useState<any>(null);
  const [loading, setLoading]       = useState(false);

  useEffect(() => { _setOpen = setOpen; return () => { _setOpen = null; }; }, []);
  useEffect(() => {
    if (!open) { setServer(null); }
  }, [open]);

  const decimalOdds = parseFloat(odds) || 0;
  const bankrollAmt = parseFloat(bankroll) || 1000;

  const localStakePct  = localKelly(prob, decimalOdds);
  const halfKelly      = Math.round(localStakePct / 2 * 100) / 100;
  const localStakeAmt  = Math.round((localStakePct / 100) * bankrollAmt * 100) / 100;
  const potentialProfit = Math.round(((decimalOdds - 1) * localStakeAmt) * 100) / 100;

  const impliedProb = decimalOdds > 0 ? Math.round((1 / decimalOdds) * 10000) / 100 : 0;
  const edge = Math.round((prob - impliedProb) * 100) / 100;

  const fetchServer = async () => {
    if (decimalOdds < 1.01) return;
    setLoading(true);
    try {
      const r = await apiPost<any>("/api/bankroll/kelly", {
        win_probability: prob / 100,
        decimal_odds: decimalOdds,
        bankroll: bankrollAmt,
      });
      setServer(r);
    } catch {
      // Silently ignore — local formula is still shown
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
      style={{ background: "rgba(0,0,0,0.85)" }}
    >
      <div
        className="w-full max-w-sm rounded-xl border border-white/10  overflow-hidden"
        style={{ background: "var(--vit-gradient-card)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/8">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/15 border border-primary/25 flex items-center justify-center">
              <Calculator className="w-4 h-4 text-primary" />
            </div>
            <div>
              <div className="text-sm font-bold font-mono text-foreground">Allocation Optimizer</div>
              <div className="text-[10px] font-mono text-muted-foreground">Optimal stake sizing</div>
            </div>
          </div>
          <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-white/5 transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-5">
          {/* Win Probability slider */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Win Probability</label>
              <span className="text-sm font-bold font-mono text-primary">{prob}%</span>
            </div>
            <Slider
              value={[prob]}
              onValueChange={([v]) => setProb(v)}
              min={1} max={99} step={1}
              className="w-full"
            />
            <div className="flex justify-between mt-1">
              <span className="text-[9px] font-mono text-muted-foreground/40">1%</span>
              <span className="text-[9px] font-mono text-muted-foreground/40">99%</span>
            </div>
          </div>

          {/* Decimal Odds & Bankroll inputs */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-1.5">
                Decimal Odds
              </label>
              <input
                type="number" step="0.01" min="1.01"
                value={odds}
                onChange={(e) => setOdds(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-foreground outline-none focus:border-primary/40 focus:bg-white/8 transition-all"
                placeholder="e.g. 2.10"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-1.5">
                Bankroll (VIT)
              </label>
              <input
                type="number" min="1"
                value={bankroll}
                onChange={(e) => setBankroll(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-foreground outline-none focus:border-primary/40 focus:bg-white/8 transition-all"
                placeholder="1000"
              />
            </div>
          </div>

          {/* Edge indicator */}
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${edge > 0 ? "bg-emerald-500/5 border-emerald-500/20" : "bg-rose-500/5 border-rose-500/20"}`}>
            {edge > 0
              ? <TrendingUp className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
              : <AlertTriangle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
            }
            <span className="text-[10px] font-mono text-muted-foreground">
              Implied prob: <span className="text-foreground">{impliedProb}%</span> ·
              Your edge: <span className={edge > 0 ? "text-emerald-400" : "text-rose-400"}>{edge > 0 ? "+" : ""}{edge}%</span>
            </span>
          </div>

          {/* Results */}
          <div className="rounded-xl bg-primary/5 border border-primary/15 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground">Full Kelly</span>
              <span className={`text-xl font-bold font-mono ${localStakePct > 0 ? "text-primary" : "text-rose-400"}`}>
                {localStakePct}%
              </span>
            </div>
            {localStakePct > 0 && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground">½ Kelly (recommended)</span>
                  <span className="text-sm font-bold font-mono text-secondary">{halfKelly}%</span>
                </div>
                <div className="h-px bg-white/5" />
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground">Stake amount</span>
                  <span className="text-sm font-bold font-mono text-foreground">{localStakeAmt.toLocaleString()} VIT</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground">Potential profit</span>
                  <span className="text-sm font-bold font-mono text-emerald-400">+{potentialProfit.toLocaleString()} VIT</span>
                </div>
              </>
            )}
            <ConfidenceBadge stake={localStakePct} />
          </div>

          {/* Server validation button */}
          <div className="flex items-center gap-2">
            <Button
              onClick={fetchServer}
              disabled={loading || decimalOdds < 1.01}
              size="sm"
              variant="outline"
              className="flex-1 font-mono text-xs gap-1.5"
            >
              {loading ? "Checking…" : "Validate with VIT API"}
            </Button>
            {serverResult && (
              <div className="flex items-center gap-1 text-[10px] font-mono text-emerald-400">
                <Info className="w-3 h-3" />
                API: {serverResult.kelly_stake_pct ?? serverResult.recommended_pct ?? "—"}%
              </div>
            )}
          </div>

          <p className="text-[9px] font-mono text-muted-foreground/40 leading-relaxed">
            Half Kelly reduces variance while capturing ~75% of optimal growth. Never deploy more than you can afford to lose.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Floating trigger button ──────────────────────────────────────────────────
export function AllocationFAB() {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={openAllocationCalculator}
          aria-label="Allocation Optimizer (stake sizing)"
          className="fixed bottom-24 right-5 z-50 lg:bottom-6 w-11 h-11 rounded-full bg-gradient-to-br from-primary/80 to-purple-500/80  border border-primary/40 flex items-center justify-center hover:scale-105 active:scale-95 transition-transform shadow-lg"
        >
          <Calculator className="w-4.5 h-4.5 text-primary-foreground" style={{ width: 18, height: 18 }} />
        </button>
      </TooltipTrigger>
      <TooltipContent side="left">
        Allocation Optimizer (Stake Sizing)
      </TooltipContent>
    </Tooltip>
  );
}
