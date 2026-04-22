import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useGetTopOpportunities, useGetModelConfidence } from "@/api-client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Trophy, TrendingUp, Activity, Coins, ArrowUpRight, ArrowDownRight,
  Clock, Globe, Users, ShieldCheck, Brain, ChevronRight, Zap,
  BarChart2, Target, CreditCard
} from "lucide-react";
import { format } from "date-fns";
import { Link } from "wouter";
import { LevelCard, AchievementBadges, Leaderboard, StreakCounter } from "@/components/gamification";

function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-4 w-4 rounded" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-7 w-32 mb-2" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  );
}

function MiniStatSkeleton() {
  return (
    <div className="rounded-lg border border-border/50 bg-card/30 p-3 flex items-center justify-between">
      <div className="space-y-1">
        <Skeleton className="h-2.5 w-16" />
        <Skeleton className="h-5 w-12" />
      </div>
      <Skeleton className="h-4 w-4 rounded" />
    </div>
  );
}

function ActivityItemSkeleton() {
  return (
    <div className="flex items-start gap-3">
      <Skeleton className="h-7 w-7 rounded flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
  );
}

/* ── AI Confidence Widget ─────────────────────────────── */
function AIConfidenceWidget() {
  const { data, isLoading, isError } = useGetModelConfidence();
  const displayModels = data?.models?.slice(0, 6) ?? [];
  const ensembleAccuracy = data?.ensemble_accuracy ?? 0;
  const activeCount = data?.active_count ?? 0;

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-1">
            <div className="flex justify-between">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-1.5 w-full rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-4 text-xs font-mono text-muted-foreground text-destructive/70">
        Model metrics unavailable. Train models to see accuracy data.
      </div>
    );
  }

  if (displayModels.length === 0) {
    return (
      <div className="text-center py-4 text-xs font-mono text-muted-foreground">
        No model data yet — run a prediction to populate.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {displayModels.map((m) => (
        <div key={m.key}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-mono text-muted-foreground">{m.name}</span>
            <div className="flex items-center gap-2">
              {m.predictions > 0 && (
                <span className="text-[10px] font-mono text-muted-foreground/60">{m.predictions} pred.</span>
              )}
              <span className="text-xs font-mono text-primary font-bold">{m.accuracy.toFixed(1)}%</span>
            </div>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-700"
              style={{ width: `${Math.min(m.accuracy, 100)}%` }}
            />
          </div>
        </div>
      ))}
      <div className="pt-2 border-t border-border/50 flex items-center justify-between">
        <span className="text-xs font-mono text-muted-foreground">Ensemble ({activeCount} models)</span>
        <span className="text-base font-bold font-mono text-primary">{ensembleAccuracy.toFixed(1)}%</span>
      </div>
    </div>
  );
}

/* ── Top Opportunities Widget ─────────────────────────── */
function TopOpportunitiesWidget() {
  const { data, isLoading, isError } = useGetTopOpportunities(5);
  const opportunities = data?.opportunities ?? [];

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg border border-border/40">
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3 w-40" />
              <Skeleton className="h-2.5 w-20" />
            </div>
            <div className="space-y-1 text-right">
              <Skeleton className="h-3 w-12 ml-auto" />
              <Skeleton className="h-2.5 w-10 ml-auto" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-2">
        <div className="text-center py-6 text-xs font-mono text-destructive/70">
          Predictions not yet available. Visit Matches to generate your first prediction.
        </div>
        <Link href="/matches">
          <Button variant="ghost" size="sm" className="w-full font-mono text-xs text-muted-foreground gap-1">
            Browse matches <ChevronRight className="w-3 h-3" />
          </Button>
        </Link>
      </div>
    );
  }

  if (opportunities.length === 0) {
    return (
      <div className="space-y-2">
        <div className="text-center py-6 text-xs font-mono text-muted-foreground">
          No live opportunities — make predictions to find value bets.
        </div>
        <Link href="/matches">
          <Button variant="ghost" size="sm" className="w-full font-mono text-xs text-muted-foreground gap-1">
            Browse matches <ChevronRight className="w-3 h-3" />
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {opportunities.map((o) => (
        <Link key={o.prediction_id} href={`/matches/${o.match_id}`}>
          <div className="flex items-center gap-3 p-2.5 rounded-lg border border-border/40 hover:border-primary/30 hover:bg-primary/5 transition-all cursor-pointer group">
            <div className="flex-1 min-w-0">
              <div className="text-xs font-mono font-medium truncate text-foreground group-hover:text-primary transition-colors">{o.match}</div>
              <div className="text-[10px] font-mono text-muted-foreground">{o.time}</div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className={`text-xs font-mono font-bold ${o.edge_value >= 0 ? "text-green-400" : "text-destructive"}`}>{o.edge}</div>
              <div className="text-[10px] font-mono text-muted-foreground">AI: {o.ai_confidence}%</div>
            </div>
            <ChevronRight className="w-3 h-3 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0" />
          </div>
        </Link>
      ))}
      <Link href="/matches">
        <Button variant="ghost" size="sm" className="w-full font-mono text-xs text-muted-foreground mt-1 gap-1">
          View all opportunities <ChevronRight className="w-3 h-3" />
        </Button>
      </Link>
    </div>
  );
}

