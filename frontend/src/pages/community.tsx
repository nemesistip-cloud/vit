import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  Users, Star, MessageSquare, Shield,
  ChevronRight, Globe, Zap, Search, Plus
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function CommunityPage() {
  const circles = [
    { name: "Alpha Analysts", members: 124, type: "Exclusive", activity: "High" },
    { name: "Node Operators", members: 42, type: "Technical", activity: "Stable" },
    { name: "Governance Council", members: 12, type: "Authority", activity: "High" },
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="flex items-end justify-between">
         <div className="space-y-1">
            <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Analyst Network</h1>
            <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Contributor Collective Ledger</p>
         </div>
         <Button size="sm" className="h-9 px-4 rounded shadow-lg shadow-primary/20 uppercase tracking-widest text-[10px] font-bold">
            <Plus size={14} className="mr-2" /> Sync Node
         </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Active Analysts" value="1.2k" icon={<Users size={14} />} />
        <MetricCard label="Collective XP" value="8.4M" icon={<Star size={14} />} />
        <MetricCard label="Active Hubs" value="14" icon={<Globe size={14} />} />
        <MetricCard label="Msg/sec" value="42.5" icon={<Zap size={14} />} />
      </div>

      <div className="space-y-4">
         <h3 className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground pl-1">Network Hubs</h3>
         <div className="border-t border-white/5 bg-background">
            <div className="divide-y divide-white/5">
               {circles.map((hub) => (
                  <div key={hub.name} className="p-6 flex flex-col md:flex-row justify-between items-center gap-6 hover:bg-white/[0.01] transition-all group cursor-pointer">
                     <div className="flex items-center gap-6 flex-1 w-full">
                        <div className="w-12 h-12 rounded border border-white/5 bg-white/5 flex items-center justify-center text-primary group-hover:border-primary/20 transition-all">
                           <Users size={20} />
                        </div>
                        <div className="space-y-1">
                           <div className="flex items-center gap-3">
                              <Badge variant="outline" className="text-[8px] border-white/10 uppercase tracking-tighter">{hub.type}</Badge>
                              <span className="text-[9px] font-mono text-vit-positive uppercase tracking-widest">{hub.activity} ACTIVITY</span>
                           </div>
                           <h3 className="text-base font-bold text-foreground tracking-tight group-hover:text-primary transition-colors">{hub.name}</h3>
                        </div>
                     </div>
                     <div className="flex items-center gap-8 w-full md:w-auto justify-between md:justify-end">
                        <div className="text-right">
                           <p className="font-mono text-xs font-bold text-foreground">{hub.members}</p>
                           <p className="font-mono text-[8px] text-muted-foreground uppercase mt-1">Contributors</p>
                        </div>
                        <Button variant="outline" size="icon" className="w-9 h-9 border-white/5 group-hover:border-primary group-hover:text-primary transition-all">
                           <ChevronRight size={16} />
                        </Button>
                     </div>
                  </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
}
