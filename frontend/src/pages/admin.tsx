import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPatch, apiPut, apiDelete } from "@/lib/apiClient";
import { TERMS } from "@/lib/terminology";
import {
  useAdminCalibrationFit,
  useAdminCalibrationReload,
  useAdminSettleResults,
  useAdminBackfillFtResults,
  useAdminAccumulatorPlaceBet,
  useAdminAccumulatorSend,
  useAiFeedConsensus,
  useUpdateAiPerformance,
} from "@/api-client/index";
import { useAuth } from "@/lib/auth";
import { PermissionGate } from "@/components/auth/PermissionGate";
import { Redirect } from "wouter";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Activity, Database, Settings, ShieldCheck, BarChart2,
  Globe, Coins, CreditCard, BookOpen, Cpu, Key, RefreshCw,
  Trash2, Ban, Edit, Plus, CheckCircle, XCircle, AlertCircle, AlertTriangle,
  TrendingUp, Server, Zap, Save, Search, Eye, EyeOff,
  ChevronRight, Shield, Lock, Unlock, Download,
  Users, UserCheck, Upload, Package, ClipboardList, Star, Send,
  Brain, HeartPulse, Stethoscope, BarChart3, Lightbulb, FileUp, Info, Loader2,
  Network, Plug,
} from "lucide-react";
import { toast } from "sonner";

// ─── Types ───────────────────────────────────────────────────────────

interface AdminStats {
  users: number; matches: number; training_jobs: number;
  active_plans: number; audit_entries: number;
  recent_activity: { action: string; actor: string; status: string; timestamp: string }[];
  top_users: { id: number; username: string; email: string; role: string; tier: string }[];
}

interface SystemHealth {
  api: boolean; database: boolean; redis: boolean | null;
  models_loaded: number; cpu_pct: number; mem_pct: number; disk_pct: number;
  football_api?: boolean | "limited" | null;
  odds_api?: boolean | null;
}

interface League {
  id: string; name: string; country: string; status: string;
  weight: number; data_quality: number; matches: number;
}

interface Market {
  id: string; name: string; status: string;
  min_stake: number; max_stake: number; edge_threshold: number;
  commission_rate: number; available_tiers: string[];
}

interface Currency {
  code: string; symbol: string; name: string;
  rate_to_usd: number; status: string; min_deposit: number; max_deposit: number;
}

interface Plan {
  id: number; name: string; display_name: string;
  price_monthly: number; price_yearly: number;
  prediction_limit?: number; features: Record<string, unknown>; is_active: boolean;
}

interface AuditEntry {
  id: number; action: string; actor: string; resource?: string;
  resource_id?: string; details?: Record<string, unknown>;
  ip_address?: string; status: string; timestamp: string;
}

interface AdminUser {
  id: number; email: string; username: string; role: string;
  admin_role?: string; subscription_tier: string; is_active: boolean;
  is_verified: boolean; is_banned: boolean; created_at?: string;
  last_login?: string; vitcoin_balance?: number;
}

interface ModelInfo {
  key: string; model_name: string; model_type?: string; weight: number;
  ready: boolean; is_trained?: boolean; is_active?: boolean;
  error?: string; source?: string; listing_id?: number;
  pkl_loaded?: boolean; trained_count?: number;
}

interface KYCEntry {
  id: number; user_id: number; status: string;
  full_name?: string; document_type?: string; submitted_at?: string;
  email?: string; username?: string;
}

interface MarketplaceListing {
  id: number; creator_id: number; name: string; slug: string;
  description?: string; category: string; price_per_call: string;
  listing_fee_paid: string; model_key?: string; pkl_path?: string;
  file_size_bytes?: number; webhook_url?: string;
  approval_status: string; is_verified: boolean;
  usage_count: number; avg_rating: number; created_at?: string;
  package_id?: string; primary_file?: string; package_file_count?: number;
  execution_status?: string; system_model_slot?: string;
}

