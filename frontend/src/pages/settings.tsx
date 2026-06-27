import { useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  Settings, User, Shield, Bell, Globe,
  Lock, LogOut, ChevronRight, Cpu, Eye,
  Cloud, Database, Smartphone
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const { user, logout } = useAuth();

  const sections = [
    {
      title: "Security & Access",
      items: [
        { icon: Lock, label: "Two-Factor Authentication", desc: "Secure your Terminal access", toggle: true },
        { icon: Shield, label: "API Key Management", desc: "Manage institutional integration keys" },
      ]
    },
    {
      title: "System Configuration",
      items: [
        { icon: Cpu, label: "Neural Engine Priority", desc: "Optimize for latency or accuracy", toggle: true },
        { icon: Globe, label: "Network Sharding", desc: "Distributed node connectivity settings" },
      ]
    },
    {
      title: "Communication",
      items: [
        { icon: Bell, label: "Signal Alerts", desc: "Real-time push notifications for alpha", toggle: true },
      ]
    }
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Configuration</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Institutional Terminal Settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           {/* ── User Profile ── */}
           <Card className="border-primary/20 bg-primary/[0.02]">
              <CardContent className="p-8">
                 <div className="flex items-center gap-6">
                    <div className="w-20 h-20 rounded bg-primary/10 border border-primary/20 flex items-center justify-center text-2xl font-black text-primary">
                       {user?.username?.[0]?.toUpperCase()}
                    </div>
                    <div className="space-y-2">
                       <div className="flex items-center gap-3">
                          <h2 className="text-xl font-bold tracking-tight">{user?.username}</h2>
                          <Badge className="bg-primary text-primary-foreground text-[8px] uppercase tracking-widest">{user?.tier || 'Viewer'} Tier</Badge>
                       </div>
                       <p className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">{user?.email}</p>
                       <p className="font-mono text-[9px] text-muted-foreground/50 uppercase tracking-widest">UID: {user?.id?.slice(0,12)}...</p>
                    </div>
                 </div>
              </CardContent>
           </Card>

           {/* ── Settings Sections ── */}
           {sections.map((section, i) => (
              <div key={i} className="space-y-4">
                 <h3 className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground pl-1">{section.title}</h3>
                 <Card className="border-white/5 bg-white/[0.01] overflow-hidden">
                    <div className="divide-y divide-white/5">
                       {section.items.map((item, j) => (
                          <div key={j} className="p-5 flex items-center justify-between hover:bg-white/[0.01] transition-all">
                             <div className="flex items-center gap-4">
                                <div className="w-9 h-9 rounded border border-white/5 bg-white/5 flex items-center justify-center text-muted-foreground/60">
                                   <item.icon size={16} />
                                </div>
                                <div>
                                   <p className="text-sm font-bold tracking-tight">{item.label}</p>
                                   <p className="text-[11px] text-muted-foreground">{item.desc}</p>
                                </div>
                             </div>
                             {item.toggle ? (
                                <Switch className="data-[state=checked]:bg-primary" />
                             ) : (
                                <Button variant="ghost" size="icon" className="w-8 h-8 opacity-20 hover:opacity-100">
                                   <ChevronRight size={16} />
                                </Button>
                             )}
                          </div>
                       ))}
                    </div>
                 </Card>
              </div>
           ))}

           <Button
             variant="outline"
             className="w-full h-12 text-vit-negative border-vit-negative/20 hover:bg-vit-negative/5 uppercase tracking-widest text-[10px] font-bold"
             onClick={() => logout?.()}
           >
              <LogOut size={14} className="mr-2" /> De-provision Session
           </Button>
        </div>

        <div className="space-y-6">
           <Card className="bg-white/[0.02] border-white/5">
              <CardHeader>
                 <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">Terminal Health</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                 {[
                    { label: "Connection", value: "Optimal", color: "text-vit-positive" },
                    { label: "Latency", value: "14ms", color: "text-foreground" },
                    { label: "Session", value: "Active", color: "text-foreground" },
                 ].map((stat, i) => (
                    <div key={i} className="flex justify-between items-center">
                       <span className="text-[11px] text-muted-foreground">{stat.label}</span>
                       <span className={cn("font-mono text-[11px] font-bold", stat.color)}>{stat.value}</span>
                    </div>
                 ))}
              </CardContent>
           </Card>
        </div>
      </div>
    </div>
  );
}
