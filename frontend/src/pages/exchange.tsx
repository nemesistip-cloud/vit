import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import {
  TrendingUp, Activity, BarChart2, Zap, ArrowRight,
  ArrowUpRight, ArrowDownRight, RefreshCw, Layers,
  Wallet, Landmark, ShieldCheck, Search,
  Trophy, Shield, Clock, AlertTriangle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

const TIER_CONFIG: Record<string, { color: string; bg: string; label: string; icon: typeof Zap }> = {
  ELITE:     { color: "text-yellow-300",   bg: "bg-yellow-400/10 border-yellow-400/30",   label: "ELITE",     icon: Trophy },
  STRONG:    { color: "text-emerald-400",  bg: "bg-emerald-500/10 border-emerald-500/30", label: "STRONG",    icon: TrendingUp },
  SOLID:     { color: "text-blue-400",     bg: "bg-blue-500/10 border-blue-500/30",       label: "SOLID",     icon: Shield },
  WATCHLIST: { color: "text-amber-400",    bg: "bg-amber-500/10 border-amber-500/30",     label: "WATCHLIST", icon: Clock },
  SKIP:      { color: "text-vit-text-3",   bg: "bg-muted/10 border-border",               label: "SKIP",      icon: AlertTriangle },
};

interface VITPrediction {
  prediction_id: number;
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff_time: string | null;
  actual_outcome: string | null;
  home_prob: number;
  draw_prob: number;
  away_prob: number;
  bet_side: string;
  entry_odds: number;
  edge: number;
  confidence: number;
  recommended_stake: number;
  agreement_pct: number;
  vit_score: number;
  vit_tier: string;
  vit_components: { value: number; analytics: number; trust: number };
  has_market_odds: boolean;
  prediction_age_hours: number;
  timestamp: string | null;
}

interface VITFeedResponse {
  total: number;
  tier_counts: Record<string, number>;
  predictions: VITPrediction[];
}

function TierBadge({ tier }: { tier: string }) {
  const cfg = TIER_CONFIG[tier] || TIER_CONFIG.SKIP;
  const Icon = cfg.icon;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase border", cfg.bg, cfg.color)}>
      <Icon size={9} />
      {cfg.label}
    </span>
  );
}

function SideLabel({ side, teams }: { side: string; teams: { home: string; away: string } }) {
  if (side === "home") return <span className="text-emerald-400 font-bold">{teams.home}</span>;
  if (side === "away") return <span className="text-rose-400 font-bold">{teams.away}</span>;
  return <span className="text-amber-400 font-bold">Draw</span>;
}

function SignalCard({ prediction, onEnter }: { prediction: VITPrediction; onEnter: (p: VITPrediction) => void }) {
  const cfg = TIER_CONFIG[prediction.vit_tier] || TIER_CONFIG.SKIP;
  const kickoffStr = prediction.kickoff_time
    ? safeFormatDistanceToNow(prediction.kickoff_time, { addSuffix: true })
    : "TBD";

  return (
    <div className={cn(
      "p-4 border-b border-vit-border hover:bg-vit-surface-2 transition-colors cursor-pointer group",
    )} onClick={() => onEnter(prediction)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <TierBadge tier={prediction.vit_tier} />
            <span className="text-[9px] font-mono text-vit-text-3 uppercase">{prediction.league}</span>
            <span className="text-[9px] font-mono text-vit-text-3">{kickoffStr}</span>
          </div>
          <p className="text-sm font-bold text-vit-text-1 truncate">
            {prediction.home_team} <span className="text-vit-text-3 font-normal">vs</span> {prediction.away_team}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] text-vit-text-3">Pick:</span>
            <SideLabel side={prediction.bet_side} teams={{ home: prediction.home_team, away: prediction.away_team }} />
            <span className="text-[10px] font-mono font-bold text-vit-text-2">@ {prediction.entry_odds.toFixed(2)}</span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-1 shrink-0">
          <div className="flex items-center gap-1">
            <span className={cn("text-lg font-display font-black", cfg.color)}>{prediction.vit_score.toFixed(0)}</span>
            <span className="text-[9px] text-vit-text-3 font-mono">/100</span>
          </div>
          <div className="text-right">
            <p className="text-[9px] font-mono text-vit-text-3">EDGE</p>
            <p className="text-xs font-mono font-bold text-vit-green">+{(prediction.edge * 100).toFixed(1)}%</p>
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="text-center">
            <p className="text-[8px] font-mono text-vit-text-3 uppercase">Confidence</p>
            <p className="text-[11px] font-mono font-bold">{(prediction.confidence * 100).toFixed(0)}%</p>
          </div>
          <div className="text-center">
            <p className="text-[8px] font-mono text-vit-text-3 uppercase">Consensus</p>
            <p className="text-[11px] font-mono font-bold">{prediction.agreement_pct.toFixed(0)}%</p>
          </div>
          <div className="text-center">
            <p className="text-[8px] font-mono text-vit-text-3 uppercase">Rec Stake</p>
            <p className="text-[11px] font-mono font-bold">{prediction.recommended_stake.toFixed(1)}%</p>
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-[10px] font-mono border-vit-green/30 text-vit-green hover:bg-vit-green/10 gap-1"
          onClick={(e) => { e.stopPropagation(); onEnter(prediction); }}
        >
          <Zap size={10} /> ENTER
        </Button>
      </div>
    </div>
  );
}

