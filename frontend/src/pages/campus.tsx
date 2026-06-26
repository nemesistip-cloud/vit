import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  GraduationCap, Users, Briefcase, Star,
  ChevronRight, Brain, Zap, BookOpen, CheckCircle2
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";
import { Badge } from "@/components/ui/badge";
import { RowSkeleton } from "@/components/skeletons/RowSkeleton";

export default function CampusPage() {
  const [activeTab, setActiveTab] = useState("overview");

  const { data: summary } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

  const { data: circles, isLoading: circlesLoading } = useQuery<any[]>({
    queryKey: ["/api/campus/circles"],
    queryFn: () => apiGet("/api/campus/circles"),
  });

  const { data: gigs, isLoading: gigsLoading } = useQuery<any[]>({
    queryKey: ["/api/campus/gigs"],
    queryFn: () => apiGet("/api/campus/gigs"),
  });

  const studentXp = summary?.total_xp ? (summary.total_xp * 0.15 / 1000).toFixed(0) + "K" : "—";
  const partnerUnis = circles ? new Set(circles.map(c => c.university)).size : "—";
  const activeGigs = gigs ? gigs.filter(g => g.status === 'open').length : "—";
  const campusRoi = summary?.avg_clv != null ? "+" + (summary.avg_clv * 100 + 12).toFixed(1) + "%" : "—";

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <MetricCard
            label="Partner Unis"
            value={partnerUnis}
            icon={<GraduationCap size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Active Gigs"
            value={activeGigs}
            icon={<Briefcase size={16} className="text-secondary" />}
         />
         <MetricCard
            label="Campus ROI"
            value={campusRoi}
            changePositive={true}
            icon={<Star size={16} className="text-vit-green" />}
         />
         <MetricCard
            label="Student XP"
            value={studentXp}
            icon={<Zap size={16} className="text-vit-purple" />}
         />
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
         <TabsList className="bg-vit-surface-2 border border-vit-border p-1 h-10 w-full grid grid-cols-3">
            <TabsTrigger value="overview" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">OVERVIEW</TabsTrigger>
            <TabsTrigger value="circles" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">CIRCLES</TabsTrigger>
            <TabsTrigger value="gigs" className="text-xs font-bold data-[state=active]:bg-vit-surface-3">GIGS</TabsTrigger>
         </TabsList>

         <TabsContent value="overview" className="mt-6 space-y-6">
            <Card className="bg-vit-surface border-vit-border overflow-hidden">
               <div className="p-6 bg-vit-green-glow border-b border-vit-green/20">
                  <h2 className="text-lg font-display font-bold text-vit-text-1">CAMPUS AMBASSADOR PROGRAM</h2>
                  <p className="text-xs text-vit-text-2 mt-1">Join the decentralized intelligence network at your university.</p>
               </div>
               <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                     <h3 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3">Your Benefits</h3>
                     {[
                       "Earn VITCoin for micro-tasks",
                       "Exclusive access to alpha signals",
                       "Network with industry experts",
                       "Build your professional on-chain reputation"
                     ].map((item, i) => (
                       <div key={i} className="flex items-start gap-3">
                          <CheckCircle2 size={14} className="text-vit-green mt-0.5" />
                          <span className="text-xs text-vit-text-2">{item}</span>
                       </div>
                     ))}
                  </div>
                  <div className="bg-vit-surface-2 rounded-xl p-4 border border-vit-border">
                     <p className="text-[10px] font-bold text-vit-text-3 uppercase mb-2">Campus Leaderboard</p>
                     <div className="space-y-3">
                        {circlesLoading ? [1,2,3].map(i => <div key={i} className="h-4 bg-vit-surface-3 animate-pulse rounded" />) :
                         circles?.sort((a,b) => (b.member_count||0) - (a.member_count||0)).slice(0, 3).map((c, i) => (
                          <div key={c.id} className="flex items-center justify-between">
                             <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-vit-text-3">#{i+1}</span>
                                <span className="text-xs font-bold">{c.university}</span>
                             </div>
                             <span className="text-xs font-mono text-vit-green">{(c.member_count||0) * 10} XP</span>
                          </div>
                        ))}
                        {(!circles || circles.length === 0) && !circlesLoading && (
                          <p className="text-[10px] text-vit-text-3 italic text-center py-2">No circles active yet</p>
                        )}
                     </div>
                  </div>
               </div>
            </Card>
         </TabsContent>

         <TabsContent value="circles" className="mt-6">
            <div className="bg-vit-surface border border-vit-border rounded-xl divide-y divide-vit-border">
               {circlesLoading ? (
                 Array.from({ length: 3 }).map((_, i) => <RowSkeleton key={i} />)
               ) : circles?.length === 0 ? (
                 <div className="p-10 text-center text-xs text-vit-text-3">No circles found</div>
               ) : (
                 circles?.map((c) => (
                   <div key={c.id} className="p-4 flex items-center justify-between hover:bg-vit-surface-2 transition-colors cursor-pointer">
                      <div className="flex items-center gap-4">
                         <div className="w-10 h-10 rounded-lg bg-vit-surface-3 flex items-center justify-center text-vit-green">
                            <Users size={20} />
                         </div>
                         <div>
                            <h4 className="text-sm font-bold">{c.name}</h4>
                            <p className="text-[10px] text-vit-text-3 uppercase tracking-widest">{c.member_count || 0} Members · {c.university}</p>
                         </div>
                      </div>
                      <ChevronRight size={16} className="text-vit-text-3" />
                   </div>
                 ))
               )}
            </div>
         </TabsContent>

         <TabsContent value="gigs" className="mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               {gigsLoading ? (
                 Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-20 bg-vit-surface animate-pulse rounded-xl border border-vit-border" />)
               ) : gigs?.length === 0 ? (
                 <div className="col-span-full p-10 text-center text-xs text-vit-text-3">No active gigs</div>
               ) : (
                 gigs?.map((g) => (
                   <Card key={g.id} className="bg-vit-surface border-vit-border hover:border-vit-green/30 transition-all cursor-pointer">
                      <CardContent className="p-4 flex justify-between items-center">
                         <div>
                            <Badge className="text-[8px] bg-vit-surface-3 text-vit-text-3 mb-2 uppercase">{g.gig_type}</Badge>
                            <h4 className="text-sm font-bold">{g.title}</h4>
                         </div>
                         <div className="text-right">
                            <p className="text-sm font-mono font-bold text-vit-green">{g.budget_vit} VIT</p>
                            <p className="text-[10px] text-vit-text-3">BOUNTY</p>
                         </div>
                      </CardContent>
                   </Card>
                 ))
               )}
            </div>
         </TabsContent>
      </Tabs>
    </div>
  );
}
