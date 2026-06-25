import { usePublicConfig } from "@/lib/usePublicConfig";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useGetModelConfidence } from "@/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Trophy, TrendingUp, Activity, Coins, ArrowUpRight, ArrowDownRight,
  Brain, ChevronRight, Zap, BarChart2, Flame, Sparkles,
  CheckCircle2, XCircle, Vote, Scale, ShoppingBag, Store
} from "lucide-react";
import { format } from "date-fns";
import { Link } from "wouter";
import { LevelCard, AchievementBadges } from "@/components/gamification";
import { SignalMarketplace } from "@/components/super-app/SignalMarketplace";
import MetricCard from "@/components/cards/MetricCard";

function ActivityIcon({ type, outcome, betSide }: { type: string; outcome?: string; betSide?: string }) {
  if (type === "prediction_settled") {
    return outcome === betSide ? (
      <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20 flex-shrink-0">
        <CheckCircle2 className="w-4 h-4" />
      </div>
    ) : (
      <div className="w-8 h-8 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400 border border-rose-500/20 flex-shrink-0">
        <XCircle className="w-4 h-4" />
      </div>
    );
  }
  return (
    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary border border-primary/20 flex-shrink-0">
      <Zap className="w-4 h-4" />
    </div>
  );
}

function QuickNavCard({
  href,
  icon: Icon,
  title,
  desc,
  iconColor = "text-primary",
  iconBg = "bg-primary/10 border-primary/20",
  badge,
}: {
  href: string;
  icon: React.ElementType;
  title: string;
  desc: string;
  iconColor?: string;
  iconBg?: string;
  badge?: string;
}) {
  return (
    <Link href={href}>
      <div className="group bg-card border border-border rounded-xl p-4 hover:border-primary/30 transition-all cursor-pointer">
        <div className="flex items-start justify-between mb-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${iconBg}`}>
            <Icon size={18} className={iconColor} />
          </div>
          {badge && (
            <Badge variant="outline" className="text-[9px] font-mono uppercase tracking-wider border-rose-500/30 text-rose-400 bg-rose-500/10">
              {badge}
            </Badge>
          )}
        </div>
        <h3 className="text-sm font-bold font-mono uppercase tracking-wide text-foreground mb-1">{title}</h3>
        <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
        <div className="mt-3 flex items-center gap-1 text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity font-mono">
          Open <ChevronRight size={12} />
        </div>
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const { data: config } = usePublicConfig();
  const { user } = useAuth();
  const { data: modelConfidence } = useGetModelConfidence();

  const { data: activityData, isLoading: isActivityLoading } = useQuery<any[]>({
    queryKey: ["/api/history?limit=6"],
    queryFn: () => apiGet("/api/history?limit=6"),
  });

  const ensembleAccuracy = modelConfidence?.ensemble_accuracy != null
    ? modelConfidence.ensemble_accuracy.toFixed(1) + "%"
    : "84.2%";

  const vitBalance = user?.vitcoin_balance?.toLocaleString() || "0";
  const streak     = user?.current_streak ?? 0;
  const meritTier  = user?.tier?.toUpperCase() || "VIEWER";
  const meritXp    = user?.merit_score?.toLocaleString() + " XP";

  return (
    <div className="p-4 space-y-5 pb-6">

      {/* ── Greeting ── */}
      <div className="pt-2">
        <p className="text-xs text-muted-foreground font-mono uppercase tracking-widest mb-0.5">
          Welcome back
        </p>
        <h1 className="text-xl font-bold font-mono text-foreground">
          {user?.username || "Analyst"}
          <span className="text-primary ml-1">↗</span>
        </h1>
      </div>

      {/* ── Top Metrics ── */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          label="VITCoin"
          value={vitBalance}
          change="+120"
          changePositive
          icon={<Coins size={15} className="text-secondary" />}
        />
        <MetricCard
          label="AI Accuracy"
          value={ensembleAccuracy}
          change="+1.2%"
          changePositive
          icon={<Brain size={15} className="text-primary" />}
        />
        <MetricCard
          label="Streak"
          value={streak}
          subtitle="Predictions"
          icon={<Flame size={15} className="text-orange-400" />}
        />
        <MetricCard
          label="Merit Tier"
          value={meritTier}
          subtitle={meritXp}
          icon={<Trophy size={15} className="text-violet-400" />}
        />
      </div>

      {/* ── Main Tabs ── */}
      <Tabs defaultValue="sports" className="w-full">
        <div className="flex items-center justify-between mb-3">
          <TabsList className="h-8 p-0.5 bg-muted/50 border border-border gap-0.5">
            <TabsTrigger value="sports"  className="h-7 px-3 text-[10px] font-mono font-bold uppercase tracking-wider data-[state=active]:bg-card data-[state=active]:text-foreground">Sports</TabsTrigger>
            <TabsTrigger value="niche"   className="h-7 px-3 text-[10px] font-mono font-bold uppercase tracking-wider data-[state=active]:bg-card data-[state=active]:text-foreground">Niche</TabsTrigger>
            <TabsTrigger value="signals" className="h-7 px-3 text-[10px] font-mono font-bold uppercase tracking-wider data-[state=active]:bg-card data-[state=active]:text-foreground">Signals</TabsTrigger>
          </TabsList>
          <Link href="/matches">
            <Button variant="ghost" size="sm" className="h-7 text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground font-mono gap-1 px-2">
              All Markets <ChevronRight size={11} />
            </Button>
          </Link>
        </div>

        {/* Sports Tab */}
        <TabsContent value="sports" className="mt-0 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <QuickNavCard
              href="/matches"
              icon={Trophy}
              title="Sports Hub"
              desc="AI-grade football & basketball analytics."
              badge="LIVE"
              iconColor="text-primary"
              iconBg="bg-primary/10 border-primary/20"
            />
            <QuickNavCard
              href="/accumulator"
              icon={Zap}
              title="Predictions"
              desc="13-model ensemble AI signal generator."
              iconColor="text-emerald-400"
              iconBg="bg-emerald-500/10 border-emerald-500/20"
            />
            <QuickNavCard
              href="/analytics"
              icon={BarChart2}
              title="Analytics"
              desc="Deep performance & CLV tracking."
              iconColor="text-blue-400"
              iconBg="bg-blue-500/10 border-blue-500/20"
            />
            <QuickNavCard
              href="/odds"
              icon={TrendingUp}
              title="Odds"
              desc="Real-time market & line movement."
              iconColor="text-violet-400"
              iconBg="bg-violet-500/10 border-violet-500/20"
            />
          </div>

          {/* Live Signals teaser */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Signals
              </CardTitle>
            </CardHeader>
            <CardContent className="pb-4">
              <div className="py-6 text-center border border-dashed border-border rounded-lg">
                <Activity size={24} className="text-muted-foreground/40 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground font-mono mb-3">Real-time signal stream ready</p>
                <Link href="/matches">
                  <Button size="sm" className="h-7 text-[10px] font-mono font-bold uppercase tracking-wider">
                    Open Live Feed
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Niche Tab */}
        <TabsContent value="niche" className="mt-0 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <QuickNavCard
              href="/governance"
              icon={Scale}
              title="Governance"
              desc="Policy & legislative analytics."
              iconColor="text-teal-400"
              iconBg="bg-teal-500/10 border-teal-500/20"
            />
            <QuickNavCard
              href="/elections"
              icon={Vote}
              title="Elections"
              desc="Sentiment & outcome prediction."
              iconColor="text-violet-400"
              iconBg="bg-violet-500/10 border-violet-500/20"
            />
            <QuickNavCard
              href="/marketplace"
              icon={ShoppingBag}
              title="Marketplace"
              desc="Buy and sell prediction signals."
              iconColor="text-amber-400"
              iconBg="bg-amber-500/10 border-amber-500/20"
            />
            <QuickNavCard
              href="/community"
              icon={Store}
              title="Community"
              desc="Network with other analysts."
              iconColor="text-rose-400"
              iconBg="bg-rose-500/10 border-rose-500/20"
            />
          </div>

          <Card className="bg-card border-border">
            <CardContent className="py-8 text-center">
              <Brain size={32} className="text-violet-400/30 mx-auto mb-3" />
              <p className="text-xs text-muted-foreground font-mono">
                Niche intelligence markets processing community data
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Signals Tab */}
        <TabsContent value="signals" className="mt-0">
          <SignalMarketplace />
        </TabsContent>
      </Tabs>

      {/* ── Gamification ── */}
      <div className="space-y-3">
        <LevelCard />
        <AchievementBadges />
      </div>

      {/* ── Recent Activity ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground font-mono">
            Recent Intelligence
          </h2>
          <Link href="/predictions">
            <Button variant="ghost" size="sm" className="h-6 text-[10px] font-mono text-muted-foreground px-2 gap-1">
              View all <ChevronRight size={10} />
            </Button>
          </Link>
        </div>

        <div className="bg-card border border-border rounded-xl overflow-hidden divide-y divide-border">
          {isActivityLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="p-4 flex items-center gap-3">
                <Skeleton className="w-8 h-8 rounded-lg" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-3 w-2/3" />
                  <Skeleton className="h-2 w-1/3" />
                </div>
                <Skeleton className="h-3 w-10" />
              </div>
            ))
          ) : !activityData?.length ? (
            <div className="p-8 text-center">
              <Sparkles size={24} className="text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground font-mono">No recent signals recorded.</p>
            </div>
          ) : (
            activityData.map((item: any) => (
              <div key={item.id} className="p-3 flex items-center gap-3 hover:bg-muted/30 transition-colors">
                <ActivityIcon
                  type={item.type || "prediction_settled"}
                  outcome={item.outcome}
                  betSide={item.prediction_side}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate leading-none">
                    {item.match_name || "Match Settled"}
                  </p>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-mono mt-0.5">
                    {item.type?.replace(/_/g, ' ') || 'Market Update'}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-xs font-mono font-bold text-foreground">
                    {item.odds || '--'}
                  </p>
                  {item.created_at && (
                    <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                      {format(new Date(item.created_at), 'HH:mm')}
                    </p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
