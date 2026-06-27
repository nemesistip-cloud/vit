import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  ShoppingBag, Zap, Brain, BarChart3, Search,
  Filter, ChevronRight, Globe, Layers, Cpu, Database
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function MarketplacePage() {
  const [search, setSearch] = useState("");

  const listings = [
    { id: 1, name: "Neural XGB-13 Alpha Feed", category: "Models", price: "500 VIT", accuracy: "88.4%", owner: "Ensemble Core" },
    { id: 2, name: "Deep LSTM Sentient Flow", category: "Models", price: "300 VIT", accuracy: "82.1%", owner: "Alpha Labs" },
    { id: 3, name: "Premium Liquidity Insights", category: "Data", price: "150 VIT", accuracy: "N/A", owner: "Treasury Hub" },
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Asset Marketplace</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Alpha Feeds & Neural Weights</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <MetricCard label="Active Listings" value="42" icon={<ShoppingBag size={14} />} />
        <MetricCard label="Avg Yield" value="12.4%" icon={<Zap size={14} />} />
        <MetricCard label="Nodes Active" value="14" icon={<Globe size={14} />} />
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
        <Input
          placeholder="Search alpha, models, or data sets..."
          className="pl-9 bg-white/[0.02] border-white/5 h-10 text-xs font-mono"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="border-t border-white/5 bg-background overflow-hidden">
         <div className="divide-y divide-white/5">
            {listings.map((item) => (
              <div key={item.id} className="p-6 flex flex-col md:flex-row justify-between items-center gap-6 hover:bg-white/[0.01] transition-all group cursor-pointer">
                 <div className="flex items-center gap-6 flex-1 w-full">
                    <div className="w-12 h-12 rounded border border-white/5 bg-white/5 flex items-center justify-center text-primary group-hover:border-primary/20 group-hover:bg-primary/5 transition-all">
                       {item.category === 'Models' ? <Cpu size={20} /> : <Database size={20} />}
                    </div>
                    <div className="space-y-1">
                       <div className="flex items-center gap-3">
                          <Badge variant="outline" className="text-[8px] border-white/10 uppercase tracking-tighter">{item.category}</Badge>
                          <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">{item.owner}</span>
                       </div>
                       <h3 className="text-base font-bold text-foreground tracking-tight group-hover:text-primary transition-colors">{item.name}</h3>
                    </div>
                 </div>

                 <div className="flex items-center gap-8 w-full md:w-auto justify-between md:justify-end">
                    <div className="text-right">
                       <p className="font-mono text-xs font-bold text-foreground">{item.price}</p>
                       <p className="font-mono text-[8px] text-muted-foreground uppercase mt-1">One-time Lease</p>
                    </div>
                    {item.accuracy !== 'N/A' && (
                       <div className="text-right">
                          <p className="font-mono text-xs font-bold text-vit-positive">{item.accuracy}</p>
                          <p className="font-mono text-[8px] text-muted-foreground uppercase mt-1">Alpha Rating</p>
                       </div>
                    )}
                    <Button variant="outline" size="icon" className="w-9 h-9 border-white/5 group-hover:border-primary group-hover:text-primary transition-all">
                       <ChevronRight size={16} />
                    </Button>
                 </div>
              </div>
            ))}
         </div>
      </div>
    </div>
  );
}