// ─── Status Badge ─────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    paused: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    disabled: "bg-red-500/20 text-red-400 border-red-500/30",
    success: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    failure: "bg-red-500/20 text-red-400 border-red-500/30",
    warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border font-medium ${map[status] ?? "bg-gray-500/20 text-gray-400 border-gray-500/30"}`}>
      {status}
    </span>
  );
}

function HealthDot({ ok, optional }: { ok: boolean; optional?: boolean }) {
  return <span className={`inline-block w-2 h-2 rounded-full ${optional ? "bg-gray-500" : ok ? "bg-emerald-400" : "bg-red-400"}`} />;
}

// ─── Module 1: Dashboard ──────────────────────────────────────────────

function DashboardTab() {
  const { data: stats, isLoading: sLoading } = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    queryFn: () => apiGet("/api/admin/stats"),
    refetchInterval: 30000,
  });
  const { data: health } = useQuery<SystemHealth>({
    queryKey: ["admin-health"],
    queryFn: () => apiGet("/api/admin/system/health"),
    refetchInterval: 15000,
  });
  const qc = useQueryClient();

  const clearCache = useMutation({
    mutationFn: () => apiPost("/api/admin/system/cache/clear", {}),
    onSuccess: () => toast.success("Cache cleared"),
    onError: () => toast.error("Failed to clear cache"),
  });
  const backup = useMutation({
    mutationFn: () => apiPost("/api/admin/system/backup", {}),
    onSuccess: (d: any) => toast.success(`Backup: ${d.backup}`),
    onError: () => toast.error("Backup failed"),
  });
  const fetchFixtures = useMutation({
    mutationFn: () => apiPost("/api/admin/matches/fetch-fixtures?count=50&days=14", {}),
    onSuccess: (d: any) => {
      toast.success(`Pipeline: fetched ${d.stored ?? 0} new fixtures (${d.skipped_existing ?? 0} already existed)`);
      qc.invalidateQueries({ queryKey: ["/matches/upcoming"] });
      qc.invalidateQueries({ queryKey: ["matches-recent"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: () => toast.error("Fixture fetch failed — check Football API key in settings"),
  });

  const syncAndSeed = useMutation({
    mutationFn: () => apiPost("/api/admin/sync-fixtures", {}),
    onSuccess: (d: any) => {
      const f = d.fixtures ?? {};
      const p = d.predictions ?? {};
      toast.success(
        `Sync complete: +${f.inserted ?? 0} fixtures, ${p.seeded ?? 0} predictions seeded, ${p.alerts_sent ?? 0} alerts sent`
      );
      qc.invalidateQueries({ queryKey: ["/matches/upcoming"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: () => toast.error("Sync failed — check server logs"),
  });

  const kpis = [
    {
      label: "Total Users", value: stats?.users ?? 0, icon: Users,
      gradient: "from-cyan-500/10 to-transparent", border: "border-cyan-500/20",
      glow: "shadow-[0_0_20px_rgba(6,182,212,0.08)]", iconColor: "text-cyan-400",
      valueCls: "text-cyan-400",
    },
    {
      label: "Total Matches", value: stats?.matches ?? 0, icon: BarChart2,
      gradient: "from-purple-500/10 to-transparent", border: "border-purple-500/20",
      glow: "shadow-[0_0_20px_rgba(168,85,247,0.08)]", iconColor: "text-purple-400",
      valueCls: "text-purple-300",
    },
    {
      label: "Training Jobs", value: stats?.training_jobs ?? 0, icon: Cpu,
      gradient: "from-emerald-500/10 to-transparent", border: "border-emerald-500/20",
      glow: "shadow-[0_0_20px_rgba(52,211,153,0.08)]", iconColor: "text-emerald-400",
      valueCls: "text-emerald-300",
    },
    {
      label: "Active Plans", value: stats?.active_plans ?? 0, icon: CreditCard,
      gradient: "from-amber-500/10 to-transparent", border: "border-amber-500/20",
      glow: "shadow-[0_0_20px_rgba(245,158,11,0.08)]", iconColor: "text-amber-400",
      valueCls: "text-amber-300",
    },
  ];

  if (sLoading) return (
    <div className="flex justify-center py-20">
      <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const serviceRows = [
    { label: "API Server",   ok: health?.api,                          optional: false, icon: Server },
    { label: "Database",     ok: health?.database,                     optional: false, icon: Database },
    { label: "Redis Cache",  ok: health?.redis === true,               optional: health?.redis === null, icon: Zap },
    { label: "ML Models",    ok: (health?.models_loaded ?? 0) > 0,     optional: false, icon: Cpu, detail: health ? `${health.models_loaded} loaded` : undefined },
    { label: "Football API", ok: health?.football_api === true,        optional: health?.football_api == null, limited: health?.football_api === "limited", icon: Globe },
    { label: "Odds API",     ok: health?.odds_api === true,            optional: health?.odds_api == null, icon: TrendingUp },
  ] as { label: string; ok: boolean; optional: boolean; limited?: boolean; icon: any; detail?: string }[];

  return (
    <div className="space-y-5">

      {/* ── KPI Cards ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {kpis.map(k => (
          <div key={k.label} className={`relative overflow-hidden rounded-xl border ${k.border} bg-gray-900 ${k.glow} transition-all hover:scale-[1.01]`}>
            <div className={`absolute inset-0 bg-gradient-to-br ${k.gradient}`} />
            <div className="relative p-4">
              <div className="flex items-start justify-between mb-3">
                <div className={`p-2 rounded-lg bg-gray-800/80 border border-gray-700/50`}>
                  <k.icon className={`w-4 h-4 ${k.iconColor}`} />
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-gray-600" />
              </div>
              <div className={`text-2xl sm:text-3xl font-bold font-mono tabular-nums ${k.valueCls}`}>
                {sLoading ? "—" : (typeof k.value === "number" ? k.value.toLocaleString() : (k.value ?? "—"))}
              </div>
              <div className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">{k.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">

        {/* ── System Health Matrix ─────────────────────────────────── */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
          <div className="px-4 pt-4 pb-3 border-b border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-4 rounded-full bg-cyan-400/80" />
              <span className="text-sm font-semibold text-white">System Health</span>
            </div>
            <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-gray-500 hover:text-cyan-400"
              onClick={() => qc.invalidateQueries({ queryKey: ["admin-health"] })}>
              <RefreshCw className="w-3 h-3" />
            </Button>
          </div>
          <div className="p-4 space-y-2">
            {!health ? (
              <div className="grid grid-cols-2 gap-2">
                {[1,2,3,4,5,6].map(i => <div key={i} className="h-9 rounded-lg bg-gray-800 animate-pulse" />)}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {serviceRows.map(row => (
                  <div key={row.label} className={`flex items-center gap-2.5 px-3 py-2 rounded-lg border transition-colors ${
                    row.optional && !row.ok
                      ? "bg-gray-800/30 border-gray-700/50"
                      : row.limited
                        ? "bg-amber-500/5 border-amber-500/20"
                        : row.ok
                          ? "bg-emerald-500/5 border-emerald-500/20"
                          : "bg-red-500/5 border-red-500/20"
                  }`}>
                    <span className={`w-2 h-2 rounded-full shrink-0 ${
                      row.optional && !row.ok ? "bg-gray-600" :
                      row.limited ? "bg-amber-400" :
                      row.ok ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" : "bg-red-400 animate-pulse"
                    }`} />
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-gray-300 truncate">{row.label}</div>
                      {row.detail && <div className="text-[10px] text-gray-500">{row.detail}</div>}
                    </div>
                    <span className={`ml-auto text-[10px] font-medium shrink-0 ${
                      row.optional && !row.ok ? "text-gray-600" :
                      row.limited ? "text-amber-400" :
                      row.ok ? "text-emerald-400" : "text-red-400"
                    }`}>
                      {row.optional && !row.ok ? "N/A" : row.limited ? "Limited" : row.ok ? "OK" : "DOWN"}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {health && (
              <div className="mt-3 pt-3 border-t border-gray-800 grid grid-cols-3 gap-2">
                {[
                  { label: "CPU", value: health.cpu_pct, warn: 80 },
                  { label: "RAM", value: health.mem_pct, warn: 85 },
                  { label: "Disk", value: health.disk_pct, warn: 90 },
                ].map(m => (
                  <div key={m.label} className="text-center">
                    <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">{m.label}</div>
                    <div className={`text-lg font-bold font-mono ${m.value > m.warn ? "text-red-400" : "text-white"}`}>
                      {m.value}%
                    </div>
                    <div className="mt-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all ${m.value > m.warn ? "bg-red-400" : m.value > m.warn * 0.8 ? "bg-amber-400" : "bg-emerald-400"}`}
                        style={{ width: `${m.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Quick Actions ────────────────────────────────────────── */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
          <div className="px-4 pt-4 pb-3 border-b border-gray-800 flex items-center gap-2">
            <div className="w-1.5 h-4 rounded-full bg-amber-400/80" />
            <span className="text-sm font-semibold text-white">Quick Actions</span>
          </div>
          <div className="p-4 grid grid-cols-2 gap-2">
            {[
              { label: "Refresh Stats",  icon: RefreshCw, action: () => qc.invalidateQueries({ queryKey: ["admin-stats"] }),  cls: "from-cyan-500/10 border-cyan-500/20 text-cyan-400 hover:border-cyan-400/60",    loading: false },
              { label: "Clear Cache",    icon: Zap,        action: () => clearCache.mutate(),    cls: "from-purple-500/10 border-purple-500/20 text-purple-400 hover:border-purple-400/60",  loading: clearCache.isPending },
              { label: "Create Backup",  icon: Database,   action: () => backup.mutate(),         cls: "from-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:border-emerald-400/60", loading: backup.isPending },
              { label: "Reload Health",  icon: Activity,   action: () => qc.invalidateQueries({ queryKey: ["admin-health"] }), cls: "from-amber-500/10 border-amber-500/20 text-amber-400 hover:border-amber-400/60",  loading: false },
              { label: "Fetch Fixtures", icon: Download,   action: () => fetchFixtures.mutate(), cls: "from-rose-500/10 border-rose-500/20 text-rose-400 hover:border-rose-400/60",         loading: fetchFixtures.isPending },
              { label: "Sync + Seed",   icon: RefreshCw,  action: () => syncAndSeed.mutate(),   cls: "from-cyan-500/10 border-cyan-500/20 text-cyan-400 hover:border-cyan-400/60",          loading: syncAndSeed.isPending },
            ].map(a => (
              <button key={a.label}
                disabled={a.loading}
                onClick={a.action}
                className={`flex flex-col items-center justify-center gap-1.5 h-16 rounded-lg border bg-gradient-to-br ${a.cls}
                  transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed`}>
                <a.icon className={`w-4 h-4 ${a.loading ? "animate-spin" : ""}`} />
                <span className="text-[11px] font-medium leading-tight text-center">
                  {a.loading ? "Working…" : a.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Recent Activity ──────────────────────────────────────────── */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
        <div className="px-4 pt-4 pb-3 border-b border-gray-800 flex items-center gap-2">
          <div className="w-1.5 h-4 rounded-full bg-purple-400/80" />
          <span className="text-sm font-semibold text-white">Recent Activity</span>
          {stats?.recent_activity?.length ? (
            <span className="ml-auto text-xs text-gray-500">{stats.recent_activity.length} events</span>
          ) : null}
        </div>
        <div className="divide-y divide-gray-800/80">
          {stats?.recent_activity?.length ? (
            stats.recent_activity.slice(0, 8).map((a, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-800/30 transition-colors">
                <StatusBadge status={a.status} />
                <span className="text-xs text-gray-300 font-mono flex-1 truncate">{a.action}</span>
                <span className="text-xs text-gray-600 hidden sm:block shrink-0">
                  {a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : ""}
                </span>
              </div>
            ))
          ) : (
            <div className="text-center text-gray-600 text-sm py-10">
              <Activity className="w-8 h-8 mx-auto mb-2 opacity-20" />
              No recent activity
            </div>
          )}
        </div>
      </div>

    </div>
  );
}

// ─── Module 3: Leagues ────────────────────────────────────────────────

function LeaguesTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<{ leagues: League[] }>({
    queryKey: ["admin-leagues"],
    queryFn: () => apiGet("/api/admin/leagues"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<League> }) => apiPut(`/api/admin/leagues/${id}`, body),
    onSuccess: () => { toast.success("League updated"); qc.invalidateQueries({ queryKey: ["admin-leagues"] }); },
    onError: () => toast.error("Update failed"),
  });

  const statusColor = { active: "text-emerald-400", paused: "text-yellow-400", disabled: "text-red-400" };

  if (isLoading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <Card className="bg-gray-900 border-gray-700">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Globe className="w-5 h-5 text-cyan-400" /> League Configuration ({data?.leagues?.length ?? 0} leagues)
        </CardTitle>
        <CardDescription className="text-gray-400">Configure status, weights and data quality for each league</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-gray-400">
                <th className="text-left p-3">League</th>
                <th className="text-left p-3">Country</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Weight</th>
                <th className="text-left p-3">Quality</th>
                <th className="text-right p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.leagues?.map(lg => (
                <tr key={lg.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="p-3 font-medium text-white">{lg.name}</td>
                  <td className="p-3 text-gray-400">{lg.country}</td>
                  <td className="p-3">
                    <span className={`capitalize font-medium ${(statusColor as any)[lg.status] ?? "text-gray-400"}`}>{lg.status}</span>
                  </td>
                  <td className="p-3 text-gray-300">{lg.weight.toFixed(1)}×</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div className="h-full bg-cyan-400 rounded-full" style={{ width: `${lg.data_quality}%` }} />
                      </div>
                      <span className="text-gray-400 text-xs">{lg.data_quality}%</span>
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="flex items-center justify-end gap-1">
                      {(["active", "paused", "disabled"] as const).map(s => (
                        <Button key={s} size="sm" variant="outline"
                          className={`h-6 px-2 text-xs border-gray-600 ${lg.status === s ? "bg-gray-700" : "bg-transparent"}`}
                          onClick={() => updateMutation.mutate({ id: lg.id, body: { status: s } })}>
                          {s}
                        </Button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Module 4: Markets ────────────────────────────────────────────────

function MarketsTab() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Market | null>(null);
  const { data, isLoading } = useQuery<{ markets: Market[] }>({
    queryKey: ["admin-markets"],
    queryFn: () => apiGet("/api/admin/markets"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Market> }) => apiPut(`/api/admin/markets/${id}`, body),
    onSuccess: () => { toast.success("Market updated"); setEditing(null); qc.invalidateQueries({ queryKey: ["admin-markets"] }); },
    onError: () => toast.error("Update failed"),
  });

  if (isLoading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {data?.markets?.map(mk => (
          <Card key={mk.id} className="bg-gray-900 border-gray-700">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <CardTitle className="text-white text-base">{mk.name}</CardTitle>
                <StatusBadge status={mk.status} />
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between text-gray-400">
                <span>Stake Range</span>
                <span className="text-white">{mk.min_stake}–{mk.max_stake} VIT</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Edge Threshold</span>
                <span className="text-white">{mk.edge_threshold}%</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Commission</span>
                <span className="text-white">{mk.commission_rate}%</span>
              </div>
              <div className="flex flex-wrap gap-1 pt-1">
                {mk.available_tiers.map(t => (
                  <Badge key={t} variant="outline" className="text-xs border-gray-600 text-gray-400 capitalize">{t}</Badge>
                ))}
              </div>
              <Button size="sm" variant="outline" className="w-full mt-2 border-gray-600 text-gray-300 hover:text-white"
                onClick={() => setEditing(mk)}>
                <Edit className="w-3 h-3 mr-1" /> Configure
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {editing && (
        <Dialog open onOpenChange={() => setEditing(null)}>
          <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
            <DialogHeader><DialogTitle>Configure — {editing.name}</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <div className="space-y-1">
                <Label className="text-gray-400">Status</Label>
                <Select defaultValue={editing.status} onValueChange={v => setEditing(e => e ? { ...e, status: v } : null)}>
                  <SelectTrigger className="bg-gray-800 border-gray-600"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700">
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="paused">Paused</SelectItem>
                    <SelectItem value="disabled">Disabled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-gray-400">Min Stake (VIT)</Label>
                  <Input type="number" className="bg-gray-800 border-gray-600 text-white" defaultValue={editing.min_stake}
                    onChange={e => setEditing(m => m ? { ...m, min_stake: +e.target.value } : null)} />
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-400">Max Stake (VIT)</Label>
                  <Input type="number" className="bg-gray-800 border-gray-600 text-white" defaultValue={editing.max_stake}
                    onChange={e => setEditing(m => m ? { ...m, max_stake: +e.target.value } : null)} />
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-400">Edge Threshold %</Label>
                  <Input type="number" step="0.1" className="bg-gray-800 border-gray-600 text-white" defaultValue={editing.edge_threshold}
                    onChange={e => setEditing(m => m ? { ...m, edge_threshold: +e.target.value } : null)} />
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-400">Commission %</Label>
                  <Input type="number" step="0.1" className="bg-gray-800 border-gray-600 text-white" defaultValue={editing.commission_rate}
                    onChange={e => setEditing(m => m ? { ...m, commission_rate: +e.target.value } : null)} />
                </div>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" className="border-gray-600" onClick={() => setEditing(null)}>Cancel</Button>
              <Button className="bg-cyan-500 hover:bg-cyan-400 text-black"
                disabled={updateMutation.isPending}
                onClick={() => updateMutation.mutate({ id: editing.id, body: { status: editing.status, min_stake: editing.min_stake, max_stake: editing.max_stake, edge_threshold: editing.edge_threshold, commission_rate: editing.commission_rate } })}>
                Save
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

// ─── Module 5: Currency ───────────────────────────────────────────────

function CurrencyTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<{ currencies: Currency[]; conversion_fees: Record<string, number>; vit_pricing: Record<string, number> }>({
    queryKey: ["admin-currency"],
    queryFn: () => apiGet("/api/admin/currency"),
  });

  const recalcMutation = useMutation({
    mutationFn: () => apiPost("/api/admin/currency/recalculate-vit", {}),
    onSuccess: (d: any) => { toast.success(`New VIT price: $${d.new_price_usd}`); qc.invalidateQueries({ queryKey: ["admin-currency"] }); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ code, body }: { code: string; body: Partial<Currency> }) => apiPut(`/api/admin/currency/${code}`, body),
    onSuccess: () => { toast.success("Rate updated"); qc.invalidateQueries({ queryKey: ["admin-currency"] }); },
  });

  if (isLoading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>;

  const vit = data?.vit_pricing ?? {};
  const fees = data?.conversion_fees ?? {};

  return (
    <div className="space-y-6">
      {/* VIT Pricing Engine */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Coins className="w-5 h-5 text-amber-400" /> VIT Coin Pricing Engine
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-xs text-gray-500 mb-1">Current Price</div>
              <div className="text-xl font-bold text-amber-400 truncate">${(vit.current_price_usd ?? 0.10).toFixed(6)}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-xs text-gray-500 mb-1">Circulating Supply</div>
              <div className="text-xl font-bold text-white truncate">{(vit.circulating_supply ?? 0).toLocaleString()}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-xs text-gray-500 mb-1">30d Revenue</div>
              <div className="text-xl font-bold text-emerald-400 truncate">${(vit.rolling_revenue_usd ?? 0).toFixed(2)}</div>
            </div>
          </div>
          <Button className="bg-amber-500 hover:bg-amber-400 text-black" onClick={() => recalcMutation.mutate()}>
            <RefreshCw className="w-4 h-4 mr-2" /> Recalculate VIT Price
          </Button>
        </CardContent>
      </Card>

      {/* Fiat Currencies */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Fiat Currency Rates</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-gray-400">
                <th className="text-left p-3">Currency</th>
                <th className="text-left p-3">Rate (USD)</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Min / Max Deposit</th>
              </tr>
            </thead>
            <tbody>
              {data?.currencies?.map(c => (
                <tr key={c.code} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="p-3">
                    <span className="font-bold text-white">{c.symbol}</span>
                    <span className="ml-2 text-gray-400">{c.code} — {c.name}</span>
                  </td>
                  <td className="p-3 font-mono text-gray-200">{c.rate_to_usd}</td>
                  <td className="p-3"><StatusBadge status={c.status} /></td>
                  <td className="p-3 text-gray-400 text-xs">
                    {c.symbol}{c.min_deposit.toLocaleString()} / {c.symbol}{c.max_deposit.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Conversion Fees */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader><CardTitle className="text-white">Conversion Fees</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-3 gap-4">
          {[
            { label: "Fiat → VIT", key: "fiat_to_vit" },
            { label: "VIT → Fiat", key: "vit_to_fiat" },
            { label: "Cross-Fiat",  key: "cross_fiat" },
          ].map(f => (
            <div key={f.key} className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-xs text-gray-500 mb-1">{f.label}</div>
              <div className="text-xl font-bold text-white">{fees[f.key] ?? 0}%</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Module 6: Subscriptions ──────────────────────────────────────────

function SubscriptionsTab() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Plan | null>(null);
  const { data, isLoading } = useQuery<{ plans: Plan[] }>({
    queryKey: ["admin-subscriptions"],
    queryFn: () => apiGet("/api/admin/subscriptions"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Plan> }) => apiPut(`/api/admin/subscriptions/${id}`, body),
    onSuccess: () => { toast.success("Plan updated"); setEditing(null); qc.invalidateQueries({ queryKey: ["admin-subscriptions"] }); },
  });

  const tierColors: Record<string, string> = {
    free: "border-zinc-600 bg-zinc-900",
    analyst: "border-blue-500/40 bg-blue-500/10",
    pro: "border-emerald-500/40 bg-emerald-500/10",
    elite: "border-emerald-500/40 bg-emerald-500/10",
  };

  if (isLoading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {data?.plans?.map(plan => (
          <Card key={plan.id} className={`border ${tierColors[plan.name] ?? "border-gray-700 bg-gray-900"}`}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white text-lg">{plan.display_name}</CardTitle>
                {!plan.is_active && <Badge variant="outline" className="border-red-500/50 text-red-400 text-xs">Inactive</Badge>}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-2xl font-bold text-white">
                ${plan.price_monthly}<span className="text-sm text-gray-400">/mo</span>
              </div>
              <div className="text-sm text-gray-400">
                ${plan.price_yearly}<span className="text-gray-500">/yr</span>
              </div>
              <div className="text-sm text-gray-300">
                {plan.prediction_limit === null || plan.prediction_limit === undefined
                  ? "Unlimited predictions/day"
                  : `${plan.prediction_limit} predictions/day`}
              </div>
              <Button size="sm" variant="outline" className="w-full border-gray-600 text-gray-300 hover:text-white"
                onClick={() => setEditing(plan)}>
                <Edit className="w-3 h-3 mr-1" /> Edit Plan
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {editing && (
        <Dialog open onOpenChange={() => setEditing(null)}>
          <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
            <DialogHeader><DialogTitle>Edit Plan — {editing.display_name}</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-gray-400">Monthly Price ($)</Label>
                  <Input type="number" step="0.01" className="bg-gray-800 border-gray-600 text-white"
                    defaultValue={editing.price_monthly}
                    onChange={e => setEditing(p => p ? { ...p, price_monthly: +e.target.value } : null)} />
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-400">Yearly Price ($)</Label>
                  <Input type="number" step="0.01" className="bg-gray-800 border-gray-600 text-white"
                    defaultValue={editing.price_yearly}
                    onChange={e => setEditing(p => p ? { ...p, price_yearly: +e.target.value } : null)} />
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-gray-400">Daily Prediction Limit (blank = unlimited)</Label>
                <Input type="number" className="bg-gray-800 border-gray-600 text-white"
                  defaultValue={editing.prediction_limit ?? ""}
                  onChange={e => setEditing(p => p ? { ...p, prediction_limit: e.target.value ? +e.target.value : undefined } : null)} />
              </div>
              <div className="flex items-center justify-between py-2">
                <Label className="text-gray-400">Active</Label>
                <Switch defaultChecked={editing.is_active}
                  onCheckedChange={v => setEditing(p => p ? { ...p, is_active: v } : null)} />
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" className="border-gray-600" onClick={() => setEditing(null)}>Cancel</Button>
              <Button className="bg-cyan-500 hover:bg-cyan-400 text-black"
                disabled={updateMutation.isPending}
                onClick={() => updateMutation.mutate({ id: editing.id, body: { price_monthly: editing.price_monthly, price_yearly: editing.price_yearly, prediction_limit: editing.prediction_limit, is_active: editing.is_active } })}>
                Save Plan
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

// ─── Module 7: System Configuration ──────────────────────────────────

function SystemTab() {
  const qc = useQueryClient();
  const { isSuperAdmin } = useAuth();
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});
  const [editingKey, setEditingKey] = useState<{ name: string; label: string; description: string } | null>(null);
  const [newKeyValue, setNewKeyValue] = useState("");
  const [showNewKey, setShowNewKey] = useState(false);

  const { data: flagsData, isLoading } = useQuery<{ flags: Record<string, { value: boolean; description: string }> }>({
    queryKey: ["admin-flags"],
    queryFn: () => apiGet("/api/admin/system/flags"),
  });
  const { data: keysData } = useQuery<{ keys: { name: string; label: string; description: string; configured: boolean; masked: string; required: boolean; group: string; source: "replit_secret" | "database" | "unset" }[] }>({
    queryKey: ["admin-keys"],
    queryFn: () => apiGet("/api/admin/api-keys"),
  });
  const { data: configStatus } = useQuery<{
    services: { key: string; label: string; set: boolean; required: boolean; status: string }[];
    summary: { total: number; ok: number; warnings: number; errors: number; healthy: boolean };
  }>({
    queryKey: ["admin-config-status"],
    queryFn: () => apiGet("/api/admin/config-status"),
    refetchInterval: 30000,
  });

  const flagMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: boolean }) => apiPut("/api/admin/system/flags", { flags: { [key]: value } }),
    onSuccess: () => { toast.success("Flag updated"); qc.invalidateQueries({ queryKey: ["admin-flags"] }); },
    onError: () => toast.error("Update failed"),
  });
  const cacheMutation = useMutation({
    mutationFn: () => apiPost("/api/admin/system/cache/clear", {}),
    onSuccess: () => toast.success("Cache cleared"),
  });
  const backupMutation = useMutation({
    mutationFn: () => apiPost("/api/admin/system/backup", {}),
    onSuccess: (d: any) => toast.success(d.message),
    onError: () => toast.error("Backup failed — super_admin only"),
  });
  const updateKeyMutation = useMutation({
    mutationFn: ({ name, value }: { name: string; value: string }) =>
      apiPost<{ updated: Record<string, string>; errors: Record<string, string>; warnings?: Record<string, string>; message: string }>(
        "/api/admin/api-keys/update",
        { updates: { [name]: value } },
      ),
    onSuccess: (resp, vars) => {
      const errMsg = resp?.errors?.[vars.name];
      if (errMsg) {
        toast.error(`Update failed: ${errMsg}`);
        return;
      }
      toast.success("Key saved — active now and persisted to database");
      qc.invalidateQueries({ queryKey: ["admin-keys"] });
      qc.invalidateQueries({ queryKey: ["admin-config-status"] });
      setEditingKey(null);
      setNewKeyValue("");
    },
    onError: () => toast.error("Failed to update API key"),
  });

  const deleteKeyMutation = useMutation({
    mutationFn: (name: string) => apiDelete(`/api/admin/api-keys/${name}`),
    onSuccess: (_d, name) => {
      toast.success(`${name} removed from database`);
      qc.invalidateQueries({ queryKey: ["admin-keys"] });
      qc.invalidateQueries({ queryKey: ["admin-config-status"] });
    },
    onError: () => toast.error("Failed to remove key from database"),
  });

  // Group keys by their group field
  type KeyEntry = { name: string; label: string; description: string; configured: boolean; masked: string; required: boolean; group: string; source: "replit_secret" | "database" | "unset" };
  const keysByGroup = (keysData?.keys ?? []).reduce<Record<string, KeyEntry[]>>((acc, k) => {
    const g = k.group ?? "Other";
    if (!acc[g]) acc[g] = [];
    acc[g].push(k);
    return acc;
  }, {});
  const groupOrder = ["Sports Data", "AI Providers", "Payments", "KYC / Identity", "Blockchain", "Infrastructure", "Messaging", "AI Feeds", "Security", "Other"];
  const sortedGroups = groupOrder.filter(g => keysByGroup[g]);

  return (
    <div className="space-y-6">
      {/* Config Health Strip */}
      {configStatus && (
        <Card className={`border ${configStatus.summary.errors > 0 ? "border-red-500/40 bg-red-500/5" : configStatus.summary.warnings > 0 ? "border-amber-500/40 bg-amber-500/5" : "border-emerald-500/40 bg-emerald-500/5"}`}>
          <CardHeader className="pb-3">
            <CardTitle className="text-white flex items-center gap-2 text-sm">
              {configStatus.summary.errors > 0
                ? <XCircle className="w-4 h-4 text-red-400" />
                : configStatus.summary.warnings > 0
                ? <AlertTriangle className="w-4 h-4 text-amber-400" />
                : <CheckCircle className="w-4 h-4 text-emerald-400" />}
              Configuration Health
              <span className="ml-auto text-xs font-normal text-gray-400">
                {configStatus.summary.ok}/{configStatus.summary.total} services configured
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {configStatus.services.map(s => (
                <div key={s.key} className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs border ${
                  s.status === "ok" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300" :
                  s.status === "error" ? "bg-red-500/10 border-red-500/20 text-red-300" :
                  "bg-amber-500/10 border-amber-500/20 text-amber-300"
                }`}>
                  {s.status === "ok"
                    ? <CheckCircle className="w-3 h-3" />
                    : s.status === "error"
                    ? <XCircle className="w-3 h-3" />
                    : <AlertTriangle className="w-3 h-3" />}
                  {s.label}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Feature Flags */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-purple-400" /> Feature Flags
          </CardTitle>
          <CardDescription className="text-gray-400">Toggle platform features without code changes</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-6"><div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(flagsData?.flags ?? {}).map(([key, val]) => {
                const isOn = typeof val === "object" ? val.value : val;
                const desc = typeof val === "object" ? val.description : key;
                return (
                  <div key={key} className="flex items-center justify-between p-3 rounded-lg border border-gray-800 bg-gray-900/50 hover:border-gray-700 transition-colors">
                    <div className="min-w-0 flex-1 mr-4">
                      <div className="text-white font-mono text-sm truncate" title={key}>{key}</div>
                      <div className="text-[10px] text-gray-500 line-clamp-1 mt-0.5" title={desc}>{desc}</div>
                    </div>
                    <Switch checked={isOn} onCheckedChange={v => flagMutation.mutate({ key, value: v })} className="shrink-0" />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* API Keys — Grouped */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Key className="w-5 h-5 text-amber-400" /> API Keys & Secrets
          </CardTitle>
          <CardDescription className="text-gray-400">
            Set keys here to persist them encrypted in the database — they survive restarts automatically.
            Keys already in <span className="text-cyan-400 font-medium">Replit Secrets</span> always take priority and are shown with a cyan badge.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {sortedGroups.map(group => (
            <div key={group} className="space-y-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500 mb-2 px-1 flex items-center gap-2">
                <div className="h-px flex-1 bg-gray-800" />
                {group}
                <div className="h-px flex-1 bg-gray-800" />
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {keysByGroup[group].map(k => (
                  <div key={k.name} className="flex flex-col sm:flex-row sm:items-center justify-between py-3 px-4 rounded-xl border border-gray-800 bg-gray-900/40 hover:border-gray-700 transition-all gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <div className="text-white text-sm font-bold tracking-tight">{k.label}</div>
                        {k.required && (
                          <span className="text-[9px] uppercase font-bold bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded leading-none">
                            Required
                          </span>
                        )}
                        {k.source === "replit_secret" && (
                          <span className="text-[9px] uppercase font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 px-1.5 py-0.5 rounded flex items-center gap-1 leading-none">
                            <Shield className="w-2.5 h-2.5" /> Replit
                          </span>
                        )}
                        {k.source === "database" && (
                          <span className="text-[9px] uppercase font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded flex items-center gap-1 leading-none">
                            <Database className="w-2.5 h-2.5" /> DB
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-gray-500 line-clamp-1 italic" title={k.description}>
                        {k.description}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                      <div className="flex flex-col items-end mr-1">
                        <span className="font-mono text-[10px] text-gray-400">
                          {showKey[k.name] ? (k.masked || "Not set") : (k.configured ? "••••••••" : "Not set")}
                        </span>
                      </div>

                      <div className="flex items-center gap-1 bg-gray-950/50 rounded-lg p-1 border border-gray-800">
                        {k.configured && (
                          <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-gray-500 hover:text-white"
                            onClick={() => setShowKey(s => ({ ...s, [k.name]: !s[k.name] }))}>
                            {showKey[k.name] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                          </Button>
                        )}

                        {k.source === "database" && (
                          <Button size="sm" variant="ghost"
                            className="h-7 w-7 p-0 text-gray-500 hover:text-red-400"
                            title="Remove from database"
                            onClick={() => deleteKeyMutation.mutate(k.name)}>
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        )}

                        <Button size="sm" variant="outline"
                          className="h-7 px-3 border-amber-500/30 text-amber-400 hover:bg-amber-500/10 hover:border-amber-400 text-[10px] font-bold uppercase tracking-wider"
                          onClick={() => { setEditingKey(k); setNewKeyValue(""); setShowNewKey(false); }}>
                          {k.configured ? "Update" : "Set"}
                        </Button>
                      </div>

                      {k.configured
                        ? <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                        : <XCircle className="w-4 h-4 text-gray-700 shrink-0" />}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* API Key Edit Dialog */}
      {editingKey && (
        <Dialog open onOpenChange={() => setEditingKey(null)}>
          <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Key className="w-5 h-5 text-amber-400" /> Update {editingKey.label}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-sm text-gray-400">{editingKey.description}</p>
              <div className="space-y-2">
                <Label className="text-gray-300">New Value</Label>
                <div className="relative">
                  <Input
                    type={showNewKey ? "text" : "password"}
                    placeholder={`Enter new value for ${editingKey.name}`}
                    value={newKeyValue}
                    onChange={e => setNewKeyValue(e.target.value)}
                    className="bg-gray-800 border-gray-600 text-white pr-10 font-mono"
                    autoFocus
                  />
                  <Button size="sm" variant="ghost"
                    className="absolute right-1 top-1 h-7 w-7 p-0 text-gray-500 hover:text-white"
                    onClick={() => setShowNewKey(v => !v)}>
                    {showNewKey ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                  </Button>
                </div>
                <p className="text-xs text-gray-500">
                  Variable name: <span className="font-mono text-amber-400">{editingKey.name}</span>
                </p>
              </div>
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded p-3 text-xs text-emerald-300 space-y-1">
                <div className="flex items-center gap-1.5 font-medium"><Database className="w-3 h-3" /> Saved to database — survives restarts</div>
                <div className="text-emerald-400/80">The key is encrypted with AES-256 and loaded automatically on every server start. No need to also add it to Replit Secrets (though Replit Secrets always take priority if h exist).</div>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" className="border-gray-600 text-gray-300"
                onClick={() => setEditingKey(null)}>Cancel</Button>
              <Button
                className="bg-amber-500 hover:bg-amber-400 text-black font-semibold"
                disabled={!newKeyValue.trim() || updateKeyMutation.isPending}
                onClick={() => updateKeyMutation.mutate({ name: editingKey.name, value: newKeyValue.trim() })}>
                <Save className="w-4 h-4 mr-2" />
                {updateKeyMutation.isPending ? "Saving…" : "Save Key"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Football-Data Integration */}
      <FootballDataCard />

      {/* CSV Fixture Upload */}
      <CSVUploadCard />

      {/* System Actions */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Server className="w-5 h-5 text-cyan-400" /> System Actions
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button variant="outline" className="border-purple-500/50 text-purple-400 hover:border-purple-400"
            onClick={() => cacheMutation.mutate()}>
            <Zap className="w-4 h-4 mr-2" /> Clear Cache
          </Button>
          {isSuperAdmin && (
            <Button variant="outline" className="border-cyan-500/50 text-cyan-400 hover:border-cyan-400"
              onClick={() => backupMutation.mutate()}>
              <Database className="w-4 h-4 mr-2" /> Create Backup
            </Button>
          )}
        </CardContent>
      </Card>

      {/* ML Calibration */}
      <MLCalibrationCard />

      {/* Manual Settlement */}
      <ManualSettlementCard />

      {/* Global Accumulator */}
      <GlobalAccumulatorCard />

      {/* AI Feed Consensus */}
      <AIFeedConsensusCard />

      {/* Fixture Ecosystem Health */}
      <FixtureHealthCard />
    </div>
  );
}

// ─── Fixture Ecosystem Health Card ───────────────────────────────────
interface FixtureHealthCategory {
  count: number;
  label: string;
  severity: "ok" | "warning" | "error";
  sample: Record<string, unknown>[];
}

interface FixtureHealthData {
  total_fixtures: number;
  health_pct: number;
  issues: number;
  categories: Record<string, FixtureHealthCategory>;
  checked_at: string;
}

function FixtureHealthCard() {
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading, refetch, isFetching } = useQuery<FixtureHealthData>({
    queryKey: ["admin-fixture-health"],
    queryFn: () => apiGet("/api/admin/fixture-health"),
    staleTime: 60_000,
  });

  const severityColor = (s: string) =>
    s === "error" ? "text-red-500" : s === "warning" ? "text-amber-500" : "text-emerald-500";
  const severityBg = (s: string) =>
    s === "error" ? "bg-red-500/10 border-red-500/20" : s === "warning" ? "bg-amber-500/10 border-amber-500/20" : "bg-emerald-500/10 border-emerald-500/20";

  const healthColor =
    !data ? "text-muted-foreground"
    : data.health_pct >= 95 ? "text-emerald-500"
    : data.health_pct >= 80 ? "text-amber-500"
    : "text-red-500";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Stethoscope className="w-4 h-4 text-primary" />
            <CardTitle className="text-sm font-mono">Fixture Ecosystem Health</CardTitle>
          </div>
          <div className="flex items-center gap-3">
            {data && (
              <span className={`text-xl font-mono font-bold ${healthColor}`}>
                {data.health_pct}%
              </span>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => refetch()}
              disabled={isFetching}
              className="h-7 px-2 font-mono text-xs"
            >
              <RefreshCw className={`w-3 h-3 mr-1 ${isFetching ? "animate-spin" : ""}`} />
              Scan
            </Button>
          </div>
        </div>
        <CardDescription className="font-mono text-xs">
          Scans all {data?.total_fixtures ?? "…"} fixtures for data-quality issues
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-2">
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-10 rounded bg-muted animate-pulse" />)}
          </div>
        ) : !data ? (
          <p className="text-xs font-mono text-muted-foreground">Click Scan to run health check.</p>
        ) : data.issues === 0 ? (
          <div className="flex items-center gap-2 py-3 text-emerald-500 font-mono text-sm">
            <HeartPulse className="w-4 h-4" />
            All fixtures healthy — no issues detected.
          </div>
        ) : (
          Object.entries(data.categories).map(([key, cat]) => (
            <div key={key} className={`rounded-md border p-3 ${severityBg(cat.severity)}`}>
              <button
                className="w-full flex items-center justify-between gap-2"
                onClick={() => setExpanded(expanded === key ? null : key)}
              >
                <div className="flex items-center gap-2">
                  {cat.severity === "ok"
                    ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    : cat.severity === "warning"
                    ? <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    : <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                  }
                  <span className="text-xs font-mono font-medium">{cat.label}</span>
                </div>
                <span className={`text-xs font-mono font-bold shrink-0 ${severityColor(cat.severity)}`}>
                  {cat.count} {cat.count === 1 ? "issue" : "issues"}
                  {cat.sample.length > 0 && (
                    <ChevronRight className={`inline w-3 h-3 ml-1 transition-transform ${expanded === key ? "rotate-90" : ""}`} />
                  )}
                </span>
              </button>

              {expanded === key && cat.sample.length > 0 && (
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-[10px] font-mono border-separate border-spacing-y-0.5">
                    <tbody>
                      {cat.sample.map((row, i) => (
                        <tr key={i} className="bg-background/60 rounded">
                          {Object.entries(row).map(([k, v]) => (
                            <td key={k} className="px-2 py-1 align-top first:text-muted-foreground">
                              {String(v ?? "—")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))
        )}

        {data && (
          <p className="text-[10px] font-mono text-muted-foreground/50 pt-1">
            Last scanned: {new Date(data.checked_at).toLocaleString()}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Football-Data.org Integration Card ──────────────────────────────

function FootballDataCard() {
  const qc = useQueryClient();
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);

  const testMutation = useMutation({
    mutationFn: () => apiPost<{ status: string; message: string }>(
      "/api/admin/data-sources/test/football_data", {}),
    onSuccess: (r) => {
      setTestResult(r);
      if (r.status === "ok") toast.success(r.message);
      else toast.error(r.message);
    },
    onError: (e: any) => {
      const msg = e?.message || "Connection test failed";
      setTestResult({ status: "down", message: msg });
      toast.error(msg);
    },
  });

  const fetchMutation = useMutation({
    mutationFn: () => apiPost<{ stored: number; skipped_existing?: number; message?: string }>(
      "/api/admin/matches/fetch-fixtures?count=100&days=14", {}),
    onSuccess: (d) => {
      toast.success(`Fetched ${d.stored ?? 0} new fixtures (${d.skipped_existing ?? 0} duplicates skipped)`);
      qc.invalidateQueries({ queryKey: ["matches-recent"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: () => toast.error("Fixture fetch failed — check the Football-Data.org key first"),
  });

  const settleMutation = useMutation({
    mutationFn: () => apiPost<{ settled: number; already_settled: number; created_new?: number; message?: string }>(
      "/api/admin/settle-results?days_back=7", {}),
    onSuccess: (d) => {
      toast.success(`Settled ${d.settled ?? 0} match(es), ${d.already_settled ?? 0} already done, ${d.created_new ?? 0} new records created`);
      qc.invalidateQueries({ queryKey: ["matches-recent"] });
    },
    onError: () => toast.error("Settle pass failed — check the API key"),
  });

  const backfillMutation = useMutation({
    mutationFn: () => apiPost<{ settled_real: number; simulated_local: number; skipped_real_no_api: number }>(
      "/api/admin/matches/backfill-ft-results?settle_real=true&simulate_local=true&days_back=14", {}),
    onSuccess: (d) => {
      toast.success(`Backfill done — ${d.settled_real} from API + ${d.simulated_local} simulated, ${d.skipped_real_no_api} real matches skipped`);
      qc.invalidateQueries({ queryKey: ["matches-recent"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: () => toast.error("Backfill failed"),
  });

  const statusColor =
    testResult?.status === "ok" ? "text-emerald-400" :
    testResult?.status === "no_key" ? "text-amber-400" :
    testResult ? "text-red-400" : "text-gray-500";

  return (
    <Card className="bg-gray-900 border-gray-700">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Globe className="w-5 h-5 text-emerald-400" /> Football-Data.org Integration
        </CardTitle>
        <CardDescription className="text-gray-400">
          Update <span className="font-mono text-amber-400">FOOTBALL_DATA_API_KEY</span> above first,
          then test the connection and pull fixtures or finished-match results.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" className="border-emerald-500/50 text-emerald-400 hover:border-emerald-400"
            disabled={testMutation.isPending}
            onClick={() => testMutation.mutate()}>
            <CheckCircle className="w-4 h-4 mr-2" />
            {testMutation.isPending ? "Testing…" : "Test Connection"}
          </Button>
          <Button variant="outline" className="border-cyan-500/50 text-cyan-400 hover:border-cyan-400"
            disabled={fetchMutation.isPending}
            onClick={() => fetchMutation.mutate()}>
            <Download className="w-4 h-4 mr-2" />
            {fetchMutation.isPending ? "Fetching…" : "Fetch Upcoming Fixtures"}
          </Button>
          <Button variant="outline" className="border-purple-500/50 text-purple-400 hover:border-purple-400"
            disabled={settleMutation.isPending}
            onClick={() => settleMutation.mutate()}>
            <RefreshCw className="w-4 h-4 mr-2" />
            {settleMutation.isPending ? "Syncing…" : "Sync FT Results"}
          </Button>
          <Button variant="outline" className="border-amber-500/50 text-amber-400 hover:border-amber-400"
            disabled={backfillMutation.isPending}
            onClick={() => backfillMutation.mutate()}>
            <Activity className="w-4 h-4 mr-2" />
            {backfillMutation.isPending ? "Working…" : "Backfill Past Results"}
          </Button>
        </div>
        {testResult && (
          <div className={`text-xs px-3 py-2 rounded border border-gray-800 bg-gray-950 ${statusColor}`}>
            <span className="font-semibold uppercase mr-2">{testResult.status}</span>
            {testResult.message}
          </div>
        )}
        <div className="text-xs text-gray-500 space-y-1">
          <div>• <span className="text-cyan-400">Fetch Upcoming Fixtures</span> — pulls scheduled matches for the next 14 days, dedup'd against existing rows.</div>
          <div>• <span className="text-purple-400">Sync FT Results</span> — settles predictions against finished matches from the API (last 7 days).</div>
          <div>• <span className="text-amber-400">Backfill Past Results</span> — runs the API settle, then simulates final scores for any past local-only/seed matches that have no provider counterpart.</div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── CSV Fixture Upload Card ──────────────────────────────────────────

interface CsvUploadRow {
  row: number;
  home_team: string;
  away_team: string;
  league?: string;
  kickoff?: string;
  match_id?: number;
  action?: string;
  status: "ok" | "duplicate" | "warning" | "error";
  message?: string;
  home_prob?: number;
  draw_prob?: number;
  away_prob?: number;
  best_side?: string;
  edge?: number;
  home_odds?: number;
  draw_odds?: number;
  away_odds?: number;
}

interface CsvUploadResult {
  imported: number;
  duplicates: number;
  warnings: string[];
  rows: CsvUploadRow[];
  errors?: number;
}

function CSVUploadCard() {
  const [file, setFile]         = useState<File | null>(null);
  const [result, setResult]     = useState<CsvUploadResult | null>(null);
  const [showFormat, setShowFormat] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: async (f: File) => {
      const form = new FormData();
      form.append("file", f);
      const token = localStorage.getItem("vit_token") || "";
      const resp = await fetch("/api/admin/upload/csv", {
        method: "POST",
        body: form,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail ?? "Upload failed");
      }
      return resp.json() as Promise<CsvUploadResult>;
    },
    onSuccess: (d) => {
      setResult(d);
      const n = d.imported ?? (d as any).created ?? 0;
      const sk = d.duplicates ?? 0;
      toast.success(`CSV uploaded — ${n} imported, ${sk} duplicates skipped`);
      if (d.warnings?.length) {
        // Show first 3 warnings as toasts; rest are visible in the table
        d.warnings.slice(0, 3).forEach(w => toast.warning(w, { duration: 6000 }));
      }
    },
    onError: (e: any) => toast.error(e?.message || "CSV upload failed"),
  });

  const STATUS_BADGE: Record<string, string> = {
    ok:        "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    duplicate: "bg-gray-500/10 text-gray-400 border-gray-500/30",
    warning:   "bg-amber-500/10 text-amber-400 border-amber-500/30",
    error:     "bg-red-500/10 text-red-400 border-red-500/30",
  };

  const SIDE_LABEL: Record<string, string> = { home: "H", draw: "D", away: "A" };

  const imported  = result ? (result.imported ?? (result as any).created ?? 0) : 0;
  const skipped   = result?.duplicates ?? 0;
  const errCount  = result?.errors ?? 0;
  const warnCount = result?.warnings?.length ?? 0;
  const rows      = result?.rows ?? (result as any)?.results ?? [];

  return (
    <Card className="bg-gray-900 border-gray-700">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <FileUp className="w-5 h-5 text-purple-400" /> CSV Fixture Upload
        </CardTitle>
        <CardDescription className="text-gray-400">
          Bulk-import fixtures from a CSV file — runs ML predictions immediately on import.
          Supports h standard format and shorthand <span className="font-mono text-purple-300">#,date,time,home,away,league,H,D,A</span>.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">

        {/* Upload controls */}
        <div className="flex flex-wrap gap-3 items-center">
          <label className="cursor-pointer flex items-center gap-2 px-4 py-2 rounded border border-purple-500/40 text-purple-400 hover:border-purple-400 transition-colors text-sm font-mono">
            <Upload className="w-4 h-4" />
            {file ? file.name : "Choose CSV file…"}
            <input
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={e => { setFile(e.target.files?.[0] ?? null); setResult(null); }}
            />
          </label>
          <Button
            className="bg-purple-600 hover:bg-purple-500 text-white"
            disabled={!file || uploadMutation.isPending}
            onClick={() => file && uploadMutation.mutate(file)}
          >
            {uploadMutation.isPending ? "Uploading…" : "Upload & Predict"}
          </Button>
          <button
            className="text-xs font-mono text-gray-500 hover:text-gray-300 underline underline-offset-2"
            onClick={() => setShowFormat(f => !f)}
          >
            {showFormat ? "Hide format guide" : "Show format guide"}
          </button>
        </div>

        {/* Summary strip */}
        {result && (
          <div className="flex gap-4 text-xs font-mono flex-wrap">
            <span className="text-emerald-400 font-bold">{imported} imported</span>
            <span className="text-gray-400">{skipped} duplicates</span>
            {warnCount > 0 && <span className="text-amber-400">{warnCount} warnings</span>}
            {errCount > 0  && <span className="text-red-400">{errCount} errors</span>}
          </div>
        )}

        {/* Format guide */}
        {showFormat && (
          <div className="p-3 rounded bg-gray-800/60 border border-gray-700 space-y-3">
            <p className="text-[10px] font-mono text-gray-500 uppercase flex items-center gap-1">
              <Info className="w-3 h-3" /> Accepted CSV formats
            </p>
            <div>
              <p className="text-[10px] font-mono text-gray-500 mb-1">Standard format</p>
              <pre className="text-[11px] font-mono text-gray-400 whitespace-pre-wrap">{`home_team,away_team,kickoff_time,league,home_odds,draw_odds,away_odds
Arsenal,Chelsea,2026-05-10 15:00,premier_league,2.10,3.40,3.60`}</pre>
            </div>
            <div>
              <p className="text-[10px] font-mono text-gray-500 mb-1">Shorthand format (e.g. bookmaker export)</p>
              <pre className="text-[11px] font-mono text-gray-400 whitespace-pre-wrap">{`#,date,time,home,away,league,H,D,A
1,10 May,15:00,Arsenal,Chelsea,England - Premier League,2.10,3.40,3.60`}</pre>
            </div>
            <p className="text-[10px] font-mono text-gray-500">
              Columns <span className="text-purple-300">home_odds / H</span>, <span className="text-purple-300">draw_odds / D</span>, <span className="text-purple-300">away_odds / A</span>, <span className="text-purple-300">kickoff_time</span> and <span className="text-purple-300">league</span> are optional — defaults are applied if missing.
            </p>
          </div>
        )}

        {/* Warnings list */}
        {result && result.warnings && result.warnings.length > 0 && (
          <div className="rounded border border-amber-500/20 bg-amber-500/5 p-2 space-y-0.5 max-h-28 overflow-y-auto">
            {result.warnings.map((w, i) => (
              <p key={i} className="text-[10px] font-mono text-amber-400">{w}</p>
            ))}
          </div>
        )}

        {/* Results table */}
        {rows.length > 0 && (
          <div className="overflow-x-auto rounded border border-gray-700">
            <table className="w-full text-xs">
              <thead className="border-b border-gray-700 bg-gray-800/60 sticky top-0">
                <tr className="text-gray-400 font-mono uppercase text-[10px]">
                  <th className="text-left p-2 pl-3">#</th>
                  <th className="text-left p-2">Match</th>
                  <th className="text-left p-2 hidden sm:table-cell">League</th>
                  <th className="text-center p-2 hidden md:table-cell">Kickoff</th>
                  <th className="text-center p-2">ID</th>
                  <th className="text-center p-2">Status</th>
                  <th className="text-center p-2 hidden lg:table-cell">H / D / A probs</th>
                  <th className="text-center p-2 hidden lg:table-cell">Best Bet</th>
                  <th className="text-center p-2 hidden lg:table-cell">Edge</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r: CsvUploadRow, idx: number) => (
                  <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/40">
                    <td className="p-2 pl-3 text-gray-500 font-mono">{r.row ?? idx + 1}</td>
                    <td className="p-2 text-gray-200 font-mono whitespace-nowrap">
                      {r.home_team} <span className="text-gray-500">vs</span> {r.away_team}
                    </td>
                    <td className="p-2 text-gray-400 hidden sm:table-cell text-[10px] max-w-[140px] truncate" title={r.league}>
                      {r.league || "—"}
                    </td>
                    <td className="p-2 text-center text-gray-500 hidden md:table-cell font-mono text-[10px] whitespace-nowrap">
                      {r.kickoff ? (() => { try { return new Date(r.kickoff).toLocaleString(undefined, {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}); } catch { return r.kickoff.slice(0,16); } })() : "—"}
                    </td>
                    <td className="p-2 text-center">
                      {r.match_id ? (
                        <a href={`/matches/${r.match_id}`} target="_blank" rel="noreferrer"
                          className="font-mono text-cyan-400 hover:underline">#{r.match_id}</a>
                      ) : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="p-2 text-center whitespace-nowrap">
                      <span className={`border rounded px-1.5 py-0.5 font-mono text-[10px] ${STATUS_BADGE[r.status] ?? STATUS_BADGE.warning}`}>
                        {r.status}
                      </span>
                      {r.message && (
                        <span className="ml-1.5 text-[10px] text-gray-500 max-w-[120px] truncate inline-block align-bottom" title={r.message}>{r.message}</span>
                      )}
                    </td>
                    <td className="p-2 text-center hidden lg:table-cell font-mono text-[10px] whitespace-nowrap">
                      {r.home_prob != null ? (
                        <span>
                          <span className="text-primary">{(r.home_prob * 100).toFixed(0)}%</span>
                          <span className="text-gray-600"> / </span>
                          <span className="text-gray-300">{(r.draw_prob! * 100).toFixed(0)}%</span>
                          <span className="text-gray-600"> / </span>
                          <span className="text-primary">{(r.away_prob! * 100).toFixed(0)}%</span>
                        </span>
                      ) : "—"}
                    </td>
                    <td className="p-2 text-center hidden lg:table-cell">
                      {r.best_side ? (
                        <span className={`border rounded px-1.5 py-0.5 font-mono text-[10px] ${
                          r.best_side === "home" ? "border-primary/40 text-primary" :
                          r.best_side === "away" ? "border-orange-400/40 text-orange-400" :
                          "border-yellow-400/40 text-yellow-400"
                        }`}>
                          {SIDE_LABEL[r.best_side] ?? r.best_side}
                          {r.home_odds && r.draw_odds && r.away_odds ? (
                            <span className="text-gray-500 ml-1">
                              @{r.best_side === "home" ? r.home_odds : r.best_side === "draw" ? r.draw_odds : r.away_odds}
                            </span>
                          ) : null}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="p-2 text-center hidden lg:table-cell font-mono text-[10px]">
                      {r.edge != null ? (
                        <span className={r.edge > 0 ? "text-emerald-400" : "text-red-400"}>
                          {r.edge > 0 ? "+" : ""}{(r.edge * 100).toFixed(2)}%
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}


// ─── ML Calibration Card ─────────────────────────────────────────────

function MLCalibrationCard() {
  const qc = useQueryClient();
  const fitMutation = useAdminCalibrationFit();
  const reloadMutation = useAdminCalibrationReload();

  return (
    <Card className="bg-gray-900 border-gray-700">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Activity className="w-5 h-5 text-green-400" /> ML Calibration
        </CardTitle>
        <CardDescription className="text-gray-400">
          Fit and reload probability calibrators for improved prediction accuracy
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-3">
        <Button
          variant="outline"
          className="border-green-500/50 text-green-400 hover:border-green-400"
          disabled={fitMutation.isPending}
          onClick={() => fitMutation.mutate(undefined, {
            onSuccess: () => toast.success("Calibration fit completed"),
            onError: () => toast.error("Calibration fit failed")
          })}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${fitMutation.isPending ? 'animate-spin' : ''}`} />
          {fitMutation.isPending ? "Fitting…" : "Fit Calibrators"}
        </Button>
        <Button
          variant="outline"
          className="border-blue-500/50 text-blue-400 hover:border-blue-400"
          disabled={reloadMutation.isPending}
          onClick={() => reloadMutation.mutate(undefined, {
            onSuccess: () => toast.success("Calibrators reloaded"),
            onError: () => toast.error("Reload failed")
          })}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${reloadMutation.isPending ? 'animate-spin' : ''}`} />
          {reloadMutation.isPending ? "Reloading…" : "Reload Calibrators"}
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── Manual Settlement Card ──────────────────────────────────────────

function ManualSettlementCard() {
  const qc = useQueryClient();
  const settleMutation = useAdminSettleResults();
  const backfillMutation = useAdminBackfillFtResults();
  const [confirmDialog, setConfirmDialog] = useState<{ type: 'settle' | 'backfill'; open: boolean }>({ type: 'settle', open: false });

  return (
    <>
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-orange-400" /> Manual Settlement
          </CardTitle>
          <CardDescription className="text-gray-400">
            Manually trigger result settlement and backfill operations
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button
            variant="outline"
            className="border-orange-500/50 text-orange-400 hover:border-orange-400"
            onClick={() => setConfirmDialog({ type: 'settle', open: true })}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Settle Results
          </Button>
          <Button
            variant="outline"
            className="border-red-500/50 text-red-400 hover:border-red-400"
            onClick={() => setConfirmDialog({ type: 'backfill', open: true })}
          >
            <Activity className="w-4 h-4 mr-2" />
            Backfill FT Results
          </Button>
        </CardContent>
      </Card>

      <Dialog open={confirmDialog.open} onOpenChange={(open) => setConfirmDialog(prev => ({ ...prev, open }))}>
        <DialogContent className="bg-gray-900 border-gray-700">
          <DialogHeader>
            <DialogTitle className="text-white">
              Confirm {confirmDialog.type === 'settle' ? 'Result Settlement' : 'Backfill Operation'}
            </DialogTitle>
          </DialogHeader>
          <div className="text-gray-300">
            {confirmDialog.type === 'settle'
              ? "This will settle all unsettled predictions against completed matches. Continue?"
              : "This will backfill full-time results for past matches. This operation may take time. Continue?"
            }
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDialog({ type: 'settle', open: false })}>
              Cancel
            </Button>
            <Button
              className="bg-orange-500 hover:bg-orange-400 text-black"
              disabled={settleMutation.isPending || backfillMutation.isPending}
              onClick={() => {
                const mutation = confirmDialog.type === 'settle' ? settleMutation : backfillMutation;
                mutation.mutate(undefined, {
                  onSuccess: (data) => {
                    toast.success(`${confirmDialog.type === 'settle' ? 'Settlement' : 'Backfill'} completed`);
                    setConfirmDialog({ type: 'settle', open: false });
                    qc.invalidateQueries({ queryKey: ['matches-recent'] });
                  },
                  onError: () => toast.error(`${confirmDialog.type === 'settle' ? 'Settlement' : 'Backfill'} failed`)
                });
              }}
            >
              {settleMutation.isPending || backfillMutation.isPending ? 'Processing…' : 'Confirm'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ─── Global Accumulator Card ─────────────────────────────────────────

function GlobalAccumulatorCard() {
  const [accumulatorId, setAccumulatorId] = useState("");
  const [stakeAmount, setStakeAmount] = useState("");
  const [message, setMessage] = useState("");

  const placeBetMutation = useAdminAccumulatorPlaceBet();
  const sendMutation = useAdminAccumulatorSend();

  return (
    <Card className="bg-gray-900 border-gray-700">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Package className="w-5 h-5 text-purple-400" /> Global Accumulator
        </CardTitle>
        <CardDescription className="text-gray-400">
          Register positions on and broadcast accumulator signals
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label className="text-gray-300">Accumulator ID</Label>
            <Input
              placeholder="Enter accumulator ID"
              value={accumulatorId}
              onChange={(e) => setAccumulatorId(e.target.value)}
              className="bg-gray-800 border-gray-600 text-white"
            />
          </div>
          <div>
            <Label className="text-gray-300">Stake Amount</Label>
            <Input
              type="number"
              placeholder="0.00"
              value={stakeAmount}
              onChange={(e) => setStakeAmount(e.target.value)}
              className="bg-gray-800 border-gray-600 text-white"
            />
          </div>
        </div>
        <div>
          <Label className="text-gray-300">Broadcast Message (Optional)</Label>
          <Input
            placeholder="Custom message for broadcast"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="bg-gray-800 border-gray-600 text-white"
          />
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            className="border-purple-500/50 text-purple-400 hover:border-purple-400"
            disabled={placeBetMutation.isPending || !accumulatorId || !stakeAmount}
            onClick={() => placeBetMutation.mutate(
              { accumulator_id: accumulatorId, stake_amount: parseFloat(stakeAmount) },
              {
                onSuccess: () => {
                  toast.success("Signal registered successfully");
                  setAccumulatorId("");
                  setStakeAmount("");
                },
                onError: () => toast.error("Signal submission failed")
              }
            )}
          >
            <Coins className="w-4 h-4 mr-2" />
            {placeBetMutation.isPending ? "Placing…" : "Place Bet"}
          </Button>
          <Button
            variant="outline"
            className="border-blue-500/50 text-blue-400 hover:border-blue-400"
            disabled={sendMutation.isPending || !accumulatorId}
            onClick={() => sendMutation.mutate(
              { accumulator_id: accumulatorId, message: message || undefined },
              {
                onSuccess: () => {
                  toast.success("Accumulator broadcast sent");
                  setMessage("");
                },
                onError: () => toast.error("Failed to send broadcast")
              }
            )}
          >
            <Send className="w-4 h-4 mr-2" />
            {sendMutation.isPending ? "Sending…" : "Broadcast"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── AI Feed Consensus Card ──────────────────────────────────────────

function AIFeedConsensusCard() {
  const [homeTeam, setHomeTeam] = useState("");
  const [awayTeam, setAwayTeam] = useState("");
  const [league, setLeague] = useState("");
  const [marketOdds, setMarketOdds] = useState("");

  const consensusMutation = useAiFeedConsensus();

  const handleConsensus = () => {
    let odds: Record<string, number> = {};
    if (marketOdds.trim()) {
      try {
        odds = JSON.parse(marketOdds);
      } catch {
        toast.error("Market Odds must be valid JSON (e.g. {\"home\": 2.1, \"draw\": 3.2, \"away\": 3.5})");
        return;
      }
    }
    consensusMutation.mutate(
      {
        home_team: homeTeam,
        away_team: awayTeam,
        league: league,
        market_odds: odds
      },
      {
        onSuccess: (data) => {
          toast.success("Consensus pushed successfully");
          setHomeTeam("");
          setAwayTeam("");
          setLeague("");
          setMarketOdds("");
        },
        onError: () => toast.error("Failed to push consensus")
      }
    );
  };

  return (
    <Card className="bg-gray-900 border-gray-700">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-400" /> AI Feed Consensus
        </CardTitle>
        <CardDescription className="text-gray-400">
          Manually push AI consensus predictions
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label className="text-gray-300">Home Team</Label>
            <Input
              placeholder="Home team name"
              value={homeTeam}
              onChange={(e) => setHomeTeam(e.target.value)}
              className="bg-gray-800 border-gray-600 text-white"
            />
          </div>
          <div>
            <Label className="text-gray-300">Away Team</Label>
            <Input
              placeholder="Away team name"
              value={awayTeam}
              onChange={(e) => setAwayTeam(e.target.value)}
              className="bg-gray-800 border-gray-600 text-white"
            />
          </div>
          <div>
            <Label className="text-gray-300">League</Label>
            <Input
              placeholder="League name"
              value={league}
              onChange={(e) => setLeague(e.target.value)}
              className="bg-gray-800 border-gray-600 text-white"
            />
          </div>
        </div>
        <div>
          <Label className="text-gray-300">Market Odds (JSON)</Label>
          <Input
            placeholder='{"home": 2.1, "draw": 3.2, "away": 3.5}'
            value={marketOdds}
            onChange={(e) => setMarketOdds(e.target.value)}
            className="bg-gray-800 border-gray-600 text-white"
          />
        </div>
        <Button
          variant="outline"
          className="border-yellow-500/50 text-yellow-400 hover:border-yellow-400"
          disabled={consensusMutation.isPending || !homeTeam || !awayTeam || !league}
          onClick={handleConsensus}
        >
          <Zap className="w-4 h-4 mr-2" />
          {consensusMutation.isPending ? "Pushing…" : "Push Consensus"}
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── Module 8: User Management ───────────────────────────────────────

function UsersTab() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [editForm, setEditForm] = useState<Partial<AdminUser>>({});

  const { data, isLoading, isError } = useQuery<{ users: AdminUser[]; total: number }>({
    queryKey: ["admin-users", search],
    queryFn: () => apiGet(`/api/admin/users?limit=100${search ? `&search=${encodeURIComponent(search)}` : ""}`),
    refetchInterval: 30000,
  });

  const banMutation = useMutation({
    mutationFn: ({ id, ban }: { id: number; ban: boolean }) =>
      apiPost(`/api/admin/users/${id}/ban`, { banned: ban, reason: ban ? "Banned by admin" : "Unbanned by admin" }),
    onSuccess: (_, v) => { toast.success(v.ban ? "User banned" : "User unbanned"); qc.invalidateQueries({ queryKey: ["admin-users"] }); },
    onError: () => toast.error("Action failed"),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<AdminUser> }) => apiPut(`/api/admin/users/${id}`, body),
    onSuccess: () => { toast.success("User updated"); qc.invalidateQueries({ queryKey: ["admin-users"] }); setEditingUser(null); },
    onError: () => toast.error("Update failed"),
  });

  const tierColors: Record<string, string> = {
    free: "text-zinc-400", viewer: "text-zinc-400", analyst: "text-blue-400",
    pro: "text-emerald-400", elite: "text-emerald-400",
  };

  return (
    <div className="space-y-4">
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-cyan-400" /> User Management
              <Badge className="ml-2 bg-cyan-500/20 text-cyan-400 border-cyan-500/30">{data?.total ?? 0} users</Badge>
            </CardTitle>
            <div className="relative w-64">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-500" />
              <Input placeholder="Search users…" value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9 bg-gray-800 border-gray-600 text-white h-9" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex justify-center py-10"><div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <AlertTriangle className="w-8 h-8 text-red-400 opacity-60" />
              <p className="text-sm text-gray-500 font-mono">Failed to load users — check auth &amp; server logs</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400">
                    <th className="text-left p-3">User</th>
                    <th className="text-left p-3">Role</th>
                    <th className="text-left p-3">Tier</th>
                    <th className="text-left p-3">VITCoin</th>
                    <th className="text-left p-3">Status</th>
                    <th className="text-left p-3">Joined</th>
                    <th className="text-left p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.users?.map(u => (
                    <tr key={u.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                      <td className="p-3">
                        <div className="font-medium text-white">{u.username}</div>
                        <div className="text-xs text-gray-500 font-mono">{u.email}</div>
                      </td>
                      <td className="p-3">
                        <span className={`text-xs font-mono ${u.role === "admin" ? "text-amber-400" : "text-gray-300"}`}>
                          {u.role}{u.admin_role ? ` (${u.admin_role})` : ""}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className={`text-xs font-semibold ${tierColors[u.subscription_tier] ?? "text-gray-400"}`}>
                          {TERMS.tiers[u.subscription_tier as keyof typeof TERMS.tiers] || u.subscription_tier}
                        </span>
                      </td>
                      <td className="p-3 text-amber-400 font-mono text-xs">
                        {u.vitcoin_balance?.toFixed(2) ?? "0.00"}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1 flex-wrap">
                          {u.is_banned
                            ? <span className="text-xs bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded">Banned</span>
                            : u.is_active
                              ? <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">Active</span>
                              : <span className="text-xs bg-gray-500/20 text-gray-400 border border-gray-500/30 px-1.5 py-0.5 rounded">Inactive</span>}
                          {u.is_verified && <span className="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded">Verified</span>}
                        </div>
                      </td>
                      <td className="p-3 text-gray-500 text-xs whitespace-nowrap">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-gray-400 hover:text-white"
                            onClick={() => { setEditingUser(u); setEditForm({ role: u.role, subscription_tier: u.subscription_tier, is_active: u.is_active, is_verified: u.is_verified }); }}>
                            <Edit className="w-3.5 h-3.5" />
                          </Button>
                          <Button size="sm" variant="ghost"
                            className={`h-7 w-7 p-0 ${u.is_banned ? "text-emerald-400 hover:text-emerald-300" : "text-red-400 hover:text-red-300"}`}
                            onClick={() => banMutation.mutate({ id: u.id, ban: !u.is_banned })}>
                            {u.is_banned ? <Unlock className="w-3.5 h-3.5" /> : <Ban className="w-3.5 h-3.5" />}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!data?.users?.length && !isLoading && (
                    <tr>
                      <td colSpan={7} className="text-center text-gray-500 py-8 font-mono text-sm">
                        No users found{search ? ` matching "${search}"` : ""}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit User Dialog */}
      {editingUser && (
        <Dialog open onOpenChange={() => setEditingUser(null)}>
          <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit className="w-5 h-5 text-cyan-400" /> Edit User — {editingUser.username}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-1">
                <Label className="text-gray-300">Role</Label>
                <Select value={editForm.role} onValueChange={v => setEditForm(f => ({ ...f, role: v }))}>
                  <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700 text-white">
                    {["user", "admin"].map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-gray-300">Subscription Tier</Label>
                <Select value={editForm.subscription_tier} onValueChange={v => setEditForm(f => ({ ...f, subscription_tier: v }))}>
                  <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700 text-white">
                    {["viewer", "analyst", "pro", "elite"].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label className="text-gray-300">Account Active</Label>
                <Switch checked={editForm.is_active ?? true}
                  onCheckedChange={v => setEditForm(f => ({ ...f, is_active: v }))} />
              </div>
              <div className="flex items-center justify-between">
                <Label className="text-gray-300">Email Verified</Label>
                <Switch checked={editForm.is_verified ?? false}
                  onCheckedChange={v => setEditForm(f => ({ ...f, is_verified: v }))} />
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" className="border-gray-600 text-gray-300" onClick={() => setEditingUser(null)}>Cancel</Button>
              <Button className="bg-cyan-500 hover:bg-cyan-400 text-black font-semibold"
                disabled={editMutation.isPending}
                onClick={() => editMutation.mutate({ id: editingUser.id, body: editForm })}>
                <Save className="w-4 h-4 mr-2" />
                {editMutation.isPending ? "Saving…" : "Save Changes"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

// ─── Module 9: Models & AI Engine ─────────────────────────────────────

// ─── Live Training Progress Panel ────────────────────────────────────────────

interface TrainingEvent {
  type: string;
  message?: string;
  model?: string;
  accuracy?: number;
  elapsed_s?: number;
  error?: string;
  ts?: number;
  index?: number;
  total?: number;
  summary?: Record<string, any>;
  files?: Record<string, string>;
  count?: number;
}

interface TrainingJobStatus {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  events: TrainingEvent[];
  progress_pct?: number;
  current_model?: string | null;
  current_index?: number;
  total_models?: number;
  results?: Record<string, { model_name: string; accuracy?: number; status: string; elapsed_s?: number; error?: string }>;
  summary?: { models_trained?: number; models_failed?: number; avg_accuracy?: number; version?: string; saved_pkls?: Record<string, string> };
  started_at?: string | null;
  completed_at?: string | null;
}

function TrainingProgressPanel({ jobId, onDismiss }: { jobId: string; onDismiss: () => void }) {
  const logRef = useRef<HTMLDivElement>(null);

  const { data: job, isError } = useQuery<TrainingJobStatus>({
    queryKey: ["admin-training-job", jobId],
    queryFn: () => apiGet<TrainingJobStatus>(`/api/admin/training/job/${jobId}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
    staleTime: 0,
  });

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [job?.events?.length]);

  const isDone = job?.status === "completed" || job?.status === "failed";
  const pct = job?.progress_pct ?? (job?.current_index && job?.total_models
    ? Math.round((job.current_index / job.total_models) * 100)
    : 0);

  const statusColor = {
    queued:    "text-amber-400 bg-amber-500/15 border-amber-500/30",
    running:   "text-cyan-400 bg-cyan-500/15 border-cyan-500/30",
    completed: "text-emerald-400 bg-emerald-500/15 border-emerald-500/30",
    failed:    "text-red-400 bg-red-500/15 border-red-500/30",
  }[job?.status ?? "queued"] ?? "text-gray-400";

  const eventIcon = (type: string) => {
    if (type === "model_done") return "✓";
    if (type === "model_error") return "✗";
    if (type === "model_start") return "▶";
    if (type === "done") return "★";
    if (type === "weights_saved" || type === "weights_reloaded") return "💾";
    if (type === "error") return "!";
    return "·";
  };

  const eventColor = (type: string) => {
    if (type === "model_done") return "text-emerald-400";
    if (type === "model_error" || type === "error") return "text-red-400";
    if (type === "model_start") return "text-cyan-400";
    if (type === "done") return "text-amber-400";
    if (type === "weights_saved" || type === "weights_reloaded") return "text-purple-400";
    return "text-gray-400";
  };

  return (
    <div className="rounded-lg border border-cyan-500/30 bg-gray-900/80 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700/60">
        <div className="flex items-center gap-3">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-semibold text-white">Training Job</span>
          <span className="font-mono text-xs text-gray-500">JOB_{jobId.slice(0, 8)}</span>
          {job?.status && (
            <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${statusColor}`}>
              {job.status.toUpperCase()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {job?.status === "running" && (
            <span className="text-xs text-gray-400">
              Model {job.current_index ?? 0} / {job.total_models ?? "?"} — {pct}%
            </span>
          )}
          {isDone && (
            <button onClick={onDismiss} className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1 rounded hover:bg-gray-700">
              Dismiss ×
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {!isDone && (
        <div className="w-full bg-gray-800 h-1">
          <div
            className="h-1 bg-cyan-500 transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
      {isDone && job?.status === "completed" && (
        <div className="w-full bg-gray-800 h-1">
          <div className="h-1 bg-emerald-500 w-full" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-gray-700/50">
        {/* Event log */}
        <div className="p-3">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-2 font-semibold">Live Log</div>
          <div
            ref={logRef}
            className="h-44 overflow-y-auto font-mono text-xs space-y-0.5 pr-1 scrollbar-thin scrollbar-thumb-gray-700"
          >
            {isError && (
              <div className="text-red-400">Could not connect to job — retrying…</div>
            )}
            {!job && !isError && (
              <div className="text-gray-500 animate-pulse">Connecting to job…</div>
            )}
            {(job?.events ?? []).map((evt, i) => {
              const label = evt.model
                ? evt.model
                : evt.message ?? evt.type;
              const accStr = evt.accuracy !== undefined ? ` — ${(evt.accuracy * 100).toFixed(1)}%` : "";
              const elStr  = evt.elapsed_s !== undefined ? ` (${evt.elapsed_s}s)` : "";
              const ts     = evt.ts ? new Date(evt.ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "";
              return (
                <div key={i} className={`flex gap-2 leading-5 ${eventColor(evt.type)}`}>
                  <span className="shrink-0 w-[18px] text-center">{eventIcon(evt.type)}</span>
                  <span className="text-gray-500 shrink-0">{ts}</span>
                  <span className="truncate">{label}{accStr}{elStr}</span>
                </div>
              );
            })}
            {job?.status === "queued" && (job?.events?.length ?? 0) === 0 && (
              <div className="text-amber-400 animate-pulse">· Waiting in queue…</div>
            )}
            {job?.status === "running" && job?.current_model && (
              <div className="text-cyan-400 animate-pulse">▶ Training: {job.current_model}…</div>
            )}
          </div>
        </div>

        {/* Per-model results */}
        <div className="p-3">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-2 font-semibold">
            Per-Model Results
          </div>
          <div className="h-44 overflow-y-auto space-y-1 pr-1">
            {Object.entries(job?.results ?? {}).length === 0 && (
              <div className="text-gray-600 text-xs font-mono">Results appear as models complete…</div>
            )}
            {Object.entries(job?.results ?? {}).map(([key, r]) => (
              <div key={key} className="flex items-center justify-between gap-2 text-xs py-1 border-b border-gray-800">
                <span className="text-gray-300 truncate max-w-[140px]" title={r.model_name}>{r.model_name}</span>
                <div className="flex items-center gap-2 shrink-0">
                  {r.status === "ok" && r.accuracy !== undefined && (
                    <span className={`font-mono font-semibold ${r.accuracy >= 0.6 ? "text-emerald-400" : r.accuracy >= 0.5 ? "text-amber-400" : "text-red-400"}`}>
                      {(r.accuracy * 100).toFixed(1)}%
                    </span>
                  )}
                  {r.elapsed_s !== undefined && (
                    <span className="text-gray-600">{r.elapsed_s}s</span>
                  )}
                  {r.status === "ok"
                    ? <span className="text-emerald-500">✓</span>
                    : <span className="text-red-400" title={r.error}>✗</span>
                  }
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Final summary */}
      {isDone && job?.summary && (
        <div className="border-t border-gray-700/60 px-4 py-3 bg-gray-800/40">
          {job.status === "completed" ? (
            <div className="flex flex-wrap gap-4 text-xs">
              <span className="text-gray-400">
                Models trained: <span className="text-emerald-400 font-semibold">{job.summary.models_trained ?? "—"}</span>
                {(job.summary.models_failed ?? 0) > 0 && (
                  <span className="text-red-400 ml-1">({job.summary.models_failed} failed)</span>
                )}
              </span>
              {job.summary.avg_accuracy !== undefined && (
                <span className="text-gray-400">
                  Avg accuracy: <span className={`font-semibold font-mono ${(job.summary.avg_accuracy ?? 0) >= 0.6 ? "text-emerald-400" : "text-amber-400"}`}>
                    {((job.summary.avg_accuracy ?? 0) * 100).toFixed(1)}%
                  </span>
                </span>
              )}
              {job.summary.version && (
                <span className="text-gray-400">
                  Version: <span className="text-cyan-400 font-mono">{job.summary.version}</span>
                </span>
              )}
              {job.summary.saved_pkls && (
                <span className="text-gray-400">
                  Weights saved: <span className="text-purple-400 font-semibold">{Object.keys(job.summary.saved_pkls).length} .pkl files</span>
                </span>
              )}
            </div>
          ) : (
            <div className="text-red-400 text-xs">Training failed — check the event log for details.</div>
          )}
        </div>
      )}
    </div>
  );
}

function ModelsTab() {
  const qc = useQueryClient();
  const [activeSection, setActiveSection] = useState<"engine" | "accountability" | "marketplace">("engine");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const { data: modelsData, isLoading: mLoading } = useQuery<{ models: ModelInfo[]; total?: number }>({
    queryKey: ["admin-models"],
    queryFn: () => apiGet("/api/admin/models/status"),
    refetchInterval: 30000,
  });

  const { data: pendingData, isLoading: pLoading } = useQuery<{ items: MarketplaceListing[]; total: number }>({
    queryKey: ["admin-marketplace-pending"],
    queryFn: () => apiGet("/api/admin/marketplace/pending"),
    refetchInterval: 20000,
  });

  // CLV-blended accountability leaderboard (powers the Accountability section)
  const { data: perfRaw, isLoading: perfLoading } = useQuery<any>({
    queryKey: ["admin-ai-performance"],
    queryFn: () => apiGet("/api/ai-engine/performance"),
    refetchInterval: 30000,
  });
  // The endpoint returns either {models: [...]} or a bare array depending on
  // the route version — handle h so we don't crash if it changes shape.
  const perfData: any[] = Array.isArray(perfRaw)
    ? perfRaw
    : Array.isArray(perfRaw?.models)
      ? perfRaw.models
      : [];

  const setActiveMutation = useMutation({
    mutationFn: ({ key, is_active }: { key: string; is_active: boolean }) =>
      apiPost("/api/admin/models/set-active", { key, is_active }),
    onSuccess: (d: any) => {
      toast.success(d?.message ?? "Model status updated");
      qc.invalidateQueries({ queryKey: ["admin-ai-performance"] });
      qc.invalidateQueries({ queryKey: ["admin-models"] });
    },
    onError: (e: any) => toast.error(e?.message || "Failed to update model status"),
  });

  const bootstrapMutation = useMutation({
    mutationFn: () => apiPost("/api/ai-engine/performance/bootstrap", {}),
    onSuccess: (d: any) => {
      toast.success(d?.message ?? `Bootstrapped ${d?.seeded_count ?? 0} model(s)`);
      qc.invalidateQueries({ queryKey: ["admin-ai-performance"] });
    },
    onError: (e: any) => toast.error(e?.message || "Bootstrap failed"),
  });

  const reactivateZeroMutation = useMutation({
    mutationFn: () => apiPost("/api/ai-engine/performance/reactivate-zero-sample", {}),
    onSuccess: (d: any) => {
      toast.success(d?.message ?? `Reactivated ${d?.reactivated_count ?? 0} model(s)`);
      qc.invalidateQueries({ queryKey: ["admin-ai-performance"] });
    },
    onError: (e: any) => toast.error(e?.message || "Reactivation failed"),
  });

  // At-risk = negative rolling CLV with enough samples to be confident in it.
  const atRiskCount = (perfData ?? []).filter(
    (m: any) => m.is_active && (m.clv_samples ?? 0) >= 50 && (m.clv_score ?? 0) < -0.005,
  ).length;

  // KPI breakdown for the dashboard summary strip
  const accountabilityKpis = (() => {
    let healthy = 0, watch = 0, atRisk = 0, demoted = 0;
    for (const m of perfData ?? []) {
      const clv = m.clv_score ?? 0, clvN = m.clv_samples ?? 0;
      const acc = m.accuracy_1x2 ?? 0, total = m.predictions_total ?? 0;
      if (!m.is_active) { demoted++; continue; }
      if (clvN < 30 && total < 30) continue;
      if (clvN >= 50 && clv < -0.005) atRisk++;
      else if (clv < 0 || acc < 0.5) watch++;
      else healthy++;
    }
    return { healthy, watch, atRisk, demoted, total: (perfData ?? []).length };
  })();

  const reloadMutation = useMutation({
    mutationFn: (key?: string) => apiPost("/api/admin/models/reload", key ? { model_key: key } : {}),
    onSuccess: (d: any) => { toast.success(d.message ?? "Models reloaded"); qc.invalidateQueries({ queryKey: ["admin-models"] }); },
    onError: () => toast.error("Reload failed"),
  });

  const trainMutation = useMutation({
    mutationFn: (key?: string) => apiPost("/api/admin/models/train", {
      model_key: key,
      note: key ? `Admin requested retraining for ${key}` : "Admin requested full ensemble retraining",
    }),
    onSuccess: (d: any) => {
      if (d?.job_id) {
        setActiveJobId(d.job_id);
        setActiveSection("engine");
        toast.success(`Training started — JOB_${String(d.job_id).slice(0, 8)}`);
      } else {
        toast.success(d?.message ?? "Training queued");
      }
      qc.invalidateQueries({ queryKey: ["admin-models"] });
      qc.invalidateQueries({ queryKey: ["admin-training-jobs"] });
    },
    onError: (err: any) => toast.error(err?.message || "Training request failed"),
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, note, is_verified }: { id: number; note?: string; is_verified?: boolean }) =>
      apiPatch(`/api/admin/marketplace/${id}/approve`, { note, is_verified }),
    onSuccess: () => { toast.success("Listing approved and is now live"); qc.invalidateQueries({ queryKey: ["admin-marketplace-pending"] }); },
    onError: () => toast.error("Approval failed"),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      apiPatch(`/api/admin/marketplace/${id}/reject`, { reason }),
    onSuccess: () => { toast.success("Listing rejected"); qc.invalidateQueries({ queryKey: ["admin-marketplace-pending"] }); },
    onError: () => toast.error("Rejection failed"),
  });

  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        <Button
          variant={activeSection === "engine" ? "default" : "outline"}
          className={activeSection === "engine" ? "bg-cyan-500 text-black" : "border-gray-600 text-gray-300"}
          onClick={() => setActiveSection("engine")}>
          <Cpu className="w-4 h-4 mr-2" /> AI Engine ({modelsData?.models?.length ?? (modelsData as any)?.total ?? 0})
        </Button>
        <Button
          variant={activeSection === "accountability" ? "default" : "outline"}
          className={activeSection === "accountability"
            ? "bg-purple-500 text-black"
            : "border-gray-600 text-gray-300"}
          onClick={() => setActiveSection("accountability")}>
          <Activity className="w-4 h-4 mr-2" /> Accountability
          {atRiskCount > 0 && (
            <span className="ml-2 bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {atRiskCount} at risk
            </span>
          )}
        </Button>
        <Button
          variant={activeSection === "marketplace" ? "default" : "outline"}
          className={activeSection === "marketplace"
            ? "bg-amber-500 text-black"
            : "border-gray-600 text-gray-300"}
          onClick={() => setActiveSection("marketplace")}>
          <Package className="w-4 h-4 mr-2" /> Marketplace Pending
          {(pendingData?.total ?? 0) > 0 && (
            <span className="ml-2 bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {pendingData?.total}
            </span>
          )}
        </Button>
      </div>

      {activeSection === "engine" && (
        <Card className="bg-gray-900 border-gray-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white flex items-center gap-2">
                <Cpu className="w-5 h-5 text-cyan-400" /> AI Model Registry
              </CardTitle>
              <Button size="sm" variant="outline" className="border-cyan-500/30 text-cyan-400 hover:border-cyan-400"
                onClick={() => reloadMutation.mutate(undefined)} disabled={reloadMutation.isPending}>
                <RefreshCw className={`w-4 h-4 mr-2 ${reloadMutation.isPending ? "animate-spin" : ""}`} />
                Reload All
              </Button>
              <Button size="sm" className="bg-emerald-500 text-black hover:bg-emerald-400"
                onClick={() => trainMutation.mutate(undefined)} disabled={trainMutation.isPending}>
                <Zap className="w-4 h-4 mr-2" />
                Train All .pkl
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {mLoading ? (
              <div className="flex justify-center py-10"><div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 text-gray-400">
                      <th className="text-left p-3">Model</th>
                      <th className="text-left p-3">Type</th>
                      <th className="text-left p-3">Weight</th>
                      <th className="text-left p-3">Status</th>
                      <th className="text-left p-3">Source</th>
                      <th className="text-left p-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelsData?.models?.map(m => (
                      <tr key={m.key} className="border-b border-gray-800 hover:bg-gray-800/40">
                        <td className="p-3">
                          <div className="text-white font-medium">{m.model_name}</div>
                          <div className="text-xs text-gray-500 font-mono">{m.key}</div>
                        </td>
                        <td className="p-3 text-gray-400 text-xs">{m.model_type ?? "—"}</td>
                        <td className="p-3 text-cyan-400 font-mono text-xs">{m.weight?.toFixed(2)}</td>
                        <td className="p-3">
                          {(m.ready || m.error === null)
                            ? <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">Ready</span>
                            : <span className="text-xs bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded">Error</span>}
                          {m.is_trained && <span className="ml-1 text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded">Trained</span>}
                          {m.pkl_loaded && <span className="ml-1 text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">Real Weights</span>}
                        </td>
                        <td className="p-3">
                          <span className={`text-xs ${m.source === "marketplace" ? "text-amber-400" : "text-gray-500"}`}>
                            {m.source ?? "internal"}
                            {m.listing_id ? ` #${m.listing_id}` : ""}
                          </span>
                          {m.trained_count ? <div className="text-[10px] text-gray-500 mt-1">{m.trained_count.toLocaleString()} samples</div> : null}
                        </td>
                        <td className="p-3">
                          <Button size="sm" variant="ghost" className="h-7 text-xs text-emerald-400 hover:text-emerald-300"
                            onClick={() => trainMutation.mutate(m.key)} disabled={trainMutation.isPending}>
                            <Zap className="w-3 h-3 mr-1" /> Train
                          </Button>
                          <Button size="sm" variant="ghost" className="h-7 text-xs text-gray-400 hover:text-cyan-400"
                            onClick={() => reloadMutation.mutate(m.key)}>
                            <RefreshCw className="w-3 h-3 mr-1" /> Reload
                          </Button>
                        </td>
                      </tr>
                    ))}
                    {!modelsData?.models?.length && (
                      <tr><td colSpan={6} className="text-center text-gray-500 py-8">No models found</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeSection === "engine" && activeJobId && (
        <TrainingProgressPanel
          jobId={activeJobId}
          onDismiss={() => {
            setActiveJobId(null);
            qc.invalidateQueries({ queryKey: ["admin-models"] });
            qc.invalidateQueries({ queryKey: ["training-insight-report"] });
          }}
        />
      )}

      {activeSection === "engine" && <TrainingInsightCard />}

      {activeSection === "accountability" && (
        <div className="space-y-4">
          {/* ── KPI Summary Strip ────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { label: "Total Models",       value: accountabilityKpis.total,    icon: Cpu,           tone: "neutral" as const, pulse: false },
              { label: "Healthy",            value: accountabilityKpis.healthy,  icon: CheckCircle,   tone: "success" as const, pulse: false },
              { label: "On Watch",           value: accountabilityKpis.watch,    icon: AlertCircle,   tone: "warning" as const, pulse: accountabilityKpis.watch > 0 },
              { label: "At Risk · Demoted",  value: accountabilityKpis.atRisk + accountabilityKpis.demoted, icon: XCircle, tone: "destructive" as const, pulse: (accountabilityKpis.atRisk + accountabilityKpis.demoted) > 0 },
            ].map((kpi) => {
              const toneClass = {
                neutral:     { ring: "border-gray-700",         text: "text-cyan-400",    bg: "bg-cyan-500/10"    },
                success:     { ring: "border-emerald-500/30",   text: "text-emerald-400", bg: "bg-emerald-500/10" },
                warning:     { ring: kpi.value > 0 ? "border-amber-500/40" : "border-gray-700", text: "text-amber-400", bg: "bg-amber-500/10" },
                destructive: { ring: kpi.value > 0 ? "border-red-500/40"   : "border-gray-700", text: "text-red-400",   bg: "bg-red-500/10"   },
              }[kpi.tone];
              return (
                <Card key={kpi.label} className={`bg-gray-900 ${toneClass.ring} transition-colors`}>
                  <CardContent className="p-4 flex items-center justify-between">
                    <div className="min-w-0">
                      <div className="text-[10px] uppercase tracking-wider text-gray-400 font-mono truncate">{kpi.label}</div>
                      <div className={`text-3xl font-bold mt-1 ${toneClass.text} font-mono tabular-nums`}>{kpi.value}</div>
                    </div>
                    <div className={`p-2.5 rounded-lg ${toneClass.bg} ${kpi.pulse ? "vit-animate-pulse-glow" : ""}`}>
                      <kpi.icon className={`w-5 h-5 ${toneClass.text}`} />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card className="bg-gray-900 border-gray-700">
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <CardTitle className="text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-purple-400" /> CLV-Blended Accountability
                </CardTitle>
                <div className="flex items-center gap-2 flex-wrap">
                  <Button size="sm" variant="outline"
                    className="border-cyan-500/30 text-cyan-400 hover:border-cyan-400"
                    disabled={reactivateZeroMutation.isPending}
                    title="Reactivate every demoted model that has zero settled predictions — no empirical basis for demotion"
                    onClick={() => reactivateZeroMutation.mutate()}>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    {reactivateZeroMutation.isPending ? "Reactivating…" : "Reactivate Zero-Sample"}
                  </Button>
                  <Button size="sm" variant="outline"
                    className="border-amber-500/30 text-amber-400 hover:border-amber-400"
                    disabled={bootstrapMutation.isPending}
                    title="Seed brier/log-loss from training pkl metrics or model-type benchmarks for models with insufficient live data"
                    onClick={() => bootstrapMutation.mutate()}>
                    <Zap className="w-4 h-4 mr-2" />
                    {bootstrapMutation.isPending ? "Bootstrapping…" : "Bootstrap Priors"}
                  </Button>
                  <Button size="sm" variant="outline"
                    className="border-purple-500/30 text-purple-400 hover:border-purple-400"
                    onClick={() => qc.invalidateQueries({ queryKey: ["admin-ai-performance"] })}>
                    <RefreshCw className="w-4 h-4 mr-2" /> Refresh
                  </Button>
                </div>
              </div>
              <CardDescription className="text-gray-400">
                Per-model rolling Closing-Line Value alongside log-loss and accuracy.
                CLV is the leading indicator of true edge — a sustained negative
                CLV means the model is on the wrong side of sharp money.
                Metrics tagged <span className="text-amber-400 font-mono text-xs">~est</span> are
                bootstrapped from training data or type benchmarks — they improve as live predictions settle.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {atRiskCount > 0 && (
                <div className="mx-4 mb-3 mt-1 px-3 py-2 rounded border border-red-500/40 bg-red-500/10 text-red-300 text-sm flex items-center gap-2 vit-animate-pulse-glow">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span className="font-semibold">{atRiskCount}</span>
                  <span>
                    model{atRiskCount === 1 ? "" : "s"} at risk —
                    rolling CLV below −0.005 with ≥ 50 settled samples.
                    Recommend demotion until investigated.
                  </span>
                </div>
              )}
              {perfLoading ? (
                <div className="px-4 py-3 space-y-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3 py-2">
                      <Skeleton className="h-8 w-32 bg-gray-800" />
                      <Skeleton className="h-6 w-20 bg-gray-800 ml-auto" />
                      <Skeleton className="h-6 w-12 bg-gray-800" />
                      <Skeleton className="h-6 w-16 bg-gray-800" />
                      <Skeleton className="h-6 w-16 bg-gray-800" />
                      <Skeleton className="h-6 w-20 bg-gray-800" />
                      <Skeleton className="h-7 w-20 bg-gray-800" />
                    </div>
                  ))}
                </div>
              ) : !perfData?.length ? (
                <div className="text-center text-gray-500 py-12">
                  <Activity className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <div>No performance data yet.</div>
                  <div className="text-xs mt-1">CLV scores appear once matches settle and predictions are evaluated.</div>
                </div>
              ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 text-gray-400">
                      <th className="text-left p-3">Model</th>
                      <th className="text-center p-3">Status</th>
                      <th className="text-right p-3">Weight</th>
                      <th className="text-right p-3">Accuracy</th>
                      <th className="text-right p-3">Log-loss</th>
                      <th className="text-right p-3">Brier</th>
                      <th className="text-right p-3">CLV score</th>
                      <th className="text-right p-3">CLV samples</th>
                      <th className="text-right p-3">Total</th>
                      <th className="text-center p-3">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {perfData.map((m: any) => {
                      const clv = m.clv_score ?? 0;
                      const clvN = m.clv_samples ?? 0;
                      const acc = m.accuracy_1x2 ?? 0;
                      const total = m.predictions_total ?? 0;
                      const streak = m.clv_negative_streak_days ?? 0;
                      const autoDemoted = !!m.auto_demoted;
                      let status: "healthy" | "watch" | "risk" | "new";
                      if (!m.is_active) status = "risk";
                      else if (clvN < 30 && total < 30) status = "new";
                      else if (clvN >= 50 && clv < -0.005) status = "risk";
                      else if (clv < 0 || acc < 0.5) status = "watch";
                      else status = "healthy";
                      const demotedLabel = m.is_active
                        ? (streak > 0 ? `At Risk · day ${streak}/7` : "At Risk")
                        : (autoDemoted ? "Demoted (auto)" : "Demoted");
                      const statusBadge = {
                        healthy: { label: "Healthy", cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", dot: "bg-emerald-400" },
                        watch:   { label: streak > 0 ? `Watch · day ${streak}/7` : "Watch", cls: "bg-amber-500/20 text-amber-400 border-amber-500/30", dot: "bg-amber-400" },
                        risk:    { label: demotedLabel, cls: "bg-red-500/20 text-red-400 border-red-500/30 vit-animate-pulse-glow", dot: "bg-red-400 animate-pulse" },
                        new:     { label: "Insufficient",  cls: "bg-gray-500/20 text-gray-400 border-gray-500/30", dot: "bg-gray-500" },
                      }[status];
                      const showStreakDots = m.is_active && streak > 0;
                      return (
                        <tr key={m.key} className={`border-b border-gray-800 transition-colors ${!m.is_active ? "opacity-60" : "hover:bg-gray-800/40"}`}>
                          <td className="p-3">
                            <div className="text-white font-medium">{m.name}</div>
                            <div className="text-xs text-gray-500 font-mono">{m.key}</div>
                          </td>
                          <td className="p-3">
                            <div className="flex flex-col items-center gap-1.5">
                              <span className={`text-xs border px-2 py-0.5 rounded inline-flex items-center gap-1.5 ${statusBadge.cls}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dot}`} />
                                {statusBadge.label}
                              </span>
                              {showStreakDots && (
                                <div className="flex gap-0.5" title={`${streak} of 7 days below CLV threshold`}>
                                  {[0,1,2,3,4,5,6].map(i => (
                                    <div key={i} className={`w-1.5 h-1.5 rounded-full transition-colors ${
                                      i < streak
                                        ? (streak >= 5 ? "bg-red-500" : streak >= 3 ? "bg-amber-500" : "bg-amber-600")
                                        : "bg-gray-700"
                                    }`} />
                                  ))}
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="p-3 text-right text-cyan-400 font-mono text-xs">
                            {typeof m.weight === "number" ? m.weight.toFixed(3) : "—"}
                          </td>
                          <td className="p-3 text-right font-mono text-xs">
                            {typeof m.accuracy_1x2 === "number" ? (
                              <div className="flex flex-col items-end gap-0.5">
                                <span className={m.metric_source === "live" ? "text-gray-200" : "text-amber-300/80"}>
                                  {m.metric_source !== "live" && <span className="text-amber-500 mr-0.5">~</span>}
                                  {(m.accuracy_1x2 * 100).toFixed(1)}%
                                </span>
                                {m.metric_source === "bootstrapped" && (
                                  <span className="text-[9px] text-amber-500/70 font-mono">est</span>
                                )}
                              </div>
                            ) : "—"}
                          </td>
                          <td className="p-3 text-right font-mono text-xs">
                            {typeof m.log_loss === "number" ? (
                              <div className="flex flex-col items-end gap-0.5">
                                <span className={m.metric_source === "live" ? "text-yellow-400" : "text-yellow-400/70"}>
                                  {m.metric_source !== "live" && <span className="text-amber-500 mr-0.5">~</span>}
                                  {m.log_loss.toFixed(4)}
                                </span>
                                {m.metric_source === "bootstrapped" && (
                                  <span className="text-[9px] text-amber-500/70 font-mono">est</span>
                                )}
                              </div>
                            ) : "—"}
                          </td>
                          <td className="p-3 text-right font-mono text-xs">
                            {typeof m.brier_score === "number" ? (
                              <div className="flex flex-col items-end gap-0.5">
                                <span className={m.metric_source === "live" ? "text-gray-300" : "text-gray-300/70"}>
                                  {m.metric_source !== "live" && <span className="text-amber-500 mr-0.5">~</span>}
                                  {m.brier_score.toFixed(4)}
                                </span>
                                {m.metric_source === "bootstrapped" && (
                                  <span className="text-[9px] text-amber-500/70 font-mono">est</span>
                                )}
                              </div>
                            ) : "—"}
                          </td>
                          <td className="p-3">
                            <div className="flex flex-col items-end gap-1">
                              <span className={`font-mono text-xs ${
                                clv > 0.001 ? "text-emerald-400"
                                : clv < -0.001 ? "text-red-400"
                                : "text-gray-400"
                              }`}>
                                {clvN > 0 ? (clv > 0 ? "+" : "") + clv.toFixed(4) : "—"}
                              </span>
                              {clvN > 0 && (
                                <div className="relative w-20 h-1 bg-gray-800 rounded-full" title="CLV magnitude (range −0.02 to +0.02)">
                                  <div className="absolute left-1/2 top-0 w-px h-full bg-gray-600" />
                                  {clv !== 0 && (
                                    <div
                                      className={`absolute top-0 h-full rounded-full ${clv > 0 ? "bg-emerald-500" : "bg-red-500"}`}
                                      style={clv > 0
                                        ? { left: "50%", width: `${Math.min(Math.abs(clv) / 0.02, 1) * 50}%` }
                                        : { right: "50%", width: `${Math.min(Math.abs(clv) / 0.02, 1) * 50}%` }
                                      }
                                    />
                                  )}
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="p-3 text-right font-mono text-xs text-gray-400">
                            {clvN}
                          </td>
                          <td className="p-3 text-right font-mono text-xs text-gray-400">
                            {total.toLocaleString()}
                          </td>
                          <td className="p-3 text-center">
                            {m.is_active ? (
                              <Button size="sm" variant="ghost"
                                className="h-7 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                disabled={setActiveMutation.isPending}
                                onClick={() => {
                                  if (confirm(`Demote "${m.name}"? Its predictions will stop contributing to the ensemble until reactivated.`)) {
                                    setActiveMutation.mutate({ key: m.key, is_active: false });
                                  }
                                }}>
                                <XCircle className="w-3 h-3 mr-1" /> Demote
                              </Button>
                            ) : (
                              <Button size="sm" variant="ghost"
                                className="h-7 text-xs text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                                disabled={setActiveMutation.isPending}
                                onClick={() => setActiveMutation.mutate({ key: m.key, is_active: true })}>
                                <CheckCircle className="w-3 h-3 mr-1" /> Reactivate
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div className="text-xs text-gray-500 px-4 py-3 border-t border-gray-800 space-y-1">
                  <div>
                    CLV score is a rolling EMA of (model_prob − market_prob) × CLV per settled match.
                    Status thresholds: Healthy = positive CLV &amp; ≥ 50% accuracy ·
                    Watch = negative CLV or accuracy &lt; 50% ·
                    At Risk = CLV &lt; −0.005 with ≥ 50 samples ·
                    Insufficient = fewer than 30 settled samples.
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-amber-500">~</span>
                    <span className="text-amber-500/70 font-mono">est</span>
                    <span>= metric bootstrapped from training pkl or model-type benchmark prior — not yet backed by live settled predictions.</span>
                  </div>
                </div>
              </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeSection === "marketplace" && (
        <Card className="bg-gray-900 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Package className="w-5 h-5 text-amber-400" /> Pending Marketplace Models
              <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">{pendingData?.total ?? 0} pending</Badge>
            </CardTitle>
            <CardDescription className="text-gray-400">
              Review uploaded model files. Approved models are activated and registered in the prediction engine.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {pLoading ? (
              <div className="flex justify-center py-10"><div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" /></div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 text-gray-400">
                      <th className="text-left p-3">Model Name</th>
                      <th className="text-left p-3">Category</th>
                      <th className="text-left p-3">Creator</th>
                      <th className="text-left p-3">Price / Call</th>
                      <th className="text-left p-3">File</th>
                      <th className="text-left p-3">Submitted</th>
                      <th className="text-left p-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingData?.items?.map(l => (
                      <tr key={l.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                        <td className="p-3">
                          <div className="text-white font-medium">{l.name}</div>
                          <div className="text-xs text-gray-500 truncate max-w-[200px]">{l.description}</div>
                        </td>
                        <td className="p-3 text-gray-400 text-xs">{l.category}</td>
                        <td className="p-3 text-gray-400 text-xs font-mono">#{l.creator_id}</td>
                        <td className="p-3 text-amber-400 font-mono text-xs">{l.price_per_call} VIT</td>
                        <td className="p-3">
                          {l.package_id
                            ? (
                              <div className="space-y-1">
                                <span className="text-xs text-emerald-400 flex items-center gap-1">
                                  <Upload className="w-3 h-3" /> Package ({l.package_file_count ?? 0} files)
                                </span>
                                <div className="text-[11px] text-gray-500 font-mono">
                                  {l.primary_file ?? l.package_id} · {l.file_size_bytes ? `${(l.file_size_bytes / 1024).toFixed(0)} KB` : "size unknown"}
                                </div>
                                {l.execution_status && (
                                  <div className="text-[11px] text-amber-400">{l.execution_status.replaceAll("_", " ")}</div>
                                )}
                              </div>
                            )
                            : l.pkl_path
                            ? <span className="text-xs text-emerald-400 flex items-center gap-1"><Upload className="w-3 h-3" /> Model file ({l.file_size_bytes ? `${(l.file_size_bytes / 1024).toFixed(0)} KB` : "?"})</span>
                            : l.webhook_url
                              ? <span className="text-xs text-blue-400">Webhook</span>
                              : <span className="text-xs text-gray-500">No file</span>}
                        </td>
                        <td className="p-3 text-gray-500 text-xs whitespace-nowrap">
                          {l.created_at ? new Date(l.created_at).toLocaleDateString() : "-"}
                        </td>
                        <td className="p-3">
                          <div className="flex gap-1">
                            <Button size="sm" className="h-7 px-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 text-xs"
                              onClick={() => approveMutation.mutate({ id: l.id })}
                              disabled={approveMutation.isPending}>
                              <CheckCircle className="w-3 h-3 mr-1" /> Approve
                            </Button>
                            <Button size="sm" className="h-7 px-2 bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 text-xs"
                              onClick={() => approveMutation.mutate({ id: l.id, is_verified: true })}
                              disabled={approveMutation.isPending}>
                              <Star className="w-3 h-3 mr-1" /> Approve & Verify
                            </Button>
                            <Button size="sm" className="h-7 px-2 bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 text-xs"
                              onClick={() => { setRejectingId(l.id); setRejectReason(""); }}>
                              <XCircle className="w-3 h-3 mr-1" /> Reject
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!pendingData?.items?.length && (
                      <tr><td colSpan={7} className="text-center text-gray-500 py-8">No pending listings — all clear!</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Reject Dialog */}
      {rejectingId !== null && (
        <Dialog open onOpenChange={() => setRejectingId(null)}>
          <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-400">
                <XCircle className="w-5 h-5" /> Reject Listing #{rejectingId}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <Label className="text-gray-300">Rejection Reason (shown to the creator)</Label>
              <textarea
                className="w-full bg-gray-800 border border-gray-600 rounded-md text-white text-sm p-3 min-h-[100px] resize-none focus:outline-none focus:border-red-500"
                placeholder="e.g. Model does not meet performance standards, or violates marketplace guidelines."
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
              />
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" className="border-gray-600 text-gray-300" onClick={() => setRejectingId(null)}>Cancel</Button>
              <Button className="bg-red-500 hover:bg-red-400 text-white"
                disabled={!rejectReason.trim() || rejectMutation.isPending}
                onClick={() => { rejectMutation.mutate({ id: rejectingId!, reason: rejectReason }); setRejectingId(null); }}>
                Confirm Rejection
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

// ─── Training Insight Report Card ─────────────────────────────────────

interface InsightReport {
  ensemble_summary: {
    avg_accuracy: number | null;
    weighted_accuracy: number | null;
    total_models: number;
    trained_models: number;
    best_model: string | null;
    best_accuracy: number | null;
    worst_model: string | null;
    worst_accuracy: number | null;
    current_production: string | null;
  };
  model_breakdown: {
    key: string;
    name: string;
    weight: number | null;
    accuracy: number | null;
    trained: boolean;
    trained_matches: number;
    status: string;
    markets: string[];
  }[];
  weight_history: { job_id: string; completed_at: string; models: Record<string, number> }[];
  recommendations: string[];
  report_generated_at: string;
}

const STATUS_CLS: Record<string, string> = {
  healthy:   "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  watch:     "text-amber-400 border-amber-500/30 bg-amber-500/10",
  at_risk:   "text-red-400 border-red-500/30 bg-red-500/10",
  untrained: "text-gray-400 border-gray-500/30 bg-gray-500/10",
  no_data:   "text-gray-500 border-gray-600/30 bg-gray-600/10",
};

function TrainingInsightCard() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery<InsightReport>({
    queryKey: ["training-insight-report"],
    queryFn: () => apiGet<InsightReport>("/api/training/insight-report"),
    staleTime: 2 * 60 * 1000,
  });

  const summary = data?.ensemble_summary;

  return (
    <Card className="bg-gray-900 border-gray-700">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" /> Training Insight Report
          </CardTitle>
          <Button size="sm" variant="outline" className="border-indigo-500/30 text-indigo-400 hover:border-indigo-400"
            onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isFetching ? "animate-spin" : ""}`} />
            {isFetching ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
        <CardDescription className="text-gray-400">
          Per-model accuracy breakdown, weight distribution, and actionable improvement suggestions.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {isLoading && (
          <div className="space-y-2">
            {[1,2,3].map(i => <div key={i} className="h-8 rounded bg-gray-800 animate-pulse" />)}
          </div>
        )}
        {isError && (
          <div className="text-center py-6">
            <AlertCircle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
            <p className="text-gray-400 text-sm">Could not load training report. Train at least one model first.</p>
          </div>
        )}

        {data && (
          <>
            {/* Ensemble summary strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Avg Accuracy",   value: summary?.avg_accuracy      != null ? `${(summary.avg_accuracy * 100).toFixed(1)}%`     : "—", color: "text-cyan-400" },
                { label: "Wtd Accuracy",   value: summary?.weighted_accuracy  != null ? `${(summary.weighted_accuracy * 100).toFixed(1)}%` : "—", color: "text-indigo-400" },
                { label: "Models Trained", value: `${summary?.trained_models ?? 0} / ${summary?.total_models ?? 0}`,  color: "text-emerald-400" },
                { label: "Best Model",     value: summary?.best_model ?? "—", color: "text-amber-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-gray-800 rounded p-3 border border-gray-700">
                  <p className="text-xs text-gray-400 font-mono uppercase mb-1">{label}</p>
                  <p className={`text-sm font-bold font-mono truncate ${color}`}>{value}</p>
                </div>
              ))}
            </div>

            {/* Model breakdown table */}
            {data.model_breakdown.length > 0 && (
              <div className="overflow-x-auto rounded border border-gray-700">
                <table className="w-full text-sm">
                  <thead className="border-b border-gray-700 bg-gray-800/60">
                    <tr className="text-gray-400 font-mono text-xs">
                      <th className="text-left p-2 pl-3">Model</th>
                      <th className="text-right p-2">Weight</th>
                      <th className="text-right p-2">Accuracy</th>
                      <th className="text-right p-2">Trained on</th>
                      <th className="text-center p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.model_breakdown.map(m => (
                      <tr key={m.key} className="border-b border-gray-800 hover:bg-gray-800/40 transition-colors">
                        <td className="p-2 pl-3">
                          <div className="text-white text-xs font-medium">{m.name}</div>
                          <div className="text-gray-500 text-[10px] font-mono">{m.key}</div>
                        </td>
                        <td className="p-2 text-right text-cyan-400 font-mono text-xs">
                          {m.weight != null ? m.weight.toFixed(3) : "—"}
                        </td>
                        <td className="p-2 text-right text-gray-200 font-mono text-xs">
                          {m.accuracy != null ? `${(m.accuracy * 100).toFixed(1)}%` : "—"}
                        </td>
                        <td className="p-2 text-right text-gray-400 font-mono text-xs">
                          {m.trained_matches > 0 ? m.trained_matches.toLocaleString() : (m.trained ? "yes" : "—")}
                        </td>
                        <td className="p-2 text-center">
                          <span className={`text-[10px] font-mono border rounded px-1.5 py-0.5 ${STATUS_CLS[m.status] ?? STATUS_CLS.no_data}`}>
                            {m.status.replace("_", " ")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Recommendations */}
            {data.recommendations.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-mono text-gray-400 uppercase">Recommendations</p>
                {data.recommendations.map((rec, i) => (
                  <div key={i} className="flex gap-2 p-2.5 rounded bg-gray-800/60 border border-indigo-500/20 text-sm text-gray-300">
                    <Lightbulb className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            )}

            <p className="text-[10px] font-mono text-gray-600 text-right">
              Generated {new Date(data.report_generated_at).toLocaleTimeString()}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}


// ─── Module 10: KYC Verification ─────────────────────────────────────

function KYCTab() {
  const qc = useQueryClient();
  const [noteInput, setNoteInput] = useState<Record<number, string>>({});

  const { data, isLoading } = useQuery<{ kyc_requests: KYCEntry[]; total: number }>({
    queryKey: ["admin-kyc-pending"],
    queryFn: () => apiGet("/api/wallet/admin/kyc/pending"),
    refetchInterval: 20000,
  });

  const approveMutation = useMutation({
    mutationFn: (user_id: number) => apiPost(`/api/wallet/admin/kyc/${user_id}/approve`, {}),
    onSuccess: () => { toast.success("KYC approved"); qc.invalidateQueries({ queryKey: ["admin-kyc-pending"] }); },
    onError: () => toast.error("Approval failed"),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ user_id, reason }: { user_id: number; reason?: string }) =>
      apiPost(`/api/wallet/admin/kyc/${user_id}/reject`, { reason: reason ?? "Rejected by admin" }),
    onSuccess: () => { toast.success("KYC rejected"); qc.invalidateQueries({ queryKey: ["admin-kyc-pending"] }); },
    onError: () => toast.error("Rejection failed"),
  });

  return (
    <div className="space-y-4">
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-emerald-400" /> KYC Verification Queue
            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
              {data?.total ?? 0} pending
            </Badge>
          </CardTitle>
          <CardDescription className="text-gray-400">
            Review and approve user identity verification submissions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-10"><div className="w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" /></div>
          ) : data?.kyc_requests?.length ? (
            <div className="space-y-4">
              {data.kyc_requests.map(kyc => (
                <div key={kyc.id} className="border border-gray-700 rounded-lg p-4 hover:border-gray-600">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{kyc.full_name ?? `User #${kyc.user_id}`}</span>
                        <span className="text-xs bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 px-1.5 py-0.5 rounded">{kyc.status}</span>
                      </div>
                      {kyc.email && <div className="text-sm text-gray-400 font-mono">{kyc.email}</div>}
                      {kyc.document_type && <div className="text-xs text-gray-500">Document: {kyc.document_type}</div>}
                      {kyc.submitted_at && (
                        <div className="text-xs text-gray-600">
                          Submitted: {new Date(kyc.submitted_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-2 shrink-0">
                      <Button size="sm" className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30"
                        disabled={approveMutation.isPending}
                        onClick={() => approveMutation.mutate(kyc.user_id)}>
                        <CheckCircle className="w-4 h-4 mr-1" /> Approve
                      </Button>
                      <Button size="sm" className="bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30"
                        disabled={rejectMutation.isPending}
                        onClick={() => rejectMutation.mutate({ user_id: kyc.user_id, reason: noteInput[kyc.id] })}>
                        <XCircle className="w-4 h-4 mr-1" /> Reject
                      </Button>
                    </div>
                  </div>
                  <div className="mt-3">
                    <Input
                      placeholder="Rejection reason (optional)"
                      value={noteInput[kyc.id] ?? ""}
                      onChange={e => setNoteInput(n => ({ ...n, [kyc.id]: e.target.value }))}
                      className="h-8 text-xs bg-gray-800 border-gray-600 text-white"
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-500 py-12">
              <UserCheck className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No pending KYC submissions — all caught up!</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Module 11: Audit Log ─────────────────────────────────────────────

function AuditTab() {
  const [actionFilter, setActionFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("");
  const { data, isLoading } = useQuery<{ total: number; logs: AuditEntry[] }>({
    queryKey: ["admin-audit", actionFilter, actorFilter],
    queryFn: () => {
      const p = new URLSearchParams();
      if (actionFilter) p.set("action", actionFilter);
      if (actorFilter) p.set("actor", actorFilter);
      p.set("limit", "100");
      return apiGet(`/api/admin/audit?${p}`);
    },
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <Input placeholder="Filter by action…" className="pl-9 bg-gray-800 border-gray-600 text-white"
            value={actionFilter} onChange={e => setActionFilter(e.target.value)} />
        </div>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <Input placeholder="Filter by actor…" className="pl-9 bg-gray-800 border-gray-600 text-white"
            value={actorFilter} onChange={e => setActorFilter(e.target.value)} />
        </div>
      </div>

      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center justify-between">
            <span className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" /> Audit Trail
            </span>
            <span className="text-sm text-gray-500 font-normal">{data?.total ?? 0} entries</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex justify-center py-10"><div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400">
                    <th className="text-left p-3">Timestamp</th>
                    <th className="text-left p-3">Actor</th>
                    <th className="text-left p-3">Action</th>
                    <th className="text-left p-3">Resource</th>
                    <th className="text-left p-3">Status</th>
                    <th className="text-left p-3">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.logs?.map(lg => (
                    <tr key={lg.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                      <td className="p-3 text-gray-500 text-xs whitespace-nowrap">
                        {lg.timestamp ? new Date(lg.timestamp).toLocaleString() : "-"}
                      </td>
                      <td className="p-3 text-gray-300 font-mono text-xs truncate max-w-[140px]">{lg.actor}</td>
                      <td className="p-3 text-cyan-400 font-mono text-xs">{lg.action}</td>
                      <td className="p-3 text-gray-400 text-xs">{lg.resource ?? "-"}</td>
                      <td className="p-3"><StatusBadge status={lg.status} /></td>
                      <td className="p-3 text-gray-500 text-xs truncate max-w-[200px]">
                        {lg.details ? JSON.stringify(lg.details).slice(0, 60) : "-"}
                      </td>
                    </tr>
                  ))}
                  {!data?.logs?.length && (
                    <tr><td colSpan={6} className="text-center text-gray-500 py-8">No audit entries found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Module 12: Tasks Management ──────────────────────────────────────

interface EditingTask {
  id: number;
  name: string;
  category_id: number | null;
  xp_reward: number;
  vit_reward: number;
  trigger_type: string;
  reset_frequency: string;
  description: string;
  is_active: boolean;
}

function TasksTab() {
  const qc = useQueryClient();
  const [editingTask, setEditingTask] = useState<EditingTask | null>(null);
  const [newTask, setNewTask] = useState({
    name: "",
    description: "",
    category_id: "",
    xp_reward: 0,
    vit_reward: 0,
    trigger_type: "manual",
    trigger_condition: "",
    max_completions: null,
    is_active: true,
    reset_frequency: "never"
  });

  const { data: tasksData, isLoading: tasksLoading } = useQuery<{ tasks: any[]; categories: any[] }>({
    queryKey: ["admin-tasks"],
    queryFn: () => apiGet("/api/admin/tasks"),
    refetchInterval: 30000,
  });

  const { data: completionsData } = useQuery<{ completions: any[]; total: number }>({
    queryKey: ["admin-task-completions"],
    queryFn: () => apiGet("/api/admin/tasks/completions?limit=100"),
  });

  const createMutation = useMutation({
    mutationFn: (task: any) => apiPost("/api/admin/tasks", task),
    onSuccess: () => {
      toast.success("Task created");
      setNewTask({
        name: "",
        description: "",
        category_id: "",
        xp_reward: 0,
        vit_reward: 0,
        trigger_type: "manual",
        trigger_condition: "",
        max_completions: null,
        is_active: true,
        reset_frequency: "never"
      });
      qc.invalidateQueries({ queryKey: ["admin-tasks"] });
    },
    onError: () => toast.error("Failed to create task"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: any }) => apiPut(`/api/admin/tasks/${id}`, body),
    onSuccess: () => { toast.success("Task updated"); setEditingTask(null); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); },
    onError: () => toast.error("Failed to update task"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/api/admin/tasks/${id}`),
    onSuccess: () => { toast.success("Task deleted"); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); },
    onError: () => toast.error("Failed to delete task"),
  });

  const resetMutation = useMutation({
    mutationFn: () => apiPost("/api/admin/tasks/reset-expired", {}),
    onSuccess: () => { toast.success("Expired tasks reset"); qc.invalidateQueries({ queryKey: ["admin-task-completions"] }); },
    onError: () => toast.error("Failed to reset tasks"),
  });

  return (
    <div className="space-y-6">
      {/* Task Creation */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Plus className="w-5 h-5 text-emerald-400" /> Create New Task
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label className="text-gray-300">Task Name</Label>
              <Input
                value={newTask.name}
                onChange={e => setNewTask(t => ({ ...t, name: e.target.value }))}
                className="bg-gray-800 border-gray-600 text-white"
                placeholder="e.g. Make Your First Prediction"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-gray-300">Category</Label>
              <Select value={newTask.category_id} onValueChange={v => setNewTask(t => ({ ...t, category_id: v }))}>
                <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-700 text-white">
                  {tasksData?.categories?.map((cat: any) => (
                    <SelectItem key={cat.id} value={cat.id.toString()}>{cat.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-gray-300">XP Reward</Label>
              <Input
                type="number"
                value={newTask.xp_reward}
                onChange={e => setNewTask(t => ({ ...t, xp_reward: +e.target.value }))}
                className="bg-gray-800 border-gray-600 text-white"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-gray-300">VIT Reward</Label>
              <Input
                type="number"
                step="0.01"
                value={newTask.vit_reward}
                onChange={e => setNewTask(t => ({ ...t, vit_reward: +e.target.value }))}
                className="bg-gray-800 border-gray-600 text-white"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-gray-300">Trigger Type</Label>
              <Select value={newTask.trigger_type} onValueChange={v => setNewTask(t => ({ ...t, trigger_type: v }))}>
                <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-700 text-white">
                  <SelectItem value="manual">Manual</SelectItem>
                  <SelectItem value="xp_threshold">XP Threshold</SelectItem>
                  <SelectItem value="prediction_count">Prediction Count</SelectItem>
                  <SelectItem value="deposit_amount">Deposit Amount</SelectItem>
                  <SelectItem value="governance_vote">Governance Vote</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-gray-300">Reset Frequency</Label>
              <Select value={newTask.reset_frequency} onValueChange={v => setNewTask(t => ({ ...t, reset_frequency: v }))}>
                <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-700 text-white">
                  <SelectItem value="never">Never</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-gray-300">Description</Label>
            <Textarea
              value={newTask.description}
              onChange={e => setNewTask(t => ({ ...t, description: e.target.value }))}
              className="bg-gray-800 border-gray-600 text-white"
              placeholder="Task description and completion instructions"
              rows={3}
            />
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center space-x-2">
              <Switch
                checked={newTask.is_active}
                onCheckedChange={v => setNewTask(t => ({ ...t, is_active: v }))}
              />
              <Label className="text-gray-300">Active</Label>
            </div>
            <Button
              className="bg-emerald-500 hover:bg-emerald-400 text-black"
              disabled={createMutation.isPending || !newTask.name.trim()}
              onClick={() => createMutation.mutate(newTask)}
            >
              <Plus className="w-4 h-4 mr-2" />
              {createMutation.isPending ? "Creating…" : "Create Task"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Task Management */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-white flex items-center gap-2">
              <ClipboardList className="w-5 h-5 text-cyan-400" /> Task Management
              <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30">
                {tasksData?.tasks?.length ?? 0} tasks
              </Badge>
            </CardTitle>
            <Button
              variant="outline"
              className="border-amber-500/30 text-amber-400 hover:border-amber-400"
              onClick={() => resetMutation.mutate()}
              disabled={resetMutation.isPending}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${resetMutation.isPending ? "animate-spin" : ""}`} />
              Reset Expired
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {tasksLoading ? (
            <div className="flex justify-center py-10"><div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400">
                    <th className="text-left p-3">Task</th>
                    <th className="text-left p-3">Category</th>
                    <th className="text-left p-3">Rewards</th>
                    <th className="text-left p-3">Trigger</th>
                    <th className="text-left p-3">Status</th>
                    <th className="text-left p-3">Completions</th>
                    <th className="text-left p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tasksData?.tasks?.map((task: any) => (
                    <tr key={task.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                      <td className="p-3">
                        <div className="text-white font-medium">{task.name}</div>
                        <div className="text-xs text-gray-500 truncate max-w-[200px]">{task.description}</div>
                      </td>
                      <td className="p-3 text-gray-400 text-xs">
                        {tasksData.categories?.find((c: any) => c.id === task.category_id)?.name}
                      </td>
                      <td className="p-3 text-xs">
                        <div className="text-cyan-400">{task.xp_reward} XP</div>
                        <div className="text-amber-400">{task.vit_reward} VIT</div>
                      </td>
                      <td className="p-3 text-xs text-gray-400 capitalize">
                        {task.trigger_type.replace("_", " ")}
                      </td>
                      <td className="p-3">
                        <StatusBadge status={task.is_active ? "active" : "disabled"} />
                      </td>
                      <td className="p-3 text-gray-400 text-xs">
                        {task.completion_count ?? 0}
                        {task.max_completions && ` / ${task.max_completions}`}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-gray-400 hover:text-white"
                            onClick={() => setEditingTask(task)}>
                            <Edit className="w-3.5 h-3.5" />
                          </Button>
                          <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-400 hover:text-red-300"
                            onClick={() => {
                              if (confirm("Delete this task? This cannot be undone.")) {
                                deleteMutation.mutate(task.id);
                              }
                            }}>
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!tasksData?.tasks?.length && (
                    <tr><td colSpan={7} className="text-center text-gray-500 py-8">No tasks found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Completions */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400" /> Recent Completions
            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
              {completionsData?.total ?? 0} total
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-gray-400">
                  <th className="text-left p-3">User</th>
                  <th className="text-left p-3">Task</th>
                  <th className="text-left p-3">Rewards Earned</th>
                  <th className="text-left p-3">Completed At</th>
                </tr>
              </thead>
              <tbody>
                {completionsData?.completions?.slice(0, 20).map((comp: any) => (
                  <tr key={comp.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                    <td className="p-3 text-gray-300 font-mono text-xs">#{comp.user_id}</td>
                    <td className="p-3 text-white text-sm">{comp.task_name}</td>
                    <td className="p-3 text-xs">
                      <div className="text-cyan-400">{comp.xp_earned} XP</div>
                      <div className="text-amber-400">{comp.vit_earned} VIT</div>
                    </td>
                    <td className="p-3 text-gray-500 text-xs whitespace-nowrap">
                      {comp.completed_at ? new Date(comp.completed_at).toLocaleString() : "-"}
                    </td>
                  </tr>
                ))}
                {!completionsData?.completions?.length && (
                  <tr><td colSpan={4} className="text-center text-gray-500 py-8">No completions yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Edit Task Dialog */}
      {editingTask && (
        <Dialog open onOpenChange={() => setEditingTask(null)}>
          <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit className="w-5 h-5 text-cyan-400" /> Edit Task — {editingTask.name}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-gray-300">Task Name</Label>
                  <Input
                    value={editingTask.name}
                    onChange={e => setEditingTask(t => t && ({ ...t, name: e.target.value } as EditingTask))}
                    className="bg-gray-800 border-gray-600 text-white"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-300">Category</Label>
                  <Select value={editingTask.category_id?.toString()} onValueChange={v => setEditingTask(t => t && ({ ...t, category_id: Number(v) } as EditingTask))}>
                    <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-800 border-gray-700 text-white">
                      {tasksData?.categories?.map((cat: any) => (
                        <SelectItem key={cat.id} value={cat.id.toString()}>{cat.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-300">XP Reward</Label>
                  <Input
                    type="number"
                    value={editingTask.xp_reward}
                    onChange={e => setEditingTask(t => t && ({ ...t, xp_reward: +e.target.value } as EditingTask))}
                    className="bg-gray-800 border-gray-600 text-white"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-300">VIT Reward</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={editingTask.vit_reward}
                    onChange={e => setEditingTask(t => t && ({ ...t, vit_reward: +e.target.value } as EditingTask))}
                    className="bg-gray-800 border-gray-600 text-white"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-300">Trigger Type</Label>
                  <Select value={editingTask.trigger_type} onValueChange={v => setEditingTask(t => t && ({ ...t, trigger_type: v } as EditingTask))}>
                    <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-800 border-gray-700 text-white">
                      <SelectItem value="manual">Manual</SelectItem>
                      <SelectItem value="xp_threshold">XP Threshold</SelectItem>
                      <SelectItem value="prediction_count">Prediction Count</SelectItem>
                      <SelectItem value="deposit_amount">Deposit Amount</SelectItem>
                      <SelectItem value="governance_vote">Governance Vote</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-gray-300">Reset Frequency</Label>
                  <Select value={editingTask.reset_frequency} onValueChange={v => setEditingTask(t => t && ({ ...t, reset_frequency: v } as EditingTask))}>
                    <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-800 border-gray-700 text-white">
                      <SelectItem value="never">Never</SelectItem>
                      <SelectItem value="daily">Daily</SelectItem>
                      <SelectItem value="weekly">Weekly</SelectItem>
                      <SelectItem value="monthly">Monthly</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-gray-300">Description</Label>
                <Textarea
                  value={editingTask.description}
                  onChange={e => setEditingTask(t => t && ({ ...t, description: e.target.value } as EditingTask))}
                  className="bg-gray-800 border-gray-600 text-white"
                  rows={3}
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={editingTask.is_active}
                    onCheckedChange={v => setEditingTask(t => t && ({ ...t, is_active: v } as EditingTask))}
                  />
                  <Label className="text-gray-300">Active</Label>
                </div>
                <Button
                  className="bg-cyan-500 hover:bg-cyan-400 text-black"
                  disabled={updateMutation.isPending}
                  onClick={() => updateMutation.mutate({ id: editingTask.id, body: editingTask })}
                >
                  <Save className="w-4 h-4 mr-2" />
                  {updateMutation.isPending ? "Saving…" : "Save Changes"}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

interface MLAgentSnap {
  status: "idle" | "running" | "ok" | "error" | "disabled";
  last_run_at: string | null;
  next_run_at: string | null;
  run_count: number;
  error_count: number;
  last_result: Record<string, any> | null;
  last_error: string | null;
}

interface MLControlStatus {
  "performance-monitor": MLAgentSnap;
  "retrain-trigger":     MLAgentSnap;
  "model-promoter":      MLAgentSnap;
  "weight-optimizer":    MLAgentSnap;
  "self-healing":        MLAgentSnap;
}

interface MLAgentConfig {
  accuracy_floor:         number;
  retrain_cooldown_hours: number;
  min_flag_cycles:        number;
  auto_promote_threshold: number;
  auto_retrain_enabled:   boolean;
  auto_promote_enabled:   boolean;
}

function MLAgentsTab() {
  const qc = useQueryClient();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [cfg, setCfg]                 = useState<MLAgentConfig | null>(null);
  const [saving, setSaving]           = useState(false);
  const [triggering, setTriggering]   = useState<string | null>(null);

  const { data: mlStatus, isLoading } = useQuery<MLControlStatus>({
    queryKey: ["ml-control-status"],
    queryFn:  () => apiGet<MLControlStatus>("/api/admin/ml-control/status"),
    refetchInterval: 5000,
  });

  const { data: configData } = useQuery<MLAgentConfig>({
    queryKey: ["ml-control-config"],
    queryFn:  () => apiGet<MLAgentConfig>("/api/admin/ml-control/config"),
  });

  useEffect(() => {
    if (configData && !cfg) setCfg({ ...configData });
  }, [configData]);

  useEffect(() => {
    const jobs = mlStatus?.["retrain-trigger"]?.last_result?.triggered_jobs as Record<string, string> | undefined;
    if (jobs) {
      const ids = Object.values(jobs).filter(Boolean);
      if (ids.length > 0) setActiveJobId(prev => prev ?? ids[ids.length - 1]);
    }
  }, [mlStatus]);

  const triggerAgent = async (name: string) => {
    setTriggering(name);
    try {
      await apiPost(`/api/admin/ml-control/trigger/${name}`);
      toast.success(`${name} triggered`);
      setTimeout(() => qc.invalidateQueries({ queryKey: ["ml-control-status"] }), 1500);
    } catch (e: any) {
      toast.error(e?.message || `Failed to trigger ${name}`);
    }
    setTriggering(null);
  };

  const emergencyRetrain = async () => {
    setTriggering("emergency");
    try {
      const r = await apiPost<{ job_id: string }>("/api/admin/ml-control/emergency-retrain");
      if (r?.job_id) {
        setActiveJobId(r.job_id);
        toast.success(`Emergency retrain started — JOB_${r.job_id.slice(0, 8)}`);
      }
    } catch (e: any) {
      toast.error(e?.message || "Emergency retrain failed");
    }
    setTriggering(null);
  };

  const saveConfig = async () => {
    if (!cfg) return;
    setSaving(true);
    try {
      await apiPost("/api/admin/ml-control/config", cfg);
      qc.invalidateQueries({ queryKey: ["ml-control-config"] });
      toast.success("Thresholds saved — agents will use new values on next cycle");
    } catch (e: any) {
      toast.error(e?.message || "Save failed");
    }
    setSaving(false);
  };

  function relML(iso: string | null) {
    if (!iso) return "never";
    const d = (Date.now() - new Date(iso).getTime()) / 1000;
    if (d < 60)   return `${Math.round(d)}s ago`;
    if (d < 3600) return `${Math.round(d / 60)}m ago`;
    return `${Math.round(d / 3600)}h ago`;
  }

  const STATUS_STYLES: Record<string, string> = {
    running:  "bg-blue-500/20 text-blue-300 border-blue-500/30",
    ok:       "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    error:    "bg-red-500/20 text-red-300 border-red-500/30",
    idle:     "bg-slate-700/30 text-slate-400 border-slate-600/30",
    disabled: "bg-slate-800/30 text-slate-500 border-slate-700/30",
  };
  const DOT_STYLES: Record<string, string> = {
    running:  "bg-blue-400 animate-pulse",
    ok:       "bg-emerald-400",
    error:    "bg-red-400 animate-pulse",
    idle:     "bg-slate-500",
    disabled: "bg-slate-700",
  };

  const ML_AGENTS = [
    { key: "performance-monitor" as const, label: "Performance Monitor", icon: <Activity className="w-3.5 h-3.5 text-violet-400" />, description: "Tracks live model accuracy & flags drift",       period: "30m" },
    { key: "retrain-trigger"     as const, label: "Retrain Trigger",     icon: <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />,  description: "Fires training jobs on consecutive flags",    period: "12h" },
    { key: "model-promoter"      as const, label: "Model Promoter",      icon: <Zap className="w-3.5 h-3.5 text-amber-400" />,       description: "Auto-promotes better model versions",         period: "2h"  },
    { key: "weight-optimizer"    as const, label: "Weight Optimizer",    icon: <Brain className="w-3.5 h-3.5 text-purple-400" />,    description: "Re-tunes ensemble weights & temperature",     period: "6h"  },
    { key: "self-healing"        as const, label: "Self-Healing",        icon: <HeartPulse className="w-3.5 h-3.5 text-rose-400" />, description: "Detects & auto-fixes platform issues",        period: "5m"  },
  ];

  function renderInsights(key: string, result: Record<string, unknown> | null) {
    if (!result) return <p className="text-xs text-slate-500 italic">No data yet</p>;

    if (key === "performance-monitor") {
      const flagged = (result.flagged_models as string[] | undefined) ?? [];
      const checked = (result.models_checked  as number  | undefined) ?? 0;
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Checked:</span>
            <span className="text-xs font-bold text-white">{checked}</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-400">Flagged:</span>
            {flagged.length === 0
              ? <span className="text-xs text-emerald-400 font-medium">None — all nominal</span>
              : flagged.map(m => <span key={m} className="text-xs bg-red-500/20 text-red-300 border border-red-500/30 px-1.5 py-0.5 rounded">{m}</span>)
            }
          </div>
        </div>
      );
    }

    if (key === "retrain-trigger") {
      const triggered   = (result.triggered    as string[]                    | undefined) ?? [];
      const flagCounts  = (result.flag_counts  as Record<string, number>      | undefined) ?? {};
      const recent      = (result.recent_triggers as Array<{ model: string; triggered_at: string; consecutive_flags: number; job_id?: string }> | undefined) ?? [];
      const withFlags   = Object.entries(flagCounts).filter(([, n]) => n > 0);
      return (
        <div className="space-y-1.5">
          {withFlags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {withFlags.map(([m, n]) => (
                <span key={m} className="text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded">{m}: {n}</span>
              ))}
            </div>
          )}
          {triggered.length > 0
            ? <p className="text-xs text-cyan-300 font-medium">Triggered: {triggered.join(", ")}</p>
            : <p className="text-xs text-slate-500">No retrains triggered this cycle</p>
          }
          {recent.slice(-2).map((e, i) => (
            <div key={i} className="flex items-center gap-1 text-xs text-slate-400">
              <span className="text-cyan-500">↻</span>
              <span>{e.model}</span>
              {e.job_id && (
                <button onClick={() => setActiveJobId(e.job_id!)}
                  className="text-cyan-400 hover:text-cyan-200 hover:underline underline-offset-2 text-xs">
                  JOB_{e.job_id.slice(0, 6)}
                </button>
              )}
            </div>
          ))}
        </div>
      );
    }

    if (key === "model-promoter") {
      const prod         = result.current_production as string | undefined;
      const promotionLog = (result.promotion_log as Array<{ job_id: string; new_acc: number; prev_acc: number; reason: string }> | undefined) ?? [];
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Production:</span>
            <span className="text-xs font-mono text-amber-300">{prod ? prod.slice(0, 8) : "none"}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">Promoted: <span className="text-emerald-300 font-bold">{result.promoted as number ?? 0}</span></span>
            <span className="text-xs text-slate-400">Skipped: <span className="text-slate-300 font-bold">{result.skipped as number ?? 0}</span></span>
          </div>
          {promotionLog.slice(-1).map((p, i) => (
            <p key={i} className="text-xs text-emerald-400">
              Promoted {p.job_id.slice(0, 6)} · +{((p.new_acc - p.prev_acc) * 100).toFixed(1)}pp
            </p>
          ))}
        </div>
      );
    }

    if (key === "weight-optimizer") {
      const tempFit     = result.temperature_fit  as { fitted?: boolean; temperature?: number; n_samples?: number; reason?: string } | undefined;
      const weightUpdate = result.weight_update   as { models_updated?: number; needs_review?: string[] } | undefined;
      return (
        <div className="space-y-1">
          {tempFit && (
            <div className="text-xs text-slate-400">
              Temperature:{" "}
              <span className="text-purple-300 font-mono">
                {tempFit.fitted ? `${(tempFit.temperature ?? 0).toFixed(4)} (n=${tempFit.n_samples})` : (tempFit.reason ?? "not fitted")}
              </span>
            </div>
          )}
          {weightUpdate && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Models updated:</span>
              <span className="text-white font-bold">{weightUpdate.models_updated ?? 0}</span>
              {(weightUpdate.needs_review?.length ?? 0) > 0 && (
                <span className="text-amber-300">({weightUpdate.needs_review!.length} review)</span>
              )}
            </div>
          )}
        </div>
      );
    }

    if (key === "self-healing") {
      const issues  = (result.issues       as string[] | undefined) ?? [];
      const actions = (result.actions_taken as string[] | undefined) ?? [];
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">Issues: <span className={`font-bold ${issues.length > 0 ? "text-red-300" : "text-emerald-300"}`}>{issues.length}</span></span>
            <span className="text-xs text-slate-400">Actions: <span className="text-white font-bold">{actions.length}</span></span>
          </div>
          {issues.length > 0
            ? issues.slice(0, 2).map((iss, i) => <p key={i} className="text-xs text-red-300 leading-snug">{iss}</p>)
            : <p className="text-xs text-emerald-400">All systems nominal</p>
          }
        </div>
      );
    }

    return null;
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            ML Autonomous Agent Pipeline
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            5 agents govern training decisions end-to-end — monitor decisions, tune thresholds, or intervene manually
          </p>
        </div>
        <Button
          size="sm"
          onClick={emergencyRetrain}
          disabled={triggering === "emergency"}
          className="bg-red-600 hover:bg-red-500 text-white border-0 shrink-0 h-8 text-xs"
        >
          {triggering === "emergency"
            ? <><Loader2 className="w-3 h-3 mr-1.5 animate-spin" />Starting…</>
            : <><Zap className="w-3 h-3 mr-1.5" />Emergency Retrain</>
          }
        </Button>
      </div>

      {/* Live training job surfaced from retrain-trigger */}
      {activeJobId && (
        <TrainingProgressPanel jobId={activeJobId} onDismiss={() => setActiveJobId(null)} />
      )}

      {/* Threshold Config */}
      {cfg && (
        <Card className="bg-slate-900/60 border-slate-700/50">
          <CardHeader className="pb-2 pt-4 px-5">
            <CardTitle className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Settings className="w-4 h-4 text-slate-400" />
              Agent Decision Thresholds
              <span className="ml-auto text-xs font-normal text-slate-500">hot-reloaded on next agent cycle</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="space-y-1">
                <Label className="text-xs text-slate-400">Accuracy Floor</Label>
                <Input
                  type="number" step="0.01" min="0" max="1"
                  value={cfg.accuracy_floor}
                  onChange={e => setCfg(c => c ? { ...c, accuracy_floor: parseFloat(e.target.value) } : c)}
                  className="h-8 text-xs bg-slate-800 border-slate-600 text-white"
                />
                <p className="text-xs text-slate-500">Below this = flagged</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-slate-400">Cooldown (hours)</Label>
                <Input
                  type="number" step="1" min="1"
                  value={cfg.retrain_cooldown_hours}
                  onChange={e => setCfg(c => c ? { ...c, retrain_cooldown_hours: parseInt(e.target.value) } : c)}
                  className="h-8 text-xs bg-slate-800 border-slate-600 text-white"
                />
                <p className="text-xs text-slate-500">Min gap between retrains</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-slate-400">Min Flag Cycles</Label>
                <Input
                  type="number" step="1" min="1"
                  value={cfg.min_flag_cycles}
                  onChange={e => setCfg(c => c ? { ...c, min_flag_cycles: parseInt(e.target.value) } : c)}
                  className="h-8 text-xs bg-slate-800 border-slate-600 text-white"
                />
                <p className="text-xs text-slate-500">Consecutive flags to retrain</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-slate-400">Auto-Promote Δ</Label>
                <div className="relative">
                  <Input
                    type="number" step="0.1" min="0"
                    value={parseFloat((cfg.auto_promote_threshold * 100).toFixed(2))}
                    onChange={e => setCfg(c => c ? { ...c, auto_promote_threshold: parseFloat(e.target.value) / 100 } : c)}
                    className="h-8 text-xs bg-slate-800 border-slate-600 text-white pr-6"
                  />
                  <span className="absolute right-2.5 top-2 text-xs text-slate-500">%</span>
                </div>
                <p className="text-xs text-slate-500">Acc. gain needed to promote</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-2">
                <Switch checked={cfg.auto_retrain_enabled} onCheckedChange={v => setCfg(c => c ? { ...c, auto_retrain_enabled: v } : c)} />
                <Label className="text-xs text-slate-300">Auto-Retrain</Label>
                <span className={`text-xs px-1.5 py-0.5 rounded border font-semibold ${cfg.auto_retrain_enabled ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" : "bg-slate-700/30 text-slate-500 border-slate-600/30"}`}>
                  {cfg.auto_retrain_enabled ? "ON" : "OFF"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={cfg.auto_promote_enabled} onCheckedChange={v => setCfg(c => c ? { ...c, auto_promote_enabled: v } : c)} />
                <Label className="text-xs text-slate-300">Auto-Promote</Label>
                <span className={`text-xs px-1.5 py-0.5 rounded border font-semibold ${cfg.auto_promote_enabled ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" : "bg-slate-700/30 text-slate-500 border-slate-600/30"}`}>
                  {cfg.auto_promote_enabled ? "ON" : "OFF"}
                </span>
              </div>
              <Button
                size="sm"
                onClick={saveConfig}
                disabled={saving}
                className="ml-auto bg-purple-600 hover:bg-purple-500 text-white border-0 h-8 text-xs"
              >
                {saving
                  ? <><Loader2 className="w-3 h-3 mr-1.5 animate-spin" />Saving…</>
                  : <><Save className="w-3 h-3 mr-1.5" />Save Thresholds</>
                }
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agent Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[0, 1, 2, 3, 4].map(i => <Card key={i} className="h-48 bg-slate-900/60 border-slate-700/50 animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {ML_AGENTS.map(({ key, label, icon, description, period }) => {
            const snap      = mlStatus?.[key];
            const statusStr = snap?.status ?? "idle";
            const statCls   = STATUS_STYLES[statusStr] ?? STATUS_STYLES.idle;
            const dotCls    = DOT_STYLES[statusStr]    ?? DOT_STYLES.idle;

            return (
              <Card key={key} className="bg-slate-900/60 border-slate-700/50 hover:border-slate-600/50 transition-colors">
                <CardHeader className="pb-2 pt-4 px-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${dotCls}`} />
                      <span className="text-sm font-semibold text-white truncate">{label}</span>
                    </div>
                    <span className={`text-xs px-1.5 py-0.5 rounded-full border font-medium shrink-0 ${statCls}`}>
                      {statusStr}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    {icon}
                    <span className="text-xs text-slate-500">every {period}</span>
                    <span className="text-xs text-slate-600 ml-auto">{relML(snap?.last_run_at ?? null)}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 leading-snug">{description}</p>
                </CardHeader>

                <CardContent className="px-4 pb-4 space-y-3">
                  {/* Stats strip */}
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-slate-800/50 rounded-lg p-1.5">
                      <div className="text-sm font-bold text-white">{snap?.run_count ?? 0}</div>
                      <div className="text-xs text-slate-500">Runs</div>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-1.5">
                      <div className={`text-sm font-bold ${(snap?.error_count ?? 0) > 0 ? "text-red-400" : "text-white"}`}>
                        {snap?.error_count ?? 0}
                      </div>
                      <div className="text-xs text-slate-500">Errors</div>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-1.5">
                      <div className="text-sm font-bold text-cyan-400">
                        {snap?.next_run_at ? (() => {
                          const d = (new Date(snap.next_run_at).getTime() - Date.now()) / 1000;
                          return d <= 0 ? "now" : d < 60 ? `${Math.round(d)}s` : d < 3600 ? `${Math.round(d / 60)}m` : `${Math.round(d / 3600)}h`;
                        })() : "—"}
                      </div>
                      <div className="text-xs text-slate-500">Next</div>
                    </div>
                  </div>

                  {/* Interpreted last_result */}
                  <div className="min-h-[52px]">
                    {renderInsights(key, snap?.last_result ?? null)}
                  </div>

                  {/* Last error */}
                  {snap?.last_error && (
                    <div className="bg-red-950/40 border border-red-800/30 rounded px-2.5 py-1.5">
                      <p className="text-xs text-red-300 line-clamp-2">{snap.last_error}</p>
                    </div>
                  )}

                  {/* Trigger button */}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => triggerAgent(key)}
                    disabled={triggering === key}
                    className="w-full border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white text-xs h-7"
                  >
                    {triggering === key
                      ? <><Loader2 className="w-3 h-3 mr-1.5 animate-spin" />Triggering…</>
                      : <><RefreshCw className="w-3 h-3 mr-1.5" />Run Now</>
                    }
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Pipeline flow diagram — static visual */}
      <Card className="bg-slate-900/40 border-slate-700/40">
        <CardContent className="px-5 py-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Autonomous Decision Flow</p>
          <div className="flex items-center gap-1 flex-wrap text-xs">
            {[
              { label: "Performance Monitor",  color: "bg-violet-500/20 text-violet-300 border-violet-500/30",  note: "30m · flags drift" },
              { label: "Retrain Trigger",       color: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",        note: "12h · fires training" },
              { label: "Model Promoter",        color: "bg-amber-500/20 text-amber-300 border-amber-500/30",     note: "2h · promotes best" },
              { label: "Weight Optimizer",      color: "bg-purple-500/20 text-purple-300 border-purple-500/30",  note: "6h · tunes weights" },
              { label: "Self-Healing",          color: "bg-rose-500/20 text-rose-300 border-rose-500/30",        note: "5m · watchdog" },
            ].map((step, i) => (
              <div key={i} className="flex items-center gap-1">
                {i > 0 && <span className="text-slate-600">→</span>}
                <div className={`flex flex-col items-center border rounded px-2 py-1 ${step.color}`}>
                  <span className="font-semibold">{step.label}</span>
                  <span className="text-xs opacity-70">{step.note}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

    </div>
  );
}

// ─── Admin Header Health Pills ────────────────────────────────────────

function AdminHealthPills() {
  const { data: health } = useQuery<SystemHealth>({
    queryKey: ["admin-health"],
    queryFn: () => apiGet("/api/admin/system/health"),
    refetchInterval: 15000,
  });

  const pills = [
    { label: "API",      ok: health?.api ?? null },
    { label: "DB",       ok: health?.database ?? null },
    { label: "Redis",    ok: health?.redis ?? null, optional: true },
    { label: `${health?.models_loaded ?? "—"} ML`, ok: (health?.models_loaded ?? 0) > 0 || !health, optional: false },
  ];

  return (
    <div className="hidden md:flex items-center gap-1.5">
      {pills.map(p => (
        <div key={p.label} className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${
          p.ok === null
            ? "bg-gray-700/50 border-gray-600 text-gray-400"
            : p.ok
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : p.optional
                ? "bg-gray-700/50 border-gray-600 text-gray-500"
                : "bg-red-500/10 border-red-500/30 text-red-300"
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${
            p.ok === null ? "bg-gray-500" :
            p.ok ? "bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.8)]" :
            p.optional ? "bg-gray-500" : "bg-red-400 animate-pulse"
          }`} />
          {p.label}
        </div>
      ))}
    </div>
  );
}

// ─── Webhook Log Viewer ────────────────────────────────────────────────

type WebhookEventRow = {
  id: number;
  provider: string;
  event_type: string | null;
  reference: string | null;
  amount: string | null;
  currency: string | null;
  status: string;
  sig_verified: boolean | null;
  outcome: string | null;
  error_msg: string | null;
  payload_summary: Record<string, unknown> | null;
  received_at: string | null;
};

const PROVIDER_COLORS: Record<string, string> = {
  stripe:       "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
  paystack:     "bg-green-500/15 text-green-300 border-green-500/30",
  flutterwave:  "bg-orange-500/15 text-orange-300 border-orange-500/30",
  pi:           "bg-amber-500/15 text-amber-300 border-amber-500/30",
  usdt:         "bg-teal-500/15 text-teal-300 border-teal-500/30",
};

const OUTCOME_COLORS: Record<string, string> = {
  credited:             "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  withdrawal_processed: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  approved:             "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  subscription_activated: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  refunded:             "bg-amber-500/15 text-amber-400 border-amber-500/30",
  payment_failed:       "bg-red-500/15 text-red-400 border-red-500/30",
  approve_failed:       "bg-red-500/15 text-red-400 border-red-500/30",
  complete_failed:      "bg-red-500/15 text-red-400 border-red-500/30",
  cancelled:            "bg-gray-600/30 text-gray-400 border-gray-600",
  unhandled:            "bg-gray-600/30 text-gray-400 border-gray-600",
  already_processed:    "bg-gray-600/30 text-gray-400 border-gray-600",
  not_found:            "bg-gray-600/30 text-gray-400 border-gray-600",
  pending:              "bg-amber-500/15 text-amber-400 border-amber-500/30",
};

function WebhookLogViewer() {
  const qc = useQueryClient();
  const [filterProvider, setFilterProvider] = useState<string>("all");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const { data, isLoading, isFetching } = useQuery<{ events: WebhookEventRow[]; total: number }>({
    queryKey: ["webhook-events", filterProvider],
    queryFn: () => {
      const params = filterProvider !== "all" ? `?provider=${filterProvider}&limit=100` : "?limit=100";
      return apiGet(`/api/admin/integrations/webhook-events${params}`);
    },
    refetchInterval: 30000,
  });

  const events = data?.events ?? [];
  const total  = data?.total ?? 0;

  function fmtTime(iso: string | null) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function fmtRef(ref: string | null) {
    if (!ref) return "—";
    return ref.length > 20 ? `${ref.slice(0, 8)}…${ref.slice(-6)}` : ref;
  }

  const PROVIDER_TABS = ["all", "stripe", "paystack", "flutterwave", "pi", "usdt"];

  return (
    <Card className="bg-gray-900 border-gray-700">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <Activity className="w-4 h-4 text-cyan-400" />
            Webhook Delivery Log
            {total > 0 && (
              <span className="text-xs font-normal text-gray-500 ml-1">{total} total</span>
            )}
            {isFetching && !isLoading && (
              <Loader2 className="w-3 h-3 animate-spin text-gray-500 ml-1" />
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline"
              className="border-gray-600 text-gray-400 hover:text-white h-7 px-2 gap-1 text-xs"
              onClick={() => qc.invalidateQueries({ queryKey: ["webhook-events"] })}>
              <RefreshCw className="w-3 h-3" /> Refresh
            </Button>
          </div>
        </div>
        <CardDescription className="text-gray-500 text-xs mt-1">
          Live log of all incoming payment webhooks. Auto-refreshes every 30 seconds. Signature verification status and processing outcome are shown per event.
        </CardDescription>

        {/* Provider filter tabs */}
        <div className="flex items-center gap-1 mt-2 flex-wrap">
          {PROVIDER_TABS.map(p => (
            <button
              key={p}
              onClick={() => setFilterProvider(p)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold uppercase tracking-wide transition-colors border ${
                filterProvider === p
                  ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                  : "bg-transparent border-gray-700 text-gray-500 hover:border-gray-600 hover:text-gray-400"
              }`}>
              {p === "all" ? "All" : p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-10 text-gray-600">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <div className="text-sm">No webhook events recorded yet</div>
            <div className="text-xs mt-1">Events will appear here as soon as a payment webhook arrives</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  <th className="py-2 px-2 font-medium">Time</th>
                  <th className="py-2 px-2 font-medium">Provider</th>
                  <th className="py-2 px-2 font-medium">Event</th>
                  <th className="py-2 px-2 font-medium">Reference</th>
                  <th className="py-2 px-2 font-medium text-right">Amount</th>
                  <th className="py-2 px-2 font-medium">Sig</th>
                  <th className="py-2 px-2 font-medium">Outcome</th>
                  <th className="py-2 px-2 font-medium w-6" />
                </tr>
              </thead>
              <tbody>
                {events.map(e => (
                  <>
                    <tr
                      key={e.id}
                      className={`border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer transition-colors ${expandedRow === e.id ? "bg-gray-800/40" : ""}`}
                      onClick={() => setExpandedRow(expandedRow === e.id ? null : e.id)}>
                      <td className="py-2 px-2 text-gray-500 whitespace-nowrap font-mono">
                        {fmtTime(e.received_at)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-1.5 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wide ${PROVIDER_COLORS[e.provider] ?? "bg-gray-700/40 text-gray-400 border-gray-600"}`}>
                          {e.provider}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-gray-300 max-w-[160px]">
                        <span className="truncate block font-mono text-[10px]" title={e.event_type ?? ""}>
                          {e.event_type ?? <span className="text-gray-600">—</span>}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-gray-400 font-mono">
                        <span title={e.reference ?? ""}>{fmtRef(e.reference)}</span>
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-gray-300">
                        {e.amount
                          ? <>{parseFloat(e.amount).toLocaleString(undefined, { maximumFractionDigits: 6 })}<span className="text-gray-600 ml-1 text-[9px]">{e.currency}</span></>
                          : <span className="text-gray-700">—</span>}
                      </td>
                      <td className="py-2 px-2">
                        {e.sig_verified === null
                          ? <span className="text-gray-600 text-[10px]">n/a</span>
                          : e.sig_verified
                          ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                          : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                      </td>
                      <td className="py-2 px-2">
                        {e.outcome ? (
                          <span className={`px-1.5 py-0.5 rounded border text-[10px] font-bold ${OUTCOME_COLORS[e.outcome] ?? "bg-gray-700/40 text-gray-400 border-gray-600"}`}>
                            {e.outcome.replace(/_/g, " ")}
                          </span>
                        ) : <span className="text-gray-700">—</span>}
                      </td>
                      <td className="py-2 px-2">
                        <ChevronRight className={`w-3 h-3 text-gray-600 transition-transform ${expandedRow === e.id ? "rotate-90" : ""}`} />
                      </td>
                    </tr>
                    {expandedRow === e.id && (
                      <tr key={`${e.id}-detail`} className="bg-gray-800/30">
                        <td colSpan={8} className="px-4 py-3">
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {e.error_msg && (
                              <div className="col-span-full bg-red-500/10 border border-red-500/20 rounded p-2 text-xs text-red-300">
                                <span className="font-semibold">Error:</span> {e.error_msg}
                              </div>
                            )}
                            {e.reference && (
                              <div>
                                <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Full Reference</div>
                                <code className="text-gray-300 font-mono text-[11px] break-all">{e.reference}</code>
                              </div>
                            )}
                            {e.payload_summary && Object.keys(e.payload_summary).length > 0 && (
                              <div>
                                <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Payload Summary</div>
                                <pre className="text-gray-400 font-mono text-[10px] leading-relaxed bg-gray-900/60 rounded p-2 overflow-x-auto">
                                  {JSON.stringify(e.payload_summary, null, 2)}
                                </pre>
                              </div>
                            )}
                            <div>
                              <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Received At</div>
                              <code className="text-gray-400 font-mono text-[11px]">
                                {e.received_at ? new Date(e.received_at).toISOString() : "—"}
                              </code>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Integrations Tab ─────────────────────────────────────────────────

function IntegrationsTab() {
  const qc = useQueryClient();

  type IntegrationKey = {
    key: string; label: string; group: string; description: string;
    required: boolean; configured: boolean; source: "env" | "db" | "none";
  };

  const [editingKey, setEditingKey] = useState<IntegrationKey | null>(null);
  const [newValue, setNewValue] = useState("");
  const [showNewValue, setShowNewValue] = useState(false);
  const [testingPi, setTestingPi] = useState(false);
  const [piStatus, setPiStatus] = useState<any>(null);

  const { data, isLoading } = useQuery<{ settings: IntegrationKey[]; total: number }>({
    queryKey: ["integration-settings"],
    queryFn: () => apiGet("/api/admin/integrations/settings"),
  });

  const saveMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      apiPut("/api/admin/integrations/settings", { key, value }),
    onSuccess: (_d, vars) => {
      toast.success(`${vars.key} saved — active immediately`);
      qc.invalidateQueries({ queryKey: ["integration-settings"] });
      qc.invalidateQueries({ queryKey: ["admin-config-status"] });
      setEditingKey(null);
      setNewValue("");
    },
    onError: (e: any) => toast.error(e?.message || "Failed to save key"),
  });

  const deleteMutation = useMutation({
    mutationFn: (key: string) => apiDelete(`/api/admin/integrations/settings/${key}`),
    onSuccess: (_d, key) => {
      toast.success(`${key} removed from database`);
      qc.invalidateQueries({ queryKey: ["integration-settings"] });
      qc.invalidateQueries({ queryKey: ["admin-config-status"] });
    },
    onError: () => toast.error("Failed to remove key"),
  });

  const testPiConnection = async () => {
    setTestingPi(true);
    try {
      const result: any = await apiGet("/api/admin/pi/status");
      setPiStatus(result);
      toast.success(result?.configured ? "Pi Network keys are configured" : "Pi Network keys are missing");
    } catch (e: any) {
      toast.error(e?.message || "Pi status check failed");
    } finally {
      setTestingPi(false);
    }
  };

  // Group settings by their group field
  const grouped = (data?.settings ?? []).reduce<Record<string, IntegrationKey[]>>((acc, s) => {
    if (!acc[s.group]) acc[s.group] = [];
    acc[s.group].push(s);
    return acc;
  }, {});

  // Provider metadata — icon, color, description per group
  const PROVIDER_META: Record<string, {
    icon: React.ElementType; color: string; bg: string; border: string; description: string;
    testAction?: () => void; testLabel?: string; testLoading?: boolean;
  }> = {
    "Pi Network":     { icon: Zap,        color: "text-amber-400",  bg: "bg-amber-500/10",  border: "border-amber-500/30",  description: "Accept Pi cryptocurrency from Pi Network users. Set App ID and Secret from developer.pi.",         testAction: testPiConnection, testLabel: "Test Connection", testLoading: testingPi },
    "Payments":       { icon: CreditCard, color: "text-blue-400",   bg: "bg-blue-500/10",   border: "border-blue-500/30",   description: "Stripe (USD subscriptions), Paystack (NGN deposits), and Flutterwave (MoMo / card) processors." },
    "Sports Data":    { icon: Activity,   color: "text-cyan-400",   bg: "bg-cyan-500/10",   border: "border-cyan-500/30",   description: "Football-Data.org, The Odds API, and TheSportsDB for fixtures, live odds, and match data."         },
    "Messaging":      { icon: Send,       color: "text-green-400",  bg: "bg-green-500/10",  border: "border-green-500/30",  description: "Telegram bot for signal alerts and Resend for transactional email (verification, password reset)."  },
    "VIT AI":         { icon: Brain,      color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/30", description: "Native ML model flags and Google Cloud Storage bucket for syncing trained model weights."            },
    "Blockchain":     { icon: Network,    color: "text-teal-400",   bg: "bg-teal-500/10",   border: "border-teal-500/30",   description: "Base L2 RPC endpoint and VITCoin ERC-20 contract address for on-chain verification and bridge."    },
    "Infrastructure": { icon: Server,     color: "text-rose-400",   bg: "bg-rose-500/10",   border: "border-rose-500/30",   description: "Redis connection URL and SMTP credentials for background jobs and email delivery."                  },
    "Security":       { icon: Shield,     color: "text-red-400",    bg: "bg-red-500/10",    border: "border-red-500/30",    description: "JWT signing key and legacy admin API key. JWT Secret is required in production."                    },
  };

  const GROUP_ORDER = ["Pi Network", "Payments", "Sports Data", "Messaging", "VIT AI", "Blockchain", "Infrastructure", "Security"];

  // Payment sub-providers for cleaner display within the Payments group
  const PAYMENT_SUBS: Record<string, { color: string; keys: string[] }> = {
    "Stripe":      { color: "text-indigo-400", keys: ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"] },
    "Paystack":    { color: "text-green-400",  keys: ["PAYSTACK_SECRET_KEY", "PAYSTACK_WEBHOOK_SECRET"] },
    "Flutterwave": { color: "text-orange-400", keys: ["FLW_SECRET_KEY", "FLW_PUBLIC_KEY", "FLW_WEBHOOK_SECRET"] },
  };

  function statusBadge(keys: IntegrationKey[]) {
    const n = keys.filter(k => k.configured).length;
    if (n === keys.length) return { label: "Connected", cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" };
    if (n > 0)             return { label: "Partial",   cls: "bg-amber-500/15 text-amber-400 border-amber-500/30"     };
    return                        { label: "Not set",   cls: "bg-gray-700/40 text-gray-500 border-gray-700"           };
  }

  function KeyRow({ k }: { k: IntegrationKey }) {
    return (
      <div className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg border border-gray-800/80 bg-gray-900/30 hover:bg-gray-900/60 transition-colors">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <span className="text-white text-xs font-semibold">{k.label}</span>
            {k.required && (
              <span className="text-[9px] uppercase font-bold bg-red-500/20 text-red-400 border border-red-500/30 px-1 py-0.5 rounded leading-none">
                Required
              </span>
            )}
            {k.source === "env" && (
              <span className="text-[9px] uppercase font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 px-1 py-0.5 rounded flex items-center gap-1 leading-none">
                <Shield className="w-2 h-2" /> Env
              </span>
            )}
            {k.source === "db" && (
              <span className="text-[9px] uppercase font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-1 py-0.5 rounded flex items-center gap-1 leading-none">
                <Database className="w-2 h-2" /> DB
              </span>
            )}
          </div>
          <div className="text-[10px] text-gray-600 font-mono leading-tight">{k.description}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {k.source === "db" && (
            <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-gray-600 hover:text-red-400"
              title="Remove from database" onClick={() => deleteMutation.mutate(k.key)}>
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
          <Button size="sm" variant="outline"
            className={`h-6 px-2.5 text-[10px] font-bold uppercase tracking-wider transition-colors ${
              k.configured
                ? "border-gray-600 text-gray-400 hover:border-amber-500/40 hover:text-amber-400"
                : "border-amber-500/40 text-amber-400 hover:bg-amber-500/10"
            }`}
            onClick={() => { setEditingKey(k); setNewValue(""); setShowNewValue(false); }}>
            {k.configured ? "Update" : "Set"}
          </Button>
          {k.configured
            ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            : <XCircle    className="w-3.5 h-3.5 text-gray-700 shrink-0" />}
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const orderedGroups = GROUP_ORDER.filter(g => grouped[g]);
  const totalConfigured  = (data?.settings ?? []).filter(s => s.configured).length;
  const totalKeys        = data?.total ?? 0;

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-white font-bold text-lg flex items-center gap-2">
            <Plug className="w-5 h-5 text-cyan-400" /> Integration Settings
          </h2>
          <p className="text-gray-400 text-sm mt-0.5">
            Manage payment providers, data APIs, and third-party services.
            Keys saved here are encrypted in the database and active immediately — no restart needed.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <div className="text-xs font-mono text-gray-500 bg-gray-800 border border-gray-700 rounded px-2 py-1">
            <span className="text-white">{totalConfigured}</span>/{totalKeys} configured
          </div>
          <Button size="sm" variant="outline" className="border-gray-600 text-gray-400 hover:text-white gap-1.5"
            onClick={() => qc.invalidateQueries({ queryKey: ["integration-settings"] })}>
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Provider Cards */}
      {orderedGroups.map(group => {
        const keys      = grouped[group] ?? [];
        const meta      = PROVIDER_META[group] ?? { icon: Settings, color: "text-gray-400", bg: "bg-gray-700/30", border: "border-gray-700", description: "" };
        const MetaIcon  = meta.icon;
        const badge     = statusBadge(keys);
        const isPayments = group === "Payments";

        return (
          <Card key={group} className={`bg-gray-900 border ${meta.border}`}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-lg ${meta.bg} flex items-center justify-center shrink-0`}>
                    <MetaIcon className={`w-5 h-5 ${meta.color}`} />
                  </div>
                  <div>
                    <CardTitle className="text-white text-sm flex items-center gap-2 flex-wrap">
                      {group}
                      <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </CardTitle>
                    <CardDescription className="text-gray-500 text-xs mt-0.5">{meta.description}</CardDescription>
                  </div>
                </div>
                {meta.testAction && (
                  <Button size="sm" variant="outline"
                    className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10 text-xs shrink-0"
                    disabled={meta.testLoading}
                    onClick={meta.testAction}>
                    {meta.testLoading
                      ? <><Loader2 className="w-3 h-3 animate-spin mr-1.5" />Testing…</>
                      : <><Activity className="w-3 h-3 mr-1.5" />{meta.testLabel}</>}
                  </Button>
                )}
              </div>

              {/* Pi Network status result */}
              {group === "Pi Network" && piStatus && (
                <div className={`mt-3 p-3 rounded-lg border text-xs font-mono ${
                  piStatus.configured
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                    : "bg-amber-500/10 border-amber-500/30 text-amber-300"
                }`}>
                  {piStatus.configured
                    ? `✅ Configured · App ID: ${piStatus.app_id ?? "set"} · Sandbox: ${piStatus.sandbox_mode ?? "true"}`
                    : "⚠️  Pi Network keys not fully configured — Pi deposits are disabled until all keys are set"}
                </div>
              )}
            </CardHeader>

            <CardContent className="pt-0 space-y-2">
              {isPayments ? (
                /* Split Payments into Stripe / Paystack / Flutterwave sub-sections */
                Object.entries(PAYMENT_SUBS).map(([provName, prov]) => {
                  const provKeys = keys.filter(k => prov.keys.includes(k.key));
                  if (provKeys.length === 0) return null;
                  const pb = statusBadge(provKeys);
                  return (
                    <div key={provName} className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <div className="h-px flex-1 bg-gray-800" />
                        <span className={`text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 ${prov.color}`}>
                          {provName}
                          <span className={`px-1.5 py-0.5 rounded border text-[9px] ${pb.cls}`}>{pb.label}</span>
                        </span>
                        <div className="h-px flex-1 bg-gray-800" />
                      </div>
                      <div className="space-y-1.5">
                        {provKeys.map(k => <KeyRow key={k.key} k={k} />)}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="space-y-1.5">
                  {keys.map(k => <KeyRow key={k.key} k={k} />)}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}

      {/* ── Webhook Delivery Log ──────────────────────────────────────── */}
      <WebhookLogViewer />

      {/* Edit / Set Key Dialog */}
      {editingKey && (
        <Dialog open onOpenChange={() => setEditingKey(null)}>
          <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-base">
                <Key className="w-4 h-4 text-amber-400" />
                {editingKey.configured ? "Update" : "Set"} — {editingKey.label}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-sm text-gray-400 leading-relaxed">{editingKey.description}</p>
              <div className="space-y-2">
                <Label className="text-gray-300 text-sm">Value</Label>
                <div className="relative">
                  <Input
                    type={showNewValue ? "text" : "password"}
                    placeholder={`Enter value for ${editingKey.key}`}
                    value={newValue}
                    onChange={e => setNewValue(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === "Enter" && newValue.trim() && !saveMutation.isPending)
                        saveMutation.mutate({ key: editingKey.key, value: newValue.trim() });
                    }}
                    className="bg-gray-800 border-gray-600 text-white pr-10 font-mono text-sm"
                    autoFocus
                  />
                  <Button size="sm" variant="ghost"
                    className="absolute right-1 top-1 h-7 w-7 p-0 text-gray-500 hover:text-white"
                    onClick={() => setShowNewValue(v => !v)}>
                    {showNewValue ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </Button>
                </div>
                <p className="text-xs text-gray-600">
                  Environment variable: <span className="font-mono text-amber-400">{editingKey.key}</span>
                </p>
              </div>
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-xs text-emerald-300 space-y-1.5">
                <div className="flex items-center gap-1.5 font-semibold">
                  <Database className="w-3 h-3" /> Saved to database — survives restarts
                </div>
                <div className="text-emerald-400/80">
                  Encrypted with AES-256 and injected into the running process immediately.
                  Keys set here override nothing set in Replit Secrets (Secrets always take priority).
                </div>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" className="border-gray-600 text-gray-300"
                onClick={() => setEditingKey(null)}>
                Cancel
              </Button>
              <Button
                className="bg-amber-500 text-black hover:bg-amber-400 font-bold"
                disabled={!newValue.trim() || saveMutation.isPending}
                onClick={() => saveMutation.mutate({ key: editingKey.key, value: newValue.trim() })}>
                {saveMutation.isPending
                  ? <><Loader2 className="w-3 h-3 animate-spin mr-1.5" />Saving…</>
                  : <><Save className="w-3 h-3 mr-1.5" />Save & Apply</>}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

// ─── Root Admin Page ──────────────────────────────────────────────────

export default function AdminPage() {
  const { user, isAdmin, isSuperAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState("dashboard");

  if (!user) return <Redirect to="/login" />;
  if (!isAdmin) return <Redirect to="/dashboard" />;

  const adminRoleLabel: Record<string, string> = {
    super_admin: "Super Admin", admin: "Admin",
    auditor: "Auditor", support: "Support",
  };

  const tabGroups = [
    {
      label: "OVERVIEW",
      color: "text-cyan-500",
      tabs: [
        { value: "dashboard", label: "Dashboard", icon: BarChart2 },
      ],
    },
    {
      label: "INTELLIGENCE",
      color: "text-purple-400",
      tabs: [
        { value: "models",      label: "Models",      icon: Cpu },
        { value: "calibration", label: "Calibration", icon: Activity },
        { value: "agents",      label: "Agents",      icon: Brain },
      ],
    },
    {
      label: "OPERATIONS",
      color: "text-emerald-400",
      tabs: [
        { value: "users",  label: "Users",  icon: Users },
        { value: "kyc",    label: "KYC",    icon: UserCheck },
        { value: "tasks",  label: "Tasks",  icon: ClipboardList },
      ],
    },
    {
      label: "FINANCE",
      color: "text-amber-400",
      tabs: [
        { value: "markets",        label: "Markets",       icon: TrendingUp },
        { value: "currency",       label: "Currency",      icon: Coins },
        { value: "subscriptions",  label: "Subscriptions", icon: CreditCard },
        { value: "leagues",        label: "Leagues",       icon: Globe },
      ],
    },
    {
      label: "SYSTEM",
      color: "text-rose-400",
      tabs: [
        { value: "integrations", label: "Integrations", icon: Plug },
        { value: "system",       label: "System",       icon: Settings },
        { value: "audit",        label: "Audit",        icon: ShieldCheck },
      ],
    },
  ];

  const groupColor: Record<string, string> = {
    OVERVIEW:     "data-[state=active]:bg-cyan-500 data-[state=active]:text-black data-[state=active]:shadow-[0_0_12px_rgba(6,182,212,0.4)]",
    INTELLIGENCE: "data-[state=active]:bg-purple-500 data-[state=active]:text-white data-[state=active]:shadow-[0_0_12px_rgba(168,85,247,0.4)]",
    OPERATIONS:   "data-[state=active]:bg-emerald-500 data-[state=active]:text-black data-[state=active]:shadow-[0_0_12px_rgba(52,211,153,0.4)]",
    FINANCE:      "data-[state=active]:bg-amber-500 data-[state=active]:text-black data-[state=active]:shadow-[0_0_12px_rgba(245,158,11,0.4)]",
    SYSTEM:       "data-[state=active]:bg-rose-500 data-[state=active]:text-white data-[state=active]:shadow-[0_0_12px_rgba(244,63,94,0.4)]",
  };

  const activeGroup = tabGroups.find(g => g.tabs.some(t => t.value === activeTab));

  return (
    <div className="min-h-screen bg-gray-950 text-white">

      {/* ── Command Header ─────────────────────────────────────────── */}
      <div className="relative border-b border-gray-800 bg-gray-950">
        {/* Gradient accent line */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/60 to-transparent" />

        <div className="px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          {/* Left: branding */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="absolute inset-0 rounded-lg bg-cyan-500/20 blur-sm" />
              <div className="relative w-9 h-9 rounded-lg border border-cyan-500/40 bg-gray-900 flex items-center justify-center">
                <Shield className="w-5 h-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <div className="font-bold text-white text-base leading-tight tracking-wide">
                ADMIN <span className="text-cyan-400">CONTROL CENTER</span>
              </div>
              <div className="text-[10px] text-gray-500 uppercase tracking-widest">VIT Network — v5.5.0</div>
            </div>
          </div>

          {/* Center: health pills */}
          <AdminHealthPills />

          {/* Right: user */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="text-right hidden sm:block">
              <div className="text-sm text-white font-medium leading-tight">{user.username}</div>
              <div className={`text-[10px] font-semibold tracking-wide uppercase ${isSuperAdmin ? "text-amber-400" : "text-cyan-400"}`}>
                {adminRoleLabel[user.admin_role ?? "admin"] ?? "Admin"}
              </div>
            </div>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm border ${
              isSuperAdmin
                ? "bg-amber-500 text-black border-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.5)]"
                : "bg-cyan-500/20 text-cyan-400 border-cyan-500/40"
            }`}>
              {user.username[0]?.toUpperCase()}
            </div>
          </div>
        </div>

        {/* Active group accent */}
        {activeGroup && (
          <div className={`absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent ${
            activeGroup.label === "OVERVIEW"     ? "via-cyan-500/50" :
            activeGroup.label === "INTELLIGENCE" ? "via-purple-500/50" :
            activeGroup.label === "OPERATIONS"   ? "via-emerald-500/50" :
            activeGroup.label === "FINANCE"      ? "via-amber-500/50" :
            "via-rose-500/50"
          } to-transparent`} />
        )}
      </div>

      {/* ── Main Content ───────────────────────────────────────────── */}
      <div className="max-w-screen-xl mx-auto px-3 sm:px-5 py-5">
        <Tabs value={activeTab} onValueChange={setActiveTab}>

          {/* Grouped Tab Navigation — TabsList must wrap ALL TabsTrigger elements */}
          <div className="mb-6">
            <TabsList className="h-auto flex flex-wrap gap-x-1 gap-y-1.5 bg-transparent p-0 justify-start border-0 rounded-none">
              {tabGroups.map((group, gi) => (
                <div key={group.label} className="flex items-center gap-1">
                  {gi > 0 && <div className="w-px h-5 bg-gray-700 mx-1 hidden sm:block" />}
                  <div className="flex items-center gap-0.5">
                    {/* Group label — only on desktop */}
                    <span className={`hidden lg:block text-[9px] font-bold tracking-widest uppercase px-1 ${group.color} opacity-70`}>
                      {group.label}
                    </span>
                    {group.tabs.map(tab => (
                      <TabsTrigger
                        key={tab.value}
                        value={tab.value}
                        className={`${groupColor[group.label]} flex items-center gap-1.5 text-gray-400 hover:text-white
                          px-3 py-1.5 rounded-md transition-all text-xs font-medium
                          data-[state=inactive]:bg-transparent data-[state=inactive]:border data-[state=inactive]:border-transparent
                          data-[state=inactive]:hover:bg-gray-800/60 data-[state=inactive]:hover:border-gray-700`}
                      >
                        <tab.icon className="w-3.5 h-3.5 shrink-0" />
                        <span className="hidden sm:inline whitespace-nowrap">{tab.label}</span>
                      </TabsTrigger>
                    ))}
                  </div>
                </div>
              ))}
            </TabsList>
          </div>

          <TabsContent value="dashboard"><DashboardTab /></TabsContent>
          <TabsContent value="users"><UsersTab /></TabsContent>
          <TabsContent value="kyc"><KYCTab /></TabsContent>
          <TabsContent value="tasks"><TasksTab /></TabsContent>
          <TabsContent value="models"><ModelsTab /></TabsContent>
          <TabsContent value="calibration"><CalibrationTab /></TabsContent>
          <TabsContent value="leagues"><LeaguesTab /></TabsContent>
          <TabsContent value="markets"><MarketsTab /></TabsContent>
          <TabsContent value="currency"><CurrencyTab /></TabsContent>
          <TabsContent value="subscriptions"><SubscriptionsTab /></TabsContent>
          <TabsContent value="integrations"><IntegrationsTab /></TabsContent>
          <TabsContent value="system"><SystemTab /></TabsContent>
          <TabsContent value="audit"><AuditTab /></TabsContent>
          <TabsContent value="agents"><MLAgentsTab /></TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function CalibrationTab() {
  const [rollingWindow, setRollingWindow] = useState(50);
  const [busy, setBusy] = useState(false);
  const qc = useQueryClient();

  const reportQ = useQuery<any>({
    queryKey: ["ai-accuracy-report", rollingWindow],
    queryFn: () => apiGet(`/api/ai-engine/accuracy/report?window=${rollingWindow}`),
  });

  // Provider activity stats — reads from AgentInsight + AIPrediction, no auth needed
  const providerStatsQ = useQuery<any>({
    queryKey: ["ai-provider-stats"],
    queryFn: () => apiGet("/api/ai-engine/provider-stats"),
    refetchInterval: 60000,
  });

  const updatePerfMutation = useUpdateAiPerformance();

  async function refit() {
    setBusy(true);
    try {
      const res = await apiPost<any>(
        `/api/ai-engine/accuracy/enhance?min_samples=1&window=${rollingWindow}`, {},
      );
      const fit = res?.temperature_fit;
      if (!fit) {
        toast.error("No response from calibration endpoint");
        return;
      }
      if (fit.fitted) {
        const preNll  = fit.pre_fit_log_loss ?? fit.pre_nll;
        const postNll = fit.post_fit_log_loss ?? fit.best_nll;
        const T       = fit.temperature ?? fit.best_T;
        const msg = `T=${Number(T).toFixed(3)} — log-loss ${Number(preNll).toFixed(4)} → ${Number(postNll).toFixed(4)}`;
        if (fit.low_confidence) {
          toast.message(`Temperature refit (low confidence — only ${fit.n_samples} sample): ${msg}`);
        } else {
          toast.success(`Temperature refit: ${msg}`);
        }
      } else {
        toast.message(fit.reason || "Temperature not refit — no data yet");
      }
      reportQ.refetch();
    } catch (e: any) {
      toast.error(e?.message || "Re-fit failed");
    } finally {
      setBusy(false);
    }
  }

  const data   = reportQ.data;
  const models: any[] = data?.models || [];
  const T      = data?.current_temperature ?? 1.0;
  const providers: any[] = providerStatsQ.data?.providers || [];
  const activeProviders   = providers.filter((p: any) => p.has_data);

  return (
    <div className="space-y-4">
      {/* ── Ensemble Calibration ──────────────────────────────────────── */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            Ensemble Calibration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-sm text-gray-300">
              Current temperature:{" "}
              <span className="font-mono text-cyan-400">{Number(T).toFixed(3)}</span>
              <span className="ml-2 text-xs text-gray-500">
                (T&gt;1 softens overconfident probabilities)
              </span>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <label className="text-xs text-gray-400">Window</label>
              <input
                type="number"
                min={10}
                max={500}
                value={rollingWindow}
                onChange={(e) => setRollingWindow(Math.max(10, Math.min(500, Number(e.target.value) || 50)))}
                className="w-20 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-white"
              />
              <Button onClick={refit} disabled={busy} size="sm">
                {busy ? "Re-fitting…" : "Re-fit Temperature"}
              </Button>
            </div>
          </div>

          {reportQ.isLoading ? (
            <div className="text-gray-400 text-sm">Loading rolling-window report…</div>
          ) : models.length === 0 ? (
            <div className="rounded border border-gray-700 bg-gray-900/60 p-4 text-sm space-y-2">
              <div className="text-gray-300 font-medium flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                No settled predictions in the rolling window yet
              </div>
              <div className="text-gray-500 text-xs leading-relaxed">
                This table is computed from <span className="text-gray-300">AIPredictionAudit</span> records
                joined to matches with a known final result. It will populate once matches settle and the
                ensemble has generated audit-logged predictions for them.
              </div>
              <div className="text-gray-500 text-xs">
                In the meantime, the <span className="text-amber-400 font-mono">Accountability</span> tab
                shows per-model bootstrapped metrics as a baseline.
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="py-2 px-2">Model</th>
                    <th className="py-2 px-2 text-right">Samples</th>
                    <th className="py-2 px-2 text-right">Accuracy</th>
                    <th className="py-2 px-2 text-right">Log-loss</th>
                    <th className="py-2 px-2 text-right">Brier</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m, i) => (
                    <tr key={m.model_key} className="border-b border-gray-800/50">
                      <td className="py-2 px-2 font-mono text-cyan-300">
                        {i + 1}. {m.model_key}
                      </td>
                      <td className="py-2 px-2 text-right text-gray-300">{m.samples}</td>
                      <td className="py-2 px-2 text-right text-gray-200">
                        {(m.accuracy_1x2 * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-yellow-400">
                        {Number(m.log_loss).toFixed(4)}
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-gray-300">
                        {Number(m.brier).toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="text-xs text-gray-500 mt-3">
                Models sorted best → worst by log-loss (a strictly proper score). Lower is better.
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── AI Provider Activity ──────────────────────────────────────── */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle className="text-white flex items-center gap-2">
              <Brain className="w-4 h-4 text-purple-400" />
              AI Source Performance
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="border-gray-600 text-gray-400 hover:text-white"
                onClick={() => {
                  providerStatsQ.refetch();
                  qc.invalidateQueries({ queryKey: ["ai-provider-stats"] });
                }}
              >
                <RefreshCw className="w-3 h-3 mr-1.5" /> Refresh
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="border-purple-500/50 text-purple-300 hover:text-white hover:bg-purple-950/50"
                disabled={updatePerfMutation.isPending}
                title="Recompute accuracy from settled match outcomes (requires settled AIPrediction rows)"
                onClick={() => updatePerfMutation.mutate(undefined, {
                  onSuccess: () => {
                    toast.success("AI performance metrics updated from settled predictions");
                    qc.invalidateQueries({ queryKey: ["ai-provider-stats"] });
                  },
                  onError: (e: any) => toast.error(e?.message || "Update failed"),
                })}
              >
                {updatePerfMutation.isPending ? "Updating…" : "Update Performance"}
              </Button>
            </div>
          </div>
          <CardDescription className="text-gray-500 text-xs mt-1">
            Activity across the native AI layer derived from agent insight calls.
            "Accuracy" column populates only after matches settle and <span className="font-mono">Update Performance</span> is run.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {providerStatsQ.isLoading ? (
            <div className="text-gray-400 text-sm">Loading provider stats…</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="py-2 px-2">Provider</th>
                    <th className="py-2 px-2 text-right">Total calls</th>
                    <th className="py-2 px-2 text-right">Agent insights</th>
                    <th className="py-2 px-2 text-right">Avg confidence</th>
                    <th className="py-2 px-2 text-right">Accuracy</th>
                    <th className="py-2 px-2 text-right">Last active</th>
                  </tr>
                </thead>
                <tbody>
                  {providers.map((p: any) => (
                    <tr key={p.provider} className={`border-b border-gray-800/50 ${!p.has_data ? "opacity-40" : ""}`}>
                      <td className="py-2 px-2">
                        <div className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full ${p.has_data ? "bg-emerald-400" : "bg-gray-600"}`} />
                          <span className="font-mono text-purple-300 capitalize">{p.provider}</span>
                        </div>
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-gray-200">
                        {p.total_calls > 0 ? p.total_calls.toLocaleString() : "—"}
                      </td>
                      <td className="py-2 px-2 text-right text-gray-400">
                        {p.insight_count > 0 ? p.insight_count.toLocaleString() : "—"}
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-blue-400">
                        {p.avg_confidence != null ? `${(p.avg_confidence * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-2 px-2 text-right text-gray-200">
                        {p.accuracy != null
                          ? `${(p.accuracy * 100).toFixed(1)}%`
                          : <span className="text-gray-600 text-xs">awaiting settlements</span>}
                      </td>
                      <td className="py-2 px-2 text-right text-gray-400 text-xs">
                        {p.last_active ? new Date(p.last_active).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {activeProviders.length === 0 && (
                <div className="text-center text-gray-500 text-xs py-3 border-t border-gray-800 mt-2">
                  No agent calls recorded yet — providers will appear here once agents generate insights.
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
