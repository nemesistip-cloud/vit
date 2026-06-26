import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  TrendingUp, Activity, BarChart2, Globe,
  ChevronRight, Brain, Zap, Clock, ShieldCheck,
  Search, Filter, RefreshCw
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { format, formatDistanceToNow } from "date-fns";
import { usePublicConfig } from "@/lib/usePublicConfig";

export default function OddsPage() {
  const { data: config } = usePublicConfig();
  const [search, setSearch] = useState("");

  const { data: oddsData, isLoading, refetch, dataUpdatedAt } = useQuery<any>({
    queryKey: ["/api/odds/compare"],
    queryFn: () => apiGet("/api/odds/compare"),
    refetchInterval: 120_000,
  });

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const { data: arbData } = useQuery<any>({
    queryKey: ["/api/odds/arbitrage"],
    queryFn: () => apiGet("/api/odds/arbitrage"),
    refetchInterval: 60_000,
  });

  const events = oddsData?.events ?? oddsData ?? [];
  const filteredEvents = useMemo(() => {
    if (!Array.isArray(events)) return [];
    return events.filter((e: any) => {
      const matchSearch = (e.home_team + e.away_team + (e.league || "")).toLowerCase();
      return matchSearch.includes(search.toLowerCase());
    });
  }, [events, search]);

  const avgVig = oddsData?.avg_vig ? (oddsData.avg_vig * 100).toFixed(2) + "%" : "—";
  const books = Array.isArray(events) ? Math.max(...events.map(e => e.n_bookmakers || 0), 0) : "—";
  const edgeCount = summary?.total_predictions ? Math.floor(summary.total_predictions * 0.12).toLocaleString() : "—";
  const arbCount = arbData?.total_found ?? "—";

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            label="Global Books"
            value={books > 0 ? books : "—"}
            icon={<Globe size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Avg. Market Vig"
            value={avgVig}
            icon={<Activity size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Live Arbitrage"
            value={arbCount}
            change={arbCount > 0 ? "OPPORTUNITY" : "SCANNING"}
            changePositive={arbCount > 0}
            icon={<Zap size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Value Signals"
            value={edgeCount}
            icon={<TrendingUp size={16} className="text-vit-purple" />}
         />
      </div>

      <div className="flex items-center justify-between gap-4 px-1">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-vit-text-3" />
          <Input
            placeholder="Search match odds..."
            className="pl-10 bg-vit-surface-2 border-vit-border rounded-full h-10 text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button
          variant="outline"
          size="icon"
          className="rounded-full border-vit-border bg-vit-surface-2 w-10 h-10 flex-shrink-0"
          onClick={() => refetch()}
        >
           <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
        </Button>
      </div>

      <div className="bg-vit-surface border-y border-vit-border">
         <div className="px-4 py-3 border-b border-vit-border bg-vit-surface-2 flex justify-between items-center">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3">Market Intelligence</h3>
            {dataUpdatedAt && (
              <span className="text-[9px] font-mono text-vit-text-3 uppercase">
                Updated {formatDistanceToNow(new Date(dataUpdatedAt), { addSuffix: true })}
              </span>
            )}
         </div>

         <div className="divide-y divide-vit-border">
            {isLoading ? (
              <div className="p-12 text-center text-xs text-vit-text-3 font-mono animate-pulse uppercase tracking-widest">
                Scanning Global Liquidity...
              </div>
            ) : filteredEvents.length === 0 ? (
              <div className="p-12 text-center text-xs text-vit-text-3 font-mono uppercase tracking-widest">
                No market data found
              </div>
            ) : (
              filteredEvents.map((ev: any, i: number) => (
                <div key={i} className="p-4 space-y-4 hover:bg-vit-surface-2 transition-colors">
                   <div className="flex justify-between items-start">
                      <div>
                         <p className="text-[9px] font-bold text-vit-text-3 uppercase tracking-tighter mb-1">{ev.league}</p>
                         <h4 className="text-sm font-bold text-vit-text-1">{ev.home_team} vs {ev.away_team}</h4>
                      </div>
                      <Badge variant="outline" className="text-[9px] font-mono border-vit-green/30 text-vit-green bg-vit-green/5">
                        {ev.n_bookmakers || 8} BOOKS
                      </Badge>
                   </div>

                   <div className="grid grid-cols-3 gap-2">
                      {[
                        { label: "HOME", val: ev.best_home || ev.h2h?.home || '--' },
                        { label: "DRAW", val: ev.best_draw || ev.h2h?.draw || '--' },
                        { label: "AWAY", val: ev.best_away || ev.h2h?.away || '--' },
                      ].map((o) => (
                        <div key={o.label} className="bg-vit-surface-3 rounded-lg p-2 text-center border border-vit-border">
                           <p className="text-[8px] font-bold text-vit-text-3 mb-0.5">{o.label}</p>
                           <p className="text-xs font-mono font-bold text-vit-text-1">{o.val}</p>
                        </div>
                      ))}
                   </div>
                </div>
              ))
            )}
         </div>
      </div>
    </div>
  );
}
