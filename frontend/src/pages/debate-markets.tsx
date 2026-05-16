import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MessageSquare, ThumbsUp, TrendingUp, Users, Sword } from "lucide-react";

export default function DebateMarketsPage() {
  const debates = [
    {
      id: 1,
      title: "Real Madrid vs Man City: Is the market overrating the home advantage?",
      participants: 1240,
      stake_pool: "45,000 VIT",
      deadline: "2h left",
      sides: [
        { label: "Market Overrated", votes: 65, color: "text-emerald-400" },
        { label: "Fairly Priced", votes: 35, color: "text-red-400" }
      ]
    },
    {
      id: 2,
      title: "Should the XGBoost model weight be reduced after the recent 3-game losing streak?",
      participants: 850,
      stake_pool: "12,200 VIT",
      deadline: "12h left",
      sides: [
        { label: "Reduce Weight", votes: 42, color: "text-orange-400" },
        { label: "Maintain / Retrain", votes: 58, color: "text-cyan-400" }
      ]
    }
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-black uppercase tracking-tighter italic flex items-center gap-3">
          <MessageSquare className="w-8 h-8 text-purple-400" />
          Debate Markets
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Structured head-to-head prediction debates with community voting and staking.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {debates.map((d) => (
          <Card key={d.id} className="bg-zinc-900 border-zinc-800 hover:border-purple-500/30 transition-all overflow-hidden">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start mb-2">
                <Badge variant="outline" className="text-[10px] font-mono border-zinc-700">{d.deadline}</Badge>
                <div className="flex items-center gap-4 text-xs text-zinc-500">
                  <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {d.participants}</span>
                  <span className="flex items-center gap-1"><TrendingUp className="w-3 h-3" /> {d.stake_pool}</span>
                </div>
              </div>
              <CardTitle className="text-xl leading-tight">{d.title}</CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                {d.sides.map((side, i) => (
                  <button key={i} className="group relative p-6 rounded-2xl border border-zinc-800 hover:border-purple-500/50 hover:bg-purple-500/5 transition-all text-center">
                    <p className={`text-xs font-mono uppercase tracking-widest mb-2 ${side.color}`}>{side.label}</p>
                    <p className="text-3xl font-black font-mono">{side.votes}%</p>
                    <div className="mt-4 flex justify-center">
                      <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center group-hover:bg-purple-600 transition-colors">
                        <ThumbsUp className="w-4 h-4" />
                      </div>
                    </div>
                  </button>
                ))}
              </div>
              <div className="flex justify-center">
                <Button variant="ghost" className="text-zinc-500 hover:text-zinc-300 text-xs uppercase tracking-widest font-bold">
                  View Arguments <ChevronRight className="ml-1 w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Button className="w-full h-16 bg-purple-600 hover:bg-purple-500 text-lg font-bold rounded-2xl shadow-xl shadow-purple-500/20">
        <Sword className="mr-2 w-6 h-6" /> Propose New Debate
      </Button>
    </div>
  );
}
