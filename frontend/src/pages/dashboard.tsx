import { usePublicConfig } from "@/lib/usePublicConfig";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useGetTopOpportunities, useGetModelConfidence } from "@/api-client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Trophy, TrendingUp, Activity, GraduationCap, Coins, ArrowUpRight, ArrowDownRight,
  Clock, Globe, Users, ShieldCheck, Brain, ChevronRight, Zap,
  BarChart2, Target, CreditCard, Flame, Sparkles, CheckCircle2,
  XCircle, Minus, AlertTriangle, ShoppingBag, Vote, Scale, MessageCircle, Store
} from "lucide-react";
import { format } from "date-fns";
import { Link } from "wouter";
import { LevelCard, AchievementBadges, Leaderboard, StreakCounter } from "@/components/gamification";
import { SignalMarketplace } from "@/components/super-app/SignalMarketplace";
import { AgentPortal } from "@/components/super-app/AgentPortal";
import { ProjectTeamsWidget } from "@/components/ProjectTeamsWidget";
import MetricCard from "@/components/cards/MetricCard";

/* ── Activity Icon helper ────────────────────────────── */
function ActivityIcon({ type, outcome, betSide }: { type: string, outcome?: string, betSide?: string }) {
  if (type === "prediction_settled") {
    return outcome === betSide ? (
      <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
        <CheckCircle2 className="w-4 h-4" />
      </div>
    ) : (
      <div className="w-7 h-7 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400 border border-rose-500/20">
        <XCircle className="w-4 h-4" />
      </div>
    );
  }
  return (
    <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
      <Zap className="w-4 h-4" />
    </div>
  );
}

