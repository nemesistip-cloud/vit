import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import {
  Scale, Vote, ShieldCheck, Clock,
  Plus, Users, MessageSquare, ChevronRight,
  TrendingUp, BarChart3, Search
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function GovernancePage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("all");

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const { data: stats } = useQuery<any>({
    queryKey: ["/api/governance/stats"],
    queryFn: () => apiGet("/api/governance/stats"),
  });

  const { data: proposals = [], isLoading: loadingProposals } = useQuery<any[]>({
    queryKey: ["/api/governance/proposals", activeTab],
    queryFn: () => apiGet(`/api/governance/proposals?category=${activeTab}`),
  });

  const categories = [
    { id: "all", label: "All Proposals" },
    { id: "protocol", label: "Protocol" },
    { id: "treasury", label: "Treasury" },
    { id: "parameters", label: "Parameters" },
  ];

  const vitPower = user?.merit_score ? (user.merit_score / 1000).toFixed(1) + "K" : "—";
  const participation = stats?.participation_rate ? (stats.participation_rate * 100).toFixed(1) + "%" : "—";
  const activeVotes = stats?.active_proposals ?? "—";
  const protocolStatus = summary?.total_predictions ? "STABLE" : "—";

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
         <MetricCard
            variant="hero"
            label="VOTING POWER"
            value={vitPower}
            icon={<Scale size={20} className="text-vit-green" />}
         />
         <MetricCard
            label="Participation"
            value={participation}
            icon={<Users size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Active Votes"
            value={activeVotes}
            icon={<Vote size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Protocol Status"
            value={protocolStatus}
            icon={<ShieldCheck size={16} className="text-vit-purple" />}
         />
      </div>

      <div className="px-1">
        <CategoryPills
          items={categories}
          activeId={activeTab}
          onSelect={setActiveTab}
        />
      </div>

      <div className="space-y-4">
         {loadingProposals ? (
           Array.from({ length: 3 }).map((_, i) => (
             <Card key={i} className="bg-vit-surface border-vit-border h-32 animate-pulse" />
           ))
         ) : proposals.length === 0 ? (
           <div className="py-20 text-center text-vit-text-3 font-mono text-sm">
             No {activeTab !== 'all' ? activeTab : ''} proposals found in governance registry.
           </div>
         ) : (
           proposals.map((p: any) => (
             <Card key={p.id} className="bg-vit-surface border-vit-border hover:border-vit-green/20 transition-all cursor-pointer overflow-hidden">
                <div className="p-5 flex flex-col md:flex-row gap-6">
                   <div className="flex-1 space-y-3">
                      <div className="flex items-center gap-2">
                         <Badge className="text-[8px] bg-vit-surface-3 text-vit-text-3 border-vit-border uppercase">{p.category}</Badge>
                         <span className={`text-[8px] font-bold px-2 py-0.5 rounded-full ${
                           p.status === 'active' ? 'bg-vit-green-glow text-vit-green' : 'bg-vit-surface-2 text-vit-text-3'
                         }`}>{p.status.toUpperCase()}</span>
                         <span className="text-[10px] text-vit-text-3 font-mono">#{p.id}</span>
                      </div>
                      <h3 className="text-sm font-bold text-vit-text-1">{p.title}</h3>
                      <div className="flex items-center gap-4 text-[10px] text-vit-text-3 uppercase tracking-widest">
                         <span className="flex items-center gap-1"><Users size={10} /> {p.total_votes || 0} Votes</span>
                         <span className="flex items-center gap-1"><Clock size={10} /> {p.status === 'active' ? 'Ends soon' : 'Finalized'}</span>
                      </div>
                   </div>
                   <div className="w-full md:w-48 space-y-2">
                      <div className="flex justify-between text-[10px] font-bold">
                         <span className="text-vit-green">FOR {p.approval_pct || 0}%</span>
                         <span className="text-vit-negative">{100 - (p.approval_pct || 0)}% AGAINST</span>
                      </div>
                      <div className="h-1.5 bg-vit-surface-3 rounded-full overflow-hidden">
                         <div className="h-full bg-vit-green" style={{ width: `${p.approval_pct || 0}%` }} />
                      </div>
                      <Button variant="outline" className="w-full h-8 text-[10px] font-bold border-vit-border hover:bg-vit-surface-2">
                         VIEW PROPOSAL
                      </Button>
                   </div>
                </div>
             </Card>
           ))
         )}
      </div>
    </div>
  );
}
