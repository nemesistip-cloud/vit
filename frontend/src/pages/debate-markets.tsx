import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageSquare, ThumbsUp, TrendingUp, Users, Sword, ChevronRight, Brain, BarChart2, Activity, Zap } from "lucide-react";
import { Link } from "wouter";

export default function DebateMarketsPage() {
  // Fetch governance proposals — these are the closest real "debates" we have
  const { data: proposals, isLoading: loadingProps } = useQuery<any>({
    queryKey: ["/api/governance/proposals"],
    queryFn: () => apiGet("/api/governance/proposals"),
    staleTime: 60_000,
  });

  // Fetch model performance for "model debates"
  const { data: modelPerf, isLoading: loadingModels } = useQuery<any>({
    queryKey: ["/api/dashboard/model-confidence"],
    queryFn: () => apiGet("/api/dashboard/model-confidence"),
    staleTime: 60_000,
  });

  const isLoading = loadingProps || loadingModels;
  const rawProposals: any[] = proposals?.proposals ?? proposals?.items ?? [];
  const models: any[] = modelPerf?.models?.slice(0, 4) ?? [];

  // Build debates from governance proposals (real) and model performance signals (real)
  const realDebates = [
    ...rawProposals.slice(0, 3).map((p: any) => ({
      id: `gov-${p.id}`,
      title: p.title ?? p.description ?? "Governance Proposal",
      type: "Governance",
      participants: p.yes_votes + p.no_votes + (p.abstain_votes ?? 0) || 1,
      stake_pool: p.stake_amount ? `${Math.round(p.stake_amount).toLocaleString()} VIT` : "—",
      deadline: p.voting_ends ? new Date(p.voting_ends).toLocaleDateString() : "Open",
      sides: [
        {
          label: "YES",
          votes: p.yes_votes && (p.yes_votes + p.no_votes) > 0
            ? Math.round((p.yes_votes / (p.yes_votes + p.no_votes)) * 100)
            : 50,
          color: "text-green-400",
        },
        {
          label: "NO",
          votes: p.no_votes && (p.yes_votes + p.no_votes) > 0
            ? Math.round((p.no_votes / (p.yes_votes + p.no_votes)) * 100)
            : 50,
          color: "text-destructive",
        },
      ],
      real: true,
    })),
    ...models.slice(0, 2).map((m: any, i: number) => ({
      id: `model-${m.key ?? i}`,
      title: `Should ${m.name ?? `Model ${i + 1}`} weight be adjusted? (Current: ${m.weight ? m.weight.toFixed(2) : "1.00"}, Accuracy: ${m.accuracy?.toFixed(1) ?? "—"}%)`,
      type: "Model Governance",
      participants: 0,
      stake_pool: "—",
      deadline: "Open",
      sides: [
        { label: "Increase Weight", votes: m.accuracy >= 65 ? 68 : 32, color: "text-primary" },
        { label: "Reduce / Retrain", votes: m.accuracy >= 65 ? 32 : 68, color: "text-orange-400" },
      ],
      real: false,
    })),
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-mono uppercase tracking-tight flex items-center gap-2">
            <MessageSquare className="w-6 h-6 text-purple-400" />
            Debate Markets
          </h1>
          <p className="text-muted-foreground font-mono text-sm mt-1">
            Community governance votes and model performance debates
          </p>
        </div>
        <Link href="/governance">
          <Button size="sm" className="font-mono text-xs gap-1.5 bg-purple-500/10 text-purple-400 border border-purple-500/30 hover:bg-purple-500/20" variant="outline">
            <Brain className="w-3.5 h-3.5" />
            View DAO Governance
          </Button>
        </Link>
      </div>

      {/* Coming soon notice */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-purple-500/5 border border-purple-500/20 text-sm font-mono text-muted-foreground">
        <Zap className="w-4 h-4 text-purple-400 flex-shrink-0" />
        <span>
          Debate Markets pull from live governance proposals and real model metrics.
          Full staking debate engine launches in v6.0 — vote on{" "}
          <Link href="/governance" className="text-purple-400 hover:underline">governance proposals</Link> now.
        </span>
      </div>

      {/* Debates */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="bg-card/40 border-border/40">
              <CardHeader><Skeleton className="h-6 w-3/4" /></CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <Skeleton className="h-24 rounded-2xl" />
                  <Skeleton className="h-24 rounded-2xl" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : realDebates.length > 0 ? (
        <div className="space-y-4">
          {realDebates.map((d) => (
            <Card key={d.id} className="bg-card/40 border-border/40 hover:border-purple-500/30 transition-all">
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={`font-mono text-[10px] ${d.real ? "border-green-500/30 text-green-400" : "border-border/50 text-muted-foreground"}`}>
                      {d.real ? "● Live" : "● Signal"}
                    </Badge>
                    <Badge variant="outline" className="font-mono text-[10px] border-purple-500/30 text-purple-400">
                      {d.type}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
                    {d.participants > 0 && (
                      <span className="flex items-center gap-1">
                        <Users className="w-3 h-3" /> {d.participants.toLocaleString()}
                      </span>
                    )}
                    {d.stake_pool !== "—" && (
                      <span className="flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" /> {d.stake_pool}
                      </span>
                    )}
                  </div>
                </div>
                <CardTitle className="text-sm font-mono leading-snug font-medium">{d.title}</CardTitle>
              </CardHeader>
              <CardContent className="pt-2 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  {d.sides.map((side, i) => (
                    <button
                      key={i}
                      className="group relative p-4 rounded-xl border border-border/40 hover:border-purple-500/50 hover:bg-purple-500/5 transition-all text-center"
                    >
                      <p className={`text-[10px] font-mono uppercase tracking-widest mb-2 ${side.color}`}>{side.label}</p>
                      <p className="text-2xl font-bold font-mono">{side.votes}%</p>
                      <div className="mt-3 h-1 bg-muted/30 rounded-full overflow-hidden">
                        <div className={`h-full ${i === 0 ? "bg-primary" : "bg-destructive"} rounded-full`} style={{ width: `${side.votes}%` }} />
                      </div>
                    </button>
                  ))}
                </div>
                <div className="flex justify-end">
                  <Link href="/governance">
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground text-xs font-mono gap-1">
                      View in Governance <ChevronRight className="w-3.5 h-3.5" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="bg-card/30 border-border/30">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center space-y-4">
            <MessageSquare className="w-10 h-10 text-muted-foreground/40" />
            <div>
              <p className="font-mono text-sm text-muted-foreground">No active debates yet</p>
              <p className="font-mono text-xs text-muted-foreground/60 mt-1">
                Governance proposals appear here automatically
              </p>
            </div>
            <Link href="/governance">
              <Button size="sm" variant="outline" className="font-mono text-xs border-purple-500/30 text-purple-400">
                Go to Governance DAO
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <Button className="w-full h-12 font-mono text-sm font-bold border-purple-500/30 text-purple-400 hover:bg-purple-500/10" variant="outline">
        <Sword className="mr-2 w-4 h-4" /> Propose New Debate
      </Button>
    </div>
  );
}
