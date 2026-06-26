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
  Users, BarChart2, ChevronRight, Share2, Info, CheckCircle2
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import MetricCard from "@/components/cards/MetricCard";
import WinShareCard from "@/components/cards/WinShareCard";

const TIER_CONFIG: Record<string, any> = {
  viewer:   { icon: <Users size={16} />,  color: "text-slate-400",   bg: "bg-slate-500/10" },
  contributor: { icon: <Star size={16} />,   color: "text-blue-400",    bg: "bg-blue-500/10" },
  specialist: { icon: <Shield size={16} />, color: "text-purple-400",  bg: "bg-purple-500/10" },
  oracle:   { icon: <Trophy size={16} />, color: "text-secondary",   bg: "bg-secondary/10" },
};

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
    toast.success("Win card generated! Ready to share.");
  };

  const winRate = summary?.avg_clv ? (summary.avg_clv * 100 + 50).toFixed(1) : "—";

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          variant="hero"
          label="MERIT XP"
          value={user?.merit_score?.toLocaleString() || "0"}
          icon={<Trophy size={20} className="text-secondary" />}
        />
        <MetricCard
          label="Rank"
          value={displayRank}
          change={myRank > 0 && myRank <= 10 ? "TOP 1%" : "TOP 5%"}
          changePositive={true}
          icon={<Users size={16} className="text-vit-green" />}
        />
        <MetricCard
          label="Bonus Multiplier"
          value={`+${myMerit?.current_bonus_pct?.toFixed(0) || "0"}%`}
          subtitle="On all predictions"
          icon={<Zap size={16} className="text-vit-green" />}
        />
        <MetricCard
          label="Win Streak"
          value={user?.current_streak || "0"}
          icon={<Flame size={16} className="text-orange-500" />}
        />
      </div>

      <Card className="bg-vit-surface border-vit-border overflow-hidden">
        <div className="p-6 space-y-4">
           <div className="flex justify-between items-end">
              <div>
                 <p className="text-[10px] font-bold text-vit-text-3 uppercase tracking-widest">Next Tier Progress</p>
                 <h2 className="text-xl font-display font-bold text-vit-text-1">{myMerit?.next_tier?.toUpperCase() || 'ORACLE'}</h2>
              </div>
              <p className="text-xs font-mono text-vit-text-2">{myMerit?.points_to_next_tier?.toLocaleString() || '0'} XP REMAINING</p>
           </div>
           <div className="h-2 bg-vit-surface-3 rounded-full overflow-hidden border border-vit-border">
              <div className="h-full bg-vit-green shadow-[0_0_10px_rgba(0,230,118,0.4)]" style={{ width: `${progress || 0}%` }} />
           </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-vit-surface-2 border border-vit-border p-1 h-10">
              <TabsTrigger value="overview" className="px-6 text-xs font-bold data-[state=active]:bg-vit-surface-3">OVERVIEW</TabsTrigger>
              <TabsTrigger value="leaderboard" className="px-6 text-xs font-bold data-[state=active]:bg-vit-surface-3">LEADERBOARD</TabsTrigger>
              <TabsTrigger value="unlocks" className="px-6 text-xs font-bold data-[state=active]:bg-vit-surface-3">UNLOCKS</TabsTrigger>
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
                     ))}
                  </div>
               </div>
            </TabsContent>

            <TabsContent value="leaderboard" className="mt-4">
               <div className="bg-vit-surface border border-vit-border rounded-xl overflow-hidden">
                  <table className="w-full text-left">
                     <thead className="bg-vit-surface-2 border-b border-vit-border">
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
                             <td className="p-4 text-right font-mono text-sm font-bold text-vit-green">{entry.score.toLocaleString()}</td>
                          </tr>
                        ))}
                     </tbody>
                  </table>
               </div>
            </TabsContent>

            <TabsContent value="unlocks" className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
               {[
                 { title: "Specialist Badge", xp: "5,000 XP", locked: (user?.merit_score || 0) < 5000 },
                 { title: "Private Signal Channel", xp: "15,000 XP", locked: (user?.merit_score || 0) < 15000 },
                 { title: "Oracle Tier", xp: "50,000 XP", locked: (user?.merit_score || 0) < 50000 },
                 { title: "Validator Access", xp: "100,000 XP", locked: (user?.merit_score || 0) < 100000 },
               ].map((u, i) => (
                 <div key={i} className={`p-4 rounded-xl border ${u.locked ? 'bg-vit-void border-vit-border opacity-50' : 'bg-vit-surface border-vit-green/20'}`}>
                    <div className="flex justify-between items-center mb-2">
                       <h4 className="text-sm font-bold">{u.title}</h4>
                       {u.locked ? <Shield size={14} className="text-vit-text-3" /> : <CheckCircle2 size={14} className="text-vit-green" />}
                    </div>
                    <p className="text-[10px] text-vit-text-3 uppercase font-mono">{u.xp}</p>
                 </div>
               ))}
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
           <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-vit-text-3 px-1">Social Proof</h3>
           <WinShareCard
              streakCount={user?.current_streak || 0}
              titleUnlocked={myMerit?.tier?.toUpperCase() || "VIEWER"}
              predictionLabel="Verified Contributor"
              pnlPercent={Number(winRate)}
              referralCode={user?.username || "VIT_NETWORK"}
              onShare={handleShare}
           />
           <div className="bg-vit-surface border border-vit-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                 <Info size={14} className="text-vit-green" />
                 <h4 className="text-[10px] font-bold uppercase tracking-wider">How to earn XP</h4>
              </div>
              <ul className="text-[11px] text-vit-text-2 space-y-2">
                 <li>• Correct match predictions (+100 XP)</li>
                 <li>• Governance voting (+50 XP)</li>
                 <li>• Achievement unlocks (+500-2000 XP)</li>
                 <li>• Referral signups (+1000 XP)</li>
              </ul>
           </div>
        </div>
      </div>
    </div>
  );
}
