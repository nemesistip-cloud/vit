import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Users, UserPlus, TrendingUp, Trophy, Lock, MessageSquare } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export default function BetRoomsPage() {
  const rooms = [
    {
      id: 1,
      name: "The Whale's Den",
      creator: "Alpha_Pred",
      participants: 450,
      roi_30d: 12.4,
      entry: "0.5 VIT",
      type: "Public",
      is_locked: false
    },
    {
      id: 2,
      name: "Draw Specialists Only",
      creator: "Stalemate_King",
      participants: 89,
      roi_30d: 28.1,
      entry: "Premium Only",
      type: "Elite",
      is_locked: true
    },
    {
      id: 3,
      name: "EPL Momentum Chasers",
      creator: "VITSports_Official",
      participants: 1240,
      roi_30d: 8.5,
      entry: "Free",
      type: "Verified",
      is_locked: false
    }
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black uppercase tracking-tighter italic flex items-center gap-3">
            <Users className="w-8 h-8 text-cyan-400" />
            Bet With Rooms
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Join expert-led prediction rooms. Copy, fade, and compete with the community.
          </p>
        </div>
        <Button className="bg-white text-black hover:bg-zinc-200 font-bold rounded-xl h-12">
          Create My Room (Earn 20%)
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {rooms.map((room) => (
          <Card key={room.id} className="bg-zinc-900 border-border/50 hover:border-cyan-500/30 transition-all overflow-hidden relative group">
            {room.is_locked && (
              <div className="absolute top-3 right-3 z-10">
                <Lock className="w-4 h-4 text-amber-500" />
              </div>
            )}
            <CardHeader className="pb-2">
              <div className="flex items-center gap-3 mb-4">
                <Avatar className="w-10 h-10 border border-border">
                  <AvatarFallback className="bg-zinc-800 text-[10px]">{room.creator.slice(0,2).toUpperCase()}</AvatarFallback>
                </Avatar>
                <div>
                  <CardTitle className="text-sm font-bold truncate max-w-[180px]">{room.name}</CardTitle>
                  <CardDescription className="text-[10px] font-mono text-zinc-500">by @{room.creator}</CardDescription>
                </div>
              </div>
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-zinc-500 uppercase tracking-tighter">Participants</span>
                <span className="text-white">{room.participants}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-6 pt-4">
              <div className="bg-zinc-950 rounded-xl p-4 border border-border/30 flex justify-between items-center">
                <div>
                  <p className="text-[10px] text-zinc-500 uppercase mb-1">30d ROI</p>
                  <p className="text-xl font-black italic text-emerald-400">+{room.roi_30d}%</p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-zinc-500 uppercase mb-1">Entry</p>
                  <p className="text-sm font-bold text-zinc-300">{room.entry}</p>
                </div>
              </div>

              <Button variant={room.is_locked ? "outline" : "default"} className={`w-full font-bold h-11 rounded-xl ${room.is_locked ? "border-zinc-800 text-zinc-400" : "bg-cyan-600 hover:bg-cyan-500"}`}>
                {room.is_locked ? "Upgrade to Join" : "Join Room"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
