import { useState } from "react";
import {
  ShieldCheck, FileText, Scale, Activity,
  ChevronRight, Search, Zap, Globe, Layers, Cpu
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function PolicyLedgerPage() {
  const bills = [
    { id: "HR-1042", title: "Digital Asset Sovereignty Act", impact: "High", phase: "Review", probability: "64%" },
    { id: "EU-402", title: "Neural Compute Compliance Framework", impact: "Medium", phase: "Drafting", probability: "82%" },
    { id: "NG-92", title: "Cross-Border Liquidity Protocol", impact: "High", phase: "Final", probability: "91%" },
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Regulatory Ledger</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Legislative Analysis & Compliance Forecasting</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Bills Scanned" value="1.2k" icon={<FileText size={14} />} />
        <MetricCard label="Compliance" value="94%" icon={<ShieldCheck size={14} />} />
        <MetricCard label="Active Alerts" value="14" icon={<Activity size={14} />} />
        <MetricCard label="Alpha Drift" value="Low" icon={<Scale size={14} />} />
      </div>

      <div className="space-y-4">
         <h3 className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground pl-1">Legislative Pipeline</h3>
         <div className="border-t border-white/5 bg-background">
            <div className="divide-y divide-white/5">
               {bills.map((bill) => (
                  <div key={bill.id} className="p-6 flex flex-col md:flex-row justify-between items-center gap-6 hover:bg-white/[0.01] transition-all group cursor-pointer">
                     <div className="flex items-center gap-6 flex-1 w-full">
                        <div className="w-12 h-12 rounded border border-white/5 bg-white/5 flex items-center justify-center text-primary group-hover:border-primary/20 transition-all">
                           <Layers size={20} />
                        </div>
                        <div className="space-y-1">
                           <div className="flex items-center gap-3">
                              <Badge variant="outline" className="text-[8px] border-white/10 uppercase tracking-tighter">#{bill.id}</Badge>
                              <span className="text-[9px] font-mono text-vit-positive uppercase tracking-widest">{bill.impact} IMPACT</span>
                           </div>
                           <h3 className="text-base font-bold text-foreground tracking-tight group-hover:text-primary transition-colors">{bill.title}</h3>
                        </div>
                     </div>
                     <div className="flex items-center gap-8 w-full md:w-auto justify-between md:justify-end">
                        <div className="text-right">
                           <p className="font-mono text-xs font-bold text-foreground">{bill.phase}</p>
                           <p className="font-mono text-[8px] text-muted-foreground uppercase mt-1">Status</p>
                        </div>
                        <div className="text-right">
                           <p className="font-mono text-xs font-bold text-primary">{bill.probability}</p>
                           <p className="font-mono text-[8px] text-muted-foreground uppercase mt-1">Pass Prob</p>
                        </div>
                        <ChevronRight size={16} className="text-muted-foreground/20 group-hover:text-primary transition-all" />
                     </div>
                  </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
}
