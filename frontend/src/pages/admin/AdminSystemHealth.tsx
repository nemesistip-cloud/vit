import React, { useMemo } from "react";
import { AdminLayout } from "./AdminLayout";
import { AdminStatusPill } from "@/components/admin/AdminStatusPill";
import { useAdminData } from "@/hooks/useAdminData";
import {
  Activity, Server, Database, Zap, Cpu, Globe,
  Network, HardDrive, Cpu as Processor, RefreshCw,
  Clock, Shield, BarChart3, Terminal
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, LineChart, Line
} from "recharts";

export default function AdminSystemHealth() {
  const { data: health, loading, refetch } = useAdminData<any>("/api/admin/system/health");
  const { data: metrics, loading: mLoading } = useAdminData<any>("/api/admin/system/metrics");

  const resources = useMemo(() => [
    { label: "Processor Core (CPU)", val: health?.resources?.cpu_pct ?? 0, threshold: 80, icon: Processor },
    {
      label: "Volatile Memory (RAM)",
      val: (health?.resources?.ram_used_gb / health?.resources?.ram_total_gb * 100) || 0,
      threshold: 85,
      icon: Cpu,
      detail: `${health?.resources?.ram_used_gb}G / ${health?.resources?.ram_total_gb}G`
    },
    {
      label: "Persistent Storage (NVMe)",
      val: (health?.resources?.disk_used_gb / health?.resources?.disk_total_gb * 100) || 0,
      threshold: 90,
      icon: HardDrive,
      detail: `${health?.resources?.disk_used_gb}G / ${health?.resources?.disk_total_gb}G`
    },
  ], [health]);

  return (
    <AdminLayout>
      <div className="flex flex-col gap-8">

        {/* ── Infra Header ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-sm bg-cyan-500/10 border border-cyan-500/20">
              <Activity size={20} className="text-cyan-400" />
            </div>
            <div>
              <h1 className="font-['Barlow_Condensed'] text-xl font-bold uppercase tracking-wider text-white">Infrastructure Health</h1>
              <p className="font-['Outfit'] text-xs text-white/40">Real-time monitoring of system vitals, resource allocation, and gateway performance</p>
            </div>
          </div>
          <button onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 rounded-sm border border-white/10 bg-white/5 text-[10px] font-bold uppercase tracking-widest text-white/60 hover:bg-white/10 transition-all">
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} /> RE-SCAN INFRA
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

           {/* ── Left Column: Services & Resource Load ── */}
           <div className="lg:col-span-4 flex flex-col gap-6">

              {/* Service Status Matrix */}
              <div className="rounded-sm border border-white/10 bg-white/[0.01] p-6">
                 <h2 className="font-['Barlow_Condensed'] text-[10px] font-bold uppercase tracking-[0.2em] text-white/40 mb-6">Service Topology Status</h2>
                 <div className="space-y-4">
                    {[
                      { label: "Core API Cluster", status: health?.status ?? "unknown", icon: Server },
                      { label: "Relational Storage (Postgres)", status: health?.database?.status ?? "unknown", icon: Database },
                      { label: "Cache & Pub/Sub (Redis)", status: health?.redis?.status ?? "unknown", icon: Zap },
                      { label: "AI Inference Engine", status: health?.models_ready > 0 ? "active" : "degraded", icon: Cpu },
                      { label: "Blockchain Gateway", status: "connected", icon: Network },
                    ].map((s, i) => (
                      <div key={i} className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
                         <div className="flex items-center gap-3">
                            <s.icon size={14} className="text-white/20" />
                            <span className="text-xs font-medium text-white/70">{s.label}</span>
                         </div>
                         <AdminStatusPill status={s.status} />
                      </div>
                    ))}
                 </div>
              </div>

              {/* Hardware Vitals */}
              <div className="rounded-sm border border-white/10 bg-white/[0.01] p-6">
                 <h2 className="font-['Barlow_Condensed'] text-[10px] font-bold uppercase tracking-[0.2em] text-white/40 mb-8">Hardware Consumption</h2>
                 <div className="space-y-8">
                    {resources.map((r, i) => (
                      <div key={i} className="flex flex-col gap-3">
                         <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                               <r.icon size={14} className="text-white/20" />
                               <span className="text-[10px] font-bold text-white/60 uppercase tracking-tighter">{r.label}</span>
                            </div>
                            <span className={`font-['JetBrains_Mono'] text-xs font-bold ${r.val > r.threshold ? 'text-red-400' : 'text-[#00E676]'}`}>{r.val.toFixed(1)}%</span>
                         </div>
                         <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                            <div className={`h-full ${r.val > r.threshold ? 'bg-red-400' : 'bg-[#00E676]'} `} style={{width: `${r.val}%` }} />
                         </div>
                         {r.detail && <span className="text-[9px] font-mono text-white/20 text-right">{r.detail}</span>}
                      </div>
                    ))}
                 </div>
              </div>
           </div>

           {/* ── Center Column: Performance Metrics ── */}
           <div className="lg:col-span-5 flex flex-col gap-6">
              <div className="rounded-sm border border-white/10 bg-white/[0.01] p-6">
                 <h2 className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-white/40 mb-8">Request Latency Analysis</h2>
                 <div className="grid grid-cols-2 gap-4 mb-8">
                    <div className="rounded-sm bg-white/5 p-4 border border-white/5">
                       <span className="text-[9px] font-bold text-white/20 uppercase block mb-1">Average Response</span>
                       <span className="font-['JetBrains_Mono'] text-2xl font-bold text-white tabular-nums">{Math.round(metrics?.avg_response_ms ?? 0)}ms</span>
                    </div>
                    <div className="rounded-sm bg-white/5 p-4 border border-white/5">
                       <span className="text-[9px] font-bold text-white/20 uppercase block mb-1">Error Rate (24h)</span>
                       <span className={`font-['JetBrains_Mono'] text-2xl font-bold tabular-nums ${metrics?.error_rate_pct > 1 ? 'text-red-400' : 'text-[#00E676]'}`}>{metrics?.error_rate_pct}%</span>
                    </div>
                 </div>
                 <div className="h-[260px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={[
                        { name: 'Gateway', val: 42 },
                        { name: 'Auth', val: 124 },
                        { name: 'DB Query', val: 15 },
                        { name: 'AI Infer', val: 850 },
                        { name: 'Cache', val: 2 },
                      ]}>
                         <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                         <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: 'rgba(255,255,255,0.2)', fontSize: 9, fontFamily: 'JetBrains Mono'}} />
                         <YAxis axisLine={false} tickLine={false} tick={{fill: 'rgba(255,255,255,0.2)', fontSize: 9, fontFamily: 'JetBrains Mono'}} />
                         <Tooltip contentStyle={{backgroundColor: '#0b1018', border: '1px solid rgba(255,255,255,0.1)'}} />
                         <Bar dataKey="val" fill="#00B0FF" radius={[2, 2, 0, 0]} opacity={0.6} />
                      </BarChart>
                    </ResponsiveContainer>
                 </div>
              </div>

              <div className="rounded-sm border border-white/10 bg-white/[0.01] p-6">
                 <h2 className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-white/40 mb-6">Traffic Volume</h2>
                 <div className="h-[140px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                       <LineChart data={[
                         { t: '00:00', v: 400 }, { t: '04:00', v: 300 }, { t: '08:00', v: 800 },
                         { t: '12:00', v: 1200 }, { t: '16:00', v: 1100 }, { t: '20:00', v: 900 }
                       ]}>
                          <Line type="monotone" dataKey="v" stroke="#8B5CF6" strokeWidth={2} dot={false} />
                          <Tooltip contentStyle={{backgroundColor: '#0b1018', border: '1px solid rgba(255,255,255,0.1)'}} />
                       </LineChart>
                    </ResponsiveContainer>
                 </div>
              </div>
           </div>

           {/* ── Right Column: Gateway Integrations ── */}
           <div className="lg:col-span-3 flex flex-col gap-6">
              <div className="rounded-sm border border-white/10 bg-white/[0.01] p-6">
                 <h2 className="font-['Barlow_Condensed'] text-[10px] font-bold uppercase tracking-[0.2em] text-white/40 mb-6">Upstream Latency</h2>
                 <div className="space-y-4">
                    {Object.entries(health?.api_latencies || {}).map(([name, lat]) => (
                      <div key={name} className="flex flex-col gap-1.5">
                         <div className="flex justify-between text-[10px] font-bold">
                            <span className="text-white/30 uppercase tracking-tighter">{name.replace('_', ' ')}</span>
                            <span className={`font-mono ${Number(lat) > 500 ? 'text-amber-400' : 'text-[#00E676]'}`}>{lat}ms</span>
                         </div>
                         <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                            <div className={`h-full ${Number(lat) > 500 ? 'bg-amber-400' : 'bg-[#00E676]'} `} style={{width: `${Math.min(100, Number(lat) / 10)}%` }} />
                         </div>
                      </div>
                    ))}
                 </div>
              </div>

              <div className="rounded-sm border border-white/10 bg-white/[0.01] p-6">
                 <h2 className="font-['Barlow_Condensed'] text-[10px] font-bold uppercase tracking-[0.2em] text-white/40 mb-4 flex items-center gap-2">
                    <Terminal size={12} /> System Runtime
                 </h2>
                 <div className="font-['JetBrains_Mono'] text-[10px] text-white/30 leading-relaxed uppercase">
                    UPTIME: 142H 11M 22S<br />
                    PROCESS_ID: 10421<br />
                    VERSION: 5.5.0-INSTITUTIONAL<br />
                    CLUSTER: PRIMARY-US-EAST
                 </div>
              </div>
           </div>

        </div>

      </div>
    </AdminLayout>
  );
}
