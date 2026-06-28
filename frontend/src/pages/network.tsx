import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Activity, Award, CheckCircle2, Clock, Cpu, Globe,
  Key, Network, RefreshCw, Shield, TrendingUp, User, Zap,
  Database, Coins, Flame, Info
} from "lucide-react";
import { apiGet } from "@/lib/apiClient";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────────────────────────────

interface NetworkStats {
  total_nodes: number; active_nodes: number;
  total_contributions: number; contributions_24h: number;
  oracle_submissions_24h: number; network_health_score: number;
  growth_rate_24h_pct: number;
  activity_breakdown_24h: Record<string, number>;
  snapshot_at: string;
}

interface BlockchainMetrics {
  active_validators: number;
  total_staked: number;
  circulating_supply: number;
  total_supply: number;
  burned_tokens: number;
  tps: number;
  block_time: string;
  finality: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M`
  : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K`
  : String(n);

// ─── Main Component ──────────────────────────────────────────────────────────

export default function NetworkPage() {
  const { data: stats, isLoading: statsLoading } = useQuery<NetworkStats>({
    queryKey: ["/api/network/stats"],
    queryFn: () => apiGet("/api/network/stats"),
  });

  const { data: metrics, isLoading: metricsLoading } = useQuery<BlockchainMetrics>({
    queryKey: ["/api/blockchain/metrics"],
    queryFn: () => apiGet("/api/blockchain/metrics"),
  });

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div className="space-y-1">
           <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Mission Control</h1>
           <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">VIT Network Infrastructure Telemetry</p>
        </div>
        <div className="flex gap-2">
           <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 font-mono text-[9px] h-6">
              <Activity size={10} className="mr-1.5 animate-pulse" /> LIVE TELEMETRY
           </Badge>
           <Badge variant="outline" className="border-white/10 font-mono text-[9px] h-6 text-muted-foreground">
              v5.5.0-STABLE
           </Badge>
        </div>
      </div>

      {/* ── Protocol Metrics ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Network TPS" value={metrics?.tps?.toFixed(1) || "—"} icon={<Zap size={14} />} />
        <MetricCard label="Block Time" value={metrics?.block_time || "—"} icon={<Clock size={14} />} />
        <MetricCard label="Active Nodes" value={stats?.active_nodes?.toString() || "—"} icon={<Globe size={14} />} />
        <MetricCard label="Health Score" value={`${stats?.network_health_score?.toFixed(1)}%`} icon={<Shield size={14} />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           {/* ── Tokenomics Dashboard ── */}
           <Card className="border-white/5 bg-white/[0.01] overflow-hidden">
              <CardHeader className="bg-white/[0.01] border-b border-white/5">
                 <div className="flex justify-between items-center">
                    <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">VITCoin Tokenomics</CardTitle>
                    <Badge variant="outline" className="text-[8px] border-primary/20 text-primary">ECONOMY LAYER</Badge>
                 </div>
              </CardHeader>
              <CardContent className="pt-6 space-y-8">
                 <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                    <div className="space-y-1">
                       <p className="font-mono text-[8px] text-muted-foreground uppercase">Total Supply</p>
                       <p className="text-xl font-bold font-display">{fmt(metrics?.total_supply || 0)}</p>
                    </div>
                    <div className="space-y-1">
                       <p className="font-mono text-[8px] text-muted-foreground uppercase">Circulating</p>
                       <p className="text-xl font-bold font-display text-primary">{fmt(metrics?.circulating_supply || 0)}</p>
                    </div>
                    <div className="space-y-1">
                       <p className="font-mono text-[8px] text-muted-foreground uppercase">Burned</p>
                       <div className="flex items-center gap-1.5 text-vit-negative">
                          <Flame size={14} />
                          <p className="text-xl font-bold font-display">{fmt(metrics?.burned_tokens || 0)}</p>
                       </div>
                    </div>
                    <div className="space-y-1">
                       <p className="font-mono text-[8px] text-muted-foreground uppercase">Total Staked</p>
                       <p className="text-xl font-bold font-display text-foreground">{fmt(metrics?.total_staked || 0)}</p>
                    </div>
                 </div>

                 <div className="space-y-3">
                    <div className="flex justify-between text-[9px] font-mono uppercase text-muted-foreground">
                       <span>Staking Ratio</span>
                       <span>{((metrics?.total_staked || 0) / (metrics?.circulating_supply || 1) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                       <div
                          className="h-full bg-primary shadow-[0_0_8px_rgba(0,245,255,0.5)] transition-all duration-1000"
                          style={{ width: `${((metrics?.total_staked || 0) / (metrics?.circulating_supply || 1) * 100)}%` }}
                       />
                    </div>
                 </div>

                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-white/5">
                    <div className="flex items-center gap-4 p-4 rounded bg-white/[0.02] border border-white/5">
                       <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                          <TrendingUp size={20} />
                       </div>
                       <div>
                          <p className="font-mono text-[8px] text-muted-foreground uppercase">Daily Volume</p>
                          <p className="text-sm font-bold tracking-tight">1.2M VIT</p>
                       </div>
                    </div>
                    <div className="flex items-center gap-4 p-4 rounded bg-white/[0.02] border border-white/5">
                       <div className="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center text-secondary">
                          <Coins size={20} />
                       </div>
                       <div>
                          <p className="font-mono text-[8px] text-muted-foreground uppercase">Market Cap</p>
                          <p className="text-sm font-bold tracking-tight">.5M USD</p>
                       </div>
                    </div>
                 </div>
              </CardContent>
           </Card>

           {/* ── Network Activity Feed ── */}
           <Card className="border-white/5 bg-transparent">
              <CardHeader className="bg-white/[0.01] border-b border-white/5">
                 <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">Real-time Activity Ledger</CardTitle>
              </CardHeader>
              <div className="divide-y divide-white/5">
                 {[
                    { event: "BLOCK_PRODUCED", detail: "Slot #12,405,102", time: "2s ago", type: "success" },
                    { event: "STAKE_LOCKED", detail: "Validator node 0x8a...4b", time: "12s ago", type: "primary" },
                    { event: "ORACLE_SUBMIT", detail: "Match ID #1905 verified", time: "45s ago", type: "primary" },
                    { event: "CONTENT_ANCHOR", detail: "Tachyon shard synced", time: "1m ago", type: "success" },
                    { event: "SLASH_EVENT", detail: "Downtime penalty applied", time: "5m ago", type: "warning" },
                 ].map((item, i) => (
                    <div key={i} className="p-4 flex items-center justify-between hover:bg-white/[0.01] transition-colors">
                       <div className="flex items-center gap-4">
                          <div className={cn(
                             "w-1.5 h-1.5 rounded-full",
                             item.type === "success" ? "bg-primary" : item.type === "warning" ? "bg-vit-warning" : "bg-secondary"
                          )} />
                          <div>
                             <p className="text-[10px] font-bold tracking-widest uppercase font-mono">{item.event}</p>
                             <p className="text-[10px] text-muted-foreground">{item.detail}</p>
                          </div>
                       </div>
                       <p className="font-mono text-[9px] text-muted-foreground/50 uppercase">{item.time}</p>
                    </div>
                 ))}
              </div>
           </Card>
        </div>

        <div className="space-y-6">
           <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4 text-primary">
                 <Database size={16} />
                 <h4 className="font-display text-[10px] font-bold uppercase tracking-[0.2em]">Consensus Engine</h4>
              </div>
              <div className="space-y-4">
                 <div className="space-y-2">
                    <div className="flex justify-between text-[9px] font-mono uppercase text-muted-foreground">
                       <span>Layer Status</span>
                       <span className="text-primary font-bold">STABLE</span>
                    </div>
                    <div className="flex justify-between text-[9px] font-mono uppercase text-muted-foreground">
                       <span>Finality</span>
                       <span className="text-foreground">{metrics?.finality?.toUpperCase() || "—"}</span>
                    </div>
                 </div>
                 <Separator className="bg-white/5" />
                 <div className="space-y-2">
                    <p className="text-[9px] text-muted-foreground leading-relaxed">
                       Neural Consensus Protocol (NCP) is currently managing the validation of prediction outcomes across 124 active nodes.
                    </p>
                 </div>
              </div>
           </div>

           <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4 text-secondary">
                 <Shield size={16} />
                 <h4 className="font-display text-[10px] font-bold uppercase tracking-[0.2em]">Network Security</h4>
              </div>
              <div className="space-y-4">
                 <div className="flex items-center gap-3">
                    <CheckCircle2 size={12} className="text-secondary" />
                    <span className="text-[10px] text-muted-foreground uppercase font-mono">Quantum Resistance: ENABLED</span>
                 </div>
                 <div className="flex items-center gap-3">
                    <CheckCircle2 size={12} className="text-secondary" />
                    <span className="text-[10px] text-muted-foreground uppercase font-mono">Slashing Module: ACTIVE</span>
                 </div>
                 <div className="flex items-center gap-3">
                    <Info size={12} className="text-muted-foreground" />
                    <span className="text-[10px] text-muted-foreground uppercase font-mono">Audit Coverage: 94.2%</span>
                 </div>
              </div>
              <Button variant="outline" className="w-full mt-6 h-9 text-[9px] uppercase tracking-widest border-white/10 text-secondary border-secondary/20 hover:bg-secondary/5">
                 View Security Audit
              </Button>
           </div>
        </div>
      </div>
    </div>
  );
}
