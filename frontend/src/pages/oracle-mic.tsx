import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Play, Pause, SkipForward, Heart, Mic2, Lock } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface Episode {
  id: string;
  title: string;
  host: string;
  date: string;
  length: string;
  premium: boolean;
  current: boolean;
}

interface EpisodesResponse {
  current_episode: Episode | null;
  episodes: Episode[];
  generated_at: string;
}

export default function OraclesMicPage() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(35);
  const [activeEpisodeId, setActiveEpisodeId] = useState<string | null>(null);

  const { data, isLoading } = useQuery<EpisodesResponse>({
    queryKey: ["oracle-mic-episodes"],
    queryFn: () => apiGet("/api/freemium/oracle-mic/episodes"),
    staleTime: 5 * 60_000,
  });

  const currentEp = activeEpisodeId
    ? data?.episodes.find((e) => e.id === activeEpisodeId) ?? data?.current_episode
    : data?.current_episode;

  const handlePlayEpisode = (ep: Episode) => {
    if (ep.premium) return;
    setActiveEpisodeId(ep.id);
    setIsPlaying(true);
    setProgress(0);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Player Section */}
      <Card className="bg-zinc-900 border-border/50 overflow-hidden relative">
        <div className="absolute top-0 right-0 p-4">
          <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30 font-mono text-[10px]">
            AI GENERATED PODCAST
          </Badge>
        </div>

        <CardContent className="p-8">
          {isLoading ? (
            <div className="flex flex-col md:flex-row items-center gap-8">
              <Skeleton className="w-48 h-48 rounded-2xl shrink-0" />
              <div className="flex-1 space-y-4 w-full">
                <Skeleton className="h-8 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-2 w-full" />
                <Skeleton className="h-16 w-40 mx-auto rounded-full" />
              </div>
            </div>
          ) : (
            <div className="flex flex-col md:flex-row items-center gap-8">
              {/* Album art */}
              <div className="w-48 h-48 bg-gradient-to-br from-cyan-600 to-purple-600 rounded-2xl flex items-center justify-center  /20 shrink-0">
                <Mic2 className="w-20 h-20 text-white opacity-80" />
              </div>

              <div className="flex-1 text-center md:text-left space-y-4">
                <div>
                  <h1 className="text-2xl md:text-3xl font-black uppercase tracking-tighter italic leading-tight">
                    {currentEp?.title ?? "VIT Network Broadcasts"}
                  </h1>
                  <p className="text-cyan-400 font-mono text-sm mt-1">
                    Hosted by {currentEp?.host ?? "Veteran Analyst"}
                  </p>
                </div>

                <div className="space-y-2">
                  <Progress value={progress} className="h-1 bg-zinc-800 [&>div]:bg-cyan-500" />
                  <div className="flex justify-between text-[10px] font-mono text-zinc-500">
                    <span>
                      {Math.floor((progress / 100) * (parseInt(currentEp?.length?.split(":")[0] ?? "5") * 60 + parseInt(currentEp?.length?.split(":")[1] ?? "0")) / 60)
                        .toString().padStart(2, "0")}:{
                        Math.floor((progress / 100) * (parseInt(currentEp?.length?.split(":")[0] ?? "5") * 60 + parseInt(currentEp?.length?.split(":")[1] ?? "0")) % 60)
                          .toString().padStart(2, "0")}
                    </span>
                    <span>{currentEp?.length ?? "05:00"}</span>
                  </div>
                </div>

                <div className="flex items-center justify-center md:justify-start gap-6">
                  <Button variant="ghost" size="icon" className="text-zinc-400 hover:text-white">
                    <Heart className="w-5 h-5" />
                  </Button>
                  <Button
                    size="icon"
                    className="w-16 h-16 rounded-full bg-white text-black hover:bg-zinc-200 "
                    onClick={() => setIsPlaying(!isPlaying)}
                  >
                    {isPlaying ? <Pause className="w-8 h-8" /> : <Play className="w-8 h-8 ml-1" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-zinc-400 hover:text-white"
                    onClick={() => {
                      const eps = data?.episodes ?? [];
                      const idx = eps.findIndex((e) => e.id === (currentEp?.id ?? ""));
                      const next = eps[idx + 1];
                      if (next && !next.premium) handlePlayEpisode(next);
                    }}
                  >
                    <SkipForward className="w-5 h-5" />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Playlist */}
      <div className="space-y-4">
        <h3 className="text-sm font-mono text-zinc-500 uppercase tracking-widest px-1">Recent Episodes</h3>

        {isLoading ? (
          <div className="grid gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="grid gap-2">
            {(data?.episodes ?? []).map((ep) => {
              const isActive = ep.id === (activeEpisodeId ?? data?.current_episode?.id);
              return (
                <Card
                  key={ep.id}
                  className={`border-border/30 transition-colors cursor-pointer group ${
                    isActive
                      ? "bg-cyan-500/5 border-cyan-500/30"
                      : "bg-card/40 hover:bg-card/60"
                  } ${ep.premium ? "opacity-75" : ""}`}
                  onClick={() => handlePlayEpisode(ep)}
                >
                  <CardContent className="p-4 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                        isActive ? "bg-cyan-500/20" : "bg-zinc-800 group-hover:bg-zinc-700"
                      }`}>
                        {isActive && isPlaying
                          ? <Pause className="w-4 h-4 text-cyan-400" />
                          : ep.premium
                          ? <Lock className="w-4 h-4 text-zinc-500" />
                          : <Play className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-zinc-500"}`} />}
                      </div>
                      <div className="min-w-0">
                        <h4 className={`font-bold text-sm truncate ${isActive ? "text-cyan-400" : ""}`}>{ep.title}</h4>
                        <p className="text-xs text-zinc-500">{ep.host} · {ep.date}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs font-mono text-zinc-600">{ep.length}</span>
                      {ep.premium && (
                        <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-500 bg-amber-500/5">
                          ELITE
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
