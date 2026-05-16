import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, AlertCircle, Zap, TrendingUp, HeartPulse, Brain } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function DisciplineCoachPage() {
  const [behaviorScore, setBehaviorScore] = useState(92);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            Discipline Coach
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            AI-powered behavioral monitoring and tilt protection
          </p>
        </div>
        <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-mono">
          STATUS: DISCIPLINED
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-card border-border/50 md:col-span-1">
          <CardHeader className="pb-2 text-center">
            <CardTitle className="text-sm font-mono text-zinc-500 uppercase">Behavior Score</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center py-6">
            <div className="relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="64" cy="64" r="58" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-zinc-800" />
                <circle cx="64" cy="64" r="58" stroke="currentColor" strokeWidth="8" fill="transparent" strokeDasharray={364} strokeDashoffset={364 - (364 * behaviorScore) / 100} className="text-emerald-500" />
              </svg>
              <div className="absolute text-3xl font-black font-mono">{behaviorScore}</div>
            </div>
            <p className="mt-4 text-xs text-zinc-500 text-center px-4">
              You are in the <span className="text-emerald-400 font-bold">top 2%</span> of disciplined users.
            </p>
          </CardContent>
        </Card>

        <Card className="bg-card border-border/50 md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Coach Insights</CardTitle>
            <CardDescription>Real-time feedback on your betting patterns</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4 p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl">
              <Zap className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-emerald-400">Consistent Sizing</h4>
                <p className="text-xs text-zinc-400 mt-1">Your stake size remains consistent relative to your bankroll. No signs of "chasing" losses detected.</p>
              </div>
            </div>
            <div className="flex gap-4 p-4 bg-cyan-500/5 border border-cyan-500/10 rounded-xl">
              <Brain className="w-5 h-5 text-cyan-400 shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-cyan-400">Analytical Wait Time</h4>
                <p className="text-xs text-zinc-400 mt-1">You spend an average of 4.2 minutes reviewing model data before placing a bet. This shows high deliberation.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-zinc-900 border-red-500/20">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <HeartPulse className="w-5 h-5 text-red-400" />
            Tilt Protection
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex justify-between items-end mb-2">
            <span className="text-xs text-zinc-400 uppercase">Daily Loss Limit Usage</span>
            <span className="text-xs font-mono">$12.40 / $100.00</span>
          </div>
          <Progress value={12.4} className="h-2 bg-zinc-800" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
            <div className="p-4 border border-border/50 rounded-xl">
              <h5 className="text-xs font-mono text-zinc-500 uppercase mb-2">Self-Exclusion</h5>
              <button className="text-sm text-red-400 hover:underline">Activate 24h Cooldown</button>
            </div>
            <div className="p-4 border border-border/50 rounded-xl">
              <h5 className="text-xs font-mono text-zinc-500 uppercase mb-2">Next Milestone</h5>
              <p className="text-sm text-zinc-300">Complete 5 more deliberate bets to earn the "Zen Master" badge.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
