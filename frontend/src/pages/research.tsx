import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import {
  FileText, Search, Filter, BookOpen, Clock,
  ChevronRight, Brain, BarChart3, Database, Globe
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function ResearchHub() {
  const [search, setSearch] = useState("");

  const reports = [
    { id: 1, title: "Neural Consensus Performance Report Q3", author: "Alpha Labs", category: "Technical", date: "2d ago" },
    { id: 2, title: "Market Volatility & Ensemble Resilience", author: "Treasury Hub", category: "Economic", date: "5d ago" },
    { id: 3, title: "VESS Distributed Storage Shard Analysis", author: "Infra Core", category: "Infrastructure", date: "1w ago" },
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Intelligence Hub</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Institutional Research & Market Reports</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Pubs" value="142" icon={<FileText size={14} />} />
        <MetricCard label="Authors" value="12" icon={<Globe size={14} />} />
        <MetricCard label="Citations" value="2.4k" icon={<BookOpen size={14} />} />
        <MetricCard label="Impact" value="8.4" icon={<BarChart3 size={14} />} />
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
        <Input
          placeholder="Search reports, whitepapers, or data..."
          className="pl-9 bg-white/[0.02] border-white/5 h-10 text-xs font-mono"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="space-y-4">
         <h3 className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground pl-1">Latest Publications</h3>
         <div className="border-t border-white/5 bg-background">
            <div className="divide-y divide-white/5">
               {reports.map((report) => (
                  <div key={report.id} className="p-6 flex flex-col md:flex-row justify-between items-center gap-6 hover:bg-white/[0.01] transition-all group cursor-pointer">
                     <div className="flex items-center gap-6 flex-1 w-full">
                        <div className="w-12 h-12 rounded border border-white/5 bg-white/5 flex items-center justify-center text-primary group-hover:border-primary/20 transition-all">
                           <FileText size={20} />
                        </div>
                        <div className="space-y-1">
                           <div className="flex items-center gap-3">
                              <Badge variant="outline" className="text-[8px] border-white/10 uppercase tracking-tighter">{report.category}</Badge>
                              <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">{report.author}</span>
                           </div>
                           <h3 className="text-base font-bold text-foreground tracking-tight group-hover:text-primary transition-colors">{report.title}</h3>
                        </div>
                     </div>
                     <div className="flex items-center gap-8 w-full md:w-auto justify-between md:justify-end">
                        <div className="text-right">
                           <p className="font-mono text-xs font-bold text-muted-foreground">{report.date}</p>
                           <p className="font-mono text-[8px] text-muted-foreground/40 uppercase mt-1">Released</p>
                        </div>
                        <Button variant="outline" size="icon" className="w-9 h-9 border-white/5 group-hover:border-primary group-hover:text-primary transition-all">
                           <ChevronRight size={16} />
                        </Button>
                     </div>
                  </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
}
