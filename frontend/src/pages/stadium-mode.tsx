import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Map, Zap, Radio, Target, Activity } from "lucide-react";

export default function StadiumModePage() {
  const [isLive, setIsLive] = useState(true);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground flex items-center gap-2">
            <Map className="w-6 h-6 text-orange-400" />
            Live Attendance Mode
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Optimized for live event attendance (low battery, high contrast)
          </p>
        </div>
        <Badge variant="outline" className="bg-orange-400/10 text-orange-400 border-orange-400/20 px-3 py-1 animate-pulse">
          LIVE AT STADIUM
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="bg-zinc-950 border-orange-500/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="w-5 h-5 text-orange-400" />
              Equilibrium Meter
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center py-8">
            <div className="relative w-48 h-48 flex items-center justify-center">
              <div className="absolute inset-0 border-[12px] border-zinc-800 rounded-full" />
              <div
                className="absolute inset-0 border-[12px] border-orange-500 rounded-full"
                style={{ clipPath: 'polygon(50% 50%, 0 0, 100% 0, 100% 100%, 0 100%, 0 50%)' }}
              />
              <div className="text-4xl font-bold font-mono">68.4</div>
            </div>
            <p className="mt-4 text-sm text-zinc-400">Current DPS (Draw Propensity Score)</p>
          </CardContent>
        </Card>

        <Card className="bg-zinc-950 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Radio className="w-5 h-5 text-cyan-400" />
              In-Stadium Feed
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { time: "72'", msg: "Momentum shift detected: Home Team pushing high", type: "info" },
              { time: "68'", msg: "Tactical change: Away Team switching to 5-4-1", type: "warning" },
              { time: "65'", msg: "Substitute Alert: Striker warming up (Causal Impact: +8%)", type: "success" }
            ].map((event, i) => (
              <div key={i} className="flex gap-3 py-2 border-b border-zinc-800 last:border-0">
                <span className="font-mono text-cyan-400 text-xs mt-1">{event.time}</span>
                <span className="text-sm text-zinc-300">{event.msg}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="bg-orange-500/10 border border-orange-500/20 p-6 rounded-2xl flex flex-col items-center text-center">
        <Target className="w-10 h-10 text-orange-400 mb-4" />
        <h3 className="text-lg font-bold">Stadium Prediction Challenge</h3>
        <p className="text-sm text-zinc-400 max-w-md mt-2">
          Predict the next event in the stadium to win exclusive rewards and VIP upgrades.
        </p>
        <button className="mt-6 px-8 py-3 bg-orange-500 hover:bg-orange-400 text-white rounded-xl font-bold transition-all transform active:scale-95 shadow-lg shadow-orange-500/20">
          Predict Next Corner
        </button>
      </div>
    </div>
  );
}
