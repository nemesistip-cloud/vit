import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Target, TrendingUp, Zap, Sparkles, Filter, Info, ChevronRight } from "lucide-react";
import { toast } from "sonner";

interface EliteSignal {
  id: number;
  match: string;
  league: string;
  side: string;
  odds: number;
  edge: number;
  confidence: number;
  expected_value: number;
  rationale: string;
  suggested_stake_pct: number;
  kickoff: string;
}

export default function QualityFeedPage() {
  const [riskProfile, setRiskProfile] = useState("balanced");

  const { data, isLoading } = useQuery<{ items: EliteSignal[] }>({
    queryKey: ["quality-feed", riskProfile],
    queryFn: () => apiGet(`/api/quality-feed/curated?risk_profile=${riskProfile}&min_edge=0.04`),
    staleTime: 30_000,
  });

  const items = data?.items ?? [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground flex items-center gap-3">
            <Target className="w-8 h-8 text-cyan-400" />
            Elite Signal Feed
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Human-AI hybrid filtering: only the top 1% of +EV opportunities.
          </p>
        </div>
        <div className="flex bg-zinc-900 p-1 rounded-xl border border-border/50">
          {["conservative", "balanced", "aggressive"].map((p) => (
            <button
              key={p}
              onClick={() => setRiskProfile(p)}
              className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${riskProfile === p ? "bg-cyan-600 text-white shadow-lg shadow-cyan-500/20" : "text-zinc-500 hover:text-zinc-300"}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {isLoading ? (
          Array(3).fill(0).map((_, i) => <div key={i} className="h-40 bg-zinc-900/50 animate-pulse rounded-2xl border border-border/20" />)
        ) : items.length === 0 ? (
          <Card className="bg-zinc-900/30 border-dashed border-border/50 p-12 text-center">
            <Info className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <CardTitle className="text-zinc-500">No high-edge opportunities detected currently</CardTitle>
            <p className="text-zinc-600 text-sm mt-2">The model is scanning 10,000+ markets for inefficiencies.</p>
          </Card>
        ) : (
          items.map((bet) => (
            <Card key={bet.id} className="bg-zinc-900 border-cyan-500/20 hover:border-cyan-500/50 transition-all overflow-hidden group">
              <CardContent className="p-0 flex flex-col md:flex-row">
                <div className="p-6 md:w-1/3 bg-gradient-to-br from-zinc-900 to-cyan-900/10 border-b md:border-b-0 md:border-r border-border/50 flex flex-col justify-center">
                  <div className="flex justify-between items-center mb-3">
                    <Badge variant="outline" className="bg-cyan-500/10 text-cyan-400 border-cyan-500/20 uppercase font-mono text-[10px]">
                      {bet.league}
                    </Badge>
                    <div className="text-[10px] font-mono text-zinc-500 uppercase">
                      {new Date(bet.kickoff).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                  <h3 className="font-bold text-lg leading-tight group-hover:text-cyan-400 transition-colors">{bet.match}</h3>
                </div>

                <div className="p-6 flex-1 grid grid-cols-2 md:grid-cols-4 gap-6 items-center">
                  <div>
                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">Pick</p>
                    <p className="font-black text-xl italic uppercase">{bet.side} @ {bet.odds.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">Edge</p>
                    <p className="font-mono text-xl font-bold text-emerald-400">+▲{(bet.edge * 100).toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">Confidence</p>
                    <p className="font-mono text-xl font-bold text-purple-400">{(bet.confidence * 100).toFixed(0)}%</p>
                  </div>
                  <div className="flex justify-end">
                    <Button className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl px-6 h-12 shadow-lg shadow-cyan-500/20">
                      Allocation {Math.round(bet.suggested_stake_pct * 100)}%
                    </Button>
                  </div>
                </div>
              </CardContent>
              <div className="px-6 py-3 bg-zinc-950/50 border-t border-border/30 flex items-center gap-3">
                <Sparkles className="w-4 h-4 text-yellow-500" />
                <p className="text-xs text-zinc-400 italic">
                  <span className="text-zinc-200 font-bold not-italic mr-1">WHY THIS SIGNAL:</span>
                  {bet.rationale}
                </p>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
