import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import {
  TrendingUp, Activity, BarChart2, Zap, ArrowRight,
  ArrowUpRight, ArrowDownRight, RefreshCw, Layers,
  Wallet, Landmark, ShieldCheck, Search
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function ExchangePage() {
  const { user } = useAuth();
  const [activeSide, setActiveTab] = useState("buy");

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Liquidity Exchange</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Institutional Trading Terminal</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Trading Interface ── */}
        <div className="lg:col-span-2 space-y-6">
           <Card className="border-primary/20 bg-primary/[0.02]">
              <CardHeader className="flex flex-row items-center justify-between p-6">
                 <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center font-black text-primary">VIT</div>
                    <div>
                       <CardTitle className="text-sm font-display uppercase tracking-widest leading-none">VITCoin / USDT</CardTitle>
                       <p className="text-[10px] font-mono text-muted-foreground mt-1">Institutional Native Asset</p>
                    </div>
                 </div>
                 <div className="text-right">
                    <p className="text-xl font-mono font-bold text-foreground">$0.1242</p>
                    <p className="text-[10px] font-mono text-vit-positive uppercase font-bold">+4.12% Today</p>
                 </div>
              </CardHeader>
              <CardContent className="p-6 pt-0 space-y-6">
                 <Tabs value={activeSide} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="w-full h-12 p-1 bg-white/[0.03]">
                       <TabsTrigger value="buy" className={cn("flex-1 text-[11px] font-bold uppercase tracking-widest", activeSide === 'buy' && "text-primary bg-primary/5")}>Position LONG</TabsTrigger>
                       <TabsTrigger value="sell" className={cn("flex-1 text-[11px] font-bold uppercase tracking-widest", activeSide === 'sell' && "text-vit-negative bg-vit-negative/5")}>Position SHORT</TabsTrigger>
                    </TabsList>
                 </Tabs>

                 <div className="space-y-4">
                    <div className="space-y-2">
                       <div className="flex justify-between text-[10px] font-mono uppercase text-muted-foreground px-1">
                          <span>Collateral USDT</span>
                          <span>Max: 4,250.00</span>
                       </div>
                       <div className="relative">
                          <Input className="bg-white/5 border-white/5 h-12 font-mono text-lg" placeholder="0.00" />
                          <span className="absolute right-4 top-1/2 -translate-y-1/2 font-mono text-xs text-muted-foreground">USDT</span>
                       </div>
                    </div>

                    <div className="flex justify-center">
                       <div className="w-8 h-8 rounded border border-white/5 bg-white/5 flex items-center justify-center text-muted-foreground/40">
                          <ArrowRight size={14} className="rotate-90" />
                       </div>
                    </div>

                    <div className="space-y-2">
                       <div className="flex justify-between text-[10px] font-mono uppercase text-muted-foreground px-1">
                          <span>Output VIT</span>
                          <span>Est. Yield: 0.12%</span>
                       </div>
                       <div className="relative">
                          <Input className="bg-white/5 border-white/5 h-12 font-mono text-lg" placeholder="0.00" disabled />
                          <span className="absolute right-4 top-1/2 -translate-y-1/2 font-mono text-xs text-muted-foreground">VIT</span>
                       </div>
                    </div>
                 </div>

                 <Button className="w-full h-14 uppercase tracking-[0.2em] font-display text-base shadow-xl shadow-primary/10">
                    Execute Trade Strategy
                 </Button>
              </CardContent>
           </Card>

           <Card className="border-white/5 bg-transparent overflow-hidden">
              <CardHeader className="bg-white/[0.01] border-b border-white/5">
                 <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">Active Positions</CardTitle>
              </CardHeader>
              <div className="p-12 text-center space-y-3">
                 <Layers size={24} className="mx-auto text-muted-foreground/20" />
                 <p className="font-display text-[11px] font-bold uppercase tracking-widest text-muted-foreground/40">No active positions detected</p>
              </div>
           </Card>
        </div>

        {/* ── Order Book ── */}
        <div className="space-y-6">
           <Card className="border-white/5 bg-white/[0.01] h-full">
              <CardHeader className="border-b border-white/5">
                 <CardTitle className="text-[10px] uppercase tracking-widest">Network Order Book</CardTitle>
              </CardHeader>
              <div className="p-0 font-mono text-[10px]">
                 <div className="grid grid-cols-3 p-4 text-muted-foreground/40 border-b border-white/5">
                    <span>Price</span>
                    <span className="text-center">Amount</span>
                    <span className="text-right">Total</span>
                 </div>
                 <div className="divide-y divide-white/[0.02]">
                    {[0.1245, 0.1244, 0.1243].map((p, i) => (
                       <div key={i} className="grid grid-cols-3 p-4 hover:bg-vit-negative/5">
                          <span className="text-vit-negative font-bold">{p}</span>
                          <span className="text-center text-foreground/60">4.2k</span>
                          <span className="text-right text-foreground/60">522.4</span>
                       </div>
                    ))}
                    <div className="p-4 text-center bg-white/[0.02] border-y border-white/5">
                       <span className="text-base font-bold text-foreground">0.1242 USDT</span>
                    </div>
                    {[0.1241, 0.1240, 0.1239].map((p, i) => (
                       <div key={i} className="grid grid-cols-3 p-4 hover:bg-primary/5">
                          <span className="text-primary font-bold">{p}</span>
                          <span className="text-center text-foreground/60">2.8k</span>
                          <span className="text-right text-foreground/60">347.5</span>
                       </div>
                    ))}
                 </div>
              </div>
           </Card>
        </div>
      </div>
    </div>
  );
}
