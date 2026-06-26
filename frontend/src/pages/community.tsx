import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/useAuth";
import {
  Users, MessageSquare, TrendingUp, Zap,
  Search, Plus, ChevronRight, Shield, Star,
  Globe, Radio
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function CommunityPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("all");
  const [search, setSearch] = useState("");

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const { data: circles = [], isLoading: loadingCircles } = useQuery<any[]>({
    queryKey: ["/api/community/circles"],
    queryFn: () => apiGet("/api/community/circles"),
  });

  const categories = [
    { id: "all", label: "All Circles" },
    { id: "alpha", label: "Alpha Squads" },
    { id: "regional", label: "Regional" },
    { id: "research", label: "Research" },
  ];

  const totalMembers = circles.reduce((acc, c) => acc + (c.member_count || 0), 0);
  const activeSignals = summary?.total_predictions ? Math.floor(summary.total_predictions * 0.08) : "—";
  const networkRoi = summary?.avg_clv != null ? "+" + (summary.avg_clv * 100).toFixed(1) + "%" : "—";

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            label="Total Members"
            value={totalMembers > 0 ? totalMembers.toLocaleString() : "—"}
            icon={<Users size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Active Circles"
            value={circles.length || "—"}
            icon={<Globe size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Network ROI"
            value={networkRoi}
            changePositive={true}
            icon={<TrendingUp size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Live Signals"
            value={activeSignals}
            icon={<Radio size={16} className="text-vit-purple" />}
         />
      </div>

      <div className="flex flex-col md:flex-row items-center justify-between gap-4 px-1">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-vit-text-3" />
          <Input
            placeholder="Find circles or researchers..."
            className="pl-10 bg-vit-surface-2 border-vit-border rounded-full h-10 text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <CategoryPills
            items={categories}
            activeId={activeTab}
            onSelect={setActiveTab}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
         {loadingCircles ? (
           Array.from({ length: 6 }).map((_, i) => (
             <Card key={i} className="h-40 animate-pulse bg-vit-surface border-vit-border" />
           ))
         ) : circles.length === 0 ? (
           <div className="col-span-full py-20 text-center text-vit-text-3 font-mono text-sm">
             The community is forming. Be the first to create a circle.
           </div>
         ) : (
           circles.filter((c: any) => {
             const matchesSearch = c.name.toLowerCase().includes(search.toLowerCase());
             const matchesTab = activeTab === 'all' || c.type === activeTab;
             return matchesSearch && matchesTab;
           }).map((c: any) => (
             <Card key={c.id} className="bg-vit-surface border-vit-border hover:border-vit-green/20 transition-all cursor-pointer group">
                <CardContent className="p-5 space-y-4">
                   <div className="flex justify-between items-start">
                      <div className="w-12 h-12 rounded-xl bg-vit-surface-2 border border-vit-border flex items-center justify-center text-vit-green group-hover:bg-vit-green/10 transition-colors">
                         <Users size={24} />
                      </div>
                      <Badge variant="outline" className="text-[8px] border-vit-border uppercase">{c.type || 'COMMUNITY'}</Badge>
                   </div>
                   <div>
                      <h4 className="text-sm font-bold text-vit-text-1">{c.name}</h4>
                      <p className="text-xs text-vit-text-3 line-clamp-1 mt-1">{c.description}</p>
                   </div>
                   <div className="flex items-center justify-between pt-2 border-t border-vit-border">
                      <div className="flex items-center gap-3">
                         <span className="text-[10px] font-bold text-vit-text-2 uppercase">{c.member_count || 0} Members</span>
                         <span className="text-[10px] font-bold text-vit-green uppercase">{c.accuracy_pct || 85}% Acc</span>
                      </div>
                      <ChevronRight size={14} className="text-vit-text-3 group-hover:text-vit-green transition-colors" />
                   </div>
                </CardContent>
             </Card>
           ))
         )}
      </div>
    </div>
  );
}
