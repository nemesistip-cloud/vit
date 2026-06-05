import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { API } from "@/api-client";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  Star, Trophy, TrendingUp, TrendingDown, Flame, Zap,
  Crown, Shield, Diamond, Award, Target, Activity
} from "lucide-react";

interface TierInfo {
  tier: string;
  min_score: number;
  bonus_pct: number;
}

interface LeaderboardEntry {
  rank: number;
  user_id: number;
  score: number;
  tier: string;
  peak_score: number;
  bonus_vit_earned: number;
  streak_days: number;
}

interface UserMerit {
  user_id: number;
  score: number;
  tier: string;
  peak_score: number;
  peak_tier: string;
  total_earned: number;
  total_lost: number;
  streak_days: number;
  bonus_vit_earned: number;
  current_bonus_pct: number;
  next_tier: string | null;
  xp_to_next_tier: number;
  last_activity_at: string | null;
}

interface MeritEvent {
  id: number;
  event_type: string;
  xp_delta: number;
  score_before: number;
  score_after: number;
  tier_before: string;
  tier_after: string;
  bonus_vit: number;
  description: string | null;
  occurred_at: string;
}

const TIER_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  unranked: { icon: <Target className="w-5 h-5" />, color: "text-slate-400", bg: "bg-slate-500/20 border-slate-500/30" },
  bronze: { icon: <Shield className="w-5 h-5" />, color: "text-amber-600", bg: "bg-amber-800/20 border-amber-700/30" },
  silver: { icon: <Star className="w-5 h-5" />, color: "text-slate-300", bg: "bg-slate-400/20 border-slate-400/30" },
  gold: { icon: <Award className="w-5 h-5" />, color: "text-yellow-400", bg: "bg-yellow-500/20 border-yellow-500/30" },
  platinum: { icon: <Diamond className="w-5 h-5" />, color: "text-cyan-300", bg: "bg-cyan-500/20 border-cyan-500/30" },
  diamond: { icon: <Flame className="w-5 h-5" />, color: "text-blue-400", bg: "bg-blue-500/20 border-blue-500/30" },
  sovereign: { icon: <Crown className="w-5 h-5" />, color: "text-violet-400", bg: "bg-violet-500/20 border-violet-500/30" },
};

function TierBadge({ tier }: { tier: string }) {
  const cfg = TIER_CONFIG[tier] ?? TIER_CONFIG.unranked;
  return (
    <Badge className={`${cfg.bg} ${cfg.color} border flex items-center gap-1 text-xs`}>
      {cfg.icon}
      {tier.charAt(0).toUpperCase() + tier.slice(1)}
    </Badge>
  );
}

