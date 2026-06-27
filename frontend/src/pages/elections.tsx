import { useState } from "react";
import {
  Globe, TrendingUp, Users, Activity,
  ChevronRight, Search, Zap, Shield, Radar, BarChart2
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function GeopoliticalPage() {
  const regions = [
    { name: "US Presidential 2024", type: "Executive", sentiment: "Volatile", accuracy: "84.2%" },
    { name: "EU Legislative Reform", type: "Legislative", sentiment: "Stable", accuracy: "79.5%" },
    { name: "UK General Election", type: "Executive", sentiment: "Shifting", accuracy: "81.8%" },
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Geopolitical Forecasting</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Neural Sentiment & Outcome Analysis</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Active Nodes" value="24" icon={<Globe size={14} />} />
        <MetricCard label="Sentiment Index" value="Neutral" icon={<Activity size={14} />} />
        <MetricCard label="Model Drift" value="0.02%" icon={<Zap size={14} />} />
        <MetricCard label="Confidence" value="82.4%" icon={<Shield size={14} />} />
      </div>

      <Card className="border-primary/20 bg-primary/[0.02] overflow-hidden">
         <CardContent className="p-8 flex flex-col md:flex-row items-center gap-8">
            <div className="relative">
               <Radar size={120} className="text-primary opacity-20 animate-spin-slow" />
               <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-primary shadow-[0_0_12px_rgba(0,245,255,0.8)]" />
               </div>
            </div>
            <div className="space-y-3 flex-1">
               <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 uppercase tracking-widest text-[8px]">Scanning Global Pulse</Badge>
               <h2 className="text-xl font-bold tracking-tight">Active Sentiment Scanning</h2>
               <p className="text-xs text-muted-foreground leading-relaxed">
                  VIT ensemble models are currently processing <span className="text-foreground">1.4M data points</span> from global news, social feeds, and market liquidity to forecast high-impact geopolitical events.
               </p>
            </div>
         </CardContent>
      </Card>

      <div className="space-y-4">
         <h3 className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground pl-1">Forecasting Nodes</h3>
         <div className="border-t border-white/5 bg-background">
            <div className="divide-y divide-white/5">
               {regions.map((node) => (
                  <div key={node.name} className="p-6 flex flex-col md:flex-row justify-between items-center gap-6 hover:bg-white/[0.01] transition-all group cursor-pointer">
                     <div className="flex items-center gap-6 flex-1 w-full">
                        <div className="w-12 h-12 rounded border border-white/5 bg-white/5 flex items-center justify-center text-primary group-hover:border-primary/20 transition-all">
                           <BarChart2 size={20} />
                        </div>
                        <div className="space-y-1">
                           <div className="flex items-center gap-3">
                              <Badge variant="outline" className="text-[8px] border-white/10 uppercase tracking-tighter">{node.type}</Badge>
                              <span className="text-[9px] font-mono text-vit-positive uppercase tracking-widest">{node.sentiment} SENTIMENT</span>
                           </div>
                           <h3 className="text-base font-bold text-foreground tracking-tight group-hover:text-primary transition-colors">{node.name}</h3>
                        </div>
                     </div>
                     <div className="flex items-center gap-8 w-full md:w-auto justify-between md:justify-end">
                        <div className="text-right">
                           <p className="font-mono text-xs font-bold text-foreground">{node.accuracy}</p>
                           <p className="font-mono text-[8px] text-muted-foreground uppercase mt-1">Alpha Prob</p>
                        </div>
                        <ChevronRight size={16} className="text-muted-foreground/20 group-hover:text-primary transition-all" />
                     </div>
                  </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
}
