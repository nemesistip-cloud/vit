import { Trophy, Star, Flame, Medal, Award, TrendingUp, Crown, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/* ============================================================
   DB3: Gamification System
   - Level system
   - Achievement badges
   - Leaderboard
   - Streak counter
   ============================================================ */

export type Level = "Novice" | "Analyst" | "Pro" | "Elite" | "Legend";

interface LevelConfig {
  label: Level;
  minXP: number;
  maxXP: number;
  color: string;
  bgColor: string;
  icon: React.ElementType;
  glow: string;
}

export const LEVELS: LevelConfig[] = [
  { label: "Novice",  minXP: 0,    maxXP: 100,  color: "text-muted-foreground", bgColor: "bg-muted/30",        icon: Star,      glow: "" },
  { label: "Analyst", minXP: 100,  maxXP: 500,  color: "text-blue-400",         bgColor: "bg-blue-500/10",     icon: TrendingUp, glow: "" },
  { label: "Pro",     minXP: 500,  maxXP: 2000, color: "text-primary",          bgColor: "bg-primary/10",      icon: Trophy,    glow: "vit-glow-cyan" },
  { label: "Elite",   minXP: 2000, maxXP: 5000, color: "text-secondary",        bgColor: "bg-secondary/10",    icon: Crown,     glow: "vit-glow-gold" },
  { label: "Legend",  minXP: 5000, maxXP: 9999, color: "text-purple-400",       bgColor: "bg-purple-500/10",   icon: Zap,       glow: "vit-glow-purple" },
];

export function getLevel(xp: number): LevelConfig {
  return [...LEVELS].reverse().find((l) => xp >= l.minXP) ?? LEVELS[0];
}

interface LevelCardProps {
  xp: number;
  predictions?: number;
  winRate?: number;
  streak?: number;
}

export function LevelCard({ xp, predictions = 0, winRate = 0, streak = 0 }: LevelCardProps) {
  const level = getLevel(xp);
  const nextLevel = LEVELS[LEVELS.indexOf(level) + 1];
  const progress = nextLevel
    ? ((xp - level.minXP) / (nextLevel.minXP - level.minXP)) * 100
    : 100;

  return (
    <Card className={`border ${level.bgColor} ${level.glow}`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-xs font-mono text-muted-foreground uppercase mb-1">Current Level</div>
            <div className={`text-xl font-bold font-mono ${level.color} flex items-center gap-2`}>
              <level.icon className="w-5 h-5" />
              {level.label}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs font-mono text-muted-foreground">XP</div>
            <div className="text-lg font-bold font-mono">{xp.toLocaleString()}</div>
          </div>
        </div>

        {nextLevel && (
          <div className="mb-4">
            <div className="flex justify-between text-xs font-mono text-muted-foreground mb-1.5">
              <span>{level.label}</span>
              <span>{nextLevel.label} ({nextLevel.minXP - xp} XP to go)</span>
            </div>
            <Progress value={progress} className="h-1.5" />
          </div>
        )}

        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <div className="text-lg font-bold font-mono">{predictions}</div>
            <div className="text-[10px] font-mono text-muted-foreground uppercase">Predictions</div>
          </div>
          <div>
            <div className={`text-lg font-bold font-mono ${winRate >= 0.5 ? "text-green-400" : "text-destructive"}`}>
              {(winRate * 100).toFixed(0)}%
            </div>
            <div className="text-[10px] font-mono text-muted-foreground uppercase">Win Rate</div>
          </div>
          <div>
            <div className="text-lg font-bold font-mono flex items-center justify-center gap-1">
              {streak > 0 && <Flame className="w-4 h-4 text-orange-400" />}
              {streak}
            </div>
            <div className="text-[10px] font-mono text-muted-foreground uppercase">Streak</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Achievement Badges ───────────────────────────────── */

interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  earned: boolean;
  rarity: "common" | "rare" | "epic" | "legendary";
}

const RARITY_STYLES = {
  common:    "border-border bg-card text-muted-foreground",
  rare:      "border-blue-500/30 bg-blue-500/5 text-blue-400",
  epic:      "border-purple-500/30 bg-purple-500/5 text-purple-400",
  legendary: "border-secondary/40 bg-secondary/10 text-secondary",
};

interface AchievementBadgesProps {
  achievements?: Achievement[];
}

export function AchievementBadges({ achievements }: AchievementBadgesProps) {
  const displayAchievements = achievements ?? [];
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
          <Medal className="w-4 h-4 text-secondary" />
          Achievements
        </CardTitle>
      </CardHeader>
      <CardContent>
        {displayAchievements.length === 0 ? (
          <div className="rounded-lg border border-border/50 bg-muted/10 p-4 text-center text-xs font-mono text-muted-foreground">
            Achievements will unlock from your real prediction, wallet, and validator activity.
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {displayAchievements.map((a) => (
              <div
                key={a.id}
                title={`${a.name}: ${a.description}`}
                className={`rounded-lg border p-2.5 text-center transition-all ${
                  a.earned
                    ? RARITY_STYLES[a.rarity]
                    : "border-border/30 bg-muted/10 opacity-40 grayscale"
                }`}
              >
                <div className="text-xl mb-1">{a.icon}</div>
                <div className="text-[9px] font-mono leading-tight text-current opacity-80 truncate">
                  {a.name}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ── Leaderboard ──────────────────────────────────────── */

interface LeaderboardEntry {
  rank: number;
  username: string;
  xp: number;
  winRate: number;
  level: Level;
}

const RANK_COLORS: Record<number, string> = {
  1: "text-secondary",
  2: "text-gray-300",
  3: "text-amber-600",
};

interface LeaderboardProps {
  entries?: LeaderboardEntry[];
  currentUsername?: string;
}

export function Leaderboard({ entries, currentUsername }: LeaderboardProps) {
  const displayEntries = entries ?? [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
          <Trophy className="w-4 h-4 text-primary" />
          Leaderboard
          <Badge variant="outline" className="ml-auto font-mono text-[10px]">
            Top {displayEntries.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {displayEntries.length === 0 ? (
          <div className="px-4 py-8 text-center text-xs font-mono text-muted-foreground">
            Make predictions to appear on the real leaderboard.
          </div>
        ) : (
          <div className="divide-y divide-border/50">
            {displayEntries.map((e) => {
            const levelCfg = LEVELS.find((l) => l.label === e.level) ?? LEVELS[0];
            const isMe = e.username === currentUsername;
            return (
              <div
                key={e.rank}
                className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${isMe ? "bg-primary/5" : "hover:bg-muted/30"}`}
              >
                <span className={`w-6 text-sm font-bold font-mono text-right flex-shrink-0 ${RANK_COLORS[e.rank] ?? "text-muted-foreground"}`}>
                  {e.rank <= 3 ? ["🥇","🥈","🥉"][e.rank - 1] : e.rank}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={`text-sm font-mono font-medium truncate ${isMe ? "text-primary" : "text-foreground"}`}>
                      {e.username}
                    </span>
                    {isMe && <Badge className="text-[9px] font-mono bg-primary/20 text-primary border-primary/30">You</Badge>}
                  </div>
                  <div className={`text-[10px] font-mono ${levelCfg.color}`}>{e.level}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-sm font-bold font-mono">{e.xp.toLocaleString()}</div>
                  <div className="text-[10px] font-mono text-muted-foreground">{(e.winRate * 100).toFixed(0)}% WR</div>
                </div>
              </div>
            );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ── Streak Counter Widget ────────────────────────────── */

export function StreakCounter({ streak }: { streak: number }) {
  if (streak === 0) return null;

  const intensity = Math.min(streak / 10, 1);
  const color = streak >= 5 ? "text-orange-400" : streak >= 3 ? "text-yellow-400" : "text-muted-foreground";

  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border ${streak >= 5 ? "border-orange-500/30 bg-orange-500/10" : "border-border bg-muted/30"}`}>
      <Flame className={`w-4 h-4 ${color}`} style={{ opacity: 0.5 + intensity * 0.5 }} />
      <span className={`text-sm font-bold font-mono ${color}`}>{streak}</span>
      <span className="text-xs font-mono text-muted-foreground">streak</span>
    </div>
  );
}
