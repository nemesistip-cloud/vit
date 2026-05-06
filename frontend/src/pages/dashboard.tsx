import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useGetTopOpportunities, useGetModelConfidence } from "@/api-client";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Trophy, TrendingUp, Activity, Coins, ArrowUpRight, ArrowDownRight,
  Clock, Globe, Users, ShieldCheck, Brain, ChevronRight, Zap,
  BarChart2, Target, CreditCard, Flame, Sparkles, CheckCircle2,
  XCircle, Minus, AlertTriangle,
} from "lucide-react";
import { format } from "date-fns";
import { Link } from "wouter";
import { LevelCard, AchievementBadges, Leaderboard, StreakCounter } from "@/components/gamification";

/* ── Skeleton helpers ─────────────────────────────────── */
function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-2.5 w-20" />
        <Skeleton className="h-6 w-6 rounded-lg" />
      </div>
      <Skeleton className="h-8 w-28" />
      <Skeleton className="h-2 w-16" />
    </div>
  );
}

function MiniStatSkeleton() {
  return (
    <div className="rounded-lg border border-border/40 bg-card/30 p-3 space-y-1.5">
      <Skeleton className="h-2 w-16" />
      <Skeleton className="h-5 w-12" />
    </div>
  );
}

function ActivityItemSkeleton() {
  return (
    <div className="flex items-start gap-3">
      <Skeleton className="h-7 w-7 rounded-lg flex-shrink-0" />
      <div className="flex-1 space-y-1.5 pt-0.5">
        <Skeleton className="h-2.5 w-full" />
        <Skeleton className="h-2 w-20" />
      </div>
    </div>
  );
}

