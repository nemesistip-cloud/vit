import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  Scale, Vote, ShieldCheck, Zap,
  ChevronRight, Brain, Clock, Users, Plus, CheckCircle2,
  FileText, Landmark, Gavel, BarChart3
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function GovernancePage() {
  const [activeTab, setActiveTab] = useState("all");

  const categories = [
    { id: "all", label: "All Proposals" },
    { id: "active", label: "Active Nodes", count: 3 },
    { id: "passed", label: "Executed" },
    { id: "rejected", label: "Discarded" },
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="flex items-end justify-between">
         <div className="space-y-1">
            <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Protocol Governance</h1>
            <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Decentralized Decision Engine</p>
         </div>
         <Button size="sm" className="h-9 px-4 rounded shadow-lg shadow-primary/20 uppercase tracking-widest text-[10px] font-bold">
            <Plus size={14} className="mr-2" /> Draft Proposal
         </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Voting Units" value="1.2M" icon={<Landmark size={14} />} />
        <MetricCard label="Quorum Met" value="74.2%" icon={<Users size={14} />} />
        <MetricCard label="Active Polls" value="3" icon={<Gavel size={14} />} />
        <MetricCard label="Sovereignty" value="Stable" icon={<ShieldCheck size={14} />} />
      </div>

      <div className="px-1">
        <CategoryPills
          items={categories}
          activeId={activeTab}
          onSelect={setActiveTab}
        />
      </div>

      <div className="space-y-4">
         {[
           { id: "VIT-042", title: "Scale Multi-Chain Remittance Gateway", category: "Technical", status: "Active", votes: 82, for: 92, ends: "2d left" },
           { id: "VIT-043", title: "Calibrate Oracle XP Yield Multipliers", category: "Economic", status: "Active", votes: 45, for: 76, ends: "4d left" },
           { id: "VIT-041", title: "Provision Basketball Alpha Markets", category: "Market", status: "Passed", votes: 120, for: 98, ends: "Executed" },
         ].map((p, i) => (
           <Card key={i} className="bg-white/[0.01] border-white/5 hover:bg-white/[0.03] transition-all cursor-pointer overflow-hidden group">
              <div className="p-6 flex flex-col md:flex-row gap-8 items-center">
                 <div className="flex-1 space-y-4 w-full">
                    <div className="flex items-center gap-3">
                       <Badge variant="outline" className="text-[8px] bg-white/5 border-white/10 uppercase font-mono tracking-tighter">#{p.id}</Badge>
                       <Badge variant="outline" className={cn(
                          "text-[8px] border-none font-bold uppercase px-2 py-0.5 rounded",
                          p.status === 'Active' ? 'bg-primary/10 text-primary' : 'bg-muted/10 text-muted-foreground'
                       )}>{p.status}</Badge>
                       <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">{p.category}</span>
                    </div>
                    <h3 className="text-base font-bold text-foreground leading-tight tracking-tight group-hover:text-primary transition-colors">{p.title}</h3>
                    <div className="flex items-center gap-6">
                       <div className="flex items-center gap-2 text-muted-foreground">
                          <Users size={12} />
                          <span className="font-mono text-[10px] uppercase font-bold">{p.votes} Analysts</span>
                       </div>
                       <div className="flex items-center gap-2 text-muted-foreground">
                          <Clock size={12} />
                          <span className="font-mono text-[10px] uppercase font-bold">{p.ends}</span>
                       </div>
                    </div>
                 </div>

                 <div className="w-full md:w-64 space-y-3">
                    <div className="flex justify-between text-[10px] font-mono font-bold uppercase">
                       <span className="text-primary">Concur: {p.for}%</span>
                       <span className="text-muted-foreground">Dissent: {100-p.for}%</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                       <div className="h-full bg-primary" style={{ width: `${p.for}%` }} />
                    </div>
                    <Button variant="outline" className="w-full h-8 text-[9px] font-bold border-white/5 bg-white/[0.01] uppercase tracking-widest group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary transition-all">
                       Audit Document
                    </Button>
                 </div>
              </div>
           </Card>
         ))}
      </div>
    </div>
  );
}
