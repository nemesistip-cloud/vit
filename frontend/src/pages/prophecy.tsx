import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import {
  Sparkles, Trophy, ShieldCheck, Zap,
  ChevronRight, Brain, Lock, CheckCircle2, Target
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function ProphecyPage() {
  const { user } = useAuth();

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const { data: merit } = useQuery<any>({
    queryKey: ["/api/merit/users/me"],
    queryFn: () => user ? apiGet(`/api/merit/users/${user.id}`) : null,
    enabled: !!user,
  });

  const level = user?.merit_score ? Math.floor(user.merit_score / 2500) + 1 : 1;
  const currentAcc = summary?.avg_clv ? (summary.avg_clv * 100 + 40).toFixed(1) + "%" : "—";
  const rewards = user?.merit_score ? (user.merit_score * 0.1).toFixed(1) + "K" : "—";
  const mastered = level > 1 ? level - 1 : 0;

  const nextLevelXp = level * 2500;
  const currentLevelXp = (level - 1) * 2500;
  const progress = user?.merit_score ? ((user.merit_score - currentLevelXp) / (nextLevelXp - currentLevelXp)) * 100 : 0;

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            variant="hero"
            label="CHAIN LEVEL"
            value={`LVL ${level}`}
            icon={<Trophy size={20} className="text-secondary" />}
         />
         <MetricCard
            label="Mastered"
            value={mastered}
            subtitle="Chapters"
            icon={<CheckCircle2 size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Current Acc"
            value={currentAcc}
            change="+1.5%"
            changePositive={true}
            icon={<Brain size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="VIT Rewards"
            value={rewards}
            icon={<Zap size={16} className="text-secondary" />}
         />
      </div>

      <Card className="bg-vit-surface border-vit-border overflow-hidden">
        <div className="p-6 space-y-4">
           <div className="flex justify-between items-end">
              <div>
                 <p className="text-[10px] font-bold text-vit-text-3 uppercase tracking-widest">Active Progression</p>
                 <h2 className="text-xl font-display font-bold text-vit-text-1">CHAPTER {level}: THE {merit?.tier?.toUpperCase() || 'INITIATE'}'S PATH</h2>
              </div>
              <p className="text-xs font-mono text-vit-text-2">{progress.toFixed(0)}% COMPLETE</p>
           </div>
           <div className="h-2 bg-vit-surface-3 rounded-full overflow-hidden border border-vit-border">
              <div className="h-full bg-secondary shadow-[0_0_10px_rgba(255,215,0,0.4)]" style={{ width: `${progress}%` }} />
           </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
           <h3 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 px-1">Progression Chapters</h3>
           <div className="space-y-3">
              {[
                { id: 1, title: "Initiation", desc: "Understand the flow of decentralized intelligence.", status: level > 1 ? "mastered" : "active" },
                { id: 2, title: "Pattern Recognition", desc: "Predict 5 consecutive outcomes with >80% accuracy.", status: level > 2 ? "mastered" : level === 2 ? "active" : "locked" },
                { id: 3, title: "Consensus Builder", desc: "Collaborate in circles to refine ensemble signals.", status: level > 3 ? "mastered" : level === 3 ? "active" : "locked" },
                { id: 4, title: "The Oracle's Path", desc: "Maintain top 5% rank in the global accuracy leaderboard.", status: level > 4 ? "mastered" : level === 4 ? "active" : "locked" },
                { id: 5, title: "Ascension", desc: "Unlock priority access to the primary neural node.", status: level > 5 ? "mastered" : level === 5 ? "active" : "locked" },
              ].map((c) => (
                <Card key={c.id} className={`bg-vit-surface border-vit-border ${c.status === 'active' ? 'border-secondary/50 ring-1 ring-secondary/20' : ''}`}>
                   <CardContent className="p-4 flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${
                        c.status === 'mastered' ? 'bg-vit-green-glow border-vit-green/20 text-vit-green' :
                        c.status === 'active' ? 'bg-secondary/10 border-secondary/20 text-secondary' :
                        'bg-vit-void border-vit-border text-vit-text-3'
                      }`}>
                         {c.status === 'mastered' ? <CheckCircle2 size={18} /> :
                          c.status === 'active' ? <Sparkles size={18} /> :
                          <Lock size={18} />}
                      </div>
                      <div className="flex-1 min-w-0">
                         <div className="flex items-center gap-2">
                            <h4 className={`text-sm font-bold ${c.status === 'locked' ? 'text-vit-text-3' : 'text-vit-text-1'}`}>Chapter {c.id}: {c.title}</h4>
                            {c.status === 'mastered' && <Badge className="text-[8px] bg-vit-green-glow text-vit-green border-vit-green/20">MASTERED</Badge>}
                         </div>
                         <p className="text-[11px] text-vit-text-3 line-clamp-1">{c.desc}</p>
                      </div>
                      {c.status === 'active' && <ChevronRight size={16} className="text-secondary" />}
                   </CardContent>
                </Card>
              ))}
           </div>
        </div>

        <div className="space-y-6">
           <h3 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 px-1">Mastery Benefits</h3>
           <Card className="bg-vit-surface border-vit-border">
              <CardContent className="p-4 space-y-4">
                 {[
                   { label: "High-Volume Staking", icon: ShieldCheck },
                   { label: "Advanced Insights", icon: Brain },
                   { label: "Governance Rights", icon: Target },
                   { label: "Exclusive Drops", icon: Zap }
                 ].map((b, i) => (
                   <div key={i} className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-vit-surface-2 flex items-center justify-center text-vit-green">
                         <b.icon size={16} />
                      </div>
                      <span className="text-xs font-medium text-vit-text-2">{b.label}</span>
                   </div>
                 ))}
                 <Button className="w-full bg-secondary text-vit-text-inverse font-black tracking-widest text-xs mt-2">
                    CLAIM REWARDS
                 </Button>
              </CardContent>
           </Card>
        </div>
      </div>
    </div>
  );
}
