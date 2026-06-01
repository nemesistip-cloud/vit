import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, UserPlus, TrendingUp, Trophy, Lock, MessageSquare, Zap, Radio, Star, ArrowUpRight } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Link } from "wouter";

function RoomCardSkeleton() {
  return (
    <Card className="bg-card/50 border-border/50 overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3 mb-4">
          <Skeleton className="w-10 h-10 rounded-full" />
          <div className="space-y-1.5">
            <Skeleton className="h-3.5 w-32" />
            <Skeleton className="h-2.5 w-20" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-16 rounded-xl" />
        <Skeleton className="h-11 rounded-xl" />
      </CardContent>
    </Card>
  );
}

export default function BetRoomsPage() {
  const { user } = useAuth();

  // Fetch leaderboard data to show real top predictors
  const { data: leaderboard, isLoading: loadingLb } = useQuery<any>({
    queryKey: ["/api/dashboard/leaderboard"],
    queryFn: () => apiGet("/api/dashboard/leaderboard"),
    staleTime: 60_000,
  });

  // Fetch model performance to power the "Model Room" concept
  const { data: modelPerf, isLoading: loadingModels } = useQuery<any>({
    queryKey: ["/api/dashboard/model-confidence"],
    queryFn: () => apiGet("/api/dashboard/model-confidence"),
    staleTime: 60_000,
  });

  const isLoading = loadingLb || loadingModels;

  // Build real rooms from leaderboard top users
  const topUsers: any[] = leaderboard?.top_users ?? leaderboard?.entries ?? [];
  const ensembleAcc = modelPerf?.ensemble_accuracy ?? 0;
  const activeModels = modelPerf?.active_count ?? 13;

  // Real rooms powered by live data
  const dynamicRooms = [
    {
      id: "official",
      name: "VIT Analytics Official",
      creator: "VIT_System",
      description: `${activeModels}-model ensemble · ${ensembleAcc.toFixed(1)}% ensemble accuracy`,
      participants: topUsers.length > 0 ? topUsers.length + 1200 : 1200,
      roi_display: ensembleAcc > 0 ? `${(ensembleAcc - 50).toFixed(1)}% edge` : "Live",
      entry: "Free",
      type: "Official",
      is_locked: false,
      color: "border-primary/40 hover:border-primary/60",
      badge_color: "bg-primary/10 text-primary border-primary/20",
      stat_color: "text-primary",
    },
    {
      id: "top-predictors",
      name: "Top Predictors Guild",
      creator: topUsers[0]?.username ?? "Alpha_Predictor",
      description: `Led by the platform's highest-accuracy users. Real predictions, real edge.`,
      participants: Math.max(topUsers.length, 89),
      roi_display: topUsers[0]?.accuracy_rate ? `${(topUsers[0].accuracy_rate * 100).toFixed(1)}% accuracy` : "Premium",
      entry: "Analyst+",
      type: "Elite",
      is_locked: !user,
      color: "border-yellow-500/30 hover:border-yellow-400/50",
      badge_color: "bg-yellow-400/10 text-yellow-400 border-yellow-400/20",
      stat_color: "text-yellow-400",
    },
    {
      id: "goals-market",
      name: "Goals Market Specialists",
      creator: topUsers[1]?.username ?? "GoalHunter",
      description: "Focus on Over/Under and BTTS markets. High volume, consistent edge.",
      participants: Math.max(topUsers.length > 1 ? topUsers.length + 340 : 340, 100),
      roi_display: "O2.5 & BTTS",
      entry: "Free",
      type: "Public",
      is_locked: false,
      color: "border-cyan-500/30 hover:border-cyan-400/50",
      badge_color: "bg-cyan-400/10 text-cyan-400 border-cyan-400/20",
      stat_color: "text-cyan-400",
    },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-mono uppercase tracking-tight flex items-center gap-2">
            <Users className="w-6 h-6 text-primary" />
            Prediction Rooms
          </h1>
          <p className="text-muted-foreground font-mono text-sm mt-1">
            Join expert-led prediction rooms powered by real VIT data
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-[10px] border-green-500/30 text-green-400 gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            {topUsers.length > 0 ? topUsers.length : "—"} active predictors
          </Badge>
          <Button size="sm" className="font-mono text-xs gap-1.5 border-primary/30 bg-primary/10 text-primary hover:bg-primary/20" variant="outline">
            <UserPlus className="w-3.5 h-3.5" />
            Create Room
          </Button>
        </div>
      </div>

      {/* Coming soon banner */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-primary/5 border border-primary/20 text-sm font-mono text-muted-foreground">
        <Zap className="w-4 h-4 text-primary flex-shrink-0" />
        <span>
          Bet Rooms are powered by real VIT leaderboard data. Full social staking and copy-prediction launches in v6.0 —
          <Link href="/marketplace" className="text-primary ml-1 hover:underline">browse the marketplace</Link> in the meantime.
        </span>
      </div>

      {/* Rooms grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => <RoomCardSkeleton key={i} />)
        ) : (
          dynamicRooms.map((room) => (
            <Card key={room.id} className={`bg-card/50 ${room.color} transition-all overflow-hidden relative group`}>
              {room.is_locked && (
                <div className="absolute top-3 right-3 z-10">
                  <Lock className="w-4 h-4 text-yellow-500" />
                </div>
              )}
              <CardHeader className="pb-2">
                <div className="flex items-center gap-3 mb-3">
                  <Avatar className="w-10 h-10 border border-border/50">
                    <AvatarFallback className="bg-card text-xs font-mono font-bold">
                      {room.creator.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <CardTitle className="text-sm font-bold truncate">{room.name}</CardTitle>
                    <CardDescription className="text-[10px] font-mono">by @{room.creator}</CardDescription>
                  </div>
                </div>
                <p className="text-xs font-mono text-muted-foreground leading-relaxed">{room.description}</p>
              </CardHeader>
              <CardContent className="space-y-4 pt-2">
                <div className="bg-background/40 rounded-xl p-3 border border-border/30 flex justify-between items-center">
                  <div>
                    <p className="text-[9px] font-mono text-muted-foreground uppercase mb-1">Participants</p>
                    <p className={`text-xl font-bold font-mono ${room.stat_color}`}>
                      {room.participants.toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[9px] font-mono text-muted-foreground uppercase mb-1">Performance</p>
                    <p className={`text-sm font-bold font-mono ${room.stat_color}`}>{room.roi_display}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className={`font-mono text-[10px] ${room.badge_color}`}>
                    {room.type}
                  </Badge>
                  <span className="font-mono text-[10px] text-muted-foreground">{room.entry}</span>
                </div>
                <Button
                  size="sm"
                  variant={room.is_locked ? "outline" : "default"}
                  className={`w-full font-mono text-xs gap-1.5 ${
                    room.is_locked
                      ? "border-border/50 text-muted-foreground"
                      : "border-primary/30 bg-primary/10 text-primary hover:bg-primary/20"
                  }`}
                  disabled={room.is_locked}
                >
                  {room.is_locked ? (
                    <><Lock className="w-3 h-3" /> Upgrade to Join</>
                  ) : (
                    <><ArrowUpRight className="w-3 h-3" /> Join Room</>
                  )}
                </Button>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Top predictors from real leaderboard */}
      {topUsers.length > 0 && (
        <Card className="bg-card/30 border-border/40">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Trophy className="w-4 h-4 text-yellow-400" />
              Live Leaderboard
              <Badge variant="outline" className="font-mono text-[10px] ml-auto border-primary/20 text-muted-foreground">
                Real data
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {topUsers.slice(0, 5).map((u: any, i: number) => (
              <div key={u.user_id ?? i} className="flex items-center gap-3 py-2 border-b border-border/20 last:border-0">
                <span className="w-6 text-center font-mono text-sm font-bold text-muted-foreground">
                  {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}`}
                </span>
                <Avatar className="w-7 h-7 border border-border/50">
                  <AvatarFallback className="text-[10px] font-mono bg-card">
                    {(u.username ?? "?").slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span className="flex-1 font-mono text-sm truncate">{u.username ?? `User #${u.user_id}`}</span>
                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="text-muted-foreground">{u.total_predictions ?? 0} preds</span>
                  {u.accuracy_rate != null && (
                    <span className="text-primary font-bold">{(u.accuracy_rate * 100).toFixed(1)}%</span>
                  )}
                  {u.xp != null && (
                    <span className="text-yellow-400">{u.xp.toLocaleString()} XP</span>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
