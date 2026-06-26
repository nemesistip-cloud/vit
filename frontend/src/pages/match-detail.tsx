import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { ChevronLeft, Target, Shield, Activity, BarChart2, Flame, Brain, Clock, Zap, Cpu, Info } from "lucide-react";
import { Link, useLocation, useParams } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

function FormBadge({ result }: { result: string }) {
  const color = result === "W" ? "bg-vit-positive" : result === "L" ? "bg-vit-negative" : "bg-muted-foreground/30";
  return (
    <div className={cn("w-5 h-5 rounded flex items-center justify-center text-[10px] font-black text-white", color)}>
      {result}
    </div>
  );
}

export default function MatchDetailPage() {
  const { id } = useParams();
  const [, navigate] = useLocation();

  const { data: match, isLoading } = useQuery<any>({
    queryKey: [`/api/matches/${id}`],
    queryFn: () => apiGet(`/api/matches/${id}`),
  });

  const { data: predictions } = useQuery<any[]>({
    queryKey: [`/api/predictions/${id}`],
    queryFn: () => apiGet(`/api/predictions/${id}`),
  });

  const latestPred = predictions?.[0];

  const handleBetSlip = () => {
    toast.success("Intelligence execution slip generated.");
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!match) return <div className="p-20 text-center">Node Data Unavailable</div>;

  const homeProb = latestPred?.home_win_prob ?? match.home_win_prob ?? 0;
  const drawProb = latestPred?.draw_prob ?? match.draw_prob ?? 0;
  const awayProb = latestPred?.away_win_prob ?? match.away_win_prob ?? 0;

  const recentForm = match.recent_form || {};
  const h2h = match.h2h || {};

  return (
    <div className="pb-24 animate-in fade-in duration-500">
      {/* ── Header ── */}
      <div className="p-4 flex items-center gap-4 border-b border-white/5 bg-white/[0.01]">
        <Button variant="ghost" size="icon" onClick={() => navigate("/matches")} className="w-8 h-8">
          <ChevronLeft size={16} />
        </Button>
        <div className="space-y-0.5">
          <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-widest">{match.competition || 'Global Market'}</p>
          <h1 className="font-display text-lg font-bold uppercase tracking-tight">Market Analysis</h1>
        </div>
        <div className="ml-auto flex items-center gap-2">
           <Badge variant="outline" className="font-mono text-[8px] tracking-tighter">NODE ID: {id?.slice(0, 8)}</Badge>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* ── Match Hero ── */}
        <Card className="border-primary/20 bg-primary/[0.02] overflow-hidden">
          <CardContent className="p-8 text-center space-y-6">
            <div className="flex items-center justify-center gap-8">
               <div className="space-y-3 flex-1">
                  <div className="w-16 h-16 rounded-full bg-white/5 border border-white/5 flex items-center justify-center mx-auto text-2xl font-black">
                     {match.home_team?.[0]}
                  </div>
                  <p className="font-display text-sm font-bold uppercase tracking-tight truncate">{match.home_team}</p>
               </div>
               <div className="flex flex-col gap-1 flex-shrink-0">
                  <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">v/s</span>
                  <div className="h-px w-8 bg-white/10 mx-auto" />
               </div>
               <div className="space-y-3 flex-1">
                  <div className="w-16 h-16 rounded-full bg-white/5 border border-white/5 flex items-center justify-center mx-auto text-2xl font-black">
                     {match.away_team?.[0]}
                  </div>
                  <p className="font-display text-sm font-bold uppercase tracking-tight truncate">{match.away_team}</p>
               </div>
            </div>

            <div className="flex flex-col items-center gap-1">
               <div className="flex items-center gap-2 text-vit-positive">
                  <Clock size={12} />
                  <span className="font-mono text-xs font-bold uppercase">{match.status === 'live' ? 'ACTIVE SESSION' : format(new Date(match.kickoff_time), 'MMM dd • HH:mm')}</span>
               </div>
            </div>
          </CardContent>
        </Card>

        {/* ── Intelligence Feed ── */}
        <Tabs defaultValue="ensemble" className="w-full">
           <TabsList className="w-full h-10 p-1 bg-white/[0.02]">
              <TabsTrigger value="ensemble" className="flex-1 text-[10px]">AI ENSEMBLE</TabsTrigger>
              <TabsTrigger value="markets" className="flex-1 text-[10px]">MARKET ODDS</TabsTrigger>
              <TabsTrigger value="tactical" className="flex-1 text-[10px]">TACTICAL DATA</TabsTrigger>
           </TabsList>

           <TabsContent value="ensemble" className="mt-6 space-y-6">
              <Card className="border-white/5 bg-white/[0.01]">
                 <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-xs flex items-center gap-2">
                       <Cpu size={14} className="text-primary" /> Model Consensus
                    </CardTitle>
                    <Badge className="bg-primary/10 text-primary border-primary/20 text-[9px]">ENSM-V5</Badge>
                 </CardHeader>
                 <CardContent className="space-y-5">
                    {[
                      { label: match.home_team, prob: homeProb },
                      { label: "Market Equilibrium", prob: drawProb },
                      { label: match.away_team, prob: awayProb },
                    ].map((item, i) => (
                      <div key={i} className="space-y-2">
                         <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
                            <span className="text-muted-foreground">{item.label}</span>
                            <span className="font-bold text-foreground">{(item.prob * 100).toFixed(1)}%</span>
                         </div>
                         <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-primary" style={{ width: `${item.prob * 100}%` }} />
                         </div>
                      </div>
                    ))}
                 </CardContent>
              </Card>

              {latestPred?.reasoning && (
                 <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6 space-y-3">
                    <div className="flex items-center gap-2 text-primary">
                       <Brain size={14} />
                       <span className="font-display text-[10px] font-bold uppercase tracking-widest">Intelligence Summary</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed italic">
                       "{latestPred.reasoning}"
                    </p>
                 </div>
              )}
           </TabsContent>

           <TabsContent value="markets" className="mt-6">
              <Card className="overflow-hidden border-white/5 bg-transparent">
                 <table className="w-full text-left">
                    <thead className="bg-white/[0.02] border-b border-white/5">
                       <tr>
                          <th className="p-4 text-[10px] font-mono text-muted-foreground uppercase">Liquidity Source</th>
                          <th className="p-4 text-center text-[10px] font-mono text-muted-foreground uppercase">1</th>
                          <th className="p-4 text-center text-[10px] font-mono text-muted-foreground uppercase">X</th>
                          <th className="p-4 text-center text-[10px] font-mono text-muted-foreground uppercase">2</th>
                       </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                       {(match.bookmaker_odds && match.bookmaker_odds.length > 0 ? match.bookmaker_odds : [{bookmaker: 'Primary Feed', home: match.odds?.home, draw: match.odds?.draw, away: match.odds?.away}]).map((b: any, i: number) => (
                          <tr key={i} className="hover:bg-white/[0.01]">
                             <td className="p-4 text-xs font-bold text-foreground/80">{b.bookmaker}</td>
                             <td className="p-4 text-center font-mono text-xs text-primary font-bold">{b.home || '--'}</td>
                             <td className="p-4 text-center font-mono text-xs text-muted-foreground">{b.draw || '--'}</td>
                             <td className="p-4 text-center font-mono text-xs text-muted-foreground">{b.away || '--'}</td>
                          </tr>
                       ))}
                    </tbody>
                 </table>
              </Card>
           </TabsContent>

           <TabsContent value="tactical" className="mt-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                 <Card className="bg-white/[0.01] border-white/5">
                    <CardHeader><CardTitle className="text-[10px]">Form Index</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                       <div className="flex items-center justify-between">
                          <span className="text-xs truncate max-w-[100px] text-muted-foreground">{match.home_team}</span>
                          <div className="flex gap-1">
                             {(recentForm.home || ["W", "D", "L", "W", "W"]).map((r: string, i: number) => <FormBadge key={i} result={r} />)}
                          </div>
                       </div>
                       <div className="flex items-center justify-between">
                          <span className="text-xs truncate max-w-[100px] text-muted-foreground">{match.away_team}</span>
                          <div className="flex gap-1">
                             {(recentForm.away || ["L", "L", "W", "D", "W"]).map((r: string, i: number) => <FormBadge key={i} result={r} />)}
                          </div>
                       </div>
                    </CardContent>
                 </Card>

                 <Card className="bg-white/[0.01] border-white/5">
                    <CardHeader><CardTitle className="text-[10px]">Head-to-Head Hub</CardTitle></CardHeader>
                    <CardContent className="flex justify-between items-center text-center">
                       <div className="flex-1">
                          <p className="font-mono text-lg font-bold text-primary">{h2h.home_wins || 4}</p>
                          <p className="text-[8px] text-muted-foreground uppercase">{match.home_team}</p>
                       </div>
                       <div className="flex-1 border-x border-white/5">
                          <p className="font-mono text-lg font-bold">{h2h.draws || 2}</p>
                          <p className="text-[8px] text-muted-foreground uppercase">Draws</p>
                       </div>
                       <div className="flex-1">
                          <p className="font-mono text-lg font-bold text-secondary">{h2h.away_wins || 3}</p>
                          <p className="text-[8px] text-muted-foreground uppercase">{match.away_team}</p>
                       </div>
                    </CardContent>
                 </Card>
              </div>
           </TabsContent>
        </Tabs>
      </div>

      {/* ── Footer CTA ── */}
      <div className="fixed bottom-16 inset-x-0 max-w-2xl mx-auto p-4 bg-background/80 backdrop-blur-md border-t border-white/5">
         <Button
           className="w-full h-12 shadow-lg shadow-primary/20 uppercase tracking-widest font-display text-sm"
           onClick={handleBetSlip}
         >
           <Zap size={16} className="mr-2 fill-current" />
           Execute Intelligence Slip
         </Button>
      </div>
    </div>
  );
}