export default function MeritPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const qc = useQueryClient();

  const { data: tiersData } = useQuery({
    queryKey: [API.meritTiers],
    queryFn: () => apiGet<{ tiers: TierInfo[] }>(API.meritTiers),
  });

  const { data: leaderboardData, isLoading: lbLoading } = useQuery({
    queryKey: [API.meritLeaderboard],
    queryFn: () => apiGet<{ leaderboard: LeaderboardEntry[] }>(API.meritLeaderboard),
    refetchInterval: 30_000,
  });

  const { data: distributionData } = useQuery({
    queryKey: [API.meritDistribution],
    queryFn: () => apiGet<{ distribution: Record<string, number> }>(API.meritDistribution),
  });

  const { data: myMerit } = useQuery({
    queryKey: [API.meritUser(user?.id ?? 0)],
    queryFn: () => apiGet<UserMerit>(API.meritUser(user!.id)),
    enabled: !!user?.id,
  });

  const { data: myHistory } = useQuery({
    queryKey: [API.meritHistory(user?.id ?? 0)],
    queryFn: () => apiGet<{ events: MeritEvent[] }>(API.meritHistory(user!.id)),
    enabled: !!user?.id,
  });

  const decayMutation = useMutation({
    mutationFn: () => apiPost(`/api/merit/users/${user?.id}/decay`, {}),
    onSuccess: () => {
      toast({ title: "Decay applied" });
      qc.invalidateQueries({ queryKey: [API.meritUser(user?.id ?? 0)] });
    },
  });

  const myTierCfg = TIER_CONFIG[myMerit?.tier ?? "unranked"] ?? TIER_CONFIG.unranked;
  const progressPct = myMerit?.xp_to_next_tier
    ? Math.max(0, Math.min(100, 100 - (myMerit.xp_to_next_tier / (myMerit.score + myMerit.xp_to_next_tier)) * 100))
    : 100;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground flex items-center gap-2">
          <Trophy className="w-6 h-6 text-yellow-400" />
          Network Merit
        </h1>
        <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest mt-1">
          Long-term reputation scoring — earn VIT bonuses by climbing the tier ladder
        </p>
      </div>

      {myMerit && (
        <Card className={`border ${myTierCfg.bg}`}>
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="text-slate-400 text-sm">Your Merit xp</div>
                <div className="text-4xl font-bold text-white mt-1">{myMerit.score.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                <div className="flex items-center gap-2 mt-2">
                  <TierBadge tier={myMerit.tier} />
                  {myMerit.streak_days > 0 && (
                    <Badge className="bg-orange-500/20 text-orange-300 border-orange-500/30 text-xs">
                      <Flame className="w-3 h-3 mr-1" />{myMerit.streak_days}d streak
                    </Badge>
                  )}
                  <Badge className="bg-green-500/10 text-green-400 border-green-500/20 text-xs">
                    +{myMerit.current_bonus_pct.toFixed(0)}% VIT bonus
                  </Badge>
                </div>
              </div>
              <div className="text-right text-sm">
                <div className="text-slate-400">Peak</div>
                <div className="text-white font-semibold">{myMerit.peak_score.toFixed(0)}</div>
                <TierBadge tier={myMerit.peak_tier} />
              </div>
            </div>
            {myMerit.next_tier && (
              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Progress to {myMerit.next_tier}</span>
                  <span>{myMerit.xp_to_next_tier.toFixed(0)} IP needed</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${myTierCfg.color.replace("text-", "bg-")}`}
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>
            )}
            <div className="grid grid-cols-3 gap-3 mt-4 text-center">
              <div className="bg-slate-800 rounded p-2">
                <div className="text-green-400 font-semibold text-sm">+{myMerit.total_earned.toFixed(0)}</div>
                <div className="text-xs text-slate-500">Earned</div>
              </div>
              <div className="bg-slate-800 rounded p-2">
                <div className="text-red-400 font-semibold text-sm">-{myMerit.total_lost.toFixed(0)}</div>
                <div className="text-xs text-slate-500">Lost</div>
              </div>
              <div className="bg-slate-800 rounded p-2">
                <div className="text-yellow-400 font-semibold text-sm">{myMerit.bonus_vit_earned.toFixed(2)}</div>
                <div className="text-xs text-slate-500">Bonus VIT</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="leaderboard">
        <TabsList className="bg-slate-800 border border-slate-700">
          <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
          <TabsTrigger value="tiers">Tier System</TabsTrigger>
          <TabsTrigger value="history">My History</TabsTrigger>
          <TabsTrigger value="distribution">Distribution</TabsTrigger>
        </TabsList>

        <TabsContent value="leaderboard" className="mt-4">
          <div className="space-y-2">
            {lbLoading ? (
              <div className="text-slate-400 text-center py-8">Loading leaderboard…</div>
            ) : (
              (leaderboardData?.leaderboard ?? []).map((entry) => {
                const cfg = TIER_CONFIG[entry.tier] ?? TIER_CONFIG.unranked;
                return (
                  <Card key={entry.user_id} className={`bg-slate-800/50 border ${entry.rank <= 3 ? "border-yellow-500/30" : "border-slate-700"}`}>
                    <CardContent className="p-3 flex items-center gap-4">
                      <div className={`text-2xl font-bold w-8 text-center ${entry.rank === 1 ? "text-yellow-400" : entry.rank === 2 ? "text-slate-300" : entry.rank === 3 ? "text-amber-600" : "text-slate-500"}`}>
                        {entry.rank <= 3 ? ["🥇", "🥈", "🥉"][entry.rank - 1] : `#${entry.rank}`}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-white font-semibold">User #{entry.user_id}</span>
                          <TierBadge tier={entry.tier} />
                        </div>
                        <div className="flex gap-3 text-xs text-slate-400 mt-1">
                          <span>{entry.streak_days}d streak</span>
                          <span>+{entry.bonus_vit_earned.toFixed(2)} VIT bonus</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`font-bold text-lg ${cfg.color}`}>{entry.score.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                        <div className="text-xs text-slate-500">merit IP</div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>
        </TabsContent>

        <TabsContent value="tiers" className="mt-4">
          <div className="grid md:grid-cols-2 gap-3">
            {(tiersData?.tiers ?? []).map((tier) => {
              const cfg = TIER_CONFIG[tier.tier] ?? TIER_CONFIG.unranked;
              return (
                <Card key={tier.tier} className={`border ${cfg.bg}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={cfg.color}>{cfg.icon}</div>
                        <div>
                          <div className={`font-semibold capitalize ${cfg.color}`}>{tier.tier}</div>
                          <div className="text-xs text-slate-400">{tier.min_score.toLocaleString()}+ xp</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`font-bold text-lg ${cfg.color}`}>+{tier.bonus_pct.toFixed(0)}%</div>
                        <div className="text-xs text-slate-400">VIT bonus</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="history" className="mt-4 space-y-2">
          {!user ? (
            <div className="text-center text-slate-400 py-8">Sign in to view your merit history</div>
          ) : (myHistory?.events ?? []).length === 0 ? (
            <div className="text-center text-slate-400 py-8">No merit events yet</div>
          ) : (
            (myHistory?.events ?? []).map((e) => (
              <Card key={e.id} className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-3 flex items-center gap-3">
                  <div className={`font-bold text-sm ${e.xp_delta >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {e.xp_delta >= 0 ? "+" : ""}{e.xp_delta.toFixed(1)}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm text-white capitalize">{e.event_type.replace(/_/g, " ")}</div>
                    {e.description && <div className="text-xs text-slate-400">{e.description}</div>}
                    {e.tier_before !== e.tier_after && (
                      <div className="flex items-center gap-1 mt-1">
                        <TierBadge tier={e.tier_before} />
                        <span className="text-slate-500 text-xs">→</span>
                        <TierBadge tier={e.tier_after} />
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-400">{e.score_after.toFixed(0)} IP</div>
                    <div className="text-xs text-slate-500">{new Date(e.occurred_at).toLocaleDateString()}</div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="distribution" className="mt-4">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-base">Tier Distribution</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {Object.entries(distributionData?.distribution ?? {}).map(([tier, count]) => {
                const cfg = TIER_CONFIG[tier] ?? TIER_CONFIG.unranked;
                const total = Object.values(distributionData?.distribution ?? {}).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                return (
                  <div key={tier} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <div className={`flex items-center gap-2 ${cfg.color}`}>
                        {cfg.icon}
                        <span className="capitalize">{tier}</span>
                      </div>
                      <span className="text-slate-300">{count} users ({pct.toFixed(1)}%)</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${cfg.color.replace("text-", "bg-")}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