function EntryModal({ prediction, onClose }: { prediction: VITPrediction; onClose: () => void }) {
  const [stake, setStake] = useState([prediction.recommended_stake]);
  const qc = useQueryClient();

  const enterMutation = useMutation({
    mutationFn: (data: { prediction_id: number; stake_pct: number }) =>
      apiPost("/api/predictions/enter-position", data),
    onSuccess: () => {
      toast.success("Position entered successfully!");
      qc.invalidateQueries({ queryKey: ["/api/wallet"] });
      qc.invalidateQueries({ queryKey: ["exchange-portfolio"] });
      onClose();
    },
    onError: (e: any) => toast.error(e.message || "Failed to enter position"),
  });

  const cfg = TIER_CONFIG[prediction.vit_tier] || TIER_CONFIG.SKIP;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg bg-vit-surface border-t border-vit-border rounded-t-2xl p-6 space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold font-mono uppercase tracking-widest">Enter Position</h3>
            <p className="text-[10px] text-vit-text-3 mt-0.5">{prediction.home_team} vs {prediction.away_team}</p>
          </div>
          <TierBadge tier={prediction.vit_tier} />
        </div>

        <div className={cn("rounded-xl border p-4 space-y-3", cfg.bg)}>
          <div className="flex justify-between text-xs">
            <span className="text-vit-text-3">Signal</span>
            <span className="font-bold"><SideLabel side={prediction.bet_side} teams={{ home: prediction.home_team, away: prediction.away_team }} /></span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-vit-text-3">Entry Odds</span>
            <span className="font-mono font-bold">{prediction.entry_odds.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-vit-text-3">Edge</span>
            <span className="font-mono font-bold text-vit-green">+{(prediction.edge * 100).toFixed(1)}%</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-vit-text-3">VIT Score</span>
            <span className={cn("font-mono font-bold", cfg.color)}>{prediction.vit_score.toFixed(0)}/100</span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-vit-text-3 font-mono uppercase">Bankroll Stake</span>
            <span className="font-mono font-bold text-vit-text-1">{stake[0].toFixed(1)}%</span>
          </div>
          <Slider
            min={0.5}
            max={Math.min(10, prediction.recommended_stake * 2)}
            step={0.5}
            value={stake}
            onValueChange={setStake}
            className="w-full"
          />
          <p className="text-[9px] text-vit-text-3 font-mono">
            Recommended: {prediction.recommended_stake.toFixed(1)}% of bankroll
          </p>
        </div>

        <div className="flex gap-3 pt-2">
          <Button variant="outline" className="flex-1 font-mono text-xs" onClick={onClose}>CANCEL</Button>
          <Button
            className="flex-1 bg-vit-green text-vit-text-inverse font-black font-mono text-xs"
            onClick={() => enterMutation.mutate({ prediction_id: prediction.prediction_id, stake_pct: stake[0] })}
            disabled={enterMutation.isPending}
          >
            {enterMutation.isPending ? "ENTERING..." : "CONFIRM POSITION"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function ExchangePage() {
  const { user } = useAuth();
  const [activeSide, setActiveTab] = useState("buy");

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Liquidity Exchange</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Institutional Trading Terminal</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Trading Interface ── */}
        <div className="lg:col-span-2 space-y-6">
           <Card className="border-primary/20 bg-primary/[0.02]">
              <CardHeader className="flex flex-row items-center justify-between p-6">
                 <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center font-black text-primary">VIT</div>
                    <div>
                       <CardTitle className="text-sm font-display uppercase tracking-widest leading-none">VITCoin / USDT</CardTitle>
                       <p className="text-[10px] font-mono text-muted-foreground mt-1">Institutional Native Asset</p>
                    </div>
                 </div>
                 <div className="text-right">
                    <p className="text-xl font-mono font-bold text-foreground">$0.1242</p>
                    <p className="text-[10px] font-mono text-vit-positive uppercase font-bold">+4.12% Today</p>
                 </div>
              </CardHeader>
              <CardContent className="p-6 pt-0 space-y-6">
                 <Tabs value={activeSide} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="w-full h-12 p-1 bg-white/[0.03]">
                       <TabsTrigger value="buy" className={cn("flex-1 text-[11px] font-bold uppercase tracking-widest", activeSide === 'buy' && "text-primary bg-primary/5")}>Position LONG</TabsTrigger>
                       <TabsTrigger value="sell" className={cn("flex-1 text-[11px] font-bold uppercase tracking-widest", activeSide === 'sell' && "text-vit-negative bg-vit-negative/5")}>Position SHORT</TabsTrigger>
                    </TabsList>
                 </Tabs>

                 <div className="space-y-4">
                    <div className="space-y-2">
                       <div className="flex justify-between text-[10px] font-mono uppercase text-muted-foreground px-1">
                          <span>Collateral USDT</span>
                          <span>Max: 4,250.00</span>
                       </div>
                       <div className="relative">
                          <Input className="bg-white/5 border-white/5 h-12 font-mono text-lg" placeholder="0.00" />
                          <span className="absolute right-4 top-1/2 -translate-y-1/2 font-mono text-xs text-muted-foreground">USDT</span>
                       </div>
                    </div>

                    <div className="flex justify-center">
                       <div className="w-8 h-8 rounded border border-white/5 bg-white/5 flex items-center justify-center text-muted-foreground/40">
                          <ArrowRight size={14} className="rotate-90" />
                       </div>
                    </div>

                    <div className="space-y-2">
                       <div className="flex justify-between text-[10px] font-mono uppercase text-muted-foreground px-1">
                          <span>Output VIT</span>
                          <span>Est. Yield: 0.12%</span>
                       </div>
                       <div className="relative">
                          <Input className="bg-white/5 border-white/5 h-12 font-mono text-lg" placeholder="0.00" disabled />
                          <span className="absolute right-4 top-1/2 -translate-y-1/2 font-mono text-xs text-muted-foreground">VIT</span>
                       </div>
                    </div>
                 </div>

                 <Button className="w-full h-14 uppercase tracking-[0.2em] font-display text-base shadow-xl shadow-primary/10">
                    Execute Trade Strategy
                 </Button>
              </CardContent>
           </Card>

           <Card className="border-white/5 bg-transparent overflow-hidden">
              <CardHeader className="bg-white/[0.01] border-b border-white/5">
                 <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">Active Positions</CardTitle>
              </CardHeader>
              <div className="p-12 text-center space-y-3">
                 <Layers size={24} className="mx-auto text-muted-foreground/20" />
                 <p className="font-display text-[11px] font-bold uppercase tracking-widest text-muted-foreground/40">No active positions detected</p>
              </div>
           </Card>
        </div>

        {/* ── Order Book ── */}
        <div className="space-y-6">
           <Card className="border-white/5 bg-white/[0.01] h-full">
              <CardHeader className="border-b border-white/5">
                 <CardTitle className="text-[10px] uppercase tracking-widest">Network Order Book</CardTitle>
              </CardHeader>
              <div className="p-0 font-mono text-[10px]">
                 <div className="grid grid-cols-3 p-4 text-muted-foreground/40 border-b border-white/5">
                    <span>Price</span>
                    <span className="text-center">Amount</span>
                    <span className="text-right">Total</span>
                 </div>
                 <div className="divide-y divide-white/[0.02]">
                    {[0.1245, 0.1244, 0.1243].map((p, i) => (
                       <div key={i} className="grid grid-cols-3 p-4 hover:bg-vit-negative/5">
                          <span className="text-vit-negative font-bold">{p}</span>
                          <span className="text-center text-foreground/60">4.2k</span>
                          <span className="text-right text-foreground/60">522.4</span>
                       </div>
                    ))}
                    <div className="p-4 text-center bg-white/[0.02] border-y border-white/5">
                       <span className="text-base font-bold text-foreground">0.1242 USDT</span>
                    </div>
                    {[0.1241, 0.1240, 0.1239].map((p, i) => (
                       <div key={i} className="grid grid-cols-3 p-4 hover:bg-primary/5">
                          <span className="text-primary font-bold">{p}</span>
                          <span className="text-center text-foreground/60">2.8k</span>
                          <span className="text-right text-foreground/60">347.5</span>
                       </div>
                    ))}
                 </div>
              </div>
           </Card>
        </div>
      </div>
    </div>
  );
}
