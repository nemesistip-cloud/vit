import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Lock, CheckCircle2, ChevronRight, Trophy, Flame, Loader2 } from "lucide-react";
import { useLocation } from "wouter";

interface ProphecyChapter {
  id: number;
  title: string;
  description: string;
  sequence_order: number;
  required_predictions: number;
  required_accuracy: number;
  reward_vit: number;
  reward_xp: number;
  reward_badge: string;
}

interface UserStatus {
  current_chapter_id: number | null;
  chapters_completed: number[];
  total_qualified_predictions: number;
  current_accuracy: number;
  is_enrolled: boolean;
}

export default function ProphecyChainPage() {
  const [, setLocation] = useLocation();

  const { data: chapters, isLoading: loadingChapters } = useQuery<ProphecyChapter[]>({
    queryKey: ["prophecy-chapters"],
    queryFn: () => apiGet("/api/prophecy/chapters"),
  });

  const { data: status, isLoading: loadingStatus } = useQuery<UserStatus>({
    queryKey: ["prophecy-status"],
    queryFn: () => apiGet("/api/prophecy/status"),
  });

  if (loadingChapters || loadingStatus) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-8 h-8 text-yellow-500 animate-spin" />
        <span className="font-mono text-xs text-muted-foreground uppercase tracking-widest">Consulting the Oracle…</span>
      </div>
    );
  }

  const completedIds = status?.chapters_completed || [];
  const currentId = status?.current_chapter_id;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black uppercase tracking-tighter italic flex items-center gap-3 text-white">
            <Sparkles className="w-8 h-8 text-yellow-400" />
            Prophecy Chain
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Serialized narrative prediction game. Unlock chapters, earn rewards, become a Prophet.
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
           <div className="flex items-center gap-2 bg-orange-500/10 border border-orange-500/20 px-4 py-2 rounded-xl">
            <Flame className="w-5 h-5 text-orange-500" />
            <span className="font-black text-orange-500 uppercase tracking-tighter italic">Qualified: {status?.total_qualified_predictions || 0}</span>
          </div>
          <div className="text-[10px] font-mono text-zinc-500 uppercase">Accuracy: {((status?.current_accuracy || 0) * 100).toFixed(1)}%</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 relative">
        <div className="absolute left-8 top-12 bottom-12 w-0.5 bg-zinc-800 z-0 hidden md:block" />

        {chapters?.map((ch) => {
          const isCompleted = completedIds.includes(ch.id);
          const isActive = currentId === ch.id || (!currentId && ch.sequence_order === 1);
          const isLocked = !isCompleted && !isActive;

          return (
            <Card
              key={ch.id}
              className={`bg-zinc-900 border-border/50 relative z-10 overflow-hidden transition-all ${
                isLocked ? 'opacity-60 grayscale' : 'hover:border-yellow-500/30'
              }`}
            >
              <CardContent className="p-0 flex flex-col md:flex-row">
                <div className={`p-6 md:w-20 flex items-center justify-center border-b md:border-b-0 md:border-r border-border/50 ${
                  isCompleted ? 'bg-emerald-500/10' : isActive ? 'bg-yellow-500/10' : 'bg-zinc-800/50'
                }`}>
                  {isCompleted ? (
                    <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                  ) : isLocked ? (
                    <Lock className="w-6 h-6 text-zinc-500" />
                  ) : (
                    <span className="text-2xl font-black text-yellow-500 italic">0{ch.sequence_order}</span>
                  )}
                </div>

                <div className="p-6 flex-1 flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-bold text-lg text-white">{ch.title}</h3>
                      {isActive && <Badge className="bg-yellow-500 text-black font-mono text-[10px]">CURRENT CHAPTER</Badge>}
                    </div>
                    <p className="text-sm text-zinc-400 max-w-md">{ch.description}</p>
                    <div className="mt-2 flex items-center gap-4">
                      <div className="text-[10px] font-mono text-zinc-500 uppercase">
                        Req: {ch.required_predictions} Preds / {(ch.required_accuracy * 100).toFixed(0)}% Acc
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col md:items-end gap-3">
                    <div className="flex flex-col gap-1 text-right">
                      {ch.reward_badge && (
                        <div className="flex items-center justify-end gap-2 text-xs font-mono text-zinc-500">
                          <Trophy className="w-3 h-3" />
                          BADGE: <span className="text-zinc-200 font-bold">{ch.reward_badge}</span>
                        </div>
                      )}
                      {ch.reward_vit > 0 && (
                        <div className="text-[10px] font-mono text-yellow-500/70">+{ch.reward_vit} VIT COIN</div>
                      )}
                      {ch.reward_xp > 0 && (
                        <div className="text-[10px] font-mono text-blue-400/70">+{ch.reward_xp} Intelligence Points</div>
                      )}
                    </div>

                    {isActive ? (
                      <Button
                        onClick={() => setLocation("/predictions")}
                        className="bg-yellow-500 hover:bg-yellow-400 text-black font-black uppercase tracking-tighter rounded-xl"
                      >
                        Enter Predictions <ChevronRight className="ml-1 w-4 h-4" />
                      </Button>
                    ) : isCompleted ? (
                      <span className="text-emerald-500 font-bold uppercase text-xs tracking-widest">CHAPTER SEALED</span>
                    ) : (
                      <span className="text-zinc-600 font-bold uppercase text-xs tracking-widest italic">LOCKED BY FATE</span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