export default function DashboardPage() {
  const { data: config } = usePublicConfig();
  const { user } = useAuth();
  const { data: modelConfidence, isLoading: isConfidenceLoading } = useGetModelConfidence();
  const { data: stats, isLoading: isStatsLoading } = useQuery<any>({
    queryKey: ["/api/admin/system/health"],
    queryFn: () => apiGet("/api/admin/system/health"),
    staleTime: 30000,
  });

  const { data: activityData, isLoading: isActivityLoading } = useQuery<any[]>({
    queryKey: ["/api/history?limit=5"],
    queryFn: () => apiGet("/api/history?limit=5"),
  });

  const ensembleAccuracy = modelConfidence?.ensemble_accuracy != null
    ? modelConfidence.ensemble_accuracy.toFixed(1) + "%"
    : "84.2%";

  return (
    <div className="space-y-6 pb-20">
      {/* ── Top Metrics ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="VITCoin Balance"
          value={user?.vitcoin_balance?.toLocaleString() || "0"}
          change="+120"
          changePositive={true}
          icon={<Coins size={16} className="text-vit-green" />}
        />
        <MetricCard
          label="Ensemble Accuracy"
          value={ensembleAccuracy}
          change="+1.2%"
          changePositive={true}
          icon={<Brain size={16} className="text-vit-green" />}
        />
        <MetricCard
          label="Current Streak"
          value={user?.current_streak || "0"}
          subtitle="Predictions"
          icon={<Flame size={16} className="text-orange-500" />}
        />
        <MetricCard
          label="Merit Tier"
          value={user?.tier?.toUpperCase() || "VIEWER"}
          subtitle={user?.merit_score?.toLocaleString() + " XP"}
          icon={<Trophy size={16} className="text-vit-purple" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Main Content Area ── */}
        <div className="lg:col-span-2 space-y-6">
          <Tabs defaultValue="sports" className="w-full">
            <div className="flex items-center justify-between mb-4">
               <TabsList className="bg-vit-surface-2 border border-vit-border p-1 h-10">
                <TabsTrigger value="sports" className="px-4 py-1 text-xs font-bold data-[state=active]:bg-vit-surface-3">SPORTS</TabsTrigger>
                <TabsTrigger value="niche" className="px-4 py-1 text-xs font-bold data-[state=active]:bg-vit-surface-3">NICHE</TabsTrigger>
                <TabsTrigger value="signals" className="px-4 py-1 text-xs font-bold data-[state=active]:bg-vit-surface-3">SIGNALS</TabsTrigger>
              </TabsList>
              <Link href="/matches">
                <Button variant="ghost" size="sm" className="text-[10px] uppercase tracking-widest text-vit-text-3 hover:text-vit-text-1">
                  View All Market <ChevronRight size={12} />
                </Button>
              </Link>
            </div>

            <TabsContent value="sports" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Link href="/matches">
                  <div className="bg-vit-surface border border-vit-border rounded-xl p-5 hover:border-vit-green/30 transition-all cursor-pointer group">
                    <div className="flex justify-between items-start mb-4">
                      <div className="w-10 h-10 rounded-lg bg-vit-green-glow flex items-center justify-center text-vit-green border border-vit-green/20">
                        <Trophy size={20} />
                      </div>
                      <Badge className="bg-vit-negative/10 text-vit-negative border-vit-negative/20 text-[9px]">LIVE</Badge>
                    </div>
                    <h3 className="font-display text-lg font-bold text-vit-text-1 mb-1">SPORTS ANALYSIS HUB</h3>
                    <p className="text-xs text-vit-text-3">Institutional-grade analytics for football & basketball markets.</p>
                  </div>
                </Link>

                <Link href="/accumulator">
                  <div className="bg-vit-surface border border-vit-border rounded-xl p-5 hover:border-vit-green/30 transition-all cursor-pointer group">
                    <div className="flex justify-between items-start mb-4">
                      <div className="w-10 h-10 rounded-lg bg-vit-green-glow flex items-center justify-center text-vit-green border border-vit-green/20">
                        <Zap size={20} />
                      </div>
                    </div>
                    <h3 className="font-display text-lg font-bold text-vit-text-1 mb-1">PREDICTION CENTER</h3>
                    <p className="text-xs text-vit-text-3">Generate high-confidence slips with 13-model AI ensemble.</p>
                  </div>
                </Link>
              </div>

              <Card className="bg-vit-surface border-vit-border">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-display font-bold flex items-center gap-2">
                    <Activity size={16} className="text-vit-green" /> LIVE SIGNALS
                  </CardTitle>
                </CardHeader>
                <CardContent>
                   <div className="py-8 text-center border-2 border-dashed border-vit-border rounded-lg">
                      <p className="text-xs text-vit-text-3 mb-4 font-mono">Real-time signal stream initializing...</p>
                      <Link href="/matches">
                        <Button size="sm" className="bg-vit-green text-vit-text-inverse font-bold">
                          OPEN LIVE FEED
                        </Button>
                      </Link>
                   </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="niche" className="space-y-4">
               <div className="grid grid-cols-2 gap-4">
                  <Link href="/governance">
                    <div className="bg-vit-surface border border-vit-border rounded-xl p-4 hover:border-vit-purple/30 transition-all cursor-pointer">
                      <Scale size={20} className="text-vit-purple mb-2" />
                      <h4 className="text-sm font-bold">Governance</h4>
                    </div>
                  </Link>
                  <Link href="/elections">
                    <div className="bg-vit-surface border border-vit-border rounded-xl p-4 hover:border-vit-purple/30 transition-all cursor-pointer">
                      <Vote size={20} className="text-vit-purple mb-2" />
                      <h4 className="text-sm font-bold">Elections</h4>
                    </div>
                  </Link>
               </div>
               <Card className="bg-vit-surface border-vit-border">
                <CardHeader>
                  <CardTitle className="text-sm font-display font-bold">AI SENTIMENT ANALYSIS</CardTitle>
                </CardHeader>
                <CardContent className="py-10 text-center">
                  <Brain size={40} className="text-vit-purple/30 mx-auto mb-4" />
                  <p className="text-xs text-vit-text-3">Niche intelligence markets are processing community data.</p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="signals">
              <SignalMarketplace />
            </TabsContent>
          </Tabs>

          <div className="space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-vit-text-3 px-1">Recent Intelligence</h2>
            <div className="bg-vit-surface border border-vit-border rounded-xl divide-y divide-vit-border overflow-hidden">
               {isActivityLoading ? (
                 <div className="p-10 text-center text-xs text-vit-text-3">Loading history...</div>
               ) : activityData?.length === 0 ? (
                 <div className="p-10 text-center text-xs text-vit-text-3">No recent signals recorded.</div>
               ) : activityData?.map((item: any) => (
                 <div key={item.id} className="p-4 flex items-center gap-4 hover:bg-vit-surface-2 transition-colors">
                    <ActivityIcon type={item.type || "prediction_settled"} outcome={item.outcome} betSide={item.prediction_side} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-vit-text-1 truncate">{item.match_name || "Match Settled"}</p>
                      <p className="text-[10px] text-vit-text-3 uppercase tracking-wider">{item.type?.replace('_', ' ') || 'Market Update'}</p>
                    </div>
                    <div className="text-right">
                       <p className="text-xs font-mono font-bold text-vit-text-1">{item.odds || '--'}</p>
                       <p className="text-[10px] text-vit-text-3">{format(new Date(item.created_at), 'HH:mm')}</p>
                    </div>
                 </div>
               ))}
            </div>
          </div>
        </div>

        {/* ── Sidebar Stats ── */}
        <div className="space-y-6">
           <LevelCard />
           <AchievementBadges />
           <ProjectTeamsWidget />
        </div>
      </div>
    </div>
  );
}
