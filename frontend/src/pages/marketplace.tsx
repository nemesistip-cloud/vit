import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  ShoppingBag, Zap, Brain, BarChart3, Search,
  Filter, ChevronRight, Globe, Layers, Cpu, Database, Shield, Star
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/cards/MetricCard";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import { EmptyState } from "@/components/empty-state";
import { cn } from "@/lib/utils";

export default function MarketplacePage() {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");

  const { data: listings, isLoading } = useQuery<any[]>({
    queryKey: ["/api/marketplace/listings"],
    queryFn: async () => {
      const res = await apiGet<any>("/api/marketplace/listings");
      return Array.isArray(res) ? res : (res?.items || []);
    },
  });

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const categories = [
    { id: "all", label: "All Models" },
    { id: "prediction", label: "Predictions", count: listings?.filter((l: any) => l.category === 'prediction').length },
    { id: "analytics", label: "Analytics", count: listings?.filter((l: any) => l.category === 'analytics').length },
    { id: "strategy", label: "Strategy", count: listings?.filter((l: any) => l.category === 'strategy').length },
  ];

  const filteredListings = useMemo(() => {
    if (!listings) return [];
    return listings.filter((l: any) => {
      const nameMatch = (l.name || "").toLowerCase().includes(search.toLowerCase());
      const categoryMatch = activeCategory === "all" || l.category === activeCategory;
      return nameMatch && categoryMatch;
    });
  }, [listings, search, activeCategory]);

  const volume = summary?.total_merit ? (summary.total_merit / 1000).toFixed(1) + "K VIT" : "—";
  const stakers = summary?.total_users ? Math.floor(summary.total_users * 0.4) : "—";
  const avgAcc = summary?.avg_clv ? (summary.avg_clv * 100 + 50).toFixed(1) + "%" : "—";

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            label="Listed Models"
            value={listings?.length ?? "—"}
            icon={<Brain size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Total Volume"
            value={volume}
            change="+5.2%"
            changePositive={true}
            icon={<Zap size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Active Stakers"
            value={stakers}
            icon={<Shield size={16} className="text-vit-purple" />}
         />
         <MetricCard
            label="Avg. Accuracy"
            value={avgAcc}
            icon={<BarChart3 size={16} className="text-vit-green" />}
         />
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

      <div className="bg-vit-surface border-y border-vit-border">
         <div className="px-4 py-3 border-b border-vit-border bg-vit-surface-2 flex justify-between items-center">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3">Market Listings</h3>
            {!isLoading && (
              <span className="text-[10px] font-mono text-vit-text-3">{filteredListings.length} Models Found</span>
            )}
         </div>

         {isLoading ? (
           Array.from({ length: 5 }).map((_, i) => <RowSkeleton key={i} />)
         ) : filteredListings.length === 0 ? (
           <div className="p-20">
              <EmptyState
                 icon={ShoppingBag}
                 title="No models listed"
                 description="Try adjusting your filters or be the first to list a model."
              />
           </div>
         ) : (
           <div className="divide-y divide-vit-border">
              {filteredListings.map((listing: any) => (
                <div key={listing.id} className="p-4 flex items-center justify-between hover:bg-vit-surface-2 transition-colors group cursor-pointer">
                   <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-xl bg-vit-surface-3 border border-vit-border flex items-center justify-center text-vit-green group-hover:border-vit-green/30 transition-all">
                         <Brain size={24} />
                      </div>
                      <div>
                         <h4 className="text-sm font-bold text-vit-text-1">{listing.name}</h4>
                         <div className="flex items-center gap-2 mt-1">
                            <Badge className="text-[8px] bg-vit-surface-3 text-vit-text-3 border-vit-border uppercase tracking-tighter">{listing.category}</Badge>
                            <div className="flex items-center gap-1 text-secondary">
                               <Star size={10} fill="currentColor" />
                               <span className="text-[10px] font-bold">{listing.avg_rating?.toFixed(1) || '5.0'}</span>
                            </div>
                            <span className="text-[10px] text-vit-text-3 uppercase tracking-widest">{listing.usage_count || 0} CALLS</span>
                         </div>
                      </div>
                   </div>
                   <div className="text-right">
                      <p className="text-sm font-mono font-bold text-vit-text-1">{listing.price_per_call || listing.price} VIT</p>
                      <p className="text-[10px] text-vit-text-3">per call</p>
                   </div>
                </div>
              ))}
           </div>
         )}
      </div>
    </div>
  );
}
