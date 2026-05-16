import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Radio, Play, Pause, SkipForward, Volume2, Mic2, User, Heart } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function OraclesMicPage() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(35);

  const episodes = [
    { title: "EPL Weekend Preview", host: "Veteran Analyst", date: "Today", length: "05:00", premium: false },
    { title: "The Equilibrium Deep-Dive", host: "Data Nerd", date: "Yesterday", length: "08:12", premium: true },
    { title: "Upset Alert: La Liga Edition", host: "Hype Man", date: "2 days ago", length: "04:30", premium: false },
  ];

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
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="w-48 h-48 bg-gradient-to-br from-cyan-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-cyan-500/20 shrink-0">
              <Mic2 className="w-20 h-20 text-white opacity-80" />
            </div>
            <div className="flex-1 text-center md:text-left space-y-4">
              <div>
                <h1 className="text-3xl font-black uppercase tracking-tighter italic">EPL Weekend Preview</h1>
                <p className="text-cyan-400 font-mono text-sm mt-1">Hosted by Veteran Analyst</p>
              </div>

              <div className="space-y-2">
                <Progress value={progress} className="h-1 bg-zinc-800" />
                <div className="flex justify-between text-[10px] font-mono text-zinc-500">
                  <span>01:45</span>
                  <span>05:00</span>
                </div>
              </div>

              <div className="flex items-center justify-center md:justify-start gap-6">
                <Button variant="ghost" size="icon" className="text-zinc-400 hover:text-white">
                  <Heart className="w-5 h-5" />
                </Button>
                <Button
                  size="icon"
                  className="w-16 h-16 rounded-full bg-white text-black hover:bg-zinc-200"
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? <Pause className="w-8 h-8" /> : <Play className="w-8 h-8 ml-1" />}
                </Button>
                <Button variant="ghost" size="icon" className="text-zinc-400 hover:text-white">
                  <SkipForward className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Playlist */}
      <div className="space-y-4">
        <h3 className="text-sm font-mono text-zinc-500 uppercase tracking-widest px-1">Recent Episodes</h3>
        <div className="grid gap-2">
          {episodes.map((ep, i) => (
            <Card key={i} className="bg-card/40 border-border/30 hover:bg-card/60 transition-colors cursor-pointer group">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-zinc-800 rounded-lg flex items-center justify-center text-zinc-500 group-hover:bg-zinc-700 transition-colors">
                    <Play className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">{ep.title}</h4>
                    <p className="text-xs text-zinc-500">{ep.host} · {ep.date}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-zinc-600">{ep.length}</span>
                  {ep.premium && (
                    <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-500 bg-amber-500/5">
                      ELITE
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