/* ── AI Confidence Widget ─────────────────────────────── */
function AIConfidenceWidget() {
  const { data, isLoading, isError } = useGetModelConfidence();
  const displayModels   = data?.models?.slice(0, 6) ?? [];
  const ensembleAccuracy = data?.ensemble_accuracy ?? 0;
  const activeCount      = data?.active_count ?? 0;

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex justify-between">
              <Skeleton className="h-2.5 w-28" />
              <Skeleton className="h-2.5 w-10" />
            </div>
            <Skeleton className="h-1.5 w-full rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-4 text-xs font-mono text-destructive/70">
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
      {displayModels.map((m: any) => (
        <div key={m.key}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-mono text-muted-foreground">{m.name}</span>
            <div className="flex items-center gap-2">
              {m.predictions > 0 && (
                <span className="text-[10px] font-mono text-muted-foreground/50">{m.predictions} pred</span>
              )}
              <span className="text-xs font-mono text-primary font-bold">{m.accuracy.toFixed(1)}%</span>
            </div>
          </div>
          <div className="h-1.5 bg-muted/50 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-purple-400 transition-all duration-700"
              style={{ width: `${Math.min(m.accuracy, 100)}%` }}
            />
          </div>
        </div>
      ))}
      <div className="pt-2 border-t border-border/40 flex items-center justify-between">
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
          <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg border border-border/30 bg-card/20">
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-2.5 w-36" />
              <Skeleton className="h-2 w-20" />
            </div>
            <div className="space-y-1 text-right">
              <Skeleton className="h-2.5 w-10 ml-auto" />
              <Skeleton className="h-2 w-8 ml-auto" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (isError || opportunities.length === 0) {
    return (
      <div className="space-y-3">
        <div className="text-center py-6">
          <Target className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
          <p className="text-xs font-mono text-muted-foreground">
            {isError ? "Predictions not available yet." : "No live opportunities — make predictions to find value bets."}
          </p>
        </div>
        <Link href="/matches">
          <Button variant="outline" size="sm" className="w-full font-mono text-xs gap-1.5">
            Browse Matches <ChevronRight className="w-3 h-3" />
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {opportunities.map((o: any) => (
        <Link key={o.prediction_id} href={`/matches/${o.match_id}`}>
          <div className="flex items-center gap-3 p-2.5 rounded-lg border border-border/30 bg-card/20 hover:border-primary/25 hover:bg-primary/5 transition-all cursor-pointer group">
            <div className="flex-1 min-w-0">
              <div className="text-xs font-mono font-medium truncate text-foreground group-hover:text-primary transition-colors">{o.match}</div>
              <div className="text-[10px] font-mono text-muted-foreground mt-0.5">{o.time}</div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className={`text-xs font-mono font-bold ${o.edge_value >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{o.edge}</div>
              <div className="text-[10px] font-mono text-muted-foreground">AI: {o.ai_confidence}%</div>
            </div>
            <ChevronRight className="w-3 h-3 text-muted-foreground/40 group-hover:text-primary transition-colors flex-shrink-0" />
          </div>
        </Link>
      ))}
      <Link href="/matches">
        <Button variant="ghost" size="sm" className="w-full font-mono text-xs text-muted-foreground mt-1 gap-1 hover:text-foreground">
          View all opportunities <ChevronRight className="w-3 h-3" />
        </Button>
      </Link>
    </div>
  );
}

/* ── Activity icon helper ─────────────────────────────── */
function ActivityIcon({ type, outcome, betSide }: { type?: string; outcome?: string; betSide?: string }) {
  const won = outcome && betSide && outcome === betSide;
  const lost = outcome && betSide && outcome !== betSide;

  if (won)  return <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3 text-emerald-400" /></div>;
  if (lost) return <div className="p-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20"><XCircle className="w-3 h-3 text-rose-400" /></div>;
  if (type === "prediction") return <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20"><Target className="w-3 h-3 text-primary" /></div>;
  if (type === "login") return <div className="p-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20"><Zap className="w-3 h-3 text-blue-400" /></div>;
  return <div className="p-1.5 rounded-lg bg-muted/40 border border-border/50"><Clock className="w-3 h-3 text-muted-foreground" /></div>;
}

/* ── Quick Actions FAB (mobile) ───────────────────────── */
function QuickActionsFAB() {
  return (
    <div className="fixed bottom-20 right-5 z-50 md:hidden">
      <Link href="/matches">
        <button className="w-12 h-12 bg-primary text-primary-foreground rounded-full shadow-xl vit-glow-cyan flex items-center justify-center active:scale-95 transition-transform">
          <Zap className="w-5 h-5" />
        </button>
      </Link>
    </div>
  );
}

/* ── KPI Card ─────────────────────────────────────────── */
function KPICard({
  label, value, sub, icon: Icon, accentClass, borderClass, iconBg,
}: {
  label: string;
  value: React.ReactNode;
  sub: string;
  icon: React.ElementType;
  accentClass: string;
  borderClass: string;
  iconBg: string;
}) {
  return (
    <div className={`rounded-xl border ${borderClass} bg-card/40 backdrop-blur p-4 space-y-3 hover:bg-card/60 transition-colors`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">{label}</span>
        <div className={`w-7 h-7 rounded-lg ${iconBg} flex items-center justify-center`}>
          <Icon className={`w-3.5 h-3.5 ${accentClass}`} />
        </div>
      </div>
      <div className={`text-2xl font-bold font-mono ${accentClass} vit-metric`}>{value}</div>
      <div className="text-[10px] font-mono text-muted-foreground/70">{sub}</div>
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────── */
export default function DashboardPage() {
  const { user } = useAuth();
  const { data: publicCfg } = usePublicConfig();

  const { data: summary, isLoading: isLoadingSummary, isError: isErrorSummary } = useQuery<any>({
    queryKey: ["dashboard-summary"],
    queryFn:  () => apiGet<any>("/api/dashboard/summary"),
    refetchInterval: 30_000,
  });

  const { data: price, isLoading: isLoadingPrice } = useQuery<any>({
    queryKey: ["dashboard-price"],
    queryFn:  () => apiGet<any>("/api/dashboard/vitcoin-price"),
    refetchInterval: 60_000,
  });

  const { data: activity, isLoading: isLoadingActivity, isError: isErrorActivity } = useQuery<any[]>({
    queryKey: ["dashboard-activity"],
    queryFn:  () => apiGet<any[]>("/api/dashboard/recent-activity"),
    refetchInterval: 30_000,
  });

  const { data: system, isLoading: isLoadingSystem, isError: isErrorSystem } = useQuery<any>({
    queryKey: ["dashboard-system"],
    queryFn:  () => apiGet<any>("/system/status"),
    refetchInterval: 60_000,
  });

  const { data: leaderboardData } = useQuery<any>({
    queryKey: ["dashboard-leaderboard"],
    queryFn:  () => apiGet<any>("/api/dashboard/leaderboard"),
    refetchInterval: 120_000,
  });

  const { data: achievementsData } = useQuery<any>({
    queryKey: ["dashboard-achievements"],
    queryFn:  () => apiGet<any>("/api/dashboard/achievements"),
    refetchInterval: 120_000,
  });

  const { data: planData } = useQuery<any>({
    queryKey: ["dashboard-plan"],
    queryFn:  () => apiGet<any>("/subscription/my-plan"),
    refetchInterval: 300_000,
  });

  const activityList = Array.isArray(activity) ? activity : [];
  const change24h    = price?.change_24h ?? 0;
  const isLoadingCards = isLoadingSummary || isLoadingPrice;

  const accuracyRate = summary?.accuracy_rate ?? 0;
  const xp = Math.floor((summary?.total_predictions ?? 0) * 10 + accuracyRate * 100);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="space-y-6 pb-20 md:pb-6 vit-animate-fade-in">

      {/* ── Welcome Header ──────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pt-1">
        <div>
          <h1 className="text-xl md:text-2xl font-mono font-bold tracking-tight leading-tight">
            {greeting},{" "}
            <span className="vit-gradient-text">{user?.username ?? "Operator"}</span>
          </h1>
          <p className="text-muted-foreground font-mono text-xs flex items-center gap-1.5 mt-1.5">
            <span className="vit-live-dot" />
            Live feeds active · auto-refreshes every 30s
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StreakCounter streak={summary?.streak ?? 0} />
          <Link href="/matches">
            <Button size="sm" className="font-mono gap-1.5 text-xs vit-glow-cyan-s hidden sm:flex">
              <Zap className="w-3 h-3" />
              New Prediction
            </Button>
          </Link>
        </div>
      </div>

      {/* ── KPI Row ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {isLoadingCards ? (
          Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)
        ) : isErrorSummary ? (
          <div className="col-span-2 lg:col-span-4 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-xs font-mono text-destructive flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            Could not load summary — retrying automatically.
          </div>
        ) : (
          <>
            <KPICard
              label="Accuracy"
              value={`${(accuracyRate * 100).toFixed(1)}%`}
              sub={`${summary?.total_predictions ?? 0} total predictions`}
              icon={Trophy}
              accentClass="text-primary"
              borderClass="border-primary/20"
              iconBg="bg-primary/10"
            />
            <KPICard
              label="VIT Balance"
              value={Number(summary?.wallet_balance ?? 0).toLocaleString()}
              sub="VITCoin in wallet"
              icon={Coins}
              accentClass="text-yellow-400"
              borderClass="border-yellow-400/20"
              iconBg="bg-yellow-400/10"
            />
            <KPICard
              label="Active Matches"
              value={summary?.active_matches ?? 0}
              sub="Awaiting settlement"
              icon={Activity}
              accentClass="text-blue-400"
              borderClass="border-blue-400/20"
              iconBg="bg-blue-400/10"
            />
            <KPICard
              label="Active Plan"
              value={planData?.plan?.display_name ?? "Free"}
              sub={`${planData?.usage?.predictions_today ?? 0}${planData?.usage?.limit_today != null ? `/${planData.usage.limit_today}` : ""} preds today`}
              icon={CreditCard}
              accentClass="text-purple-400"
              borderClass="border-purple-400/20"
              iconBg="bg-purple-400/10"
            />
          </>
        )}
      </div>

      {/* ── Network Health Strip ─────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {isLoadingSystem ? (
          Array.from({ length: 4 }).map((_, i) => <MiniStatSkeleton key={i} />)
        ) : system ? (
          [
            {
              label: "Total Users",
              value: (system.users?.total ?? system.total_users ?? 0).toLocaleString(),
              icon: Users,
              color: "text-foreground",
            },
            {
              label: "Active (30d)",
              value: (system.users?.active_30d ?? system.active_users_30d ?? 0).toLocaleString(),
              icon: Activity,
              color: "text-emerald-400",
            },
            {
              label: "Validators",
              value: (system.users?.validators ?? system.active_validators ?? 0).toLocaleString(),
              icon: ShieldCheck,
              color: "text-yellow-400",
            },
            {
              label: "VIT Price",
              value: `$${Number(price?.price ?? price?.price_usd ?? 0.001).toFixed(5)}`,
              icon: change24h >= 0 ? ArrowUpRight : ArrowDownRight,
              color: change24h >= 0 ? "text-emerald-400" : "text-rose-400",
            },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="rounded-lg border border-border/30 bg-card/20 px-3 py-2.5 flex items-center justify-between gap-2">
              <div>
                <div className="text-[9px] font-mono text-muted-foreground/60 uppercase tracking-wider">{label}</div>
                <div className={`text-sm font-bold font-mono mt-0.5 ${color} vit-metric`}>{value}</div>
              </div>
              <Icon className={`w-3.5 h-3.5 ${color} opacity-40 flex-shrink-0`} />
            </div>
          ))
        ) : null}
      </div>

      {/* ── Main 2-col grid ─────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* ── Left column (2/3) ─────────────────────────── */}
        <div className="lg:col-span-2 space-y-5">

          {/* Performance metrics */}
          <Card className="bg-card/40 backdrop-blur border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="font-mono text-sm flex items-center gap-2">
                    <BarChart2 className="w-4 h-4 text-primary" />
                    Performance Metrics
                  </CardTitle>
                  <CardDescription className="font-mono text-xs mt-0.5">Prediction intelligence summary</CardDescription>
                </div>
                <Link href="/analytics">
                  <Button variant="ghost" size="sm" className="font-mono text-xs gap-1 text-muted-foreground hover:text-foreground h-7">
                    Details <ChevronRight className="w-3 h-3" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {isLoadingSummary ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="bg-background/40 rounded-lg p-3 border border-border/30 space-y-2">
                      <Skeleton className="h-2 w-20" />
                      <Skeleton className="h-6 w-16" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    {
                      label: "Total Predictions",
                      value: (summary?.total_predictions ?? 0).toLocaleString(),
                      color: "",
                      sub: "all-time",
                    },
                    {
                      label: "Accuracy Rate",
                      value: `${(accuracyRate * 100).toFixed(1)}%`,
                      color: "text-primary",
                      sub: "win rate",
                    },
                    {
                      label: "ROI",
                      value: `${(summary?.roi ?? 0) >= 0 ? "+" : ""}${Number(summary?.roi ?? 0).toFixed(2)}`,
                      color: (summary?.roi ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400",
                      sub: "return on investment",
                    },
                    {
                      label: "Staked VIT",
                      value: Number(system?.economy?.total_staked_vit ?? 0).toLocaleString(),
                      color: "text-yellow-400",
                      sub: "platform-wide",
                    },
                    {
                      label: "Net Profit",
                      value: `${(system?.economy?.total_profit ?? 0) >= 0 ? "+" : ""}$${Number(system?.economy?.total_profit ?? 0).toFixed(2)}`,
                      color: (system?.economy?.total_profit ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400",
                      sub: "USD equivalent",
                    },
                    {
                      label: "VIT Price",
                      value: `$${Number(price?.price ?? price?.price_usd ?? 0).toFixed(8)}`,
                      color: change24h >= 0 ? "text-emerald-400" : "text-rose-400",
                      sub: `${change24h >= 0 ? "+" : ""}${Number(change24h).toFixed(2)}% 24h`,
                    },
                  ].map(({ label, value, color, sub }) => (
                    <div key={label} className="bg-background/30 rounded-lg p-3 border border-border/30 group hover:border-border/60 transition-colors">
                      <div className="text-[9px] font-mono text-muted-foreground/60 uppercase tracking-wider mb-1.5">{label}</div>
                      <div className={`text-lg font-bold font-mono vit-metric ${color}`}>{value}</div>
                      <div className="text-[9px] font-mono text-muted-foreground/40 mt-0.5">{sub}</div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI Ensemble */}
          <Card className="bg-card/40 backdrop-blur border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="font-mono text-sm flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-400" />
                    AI Ensemble Status
                  </CardTitle>
                  <CardDescription className="font-mono text-xs mt-0.5">Live model confidence per active match</CardDescription>
                </div>
                <Badge className="font-mono text-[9px] border-purple-500/25 bg-purple-500/10 text-purple-400 gap-1">
                  <Sparkles className="w-2.5 h-2.5" />
                  {publicCfg?.platform.model_count ?? 13} Models
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <AIConfidenceWidget />
            </CardContent>
          </Card>

          {/* Top Opportunities */}
          <Card className="bg-card/40 backdrop-blur border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="font-mono text-sm flex items-center gap-2">
                    <Target className="w-4 h-4 text-emerald-400" />
                    Top Opportunities
                  </CardTitle>
                  <CardDescription className="font-mono text-xs mt-0.5">AI edge sorted by value</CardDescription>
                </div>
                <Link href="/predictions">
                  <Button variant="ghost" size="sm" className="font-mono text-xs gap-1 text-muted-foreground hover:text-foreground h-7">
                    All <ChevronRight className="w-3 h-3" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <TopOpportunitiesWidget />
            </CardContent>
          </Card>
        </div>

        {/* ── Right column (1/3) ────────────────────────── */}
        <div className="space-y-5">

          {/* Level card */}
          <LevelCard
            xp={xp}
            predictions={summary?.total_predictions ?? 0}
            winRate={accuracyRate}
            streak={summary?.streak ?? 0}
          />

          {/* Activity log */}
          <Card className="bg-card/40 backdrop-blur border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                System Log
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingActivity ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => <ActivityItemSkeleton key={i} />)}
                </div>
              ) : isErrorActivity ? (
                <div className="text-center py-6 space-y-2">
                  <AlertTriangle className="w-6 h-6 text-rose-400/40 mx-auto" />
                  <p className="text-xs font-mono text-muted-foreground">Activity feed unavailable</p>
                </div>
              ) : activityList.length === 0 ? (
                <div className="text-center py-6 space-y-2">
                  <Clock className="w-6 h-6 text-muted-foreground/30 mx-auto" />
                  <p className="text-xs font-mono text-muted-foreground">No events yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {activityList.slice(0, 6).map((act: any, i: number) => (
                    <div key={act.id ?? i} className="flex items-start gap-2.5">
                      <ActivityIcon type={act.type} outcome={act.outcome} betSide={act.bet_side} />
                      <div className="flex-1 min-w-0">
                        <p className="font-mono text-xs text-foreground/80 truncate">{act.description}</p>
                        <div className="flex items-center gap-1.5 mt-0.5 text-[9px] text-muted-foreground/50 font-mono">
                          <span>{act.created_at ? format(new Date(act.created_at), "HH:mm:ss") : ""}</span>
                          {act.outcome && (
                            <>
                              <span>·</span>
                              <span className={act.outcome === act.bet_side ? "text-emerald-400" : "text-rose-400"}>
                                {act.outcome === act.bet_side ? "WIN" : "LOSS"}
                              </span>
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
