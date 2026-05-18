import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Lock, CheckCircle2, ChevronRight, Trophy, Flame } from "lucide-react";

export default function ProphecyChainPage() {
  const chapters = [
    { id: 1, title: "The Awakening", status: "completed", reward: "Genesis Badge", matches: 3, description: "Predict 3 consecutive match outcomes correctly." },
    { id: 2, title: "The Seer's Path", status: "active", reward: "50 VIT", matches: 5, description: "Identify 5 positive EV edges in a single matchday." },
    { id: 3, title: "Master of Equilibrium", status: "locked", reward: "Stalemate NFT", matches: 2, description: "Predict two 0-0 draws with 80%+ model confidence." },
    { id: 4, title: "The Oracle Ascends", status: "locked", reward: "Oracle Tier Status", matches: 10, description: "Maintain a 65% win rate over 100 bets." }
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black uppercase tracking-tighter italic flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-yellow-400" />
            Prophecy Chain
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Serialized narrative prediction game. Unlock chapters, earn rewards, become a Prophet.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-orange-500/10 border border-orange-500/20 px-4 py-2 rounded-xl">
          <Flame className="w-5 h-5 text-orange-500" />
          <span className="font-black text-orange-500 uppercase tracking-tighter italic">Current Streak: 4</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 relative">
        <div className="absolute left-8 top-12 bottom-12 w-0.5 bg-zinc-800 z-0 hidden md:block" />

        {chapters.map((ch) => (
          <Card key={ch.id} className={`bg-zinc-900 border-border/50 relative z-10 overflow-hidden ${ch.status === 'locked' ? 'opacity-60 grayscale' : 'hover:border-yellow-500/30 transition-all'}`}>
            <CardContent className="p-0 flex flex-col md:flex-row">
              <div className={`p-6 md:w-20 flex items-center justify-center border-b md:border-b-0 md:border-r border-border/50 ${ch.status === 'completed' ? 'bg-emerald-500/10' : ch.status === 'active' ? 'bg-yellow-500/10' : 'bg-zinc-800/50'}`}>
                {ch.status === 'completed' ? <CheckCircle2 className="w-8 h-8 text-emerald-500" /> :
                 ch.status === 'locked' ? <Lock className="w-6 h-6 text-zinc-500" /> :
                 <span className="text-2xl font-black text-yellow-500 italic">0{ch.id}</span>}
              </div>

              <div className="p-6 flex-1 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-bold text-lg">{ch.title}</h3>
                    {ch.status === 'active' && <Badge className="bg-yellow-500 text-black font-mono text-[10px]">CURRENT CHAPTER</Badge>}
                  </div>
                  <p className="text-sm text-zinc-400 max-w-md">{ch.description}</p>
                </div>

                <div className="flex flex-col md:items-end gap-3">
                  <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
                    <Trophy className="w-3 h-3" />
                    REWARD: <span className="text-zinc-200 font-bold">{ch.reward}</span>
                  </div>
                  {ch.status === 'active' ? (
                    <Button className="bg-yellow-500 hover:bg-yellow-400 text-black font-black uppercase tracking-tighter rounded-xl">
                      Enter Predictions <ChevronRight className="ml-1 w-4 h-4" />
                    </Button>
                  ) : ch.status === 'completed' ? (
                    <span className="text-emerald-500 font-bold uppercase text-xs tracking-widest">CHAPTER SEALED</span>
                  ) : (
                    <span className="text-zinc-600 font-bold uppercase text-xs tracking-widest italic">LOCKED BY FATE</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
