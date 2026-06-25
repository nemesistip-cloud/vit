import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  Scale, Vote, ShieldCheck, Zap,
  ChevronRight, Brain, Clock, Users, Plus, CheckCircle2
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

export default function GovernancePage() {
  const [activeTab, setActiveTab] = useState("all");

  const categories = [
    { id: "all", label: "All Proposals" },
    { id: "active", label: "Active", count: 3 },
    { id: "passed", label: "Passed" },
    { id: "rejected", label: "Rejected" },
  ];

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            label="Total Power"
            value="1.2M"
            subtitle="Voting Units"
            icon={<Scale size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Participation"
            value="74.2%"
            icon={<Users size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Active Votes"
            value="3"
            icon={<Vote size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Protocol Status"
            value="Stable"
            icon={<ShieldCheck size={16} className="text-vit-purple" />}
         />
      </div>

      <div className="flex items-center justify-between gap-4 px-1">
        <CategoryPills
          items={categories}
          activeId={activeTab}
          onSelect={setActiveTab}
        />
        <Button size="sm" className="bg-vit-green text-vit-text-inverse font-bold rounded-full gap-2">
           <Plus size={14} /> NEW PROPOSAL
        </Button>
      </div>

      <div className="space-y-4">
         {[
           { title: "VIT-042: Implement Multi-Chain Remittance", category: "Technical", status: "Active", votes: 82, for: 92, ends: "2d left" },
           { title: "VIT-043: Adjust Oracle XP Multipliers", category: "Economic", status: "Active", votes: 45, for: 76, ends: "4d left" },
           { title: "VIT-041: Add Basketball Prop Markets", category: "Market", status: "Passed", votes: 120, for: 98, ends: "Executed" },
         ].map((p, i) => (
           <Card key={i} className="bg-vit-surface border-vit-border hover:border-vit-green/20 transition-all cursor-pointer overflow-hidden">
              <div className="p-5 flex flex-col md:flex-row gap-6">
                 <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-2">
                       <Badge className="text-[8px] bg-vit-surface-3 text-vit-text-3 border-vit-border">{p.category}</Badge>
                       <span className={`text-[8px] font-bold px-2 py-0.5 rounded-full ${
                         p.status === 'Active' ? 'bg-vit-green-glow text-vit-green' : 'bg-vit-surface-2 text-vit-text-3'
                       }`}>{p.status.toUpperCase()}</span>
                       <span className="text-[10px] text-vit-text-3 font-mono">#{1000+i}</span>
                    </div>
                    <h3 className="text-sm font-bold text-vit-text-1">{p.title}</h3>
                    <div className="flex items-center gap-4 text-[10px] text-vit-text-3 uppercase tracking-widest">
                       <span className="flex items-center gap-1"><Users size={10} /> {p.votes} Votes</span>
                       <span className="flex items-center gap-1"><Clock size={10} /> {p.ends}</span>
                    </div>
                 </div>
                 <div className="w-full md:w-48 space-y-2">
                    <div className="flex justify-between text-[10px] font-bold">
                       <span className="text-vit-green">FOR {p.for}%</span>
                       <span className="text-vit-negative">{100-p.for}% AGAINST</span>
                    </div>
                    <div className="h-1.5 bg-vit-surface-3 rounded-full overflow-hidden">
                       <div className="h-full bg-vit-green" style={{ width: `${p.for}%` }} />
                    </div>
                    <Button variant="outline" className="w-full h-8 text-[10px] font-bold border-vit-border hover:bg-vit-surface-2">
                       VIEW PROPOSAL
                    </Button>
                 </div>
              </div>
           </Card>
         ))}
      </div>
    </div>
  );
}
