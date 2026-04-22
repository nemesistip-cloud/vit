import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trophy, TrendingUp, Zap, Target, Crown, Medal, Award } from "lucide-react";
import { useAuth } from "@/lib/auth";

interface LeaderboardEntry {
  rank: number;
  user_id: number;
  username: string;
  total_predictions: number;
  win_rate: number;
  roi: number;
  xp: number;
  streak: number;
  subscription_tier: string;
}

interface LeaderboardData {
  category: string;
  entries: LeaderboardEntry[];
  total_users: number;
}

const CATEGORY_OPTIONS = [
  { value: "win_rate", label: "Win Rate", icon: Target },
  { value: "xp", label: "XP Points", icon: Zap },
  { value: "streak", label: "Streak", icon: TrendingUp },
  { value: "predictions", label: "Most Active", icon: Trophy },
];

const TIER_COLORS: Record<string, string> = {
  elite: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
  pro: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  analyst: "text-purple-400 border-purple-400/30 bg-purple-400/10",
  viewer: "text-gray-400 border-gray-400/30 bg-gray-400/10",
};

function RankIcon({ rank }: { rank: number }) {
  if (rank === 1) return <Crown className="w-5 h-5 text-yellow-400" />;
  if (rank === 2) return <Medal className="w-5 h-5 text-gray-300" />;
  if (rank === 3) return <Award className="w-5 h-5 text-amber-600" />;
  return <span className="font-mono text-sm text-muted-foreground w-5 text-center">{rank}</span>;
}

export default function LeaderboardPage() {
  const [category, setCategory] = useState("win_rate");
  const { user } = useAuth();

  const { data, isLoading } = useQuery<LeaderboardData>({
    queryKey: ["leaderboard", category],
    queryFn: () => apiGet(`/api/leaderboard?category=${category}&limit=20`),
    staleTime: 60_000,
  });

  const getMetricValue = (entry: LeaderboardEntry) => {
    switch (category) {
      case "win_rate": return `${entry.win_rate}%`;
      case "xp": return `${entry.xp.toLocaleString()} XP`;
      case "streak": return `${entry.streak} 🔥`;
      case "predictions": return `${entry.total_predictions} picks`;
      default: return "";
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-yellow-500/10 border border-yellow-500/20 rounded-xl flex items-center justify-center">
          <Trophy className="w-5 h-5 text-yellow-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight">Leaderboard</h1>
          <p className="text-sm text-muted-foreground font-mono">
            Top predictors — {data?.total_users ?? 0} users ranked
          </p>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        {CATEGORY_OPTIONS.map((opt) => (
          <Button
            key={opt.value}
            variant={category === opt.value ? "default" : "outline"}
            size="sm"
            className="font-mono text-xs gap-1.5"
            onClick={() => setCategory(opt.value)}
          >
            <opt.icon className="w-3.5 h-3.5" />
            {opt.label}
          </Button>
        ))}
      </div>

      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono">
            {CATEGORY_OPTIONS.find(o => o.value === category)?.label} Rankings
          </CardTitle>
          <CardDescription className="font-mono text-xs">
            All verified predictors on the platform
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="h-12 rounded-md bg-muted/30 animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-1">
              {(data?.entries ?? []).map((entry) => {
                const isMe = user?.id === entry.user_id;
                return (
                  <div
                    key={entry.user_id}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors ${
                      isMe
                        ? "bg-primary/10 border border-primary/20"
                        : "hover:bg-muted/30"
                    }`}
                  >
                    <div className="w-6 flex items-center justify-center flex-shrink-0">
                      <RankIcon rank={entry.rank} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-medium truncate">
                          {entry.username}
                          {isMe && <span className="text-primary ml-1">(you)</span>}
                        </span>
                        <Badge
                          variant="outline"
                          className={`text-[10px] font-mono hidden sm:inline-flex ${
                            TIER_COLORS[entry.subscription_tier] ?? TIER_COLORS.viewer
                          }`}
                        >
                          {entry.subscription_tier}
                        </Badge>
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono">
                        {entry.total_predictions} predictions · {entry.win_rate}% win rate
                      </div>
                    </div>

                    <div className="font-mono font-bold text-sm text-primary tabular-nums">
                      {getMetricValue(entry)}
                    </div>
                  </div>
                );
              })}

              {(data?.entries ?? []).length === 0 && (
                <div className="py-12 text-center text-muted-foreground font-mono text-sm">
                  No entries yet. Be the first to make predictions!
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
