import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, MessageSquare, Shield, Star, CheckCircle2, ChevronRight, Brain } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";
import { useState } from "react";

export default function CommunityPage() {
  const [activeCategory, setActiveCategory] = useState("all");

  const categories = [
    { id: "all", label: "All Circles" },
    { id: "trending", label: "Trending" },
    { id: "new", label: "Newest" },
    { id: "verified", label: "Verified" },
  ];

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            label="Active Circles"
            value="124"
            icon={<Users size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Shared Signals"
            value="12.5K"
            icon={<Brain size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Community ROI"
            value="+15.2%"
            changePositive={true}
            icon={<Star size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Total Members"
            value="42.8K"
            icon={<Shield size={16} className="text-vit-purple" />}
         />
      </div>

      <CategoryPills
        items={categories}
        activeId={activeCategory}
        onSelect={setActiveCategory}
      />

      <div className="bg-vit-surface border-y border-vit-border">
         <div className="px-4 py-3 border-b border-vit-border bg-vit-surface-2 flex justify-between items-center">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3">Intelligence Circles</h3>
            <span className="text-[10px] font-mono text-vit-text-3">12 Circles Active</span>
         </div>

         <div className="divide-y divide-vit-border">
            {[
              { name: "Lagos Arbitrage Squad", members: "1.2k", signal: "92%", type: "ALGO" },
              { name: "Naira Policy Analysts", members: "450", signal: "88%", type: "POLICY" },
              { name: "Elite Signal Shop Agents", members: "2k+", signal: "95%", type: "PREDICT" },
              { name: "Delta Network Nodes", members: "820", signal: "90%", type: "TECH" },
            ].map((circle) => (
              <div key={circle.name} className="p-4 flex items-center justify-between hover:bg-vit-surface-2 transition-colors group cursor-pointer">
                 <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-vit-surface-3 border border-vit-border flex items-center justify-center text-vit-green">
                       <Users size={24} />
                    </div>
                    <div>
                       <h4 className="text-sm font-bold text-vit-text-1">{circle.name}</h4>
                       <div className="flex items-center gap-2 mt-1">
                          <Badge className="text-[8px] bg-vit-surface-3 text-vit-text-3 border-vit-border uppercase tracking-tighter">{circle.type}</Badge>
                          <div className="flex items-center gap-1 text-vit-text-3 text-[10px]">
                             <Users size={10} />
                             <span>{circle.members}</span>
                          </div>
                          <div className="flex items-center gap-1 text-vit-green">
                             <CheckCircle2 size={10} />
                             <span className="text-[10px] font-bold">{circle.signal} CONVIC.</span>
                          </div>
                       </div>
                    </div>
                 </div>
                 <ChevronRight size={16} className="text-vit-text-3 group-hover:text-vit-text-1 transition-colors" />
              </div>
            ))}
         </div>
      </div>
    </div>
  );
}
