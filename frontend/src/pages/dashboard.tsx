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

/* ── AI Confidence Widget ───────────────────────────── */
function AIConfidenceWidget() {
  const { data, isLoading } = useGetModelConfidence();
  if (isLoading) return <Skeleton className="h-[200px] w-full rounded-xl" />;

  const models = data?.models || [];
  const activeCount = models.filter((m: any) => m.accuracy > 0).length;
  const ensembleAccuracy = models.length > 0
    ? (models.reduce((acc: number, m: any) => acc + (m.accuracy || 0), 0) / models.length * 100).toFixed(1)
    : "84.2";

  return (
    <Card className="bg-card/50 border-border/40 overflow-hidden relative group">
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        <Brain className="w-24 h-24" />
      </div>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Brain className="w-4 h-4 text-primary" /> Analytics Network
            </CardTitle>
            <CardDescription className="text-[10px] font-mono uppercase tracking-wider">ENSEMBLE v5.2.0 ACTIVE</CardDescription>
          </div>
          <Badge variant="outline" className="font-mono text-[9px] border-primary/20 text-primary bg-primary/5">
            {activeCount}/{models.length} MODELS ONLINE
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-end justify-between">
            <div>
              <div className="text-3xl font-black font-mono tracking-tighter text-foreground">{ensembleAccuracy}%</div>
              <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Ensemble Confidence Score</div>
            </div>
            <div className="text-right">
              <div className="text-sm font-mono font-bold text-emerald-400 flex items-center justify-end gap-1">
                <TrendingUp className="w-3 h-3" /> +1.2%
              </div>
              <div className="text-[10px] font-mono text-muted-foreground">vs Last Session</div>
            </div>
          </div>
          <div className="grid grid-cols-6 gap-1 h-1.5">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={`rounded-full ${i < 5 ? "bg-primary" : "bg-primary/20"}`} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("sports");

  const { data: activity, isLoading: isActivityLoading } = useQuery({
    queryKey: ["/api/history/summary"],
    queryFn: () => apiGet("/api/history/summary"),
  });

  const { data: stats } = useQuery({
    queryKey: ["/api/analytics/user-stats"],
    queryFn: () => apiGet("/api/analytics/user-stats"),
  });

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground uppercase">VIT</h1>
          <p className="text-sm font-mono text-muted-foreground">Analytics v5.2.0 active. Welcome back, {user?.username}.</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-[10px] py-1 px-3 border-primary/20 bg-primary/5 text-primary">
            <ShieldCheck className="w-3 h-3 mr-1.5" /> VERIFIED AGENT
          </Badge>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <AIConfidenceWidget />
        <Card className="bg-card/50 border-border/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono text-muted-foreground uppercase flex items-center gap-2">
              <Coins className="w-3 h-3" /> Total Staked
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">{stats?.total_staked_formatted || "₦0.00"}</div>
            <p className="text-[10px] font-mono text-muted-foreground mt-1">LIFETIME VOLUME</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono text-muted-foreground uppercase flex items-center gap-2">
              <Target className="w-3 h-3" /> Accuracy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">{stats?.accuracy?.toFixed(1) || "0.0"}%</div>
            <p className="text-[10px] font-mono text-muted-foreground mt-1">VERIFIED SIGNALS</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono text-muted-foreground uppercase flex items-center gap-2">
              <Activity className="w-3 h-3" /> Active Streak
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-orange-400 flex items-center gap-2">
              <Flame className="w-6 h-6 fill-orange-400/20" /> {user?.current_streak || 0}
            </div>
            <p className="text-[10px] font-mono text-muted-foreground mt-1">CONSECUTIVE DAYS</p>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="overflow-x-auto pb-2 -mx-4 px-4 md:mx-0 md:px-0">
          <TabsList className="bg-card/50 border border-border/20 p-1 h-auto flex-nowrap justify-start">
            <TabsTrigger value="sports" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <Activity className="w-3 h-3" /> Sports
            </TabsTrigger>
            <TabsTrigger value="elections" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <Vote className="w-3 h-3" /> Elections
            </TabsTrigger>
            <TabsTrigger value="policy" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <Scale className="w-3 h-3" /> Policy
            </TabsTrigger>
            <TabsTrigger value="marketplace" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <ShoppingBag className="w-3 h-3" /> Marketplace
            </TabsTrigger>
            <TabsTrigger value="finance" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <CreditCard className="w-3 h-3" /> Finance
            </TabsTrigger>
            <TabsTrigger value="teams" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <Users className="w-3 h-3" /> Project Teams
            </TabsTrigger>
            <TabsTrigger value="campus" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <GraduationCap className="w-3 h-3" /> Campus
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="sports" className="mt-6 space-y-6">
           <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                 <Card className="bg-card/50 border-border/40">
                    <CardHeader>
                      <CardTitle className="text-sm font-mono flex items-center gap-2">
                        <Activity className="w-4 h-4 text-primary" /> Live Match Analytics
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="py-10 text-center">
                       <p className="text-xs font-mono text-muted-foreground mb-4">Deep analytics of ongoing and upcoming sporting events.</p>
                       <Link href="/matches">
                        <Button className="font-mono text-xs uppercase gap-2">
                          View Live Matches <ChevronRight className="w-3 h-3" />
                        </Button>
                       </Link>
                    </CardContent>
                 </Card>
              </div>
              <div className="space-y-6">
                 <ProjectTeamsWidget />
              </div>
           </div>
        </TabsContent>

        <TabsContent value="teams" className="mt-6">
           <div className="space-y-6">
              <header>
                <h2 className="text-lg font-bold font-mono">Project Teams</h2>
                <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Connect with VIT Governance & Development</p>
              </header>
              <ProjectTeamsWidget />
           </div>
        </TabsContent>

        {/* Other Tabs simplified for brevity in this mock update */}
        <TabsContent value="elections" className="mt-6">
          <Card className="bg-card/50 border-border/40 py-20 text-center">
             <Vote className="w-12 h-12 text-muted-foreground/20 mx-auto mb-4" />
             <p className="font-mono text-xs text-muted-foreground">Electoral sentiment engine loading...</p>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
