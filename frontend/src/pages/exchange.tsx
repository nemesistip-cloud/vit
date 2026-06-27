import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import {
  Zap, TrendingUp, Shield, Brain, Clock, Target, Filter,
  ChevronRight, ArrowUpRight, BarChart3, Trophy, RefreshCw,
  Wallet, Activity, AlertTriangle, CheckCircle2, Info,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import { useLocation } from "wouter";
import { formatDistanceToNow } from "date-fns";
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
  const [, navigate] = useLocation();
  const [tierFilter, setTierFilter] = useState("ALL");
  const [minVit, setMinVit] = useState([60]);
  const [activeTab, setActiveTab] = useState("signals");
  const [selectedPrediction, setSelectedPrediction] = useState<VITPrediction | null>(null);

  const params = new URLSearchParams();
  if (tierFilter !== "ALL") params.set("tier", tierFilter);
  params.set("min_vit", String(minVit[0]));
  params.set("limit", "50");

  const { data, isLoading, refetch, isFetching } = useQuery<VITFeedResponse>({
    queryKey: ["exchange-feed", tierFilter, minVit[0]],
    queryFn: () => apiGet<VITFeedResponse>(`/api/quality-feed/value-analytics?${params}`),
    refetchInterval: 60_000,
  });

  const { data: portfolio } = useQuery<any>({
    queryKey: ["exchange-portfolio"],
    queryFn: () => apiGet("/api/predictions/portfolio"),
    retry: false,
  });

  const { data: wallet } = useQuery<any>({
    queryKey: ["/api/wallet"],
    queryFn: () => apiGet("/api/wallet"),
  });

  const predictions = data?.predictions ?? [];
  const tierCounts = data?.tier_counts ?? {};

  const vitBalance = wallet?.balances?.VITCoin ?? wallet?.vitcoin_balance ?? 0;

  const tiers = ["ALL", "ELITE", "STRONG", "SOLID", "WATCHLIST"];

  return (
    <div className="space-y-4 pb-20">
      {selectedPrediction && (
        <EntryModal prediction={selectedPrediction} onClose={() => setSelectedPrediction(null)} />
      )}

      {/* Header Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="VITCoin Balance"
          value={typeof vitBalance === "number" ? vitBalance.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "0"}
          icon={<Wallet size={16} className="text-vit-green" />}
        />
        <MetricCard
          label="Live Signals"
          value={String(data?.total ?? "--")}
          icon={<Activity size={16} className="text-secondary" />}
        />
        <MetricCard
          label="Elite Picks"
          value={String(tierCounts["ELITE"] ?? 0)}
          icon={<Trophy size={16} className="text-yellow-400" />}
        />
        <MetricCard
          label="Avg Edge"
          value={predictions.length > 0
            ? `+${((predictions.reduce((s, p) => s + p.edge, 0) / predictions.length) * 100).toFixed(1)}%`
            : "--"
          }
          changePositive={true}
          icon={<TrendingUp size={16} className="text-vit-green" />}
        />
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-vit-surface-2 border border-vit-border p-1 h-10 w-full grid grid-cols-2">
          <TabsTrigger value="signals" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">
            LIVE SIGNALS
          </TabsTrigger>
          <TabsTrigger value="portfolio" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">
            MY POSITIONS
          </TabsTrigger>
        </TabsList>

        <TabsContent value="signals" className="mt-4 space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-3">
            <Select value={tierFilter} onValueChange={setTierFilter}>
              <SelectTrigger className="h-9 w-36 bg-vit-surface-2 border-vit-border text-xs font-mono">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {tiers.map(t => (
                  <SelectItem key={t} value={t} className="font-mono text-xs">
                    {t === "ALL" ? "All Tiers" : t}
                    {t !== "ALL" && tierCounts[t] ? ` (${tierCounts[t]})` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex-1 space-y-1">
              <div className="flex justify-between text-[9px] font-mono text-vit-text-3">
                <span>MIN VIT SCORE</span>
                <span>{minVit[0]}</span>
              </div>
              <Slider
                min={40}
                max={90}
                step={5}
                value={minVit}
                onValueChange={setMinVit}
                className="w-full"
              />
            </div>

            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9 border-vit-border bg-vit-surface-2 shrink-0"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RefreshCw size={14} className={isFetching ? "animate-spin" : ""} />
            </Button>
          </div>

          {/* Tier pill summary */}
          <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
            {["ELITE", "STRONG", "SOLID", "WATCHLIST"].map(t => {
              const cfg = TIER_CONFIG[t];
              const count = tierCounts[t] ?? 0;
              return (
                <button
                  key={t}
                  onClick={() => setTierFilter(tierFilter === t ? "ALL" : t)}
                  className={cn(
                    "shrink-0 flex items-center gap-1.5 px-3 h-7 rounded-full border text-[9px] font-bold font-mono uppercase transition-all",
                    tierFilter === t ? cfg.bg + " " + cfg.color : "bg-vit-surface-2 border-vit-border text-vit-text-3"
                  )}
                >
                  {t} <span className="opacity-70">{count}</span>
                </button>
              );
            })}
          </div>

          {/* Signal list */}
          <div className="bg-vit-surface border-y border-vit-border">
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="p-4 border-b border-vit-border space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-3 w-48" />
                </div>
              ))
            ) : predictions.length === 0 ? (
              <div className="py-16 text-center space-y-3">
                <Brain size={32} className="mx-auto text-vit-text-3 opacity-50" />
                <p className="text-sm font-bold text-vit-text-3">No signals match your filters</p>
                <p className="text-[11px] text-vit-text-3">Try lowering the VIT score threshold or broadening the tier filter</p>
                <Button size="sm" variant="outline" className="font-mono text-xs" onClick={() => { setTierFilter("ALL"); setMinVit([60]); }}>
                  RESET FILTERS
                </Button>
              </div>
            ) : (
              predictions.map(pred => (
                <SignalCard
                  key={pred.prediction_id}
                  prediction={pred}
                  onEnter={setSelectedPrediction}
                />
              ))
            )}
          </div>

          {!isLoading && predictions.length > 0 && (
            <p className="text-center text-[10px] font-mono text-vit-text-3">
              {predictions.length} signals · Updated {isFetching ? "now" : "1m ago"}
            </p>
          )}
        </TabsContent>

        <TabsContent value="portfolio" className="mt-4">
          {portfolio?.positions && portfolio.positions.length > 0 ? (
            <div className="bg-vit-surface border-y border-vit-border divide-y divide-vit-border">
              {portfolio.positions.map((pos: any) => (
                <div key={pos.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold">{pos.home_team} vs {pos.away_team}</p>
                    <p className="text-[10px] text-vit-text-3 font-mono mt-0.5 uppercase">{pos.bet_side} · {pos.stake_pct?.toFixed(1)}% stake</p>
                  </div>
                  <div className="text-right">
                    <Badge className={cn(
                      "text-[9px]",
                      pos.status === "won" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" :
                      pos.status === "lost" ? "bg-rose-500/10 text-rose-400 border-rose-500/30" :
                      "bg-vit-surface-3 text-vit-text-3 border-vit-border"
                    )}>
                      {pos.status?.toUpperCase() ?? "OPEN"}
                    </Badge>
                    {pos.pnl != null && (
                      <p className={cn("text-xs font-mono font-bold mt-1", pos.pnl >= 0 ? "text-vit-green" : "text-vit-negative")}>
                        {pos.pnl >= 0 ? "+" : ""}{pos.pnl.toFixed(2)} VIT
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-16 text-center space-y-3">
              <Target size={32} className="mx-auto text-vit-text-3 opacity-50" />
              <p className="text-sm font-bold text-vit-text-3">No open positions</p>
              <p className="text-[11px] text-vit-text-3">Enter a position from the Live Signals tab to get started</p>
              <Button
                size="sm"
                className="bg-vit-green text-vit-text-inverse font-black font-mono text-xs"
                onClick={() => setActiveTab("signals")}
              >
                <Zap size={12} className="mr-1" /> VIEW SIGNALS
              </Button>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
