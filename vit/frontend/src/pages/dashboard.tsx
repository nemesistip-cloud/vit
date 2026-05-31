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
    ? models.reduce((acc: number, m: any) => acc + (m.accuracy || 0), 0) / models.length
    : 0;

  return (
    <div className="space-y-4">
      {models.slice(0, 4).map((m: any) => (
        <div key={m.name} className="space-y-1.5">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-mono text-muted-foreground">{m.name}</span>
            <span className="text-xs font-mono text-primary font-bold">{m.accuracy.toFixed(1)}%</span>
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

  if (isLoading) return <Skeleton className="h-[150px] w-full" />;

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
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("campus");

  const { data: summary } = useQuery<any>({
    queryKey: ["ticker-summary"],
    queryFn:  () => apiGet<any>("/api/dashboard/summary"),
  });

  const { data: system } = useQuery<any>({
    queryKey: ["ticker-system"],
    queryFn:  () => apiGet<any>("/api/system/status"),
  });

  const { data: activity } = useQuery<any[]>({
    queryKey: ["dashboard-activity"],
    queryFn:  () => apiGet<any[]>("/api/dashboard/recent-activity"),
  });

  const accuracyRate = summary?.accuracy_rate ?? 0;
  const xp = summary?.xp ?? 0;

  return (
    <div className="space-y-6 pb-10">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">VIT Super App</h1>
          <p className="text-sm font-mono text-muted-foreground">Welcome back, {user?.username}. Intelligence network active.</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-[10px] py-1 px-3 border-primary/20 bg-primary/5 text-primary">
            <ShieldCheck className="w-3 h-3 mr-1.5" /> VERIFIED AGENT
          </Badge>
        </div>
      </header>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="overflow-x-auto pb-2 -mx-4 px-4 md:mx-0 md:px-0">
          <TabsList className="bg-card/50 border border-border/20 p-1 h-auto flex-nowrap justify-start">
            <TabsTrigger value="campus" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <GraduationCap className="w-3 h-3" /> Campus
            </TabsTrigger>
            <TabsTrigger value="sports" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <Activity className="w-3 h-3" /> Sports
            </TabsTrigger>
            <TabsTrigger value="elections" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <Vote className="w-3 h-3" /> Elections
            </TabsTrigger>
            <TabsTrigger value="marketplace" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <ShoppingBag className="w-3 h-3" /> Marketplace
            </TabsTrigger>
            <TabsTrigger value="policy" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <Scale className="w-3 h-3" /> Policy
            </TabsTrigger>
            <TabsTrigger value="finance" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <CreditCard className="w-3 h-3" /> Finance
            </TabsTrigger>
            <TabsTrigger value="community" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <MessageCircle className="w-3 h-3" /> Community
            </TabsTrigger>
            <TabsTrigger value="agent" className="font-mono text-[10px] uppercase tracking-wider gap-2 px-4 py-2">
              <Store className="w-3 h-3" /> Agent
            </TabsTrigger>
          </TabsList>
        </div>

                <TabsContent value="campus" className="mt-6 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Card className="bg-card/50 border-border/40">
                <CardHeader>
                  <CardTitle className="text-sm font-mono flex items-center gap-2">
                    <GraduationCap className="w-4 h-4 text-primary" /> Academic Hub
                  </CardTitle>
                </CardHeader>
                <CardContent className="py-10 text-center">
                  <p className="text-xs font-mono text-muted-foreground mb-4">Access Past Questions, Course Notes, and textbooks for your department.</p>
                  <Link href="/research">
                    <Button className="font-mono text-xs uppercase gap-2">
                      Enter Academic Hub <ChevronRight className="w-3 h-3" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>

              <Card className="bg-card/50 border-border/40">
                <CardHeader>
                  <CardTitle className="text-sm font-mono flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-400" /> AI Tutor
                  </CardTitle>
                </CardHeader>
                <CardContent className="py-6">
                  <div className="bg-background/40 border border-border/20 rounded-lg p-4 font-mono text-[11px]">
                    <p className="text-muted-foreground mb-2 italic">"How can I help you study today?"</p>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Ask about MTH101, Laplace Transforms..."
                        className="flex-1 bg-background border border-border/30 rounded px-3 py-1.5 outline-none focus:border-primary/50 transition-colors"
                      />
                      <Button size="sm" className="h-auto py-1 px-3">Ask</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
            <div className="space-y-6">
              <Card className="bg-card/50 border-border/40">
                <CardHeader>
                  <CardTitle className="text-sm font-mono">Your Identity</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-1">
                    <p className="text-[10px] uppercase text-muted-foreground font-mono">University</p>
                    <p className="text-xs font-mono font-bold">{user?.university || "Not set"}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] uppercase text-muted-foreground font-mono">Department</p>
                    <p className="text-xs font-mono font-bold">{user?.department || "Not set"}</p>
                  </div>
                  <Link href="/settings">
                    <Button variant="outline" size="sm" className="w-full text-[10px] h-8">Setup Profile</Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

<TabsContent value="sports" className="mt-6 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Card className="bg-card/50 border-border/40">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-mono flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-primary" /> Performance
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {[
                    { label: "Win Rate", value: `${(accuracyRate * 100).toFixed(1)}%` },
                    { label: "Total XP", value: xp.toLocaleString() },
                    { label: "Staked VIT", value: Number(system?.economy?.total_staked_vit || 0).toLocaleString() },
                  ].map(s => (
                    <div key={s.label} className="p-3 rounded-xl bg-background/50 border border-border/20">
                      <p className="text-[10px] font-mono text-muted-foreground uppercase">{s.label}</p>
                      <p className="text-lg font-bold font-mono text-foreground mt-1">{s.value}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="bg-card/50 border-border/40">
                <CardHeader>
                  <CardTitle className="text-sm font-mono flex items-center gap-2">
                    <Target className="w-4 h-4 text-emerald-400" /> Top Opportunities
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <TopOpportunitiesWidget />
                </CardContent>
              </Card>
            </div>
            <div className="space-y-6">
              <LevelCard xp={xp} predictions={summary?.total_predictions || 0} winRate={accuracyRate} streak={summary?.streak || 0} />
              <Card className="bg-card/50 border-border/40">
                <CardHeader>
                  <CardTitle className="text-sm font-mono flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-400" /> AI Confidence
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <AIConfidenceWidget />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="elections" className="mt-6">
          <Card className="bg-card/50 border-border/40">
            <CardHeader>
              <CardTitle className="text-sm font-mono">Electoral Intelligence Hub</CardTitle>
              <CardDescription className="text-xs font-mono uppercase tracking-widest">Verifiable Sentiment & Forecasts</CardDescription>
            </CardHeader>
            <CardContent className="py-10 text-center">
              <Link href="/elections">
                <Button className="font-mono text-xs uppercase gap-2">
                  Enter Election Hub <ChevronRight className="w-3 h-3" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="marketplace" className="mt-6">
          <div className="space-y-6">
            <header>
              <h2 className="text-lg font-bold font-mono">Signal Marketplace</h2>
              <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Premium multi-sector intelligence</p>
            </header>
            <SignalMarketplace />
          </div>
        </TabsContent>

        <TabsContent value="policy" className="mt-6">
          <Card className="bg-card/50 border-border/40">
            <CardHeader>
              <CardTitle className="text-sm font-mono">Policy Simulator</CardTitle>
            </CardHeader>
            <CardContent className="py-10 text-center">
              <Link href="/policy">
                <Button variant="outline" className="font-mono text-xs uppercase gap-2">
                  Launch Simulator <ChevronRight className="w-3 h-3" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="finance" className="mt-6">
          <Card className="bg-card/50 border-border/40">
            <CardHeader>
              <CardTitle className="text-sm font-mono">Remittances & Payments</CardTitle>
            </CardHeader>
            <CardContent className="py-10 text-center">
              <Link href="/finance">
                <Button className="font-mono text-xs uppercase gap-2">
                  Open Wallet <ChevronRight className="w-3 h-3" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="community" className="mt-6">
          <div className="space-y-6">
            <header>
              <h2 className="text-lg font-bold font-mono">Campus Circles</h2>
              <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Connect with students in your university</p>
            </header>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {user?.university ? (
                <>
                  <Card className="bg-card/40 border-border/30 border-l-4 border-l-primary">
                    <CardContent className="p-4 flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <Users className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <p className="text-xs font-mono font-bold">{user.university} Hub</p>
                        <p className="text-[10px] font-mono text-muted-foreground">General Campus Feed</p>
                      </div>
                    </CardContent>
                  </Card>
                  {user?.faculty && (
                    <Card className="bg-card/40 border-border/30 border-l-4 border-l-emerald-500">
                      <CardContent className="p-4 flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                          <Users className="w-5 h-5 text-emerald-500" />
                        </div>
                        <div>
                          <p className="text-xs font-mono font-bold">Faculty of {user.faculty}</p>
                          <p className="text-[10px] font-mono text-muted-foreground">Faculty Discussions</p>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  {user?.department && (
                    <Card className="bg-card/40 border-border/30 border-l-4 border-l-purple-500">
                      <CardContent className="p-4 flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center">
                          <Users className="w-5 h-5 text-purple-500" />
                        </div>
                        <div>
                          <p className="text-xs font-mono font-bold">{user.department} Dept</p>
                          <p className="text-[10px] font-mono text-muted-foreground">Course-specific chats</p>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : (
                <Card className="bg-card/40 border-border/30 col-span-full">
                  <CardContent className="p-6 text-center">
                    <p className="text-xs font-mono text-muted-foreground mb-3">Setup your student profile to join your campus circles.</p>
                    <Link href="/settings">
                      <Button size="sm" variant="outline" className="text-[10px] uppercase font-mono">Setup Identity</Button>
                    </Link>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="agent" className="mt-6">
          <div className="space-y-6">
            <header>
              <h2 className="text-lg font-bold font-mono">Agent Network</h2>
              <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Modernize your business with VIT</p>
            </header>
            <AgentPortal />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
