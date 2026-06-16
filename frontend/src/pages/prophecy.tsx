import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  Lock,
  CheckCircle2,
  ChevronRight,
  Trophy,
  Zap,
  Target,
  ShieldCheck,
  RefreshCw
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";

interface ProphecyChapter {
  id: number;
  title: string;
  description: string;
  required_predictions: number;
  required_accuracy: number;
  reward_vit: number;
  reward_xp: number;
  sequence_order: number;
  is_active: boolean;
}

interface UserProphecyStatus {
  current_chapter_id: number | null;
  chapters_completed: number[];
  total_qualified_predictions: number;
  current_accuracy: number;
  is_enrolled: boolean;
}

export default function ProphecyPage() {
  const qc = useQueryClient();
  const { data: config } = usePublicConfig();

  const { data: status, isLoading: statusLoading } = useQuery<UserProphecyStatus>({
    queryKey: ["prophecy-status"],
    queryFn: () => apiGet<UserProphecyStatus>("/api/prophecy/status"),
  });

  const { data: chapters, isLoading: chaptersLoading } = useQuery<ProphecyChapter[]>({
    queryKey: ["prophecy-chapters"],
    queryFn: () => apiGet<ProphecyChapter[]>("/api/prophecy/chapters"),
  });

  const enrollMutation = useMutation({
    mutationFn: () => apiPost("/api/prophecy/enroll", {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prophecy-status"] });
      toast.success("Enrolled in Prophecy Chain!");
    },
  });

  const completeMutation = useMutation({
    mutationFn: (chapterId: number) => apiPost(`/api/prophecy/chapters/${chapterId}/complete`, {}),
    onSuccess: (data: any) => {
      qc.invalidateQueries({ queryKey: ["prophecy-status"] });
      qc.invalidateQueries({ queryKey: ["wallet"] });
      toast.success(`Chapter Completed! Earned ${data.rewards.vit} VIT and ${data.rewards.xp} XP`);
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to complete chapter. Check requirements.");
    }
  });

  if (statusLoading || chaptersLoading) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-4 w-1/2" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const isEnrolled = status?.is_enrolled;
  const currentChapterId = status?.current_chapter_id;
  const chaptersCompleted = status?.chapters_completed || [];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto p-4">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-secondary" />
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground uppercase">Prophecy Chain</h1>
        </div>
        <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Master the art of prediction and ascend the chain</p>
      </header>

      {!isEnrolled ? (
        <Card className="bg-secondary/5 border-secondary/20 p-8 text-center space-y-6">
          <div className="max-w-xl mx-auto space-y-4">
            <h2 className="text-xl font-bold font-mono uppercase">Initialize Your Journey</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The Prophecy Chain is a game-ified progression system for analysts.
              Complete accuracy and volume milestones to unlock exclusive rewards,
              governance rights, and advanced AI model access.
            </p>
            <Button
              size="lg"
              className="bg-secondary text-secondary-foreground hover:bg-secondary/90 font-mono uppercase tracking-widest"
              onClick={() => enrollMutation.mutate()}
              disabled={enrollMutation.isPending}
            >
              {enrollMutation.isPending ? "Enrolling..." : "Begin Ascension"}
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="space-y-4">
              <h3 className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-2">
                <Target className="w-3 h-3" /> Progression Chapters
              </h3>
              <div className="space-y-4">
                {chapters?.map((chapter) => {
                  const isCompleted = chaptersCompleted.includes(chapter.id);
                  const isCurrent = currentChapterId === chapter.id;
                  const isLocked = !isCompleted && !isCurrent;

                  return (
                    <Card key={chapter.id} className={`bg-card/40 border-border/40 overflow-hidden transition-all ${isCurrent ? "ring-1 ring-secondary/50 border-secondary/30" : ""}`}>
                      <div className="p-5 flex items-start gap-4">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${
                          isCompleted ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" :
                          isCurrent ? "bg-secondary/10 border-secondary/20 text-secondary" :
                          "bg-muted/50 border-border/50 text-muted-foreground"
                        }`}>
                          {isCompleted ? <CheckCircle2 className="w-5 h-5" /> :
                           isLocked ? <Lock className="w-5 h-5" /> :
                           <Sparkles className="w-5 h-5 animate-pulse" />}
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center justify-between">
                            <h4 className={`font-mono font-bold ${isLocked ? "text-muted-foreground" : "text-foreground"}`}>
                              Chapter {chapter.sequence_order}: {chapter.title}
                            </h4>
                            {isCompleted && <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[8px] font-mono uppercase">Mastered</Badge>}
                            {isCurrent && <Badge className="bg-secondary/10 text-secondary border-secondary/20 text-[8px] font-mono uppercase animate-pulse">In Progress</Badge>}
                          </div>
                          <p className="text-[11px] font-mono text-muted-foreground leading-relaxed">
                            {chapter.description}
                          </p>

                          {(isCurrent || isCompleted) && (
                            <div className="pt-3 grid grid-cols-2 gap-4">
                              <div className="space-y-1">
                                <div className="flex justify-between text-[9px] font-mono uppercase">
                                  <span>Predictions</span>
                                  <span>{status.total_qualified_predictions} / {chapter.required_predictions}</span>
                                </div>
                                <Progress value={Math.min(100, (status.total_qualified_predictions / chapter.required_predictions) * 100)} className="h-1" />
                              </div>
                              <div className="space-y-1">
                                <div className="flex justify-between text-[9px] font-mono uppercase">
                                  <span>Accuracy</span>
                                  <span>{(status.current_accuracy * 100).toFixed(1)}% / {(chapter.required_accuracy * 100).toFixed(1)}%</span>
                                </div>
                                <Progress value={Math.min(100, (status.current_accuracy / chapter.required_accuracy) * 100)} className="h-1" />
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {isCurrent && (
                        <div className="px-5 py-3 bg-secondary/5 border-t border-secondary/10 flex justify-between items-center">
                          <div className="flex gap-3 text-[10px] font-mono">
                            <span className="text-secondary">Reward: {chapter.reward_vit} VIT</span>
                            <span className="text-primary">+{chapter.reward_xp} XP</span>
                          </div>
                          <Button
                            size="sm"
                            className="h-7 text-[10px] font-mono uppercase tracking-widest bg-secondary text-secondary-foreground"
                            disabled={
                              status.total_qualified_predictions < chapter.required_predictions ||
                              status.current_accuracy < chapter.required_accuracy ||
                              completeMutation.isPending
                            }
                            onClick={() => completeMutation.mutate(chapter.id)}
                          >
                            {completeMutation.isPending ? "Validating..." : "Complete Chapter"}
                          </Button>
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <Card className="bg-card/50 border-border/40">
              <CardHeader>
                <CardTitle className="text-sm font-mono flex items-center gap-2 uppercase tracking-wider">
                  <Trophy className="w-4 h-4 text-secondary" /> Current Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-background/50 border border-border/10 text-center">
                    <p className="text-[9px] font-mono text-muted-foreground uppercase">Predictions</p>
                    <p className="text-lg font-bold font-mono">{status.total_qualified_predictions}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-background/50 border border-border/10 text-center">
                    <p className="text-[9px] font-mono text-muted-foreground uppercase">Global Acc</p>
                    <p className="text-lg font-bold font-mono text-primary">{(status.current_accuracy * 100).toFixed(1)}%</p>
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-secondary/5 border border-secondary/20 flex items-center gap-3">
                  <ShieldCheck className="w-5 h-5 text-secondary" />
                  <div className="flex-1">
                    <p className="text-[10px] font-mono font-bold uppercase">Chain Level</p>
                    <p className="text-xs font-mono text-muted-foreground">{chaptersCompleted.length} Chapters Mastered</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/50 border-border/40">
              <CardHeader>
                <CardTitle className="text-sm font-mono flex items-center gap-2 uppercase tracking-wider">
                  <Zap className="w-4 h-4 text-primary" /> Mastery Benefits
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  { label: "Increased VIT Staking Limits", icon: ShieldCheck },
                  { label: "Advanced Model Insights", icon: Sparkles },
                  { label: "Governance Voting Power", icon: CheckCircle2 },
                  { label: "Priority Marketplace Access", icon: Trophy }
                ].map((benefit, i) => (
                  <div key={i} className="flex items-center gap-3 text-xs font-mono">
                    <benefit.icon className="w-3 h-3 text-primary opacity-60" />
                    <span className="text-muted-foreground">{benefit.label}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
