import { differenceInDays } from "date-fns";
import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Trophy, Star, Shield, Zap, Flame, TrendingUp, History,
  Users, BarChart2, ChevronRight, Share2, Info, CheckCircle2,
  Medal, Award, Target, Rocket
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import MetricCard from "@/components/cards/MetricCard";
import WinShareCard from "@/components/cards/WinShareCard";
import { cn } from "@/lib/utils";

export default function MeritPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");

  const { data: meritData } = useQuery<any>({
    queryKey: ["/api/merit/users/me"],
    queryFn: () => user ? apiGet(`/api/merit/users/${user.id}`) : null,
    enabled: !!user,
  });

  const { data: leaderboardData } = useQuery<any>({
    queryKey: ["/api/merit/leaderboard"],
    queryFn: () => apiGet("/api/merit/leaderboard"),
  });

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const leaderboard = leaderboardData?.leaderboard || [];
  const myRank = leaderboard.findIndex((e: any) => e.user_id === user?.id) + 1;
  const displayRank = myRank > 0 ? `#${myRank}` : "#—";

  const myMerit = meritData;
  const progress = myMerit?.points_to_next_tier != null
    ? (myMerit.score / (myMerit.score + myMerit.points_to_next_tier)) * 100
    : 0;

  const handleShare = () => {
    toast.success("Identity Proof generated.");
  };

  const winRate = summary?.avg_clv ? (summary.avg_clv * 100 + 50).toFixed(1) : "—";

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Prestige & Reputation</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Contributor Identity Ledger</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Reputation XP"
          value={user?.merit_score?.toLocaleString() || "0"}
          icon={<Award size={14} />}
          variant="default"
        />
        <MetricCard
          label="Rank"
          value={displayRank}
          change={myRank > 0 && myRank <= 10 ? "TOP 1%" : "TOP 5%"}
          changePositive={true}
          icon={<Target size={14} />}
        />
        <MetricCard
          label="Yield Multiplier"
          value={`x${(1 + (myMerit?.current_bonus_pct || 0) / 100).toFixed(2)}`}
          subtitle="Intelligence Reward"
          icon={<Zap size={14} />}
        />
        <MetricCard
          label="Signal Streak"
          value={user?.current_streak || 0}
          icon={<Flame size={14} />}
        />
      </div>

      {/* ── Tier Progress Hero ── */}
      <Card className="border-primary/20 bg-primary/[0.02]">
        <CardContent className="p-8">
           <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-8">
              <div className="space-y-4 flex-1 w-full">
                 <div className="flex justify-between items-end">
                    <div>
                       <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 mb-2">
                          Current Tier
                       </Badge>
                       <h2 className="text-4xl font-display font-bold uppercase tracking-tight">{user?.tier || 'Contributor'}</h2>
                    </div>
                    <div className="text-right">
                       <p className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest leading-none mb-2">Next Tier: {myMerit?.next_tier || 'Oracle'}</p>
                       <p className="font-mono text-xs font-bold text-primary">{(myMerit?.xp_to_next_tier || 2450).toLocaleString()} XP Needed</p>
                    </div>
                 </div>
                 <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-primary shadow-[0_0_12px_rgba(0,245,255,0.4)]" style={{ width: `${progress || 65}%` }} />
                 </div>
              </div>
              <p className="text-xs font-mono text-vit-text-2">{myMerit?.points_to_next_tier?.toLocaleString() || '0'} XP REMAINING</p>
           </div>
           <div className="h-2 bg-vit-surface-3 rounded-full overflow-hidden border border-vit-border">
              <div className="h-full bg-vit-green shadow-[0_0_10px_rgba(0,230,118,0.4)]" style={{ width: `${progress || 0}%` }} />
           </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full h-10 p-1 bg-white/[0.03]">
              <TabsTrigger value="overview" className="flex-1 text-[10px]">ACHIEVEMENTS</TabsTrigger>
              <TabsTrigger value="leaderboard" className="flex-1 text-[10px]">LEADERBOARD</TabsTrigger>
              <TabsTrigger value="unlocks" className="flex-1 text-[10px]">PRESTIGE UNLOCKS</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-4 space-y-4">
               <div className="bg-vit-surface border border-vit-border rounded-xl p-6">
                  <div className="flex items-center gap-4 mb-6">
                     <div className="w-16 h-16 rounded-2xl bg-vit-surface-2 border border-vit-border flex items-center justify-center text-secondary">
                        <Trophy size={32} />
                     </div>
                     <div>
                        <h3 className="text-lg font-bold text-vit-text-1">Your Reputation</h3>
                        <p className="text-xs text-vit-text-3">Based on your activity and signal accuracy</p>
                     </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                     {[
                       { label: "Total Predictions", value: user?.merit_score ? Math.floor(user.merit_score / 100) : 0, icon: <BarChart2 size={14} /> },
                       { label: "Successful Picks", value: user?.merit_score ? Math.floor(user.merit_score / 150) : 0, icon: <CheckCircle2 size={14} /> },
                       { label: "Network Age", value: user?.created_at ? `${Math.floor((new Date().getTime() - new Date(user.created_at).getTime()) / (1000 * 60 * 60 * 24))} Days` : "—", icon: <History size={14} /> },
                     ].map((s, i) => (
                       <div key={i} className="p-4 rounded-xl bg-vit-surface-2 border border-vit-border">
                          <div className="flex items-center gap-2 text-vit-text-3 mb-1">
                             {s.icon}
                             <span className="text-[10px] font-bold uppercase">{s.label}</span>
                          </div>
                          <p className="text-lg font-mono font-bold text-vit-text-1">{s.value}</p>
                       </div>
                       <p className="font-mono text-xs font-bold text-vit-positive">{a.xp} XP</p>
                    </div>
                  ))}
               </div>
            </TabsContent>

            <TabsContent value="leaderboard" className="mt-6">
               <Card className="border-white/5 bg-transparent overflow-hidden">
                  <table className="w-full text-left">
                     <thead className="bg-white/[0.02] border-b border-white/5">
                        <tr>
                           <th className="p-4 text-[10px] font-bold text-vit-text-3 uppercase">Rank</th>
                           <th className="p-4 text-[10px] font-bold text-vit-text-3 uppercase">User</th>
                           <th className="p-4 text-[10px] font-bold text-vit-text-3 uppercase text-right">Merit</th>
                        </tr>
                     </thead>
                     <tbody className="divide-y divide-vit-border">
                        {leaderboard.map((entry: any) => (
                          <tr key={entry.user_id} className="hover:bg-vit-surface-2 transition-colors">
                             <td className="p-4 font-mono text-sm font-bold">#{entry.rank}</td>
                             <td className="p-4">
                                <div className="flex items-center gap-2">
                                   <div className="w-6 h-6 rounded bg-vit-surface-3 flex items-center justify-center text-[10px] font-bold">U</div>
                                   <span className="text-sm font-medium">User {entry.user_id}</span>
                                   <Badge className="text-[8px] bg-secondary/10 text-secondary border-secondary/20">{entry.tier}</Badge>
                                </div>
                             </td>
                             <td className="px-6 py-4 text-right font-mono text-xs font-bold text-primary">{entry.score.toLocaleString()}</td>
                          </tr>
                        ))}
                     </tbody>
                  </table>
               </Card>
            </TabsContent>

            <TabsContent value="unlocks" className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
               {[
                 { title: "Specialist Badge", xp: "5,000 XP", locked: (user?.merit_score || 0) < 5000 },
                 { title: "Private Signal Channel", xp: "15,000 XP", locked: (user?.merit_score || 0) < 15000 },
                 { title: "Oracle Tier", xp: "50,000 XP", locked: (user?.merit_score || 0) < 50000 },
                 { title: "Validator Access", xp: "100,000 XP", locked: (user?.merit_score || 0) < 100000 },
               ].map((u, i) => (
                 <div key={i} className={cn(
                    "p-5 rounded-lg border flex flex-col gap-3 transition-all",
                    u.locked ? "bg-white/[0.01] border-white/5 opacity-50" : "bg-primary/[0.02] border-primary/20"
                 )}>
                    <div className="flex justify-between items-start">
                       <h4 className="font-display text-sm font-bold uppercase tracking-widest">{u.title}</h4>
                       {u.locked ? <Shield size={14} className="text-muted-foreground/30" /> : <Award size={14} className="text-primary" />}
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">{u.desc}</p>
                    <p className="font-mono text-[9px] text-muted-foreground/40 uppercase tracking-[0.2em] mt-auto">{u.xp}</p>
                 </div>
               ))}
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
           <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                 <Medal size={16} className="text-primary" />
                 <h4 className="font-display text-[10px] font-bold uppercase tracking-[0.2em]">Reputation Guide</h4>
              </div>
              <ul className="space-y-4">
                 {[
                    { label: "Market Success", xp: "+100 XP" },
                    { label: "Policy Vote", xp: "+50 XP" },
                    { label: "Achievement", xp: "+1k XP" },
                    { label: "Network Growth", xp: "+5k XP" },
                 ].map((item, i) => (
                    <li key={i} className="flex justify-between items-center">
                       <span className="text-[11px] text-muted-foreground">{item.label}</span>
                       <span className="font-mono text-[10px] font-bold text-primary">{item.xp}</span>
                    </li>
                 ))}
              </ul>
           </div>

           <WinShareCard
              streakCount={user?.current_streak || 0}
              titleUnlocked={myMerit?.tier?.toUpperCase() || "VIEWER"}
              predictionLabel="Verified Contributor"
              pnlPercent={Number(winRate)}
              referralCode={user?.username || "VIT_NETWORK"}
              onShare={handleShare}
           />
        </div>
      </div>
    </div>
  );
}