/* ── Quick Actions FAB (mobile) ───────────────────────── */
function QuickActionsFAB() {
  return (
    <div className="fixed bottom-6 right-6 z-50 md:hidden">
      <Link href="/matches">
        <button className="w-14 h-14 bg-primary text-primary-foreground rounded-full shadow-xl vit-glow-cyan flex items-center justify-center active:scale-95 transition-transform">
          <Zap className="w-6 h-6" />
        </button>
      </Link>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();

  const { data: summary, isLoading: isLoadingSummary } = useQuery<any>({
    queryKey: ["dashboard-summary"],
    queryFn: () => apiGet<any>("/api/dashboard/summary"),
    refetchInterval: 30_000,
  });

  const { data: price, isLoading: isLoadingPrice } = useQuery<any>({
    queryKey: ["dashboard-price"],
    queryFn: () => apiGet<any>("/api/dashboard/vitcoin-price"),
    refetchInterval: 60_000,
  });

  const { data: activity, isLoading: isLoadingActivity } = useQuery<any[]>({
    queryKey: ["dashboard-activity"],
    queryFn: () => apiGet<any[]>("/api/dashboard/recent-activity"),
    refetchInterval: 30_000,
  });

  const { data: system, isLoading: isLoadingSystem } = useQuery<any>({
    queryKey: ["dashboard-system"],
    queryFn: () => apiGet<any>("/system/status"),
    refetchInterval: 60_000,
  });

  const { data: leaderboardData } = useQuery<any>({
    queryKey: ["dashboard-leaderboard"],
    queryFn: () => apiGet<any>("/api/dashboard/leaderboard"),
    refetchInterval: 120_000,
  });

  const { data: achievementsData } = useQuery<any>({
    queryKey: ["dashboard-achievements"],
    queryFn: () => apiGet<any>("/api/dashboard/achievements"),
    refetchInterval: 120_000,
  });

  const { data: planData } = useQuery<any>({
    queryKey: ["dashboard-plan"],
    queryFn: () => apiGet<any>("/api/subscription/my-plan"),
    refetchInterval: 300_000,
  });

  const activityList = Array.isArray(activity) ? activity : [];
  const change24h = price?.change_24h ?? 0;
  const isLoadingCards = isLoadingSummary || isLoadingPrice;

  const accuracyRate = (summary?.accuracy_rate ?? 0);
  const xp = Math.floor((summary?.total_predictions ?? 0) * 10 + accuracyRate * 100);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="space-y-6 pb-20 md:pb-6">
      {/* ── Welcome Header ──────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-mono font-bold tracking-tight">
            {greeting}, <span className="text-primary">{user?.username ?? "Operator"}</span>
          </h1>
          <p className="text-muted-foreground font-mono text-sm flex items-center gap-2 mt-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Live feeds active · refreshing every 30s
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StreakCounter streak={summary?.streak ?? 0} />
          <Link href="/matches">
            <Button size="sm" className="font-mono gap-1.5 text-xs hidden sm:flex">
              <Zap className="w-3 h-3" />
              New Prediction
            </Button>
          </Link>
        </div>
      </div>

      {/* ── KPI Row ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {isLoadingCards ? (
          Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)
        ) : (
          <>
            <Card className="border-primary/20 bg-card/50 backdrop-blur">
              <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <CardTitle className="text-xs font-mono uppercase font-medium text-muted-foreground">Accuracy</CardTitle>
                <Trophy className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold font-mono text-primary">
                  {((summary?.accuracy_rate ?? 0) * 100).toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground mt-1 font-mono">
                  {summary?.total_predictions ?? 0} predictions
                </p>
              </CardContent>
            </Card>

            <Card className="border-secondary/20 bg-card/50 backdrop-blur">
              <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <CardTitle className="text-xs font-mono uppercase font-medium text-muted-foreground">VIT Balance</CardTitle>
                <Coins className="h-4 w-4 text-secondary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold font-mono text-secondary">
                  {Number(summary?.wallet_balance ?? 0).toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground mt-1 font-mono">VITCoin</p>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <CardTitle className="text-xs font-mono uppercase font-medium text-muted-foreground">Active Matches</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold font-mono">{summary?.active_matches ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1 font-mono">Awaiting settlement</p>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <CardTitle className="text-xs font-mono uppercase font-medium text-muted-foreground">Active Plan</CardTitle>
                <CreditCard className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold font-mono capitalize">
                  {planData?.plan?.display_name ?? "Free"}
                </div>
                <p className="text-xs text-muted-foreground mt-1 font-mono">
                  {planData?.usage?.predictions_today ?? 0}
                  {planData?.usage?.limit_today != null ? `/${planData.usage.limit_today}` : ""} preds today
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* ── Mini stats ──────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {isLoadingSystem ? (
          Array.from({ length: 4 }).map((_, i) => <MiniStatSkeleton key={i} />)
        ) : system ? (
          [
            { label: "Total Users",     value: system.users?.total ?? 0,                            icon: Users,       color: "text-foreground" },
            { label: "Active (30d)",    value: system.users?.active_30d ?? 0,                       icon: Activity,    color: "text-primary"    },
            { label: "Validators",      value: system.users?.validators ?? 0,                       icon: ShieldCheck, color: "text-secondary"  },
            { label: "VIT Price",       value: `$${Number(price?.price ?? 0.001).toFixed(5)}`,      icon: TrendingUp,  color: change24h >= 0 ? "text-green-400" : "text-destructive" },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="rounded-lg border border-border/50 bg-card/30 p-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-muted-foreground uppercase mb-0.5">{label}</div>
                <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
              </div>
              <Icon className={`w-4 h-4 ${color} opacity-50`} />
            </div>
          ))
        ) : null}
      </div>

      {/* ── Main 3-col grid ─────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Left: Performance + Level */}
        <div className="lg:col-span-2 space-y-5">

          {/* Performance metrics */}
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                    <BarChart2 className="w-4 h-4 text-primary" />
                    Performance Metrics
                  </CardTitle>
                  <CardDescription className="font-mono text-xs mt-0.5">Prediction intelligence summary</CardDescription>
                </div>
                <Link href="/analytics">
                  <Button variant="ghost" size="sm" className="font-mono text-xs gap-1">
                    Details <ChevronRight className="w-3 h-3" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {isLoadingSummary ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="bg-background/50 rounded-lg p-4 border border-border">
                      <Skeleton className="h-2.5 w-24 mb-2" />
                      <Skeleton className="h-7 w-20" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    { label: "Total Predictions", value: summary?.total_predictions ?? 0, color: "" },
                    { label: "Accuracy Rate",      value: `${((summary?.accuracy_rate ?? 0) * 100).toFixed(1)}%`, color: "text-primary" },
                    { label: "ROI",                value: `${(summary?.roi ?? 0) >= 0 ? "+" : ""}${Number(summary?.roi ?? 0).toFixed(2)}`, color: (summary?.roi ?? 0) >= 0 ? "text-green-400" : "text-destructive" },
                    { label: "Staked VIT",          value: Number(system?.economy?.total_staked_vit ?? 0).toLocaleString(), color: "text-secondary" },
                    { label: "Net Profit",          value: `${(system?.economy?.total_profit ?? 0) >= 0 ? "+" : ""}$${Number(system?.economy?.total_profit ?? 0).toFixed(2)}`, color: (system?.economy?.total_profit ?? 0) >= 0 ? "text-green-400" : "text-destructive" },
                    { label: "VIT Price",            value: `$${Number(price?.price ?? 0).toFixed(8)}`, color: "" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="bg-background/50 rounded-lg p-3 border border-border/50">
                      <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1.5">{label}</div>
                      <div className={`text-xl font-bold font-mono ${color}`}>{value}</div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI Transparency */}
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                  <Brain className="w-4 h-4 text-purple-400" />
                  AI Ensemble Status
                </CardTitle>
                <Badge className="font-mono text-[10px] border-purple-500/30 bg-purple-500/10 text-purple-400">
                  12 Models Active
                </Badge>
              </div>
              <CardDescription className="font-mono text-xs mt-0.5">Live model confidence for next predicted match</CardDescription>
            </CardHeader>
            <CardContent>
              <AIConfidenceWidget />
            </CardContent>
          </Card>

          {/* Top Opportunities */}
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-3">
              <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                <Target className="w-4 h-4 text-green-400" />
                Top Opportunities
              </CardTitle>
              <CardDescription className="font-mono text-xs">AI edge sorted by value</CardDescription>
            </CardHeader>
            <CardContent>
              <TopOpportunitiesWidget />
            </CardContent>
          </Card>
        </div>

        {/* Right: Gamification + Activity */}
        <div className="space-y-5">
          {/* Level card */}
          <LevelCard
            xp={xp}
            predictions={summary?.total_predictions ?? 0}
            winRate={summary?.accuracy_rate ?? 0}
            streak={summary?.streak ?? 0}
          />

          {/* Activity log */}
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-3">
              <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                System Log
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingActivity ? (
                <div className="space-y-4">
                  {Array.from({ length: 4 }).map((_, i) => <ActivityItemSkeleton key={i} />)}
                </div>
              ) : activityList.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-center space-y-2">
                  <div className="rounded-full border border-border/50 bg-muted/30 p-2.5">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <p className="text-xs font-mono text-muted-foreground">No events yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {activityList.slice(0, 6).map((act: any) => (
                    <div key={act.id} className="flex items-start gap-2.5 text-sm">
                      <div className="mt-0.5 p-1.5 rounded bg-muted/50 flex-shrink-0">
                        <Clock className="w-3 h-3 text-muted-foreground" />
                      </div>
                      <div className="flex-1 space-y-0.5 min-w-0">
                        <p className="font-mono text-xs text-muted-foreground truncate">{act.description}</p>
                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground/70 font-mono">
                          <span>{format(new Date(act.created_at), "HH:mm:ss")}</span>
                          {act.outcome && (
                            <>
                              <span>·</span>
                              <Badge
                                variant={act.outcome === act.bet_side ? "default" : "destructive"}
                                className="text-[8px] uppercase px-1 py-0"
                              >
                                {act.outcome === act.bet_side ? "WIN" : "LOSS"}
                              </Badge>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Achievements */}
          <AchievementBadges achievements={achievementsData?.achievements} />
        </div>
      </div>

      {/* ── Leaderboard ─────────────────────────────────── */}
      <Leaderboard
        entries={leaderboardData?.leaderboard?.map((e: any) => ({
          ...e,
          winRate: e.winRate ?? e.win_rate ?? 0,
        }))}
        currentUsername={user?.username}
      />

      {/* ── Mobile FAB ──────────────────────────────────── */}
      <QuickActionsFAB />
    </div>
  );
}
