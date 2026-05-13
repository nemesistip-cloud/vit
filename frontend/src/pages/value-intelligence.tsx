import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { VITScoreCard, VITTierBadge } from "@/components/VITScoreCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import {
  Shield, TrendingUp, Brain, Clock, Trophy,
  ChevronRight, RefreshCw, Activity, Target, Info,
} from "lucide-react";
import { Link } from "wouter";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

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
  over_25_prob: number;
  btts_prob: number;
  bet_side: string;
  entry_odds: number;
  edge: number;
  confidence: number;
  recommended_stake: number;
  agreement_pct: number;
  vit_score: number;
  vit_tier: string;
  vit_components: { value: number; intelligence: number; trust: number; recency?: number };
  has_market_odds: boolean;
  prediction_age_hours: number;
  timestamp: string | null;
}

interface VITFeedResponse {
  total: number;
  tier_counts: Record<string, number>;
  predictions: VITPrediction[];
}

const TIER_COLORS: Record<string, string> = {
  ELITE:     "text-yellow-300",
  STRONG:    "text-emerald-400",
  SOLID:     "text-blue-400",
  WATCHLIST: "text-amber-400",
  SKIP:      "text-muted-foreground",
};

const TIER_BG: Record<string, string> = {
  ELITE:     "bg-yellow-400/10 border-yellow-400/30",
  STRONG:    "bg-emerald-500/10 border-emerald-500/30",
  SOLID:     "bg-blue-500/10 border-blue-500/30",
  WATCHLIST: "bg-amber-500/10 border-amber-500/30",
  SKIP:      "bg-muted/10 border-border",
};

function SideLabel({ side, teams }: { side: string; teams: { home: string; away: string } }) {
  if (side === "home") return <span className="text-emerald-400 font-bold">{teams.home}</span>;
  if (side === "away") return <span className="text-rose-400 font-bold">{teams.away}</span>;
  return <span className="text-amber-400 font-bold">Draw</span>;
}

function OutcomeBadge({ actual, betSide }: { actual: string | null; betSide: string }) {
  if (!actual) return null;
  const hit = actual === betSide;
  return (
    <span className={cn(
      "inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase",
      hit ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
          : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
    )}>
      {hit ? "✓ WIN" : "✗ LOSS"}
    </span>
  );
}

function VITPredictionCard({ p }: { p: VITPrediction }) {
  const tierColor = TIER_COLORS[p.vit_tier] ?? "text-muted-foreground";
  const tierBg    = TIER_BG[p.vit_tier]    ?? TIER_BG.SKIP;
  const score     = Math.round(p.vit_score);

  return (
    <Link href={`/matches/${p.match_id}`}>
      <div className={cn(
        "rounded-xl border p-4 cursor-pointer transition-colors hover:bg-card/80 space-y-3",
        tierBg
      )}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs font-bold text-foreground truncate">
                {p.home_team} <span className="text-muted-foreground font-normal">vs</span> {p.away_team}
              </span>
              <OutcomeBadge actual={p.actual_outcome} betSide={p.bet_side} />
            </div>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="font-mono text-[10px] text-muted-foreground uppercase">{p.league?.replace(/_/g, " ")}</span>
              {p.kickoff_time && (
                <span className="font-mono text-[10px] text-muted-foreground flex items-center gap-0.5">
                  <Clock className="w-2.5 h-2.5" />
                  {formatDistanceToNow(new Date(p.kickoff_time), { addSuffix: true })}
                </span>
              )}
            </div>
          </div>

          <div className="flex-shrink-0 text-right">
            <div className={cn("font-mono text-2xl font-black", tierColor)}>{score}</div>
            <div className={cn("font-mono text-[9px] font-bold uppercase tracking-wider", tierColor)}>{p.vit_tier}</div>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-1.5">
          <div className="rounded-lg bg-background/40 border border-border/40 px-1.5 py-1.5 text-center">
            <div className="font-mono text-[8px] text-muted-foreground uppercase mb-0.5 flex items-center justify-center gap-0.5">
              <TrendingUp className="w-2 h-2 text-emerald-400" /> Value
            </div>
            <div className="font-mono text-sm font-bold text-emerald-400">{p.vit_components.value.toFixed(0)}</div>
            <div className="font-mono text-[8px] text-muted-foreground">
              {p.has_market_odds ? `${(p.edge * 100).toFixed(1)}% edge` : "no odds"}
            </div>
          </div>
          <div className="rounded-lg bg-background/40 border border-border/40 px-1.5 py-1.5 text-center">
            <div className="font-mono text-[8px] text-muted-foreground uppercase mb-0.5 flex items-center justify-center gap-0.5">
              <Brain className="w-2 h-2 text-blue-400" /> Intel
            </div>
            <div className="font-mono text-sm font-bold text-blue-400">{p.vit_components.intelligence.toFixed(0)}</div>
            <div className="font-mono text-[8px] text-muted-foreground">{(p.agreement_pct * 100).toFixed(0)}% agree</div>
          </div>
          <div className="rounded-lg bg-background/40 border border-border/40 px-1.5 py-1.5 text-center">
            <div className="font-mono text-[8px] text-muted-foreground uppercase mb-0.5 flex items-center justify-center gap-0.5">
              <Shield className="w-2 h-2 text-purple-400" /> Trust
            </div>
            <div className="font-mono text-sm font-bold text-purple-400">{p.vit_components.trust.toFixed(0)}</div>
            <div className="font-mono text-[8px] text-muted-foreground">{(p.confidence * 100).toFixed(0)}% conf</div>
          </div>
          <div className="rounded-lg bg-background/40 border border-border/40 px-1.5 py-1.5 text-center">
            <div className="font-mono text-[8px] text-muted-foreground uppercase mb-0.5 flex items-center justify-center gap-0.5">
              <Clock className="w-2 h-2 text-cyan-400" /> Fresh
            </div>
            <div className="font-mono text-sm font-bold text-cyan-400">
              {(p.vit_components.recency ?? 100).toFixed(0)}
            </div>
            <div className="font-mono text-[8px] text-muted-foreground">
              {p.prediction_age_hours < 1 ? "< 1h" : `${p.prediction_age_hours.toFixed(0)}h`}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 pt-1 border-t border-border/30">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-[10px] text-muted-foreground">
              Back <SideLabel side={p.bet_side} teams={{ home: p.home_team, away: p.away_team }} />
              {" "}@ <span className="font-bold text-foreground">{p.entry_odds.toFixed(2)}</span>
            </span>
            <span className="font-mono text-[10px] text-muted-foreground">
              Kelly: <span className="text-primary font-bold">{(p.recommended_stake * 100).toFixed(1)}%</span>
            </span>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            <span className="font-mono text-[9px]">View</span>
            <ChevronRight className="w-3 h-3" />
          </div>
        </div>
      </div>
    </Link>
  );
}

