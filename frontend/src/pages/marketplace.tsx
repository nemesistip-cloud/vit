import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  ShoppingBag, Search, Filter, Star, Zap, BarChart3,
  ChevronRight, Brain, Shield, Info
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import CategoryPills from "@/components/layout/CategoryPills";
import MetricCard from "@/components/cards/MetricCard";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";
import { EmptyState } from "@/components/empty-state";

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

      <div className="flex items-center justify-between gap-4 px-1">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-vit-text-3" />
          <Input
            placeholder="Search prediction models..."
            className="pl-10 bg-vit-surface-2 border-vit-border rounded-full h-10 text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button variant="outline" className="border-vit-border rounded-full h-10 px-6 font-bold text-xs">
           LIST MODEL
        </Button>
      </div>

      <CategoryPills
        items={categories}
        activeId={activeCategory}
        onSelect={setActiveCategory}
      />

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