function TierStat({ tier, count, total }: { tier: string; count: number; total: number }) {
  const color = TIER_COLORS[tier] ?? "text-muted-foreground";
  const pct   = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="text-center">
      <div className={cn("font-mono text-lg font-black", color)}>{count}</div>
      <div className={cn("font-mono text-[9px] uppercase font-bold", color)}>{tier}</div>
      <div className="font-mono text-[9px] text-muted-foreground">{pct}%</div>
    </div>
  );
}

export default function ValueIntelligencePage() {
  const [minVit, setMinVit] = useState(25);
  const [tierFilter, setTierFilter] = useState("all");
  const [limitFilter, setLimitFilter] = useState("20");

  const { data, isLoading, refetch, isFetching } = useQuery<VITFeedResponse>({
    queryKey: ["value-intelligence", minVit, tierFilter, limitFilter],
    queryFn: () => {
      const params = new URLSearchParams({
        min_vit: String(minVit),
        limit: limitFilter,
      });
      if (tierFilter !== "all") params.set("tier", tierFilter);
      return apiGet<VITFeedResponse>(`/predict/value-intelligence?${params}`);
    },
    refetchInterval: 60_000,
  });

  const predictions = data?.predictions ?? [];
  const tierCounts  = data?.tier_counts ?? {};
  const total       = data?.total ?? 0;
  const allTotal    = Object.values(tierCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-purple-500/20 border border-primary/30 flex items-center justify-center">
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="font-mono text-xl font-black tracking-tight">
              <span className="text-primary">V</span>alue{" "}
              <span className="text-blue-400">I</span>ntelligence{" "}
              <span className="text-purple-400">T</span>rust
            </h1>
            <p className="font-mono text-xs text-muted-foreground">
              13-model ensemble ranked by composite VIT score · trained on 50,000 fixtures
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 via-transparent to-purple-500/5 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Info className="w-3.5 h-3.5 text-primary" />
          <span className="font-mono text-xs font-bold text-primary uppercase tracking-wider">VIT Score Formula</span>
        </div>
        <div className="grid grid-cols-4 gap-2 mb-3">
          <div className="rounded-lg bg-background/40 border border-emerald-500/20 px-2 py-2 text-center">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400 mx-auto mb-1" />
            <div className="font-mono text-[10px] font-bold text-emerald-400">Value 35%</div>
            <div className="font-mono text-[8px] text-muted-foreground">Vig-free edge over market</div>
          </div>
          <div className="rounded-lg bg-background/40 border border-blue-500/20 px-2 py-2 text-center">
            <Brain className="w-3.5 h-3.5 text-blue-400 mx-auto mb-1" />
            <div className="font-mono text-[10px] font-bold text-blue-400">Intel 30%</div>
            <div className="font-mono text-[8px] text-muted-foreground">Argmax-consensus voting</div>
          </div>
          <div className="rounded-lg bg-background/40 border border-purple-500/20 px-2 py-2 text-center">
            <Shield className="w-3.5 h-3.5 text-purple-400 mx-auto mb-1" />
            <div className="font-mono text-[10px] font-bold text-purple-400">Trust 25%</div>
            <div className="font-mono text-[8px] text-muted-foreground">Entropy-based sharpness</div>
          </div>
          <div className="rounded-lg bg-background/40 border border-cyan-500/20 px-2 py-2 text-center">
            <Clock className="w-3.5 h-3.5 text-cyan-400 mx-auto mb-1" />
            <div className="font-mono text-[10px] font-bold text-cyan-400">Recency 10%</div>
            <div className="font-mono text-[8px] text-muted-foreground">Signal freshness decay</div>
          </div>
        </div>
        {allTotal > 0 && (
          <div className="flex items-center justify-center gap-6 pt-2 border-t border-border/30">
            {["ELITE", "STRONG", "SOLID", "WATCHLIST"].map((t) => (
              <TierStat key={t} tier={t} count={tierCounts[t] ?? 0} total={allTotal} />
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <span className="font-mono text-[10px] text-muted-foreground uppercase whitespace-nowrap">Min VIT:</span>
          <Slider
            value={[minVit]}
            min={0} max={80} step={5}
            onValueChange={(v) => setMinVit(v[0])}
            className="flex-1"
          />
          <span className="font-mono text-xs font-bold text-primary w-8">{minVit}</span>
        </div>

        <Select value={tierFilter} onValueChange={setTierFilter}>
          <SelectTrigger className="w-36 font-mono text-xs h-8">
            <SelectValue placeholder="All tiers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" className="font-mono text-xs">All Tiers</SelectItem>
            <SelectItem value="ELITE" className="font-mono text-xs text-yellow-300">ELITE</SelectItem>
            <SelectItem value="STRONG" className="font-mono text-xs text-emerald-400">STRONG</SelectItem>
            <SelectItem value="SOLID" className="font-mono text-xs text-blue-400">SOLID</SelectItem>
            <SelectItem value="WATCHLIST" className="font-mono text-xs text-amber-400">WATCHLIST</SelectItem>
          </SelectContent>
        </Select>

        <Select value={limitFilter} onValueChange={setLimitFilter}>
          <SelectTrigger className="w-24 font-mono text-xs h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {["10","20","50"].map((n) => (
              <SelectItem key={n} value={n} className="font-mono text-xs">Top {n}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button size="sm" variant="outline" onClick={() => refetch()} disabled={isFetching} className="h-8 gap-1.5 font-mono text-xs">
          <RefreshCw className={cn("w-3 h-3", isFetching && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-xl" />
          ))}
        </div>
      ) : predictions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border/50 p-12 text-center space-y-3">
          <Target className="w-8 h-8 text-muted-foreground mx-auto" />
          <div className="font-mono text-sm text-muted-foreground">No predictions meet the VIT threshold</div>
          <div className="font-mono text-xs text-muted-foreground/60">
            Submit predictions from the Matches page to populate this feed
          </div>
          <Button size="sm" variant="outline" onClick={() => setMinVit(0)} className="font-mono text-xs">
            Lower VIT threshold
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs text-muted-foreground">
              {total} prediction{total !== 1 ? "s" : ""} · sorted by VIT score
            </span>
            <div className="flex items-center gap-1.5">
              <Activity className="w-3 h-3 text-primary" />
              <span className="font-mono text-[10px] text-muted-foreground">Live · updates every 60s</span>
            </div>
          </div>

          {predictions.map((p) => (
            <VITPredictionCard key={p.prediction_id} p={p} />
          ))}
        </div>
      )}

      <div className="rounded-xl border border-border/30 bg-muted/10 p-4 space-y-2">
        <div className="flex items-center gap-2">
          <Trophy className="w-3.5 h-3.5 text-amber-400" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground">Tier Guide</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          {[
            { tier: "ELITE",     range: "72–100", desc: "Exceptional: strong edge + consensus + high trust" },
            { tier: "STRONG",    range: "55–71",  desc: "Strong value pick with good model agreement" },
            { tier: "SOLID",     range: "40–54",  desc: "Solid selection — worth considering" },
            { tier: "WATCHLIST", range: "25–39",  desc: "Monitor — modest edge, lower conviction" },
          ].map(({ tier, range, desc }) => (
            <div key={tier} className="flex items-start gap-2">
              <VITTierBadge tier={tier} score={0} />
              <div>
                <div className="text-muted-foreground">{range}</div>
                <div className="text-muted-foreground/60 leading-relaxed">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
