import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPatch, apiPut, apiDelete } from "@/lib/apiClient";
import {
  useAdminCalibrationFit,
  useAdminCalibrationReload,
  useAdminSettleResults,
  useAdminBackfillFtResults,
  useAdminAccumulatorPlaceBet,
  useAdminAccumulatorSend,
  useAiFeedConsensus,
  useGetAiPerformance,
  useGetAiReport,
} from "@/api-client/index";
import { useAuth } from "@/lib/auth";
import { PermissionGate } from "@/components/auth/PermissionGate";
import { Redirect } from "wouter";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Activity, Database, Settings, ShieldCheck, BarChart2,
  Globe, Coins, CreditCard, BookOpen, Cpu, Key, RefreshCw,
  Trash2, Ban, Edit, Plus, CheckCircle, XCircle, AlertCircle,
  TrendingUp, Server, Zap, Save, Search, Eye, EyeOff,
  ChevronRight, Shield, Lock, Unlock, Download,
  Users, UserCheck, Upload, Package, ClipboardList, Star, Send,
  Brain,
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
    queryFn: () => apiGet("/admin/stats"),
    refetchInterval: 30000,
  });
  const { data: health } = useQuery<SystemHealth>({
    queryKey: ["admin-health"],
    queryFn: () => apiGet("/admin/system/health"),
    refetchInterval: 15000,
  });
  const qc = useQueryClient();

  const clearCache = useMutation({
    mutationFn: () => apiPost("/admin/system/cache/clear", {}),
    onSuccess: () => toast.success("Cache cleared"),
    onError: () => toast.error("Failed to clear cache"),
  });
  const backup = useMutation({
    mutationFn: () => apiPost("/admin/system/backup", {}),
    onSuccess: (d: any) => toast.success(`Backup: ${d.backup}`),
    onError: () => toast.error("Backup failed"),
  });
  const fetchFixtures = useMutation({
    mutationFn: () => apiPost("/admin/matches/fetch-fixtures?count=50&days=14", {}),
    onSuccess: (d: any) => {
      toast.success(`Pipeline: fetched ${d.stored ?? 0} new fixtures (${d.skipped_existing ?? 0} already existed)`);
      qc.invalidateQueries({ queryKey: ["/matches/upcoming"] });
      qc.invalidateQueries({ queryKey: ["matches-recent"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: () => toast.error("Fixture fetch failed — check Football API key in settings"),
  });

  const kpis = [
    { label: "Total Users",    value: stats?.users ?? 0,         icon: Users,      color: "text-cyan-400" },
    { label: "Total Matches",  value: stats?.matches ?? 0,        icon: BarChart2,  color: "text-purple-400" },
    { label: "Training Jobs",  value: stats?.training_jobs ?? 0,  icon: Cpu,        color: "text-emerald-400" },
    { label: "Active Plans",   value: stats?.active_plans ?? 0,   icon: CreditCard, color: "text-amber-400" },
  ];

  if (sLoading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map(k => (
          <Card key={k.label} className="bg-gray-900 border-gray-700">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">{k.label}</span>
                <k.icon className={`w-5 h-5 ${k.color}`} />
              </div>
              <div className="text-3xl font-bold text-white">{k.value.toLocaleString()}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* System Health */}
        <Card className="bg-gray-900 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-cyan-400" /> System Health
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {health ? (
              <>
                {([
                  { label: "API Server",    ok: health.api,                            optional: false },
                  { label: "Database",      ok: health.database,                       optional: false },
                  { label: "Redis",         ok: health.redis === true,                 optional: health.redis === null },
                  { label: "ML Models",     ok: (health.models_loaded ?? 0) > 0,       optional: false },
                  { label: "Football API",  ok: health.football_api === true,          optional: health.football_api == null, limited: health.football_api === "limited" },
                  { label: "Odds API",      ok: health.odds_api === true,              optional: health.odds_api == null },
                ] as { label: string; ok: boolean; optional: boolean; limited?: boolean }[]).map(row => (
                  <div key={row.label} className="flex items-center justify-between">
                    <span className="text-gray-300 flex items-center gap-2">
                      <HealthDot ok={row.limited ? false : row.ok} optional={row.optional} /> {row.label}
                    </span>
                    {row.optional ? (
                      <span className="text-gray-500 text-sm">Not configured</span>
                    ) : row.limited ? (
                      <span className="text-amber-400 text-sm">Tier limited</span>
                    ) : (
                      <span className={row.ok ? "text-emerald-400 text-sm" : "text-red-400 text-sm"}>
                        {row.ok ? "Online" : "Offline"}
                      </span>
                    )}
                  </div>
                ))}
                <div className="pt-2 border-t border-gray-700 grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-xs text-gray-500">CPU</div>
                    <div className={`font-bold ${health.cpu_pct > 80 ? "text-red-400" : "text-white"}`}>{health.cpu_pct}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">RAM</div>
                    <div className={`font-bold ${health.mem_pct > 85 ? "text-red-400" : "text-white"}`}>{health.mem_pct}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Disk</div>
                    <div className={`font-bold ${health.disk_pct > 90 ? "text-red-400" : "text-white"}`}>{health.disk_pct}%</div>
                  </div>
                </div>
              </>
            ) : <div className="text-gray-500 text-sm">Loading...</div>}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="bg-gray-900 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-400" /> Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            {[
              { label: "Refresh Stats",   icon: RefreshCw,  action: () => qc.invalidateQueries({ queryKey: ["admin-stats"] }),  color: "border-cyan-500/30 hover:border-cyan-400 text-cyan-400",     loading: false },
              { label: "Clear Cache",     icon: Zap,         action: () => clearCache.mutate(),    color: "border-purple-500/30 hover:border-purple-400 text-purple-400", loading: clearCache.isPending },
              { label: "Create Backup",   icon: Database,    action: () => backup.mutate(),         color: "border-emerald-500/30 hover:border-emerald-400 text-emerald-400", loading: backup.isPending },
              { label: "Reload Health",   icon: Activity,    action: () => qc.invalidateQueries({ queryKey: ["admin-health"] }), color: "border-amber-500/30 hover:border-amber-400 text-amber-400", loading: false },
              { label: "Fetch Fixtures",  icon: Download,    action: () => fetchFixtures.mutate(), color: "border-rose-500/30 hover:border-rose-400 text-rose-400",       loading: fetchFixtures.isPending },
            ].map(a => (
              <Button key={a.label} variant="outline" disabled={a.loading}
                className={`flex flex-col h-16 gap-1 bg-transparent border ${a.color}`}
                onClick={a.action}>
                <a.icon className={`w-4 h-4 ${a.loading ? "animate-spin" : ""}`} />
                <span className="text-xs">{a.loading ? "Working…" : a.label}</span>
              </Button>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-purple-400" /> Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stats?.recent_activity?.length ? (
            <div className="space-y-2">
              {stats.recent_activity.slice(0, 8).map((a, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={a.status} />
                    <span className="text-sm text-gray-300 font-mono">{a.action}</span>
                    <span className="text-xs text-gray-500">by {a.actor}</span>
                  </div>
                  <span className="text-xs text-gray-600">{a.timestamp ? new Date(a.timestamp).toLocaleString() : ""}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm text-center py-4">No recent activity</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Module 3: Leagues ────────────────────────────────────────────────

function LeaguesTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<{ leagues: League[] }>({
    queryKey: ["admin-leagues"],
    queryFn: () => apiGet("/admin/leagues"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<League> }) => apiPut(`/admin/leagues/${id}`, body),
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
    queryFn: () => apiGet("/admin/markets"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Market> }) => apiPut(`/admin/markets/${id}`, body),
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
    queryFn: () => apiGet("/admin/currency"),
  });

  const recalcMutation = useMutation({
    mutationFn: () => apiPost("/admin/currency/recalculate-vit", {}),
    onSuccess: (d: any) => { toast.success(`New VIT price: $${d.new_price_usd}`); qc.invalidateQueries({ queryKey: ["admin-currency"] }); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ code, body }: { code: string; body: Partial<Currency> }) => apiPut(`/admin/currency/${code}`, body),
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
    queryFn: () => apiGet("/admin/subscriptions"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Plan> }) => apiPut(`/admin/subscriptions/${id}`, body),
    onSuccess: () => { toast.success("Plan updated"); setEditing(null); qc.invalidateQueries({ queryKey: ["admin-subscriptions"] }); },
  });

  const tierColors: Record<string, string> = {
    free: "border-gray-600 bg-gray-800",
    analyst: "border-blue-500/50 bg-blue-950/30",
    pro: "border-purple-500/50 bg-purple-950/30",
    elite: "border-amber-500/50 bg-amber-950/30",
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
    queryFn: () => apiGet("/admin/system/flags"),
  });
  const { data: keysData } = useQuery<{ keys: { name: string; label: string; description: string; configured: boolean; masked: string; required: boolean }[] }>({
    queryKey: ["admin-keys"],
    queryFn: () => apiGet("/admin/api-keys"),
  });

  const flagMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: boolean }) => apiPut("/admin/system/flags", { flags: { [key]: value } }),
    onSuccess: () => { toast.success("Flag updated"); qc.invalidateQueries({ queryKey: ["admin-flags"] }); },
    onError: () => toast.error("Update failed"),
  });
  const cacheMutation = useMutation({
    mutationFn: () => apiPost("/admin/system/cache/clear", {}),
    onSuccess: () => toast.success("Cache cleared"),
  });
  const backupMutation = useMutation({
    mutationFn: () => apiPost("/admin/system/backup", {}),
    onSuccess: (d: any) => toast.success(d.message),
    onError: () => toast.error("Backup failed — super_admin only"),
  });
  const updateKeyMutation = useMutation({
    mutationFn: ({ name, value }: { name: string; value: string }) =>
      apiPost<{ updated: Record<string, string>; errors: Record<string, string>; warnings?: Record<string, string>; message: string }>(
        "/admin/api-keys/update",
        { updates: { [name]: value } },
      ),
    onSuccess: (resp, vars) => {
      const errMsg = resp?.errors?.[vars.name];
      const warnMsg = resp?.warnings?.[vars.name];
      if (errMsg) {
        toast.error(`Update failed: ${errMsg}`);
        return;
      }
      if (warnMsg) {
        toast.warning(warnMsg);
      } else {
        toast.success("API key updated and saved to environment");
      }
      qc.invalidateQueries({ queryKey: ["admin-keys"] });
      setEditingKey(null);
      setNewKeyValue("");
    },
    onError: () => toast.error("Failed to update API key"),
  });

  return (
    <div className="space-y-6">
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
            <div className="space-y-3">
              {Object.entries(flagsData?.flags ?? {}).map(([key, val]) => {
                const isOn = typeof val === "object" ? val.value : val;
                const desc = typeof val === "object" ? val.description : key;
                return (
                  <div key={key} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                    <div>
                      <div className="text-white font-mono text-sm">{key}</div>
                      <div className="text-xs text-gray-500">{desc}</div>
                    </div>
                    <Switch checked={isOn} onCheckedChange={v => flagMutation.mutate({ key, value: v })} />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* API Keys */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Key className="w-5 h-5 text-amber-400" /> API Keys & Secrets
          </CardTitle>
          <CardDescription className="text-gray-400">
            Configure external service credentials. Changes are applied immediately and saved to the environment.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {keysData?.keys?.map(k => (
            <div key={k.name} className="flex items-center justify-between py-2.5 px-3 rounded-lg border border-gray-800 hover:border-gray-700">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <div className="text-white text-sm font-medium">{k.label}</div>
                  {k.required && <span className="text-xs bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded">Required</span>}
                </div>
                <div className="text-xs text-gray-500 truncate">{k.description}</div>
              </div>
              <div className="flex items-center gap-2 ml-3 shrink-0">
                <span className="font-mono text-xs text-gray-400 hidden sm:block">
                  {showKey[k.name] ? (k.masked || "Not set") : "••••••••"}
                </span>
                <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-gray-500 hover:text-white"
                  onClick={() => setShowKey(s => ({ ...s, [k.name]: !s[k.name] }))}>
                  {showKey[k.name] ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                </Button>
                {k.configured
                  ? <CheckCircle className="w-4 h-4 text-emerald-400" />
                  : <XCircle className="w-4 h-4 text-red-400" />}
                <Button size="sm" variant="outline"
                  className="h-7 px-2 border-amber-500/30 text-amber-400 hover:border-amber-400 text-xs"
                  onClick={() => { setEditingKey(k); setNewKeyValue(""); setShowNewKey(false); }}>
                  <Edit className="w-3 h-3 mr-1" /> Update
                </Button>
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
              <div className="bg-amber-500/10 border border-amber-500/20 rounded p-3 text-xs text-amber-300">
                This value will be applied to the running server immediately and persisted to the environment file.
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
    </div>
  );
}

// ─── Football-Data.org Integration Card ──────────────────────────────

function FootballDataCard() {
  const qc = useQueryClient();
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);

  const testMutation = useMutation({
    mutationFn: () => apiPost<{ status: string; message: string }>(
      "/admin/data-sources/test/football_data", {}),
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
      "/admin/matches/fetch-fixtures?count=100&days=14", {}),
    onSuccess: (d) => {
      toast.success(`Fetched ${d.stored ?? 0} new fixtures (${d.skipped_existing ?? 0} duplicates skipped)`);
      qc.invalidateQueries({ queryKey: ["matches-recent"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: () => toast.error("Fixture fetch failed — check the Football-Data.org key first"),
  });

  const settleMutation = useMutation({
    mutationFn: () => apiPost<{ settled: number; already_settled: number; created_new?: number; message?: string }>(
      "/admin/settle-results?days_back=7", {}),
    onSuccess: (d) => {
      toast.success(`Settled ${d.settled ?? 0} match(es), ${d.already_settled ?? 0} already done, ${d.created_new ?? 0} new records created`);
      qc.invalidateQueries({ queryKey: ["matches-recent"] });
    },
    onError: () => toast.error("Settle pass failed — check the API key"),
  });

  const backfillMutation = useMutation({
    mutationFn: () => apiPost<{ settled_real: number; simulated_local: number; skipped_real_no_api: number }>(
      "/admin/matches/backfill-ft-results?settle_real=true&simulate_local=true&days_back=14", {}),
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
          Place bets on and broadcast accumulator tips
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
                  toast.success("Bet placed successfully");
                  setAccumulatorId("");
                  setStakeAmount("");
                },
                onError: () => toast.error("Failed to place bet")
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
    const odds = marketOdds ? JSON.parse(marketOdds) : {};
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

  const { data, isLoading } = useQuery<{ users: AdminUser[]; total: number }>({
    queryKey: ["admin-users", search],
    queryFn: () => apiGet(`/admin/users?limit=100${search ? `&search=${encodeURIComponent(search)}` : ""}`),
    refetchInterval: 30000,
  });

  const banMutation = useMutation({
    mutationFn: ({ id, ban }: { id: number; ban: boolean }) =>
      apiPost(`/admin/users/${id}/ban`, { ban, reason: ban ? "Banned by admin" : "Unbanned by admin" }),
    onSuccess: (_, v) => { toast.success(v.ban ? "User banned" : "User unbanned"); qc.invalidateQueries({ queryKey: ["admin-users"] }); },
    onError: () => toast.error("Action failed"),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<AdminUser> }) => apiPut(`/admin/users/${id}`, body),
    onSuccess: () => { toast.success("User updated"); qc.invalidateQueries({ queryKey: ["admin-users"] }); setEditingUser(null); },
    onError: () => toast.error("Update failed"),
  });

  const tierColors: Record<string, string> = {
    viewer: "text-gray-400", analyst: "text-blue-400",
    pro: "text-purple-400", elite: "text-amber-400",
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
                          {u.subscription_tier?.toUpperCase() ?? "VIEWER"}
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
                  {!data?.users?.length && (
                    <tr><td colSpan={7} className="text-center text-gray-500 py-8">No users found</td></tr>
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

function ModelsTab() {
  const qc = useQueryClient();
  const [activeSection, setActiveSection] = useState<"engine" | "marketplace">("engine");

  const { data: modelsData, isLoading: mLoading } = useQuery<{ models: ModelInfo[] }>({
    queryKey: ["admin-models"],
    queryFn: () => apiGet("/admin/models/status"),
    refetchInterval: 30000,
  });

  const { data: pendingData, isLoading: pLoading } = useQuery<{ items: MarketplaceListing[]; total: number }>({
    queryKey: ["admin-marketplace-pending"],
    queryFn: () => apiGet("/admin/marketplace/pending"),
    refetchInterval: 20000,
  });

  const reloadMutation = useMutation({
    mutationFn: (key?: string) => apiPost("/admin/models/reload", key ? { model_key: key } : {}),
    onSuccess: (d: any) => { toast.success(d.message ?? "Models reloaded"); qc.invalidateQueries({ queryKey: ["admin-models"] }); },
    onError: () => toast.error("Reload failed"),
  });

  const trainMutation = useMutation({
    mutationFn: (key?: string) => apiPost("/admin/models/train", {
      model_key: key,
      note: key ? `Admin requested retraining for ${key}` : "Admin requested full ensemble retraining",
    }),
    onSuccess: (d: any) => {
      toast.success(`Training queued: JOB_${String(d.job_id).slice(0, 8)}`);
      qc.invalidateQueries({ queryKey: ["admin-models"] });
      qc.invalidateQueries({ queryKey: ["admin-training-jobs"] });
    },
    onError: (err: any) => toast.error(err?.message || "Training request failed"),
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, note, is_verified }: { id: number; note?: string; is_verified?: boolean }) =>
      apiPatch(`/admin/marketplace/${id}/approve`, { note, is_verified }),
    onSuccess: () => { toast.success("Listing approved and is now live"); qc.invalidateQueries({ queryKey: ["admin-marketplace-pending"] }); },
    onError: () => toast.error("Approval failed"),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      apiPatch(`/admin/marketplace/${id}/reject`, { reason }),
    onSuccess: () => { toast.success("Listing rejected"); qc.invalidateQueries({ queryKey: ["admin-marketplace-pending"] }); },
    onError: () => toast.error("Rejection failed"),
  });

  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button
          variant={activeSection === "engine" ? "default" : "outline"}
          className={activeSection === "engine" ? "bg-cyan-500 text-black" : "border-gray-600 text-gray-300"}
          onClick={() => setActiveSection("engine")}>
          <Cpu className="w-4 h-4 mr-2" /> AI Engine ({modelsData?.models?.length ?? 0})
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
              {pendingData!.total}
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

// ─── Module 10: KYC Verification ─────────────────────────────────────

function KYCTab() {
  const qc = useQueryClient();
  const [noteInput, setNoteInput] = useState<Record<number, string>>({});

  const { data, isLoading } = useQuery<{ kyc_requests: KYCEntry[]; total: number }>({
    queryKey: ["admin-kyc-pending"],
    queryFn: () => apiGet("/wallet/admin/kyc/pending"),
    refetchInterval: 20000,
  });

  const approveMutation = useMutation({
    mutationFn: (user_id: number) => apiPost(`/wallet/admin/kyc/${user_id}/approve`, {}),
    onSuccess: () => { toast.success("KYC approved"); qc.invalidateQueries({ queryKey: ["admin-kyc-pending"] }); },
    onError: () => toast.error("Approval failed"),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ user_id, reason }: { user_id: number; reason?: string }) =>
      apiPost(`/wallet/admin/kyc/${user_id}/reject`, { reason: reason ?? "Rejected by admin" }),
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
      return apiGet(`/admin/audit?${p}`);
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

// ─── Root Admin Page ──────────────────────────────────────────────────

export default function AdminPage() {
  const { user, isAdmin, isSuperAdmin } = useAuth();

  if (!user) return <Redirect to="/login" />;
  if (!isAdmin) return <Redirect to="/dashboard" />;

  const adminRoleLabel: Record<string, string> = {
    super_admin: "Super Admin", admin: "Admin",
    auditor: "Auditor", support: "Support",
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Top bar */}
      <div className="border-b border-gray-800 bg-gray-900/80 backdrop-blur px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-cyan-400" />
          <div>
            <div className="font-bold text-white text-lg leading-tight">Admin Control Center</div>
            <div className="text-xs text-gray-500">VIT Sports Intelligence Network</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-sm text-white font-medium">{user.username}</div>
            <div className="text-xs text-cyan-400">{adminRoleLabel[user.admin_role ?? "admin"] ?? "Admin"}</div>
          </div>
          <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm ${
            isSuperAdmin ? "bg-amber-500 text-black" : "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
          }`}>
            {user.username[0]?.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-screen-xl mx-auto px-4 py-6">
        <Tabs defaultValue="dashboard">
          <TabsList className="bg-gray-800 border border-gray-700 flex-wrap h-auto mb-6 p-1 gap-1">
            {[
              { value: "dashboard",      label: "Dashboard",      icon: BarChart2 },
              { value: "users",          label: "Users",          icon: Users },
              { value: "kyc",            label: "KYC",            icon: UserCheck },
              { value: "models",         label: "Models",         icon: Cpu },
              { value: "calibration",    label: "Calibration",    icon: Activity },
              { value: "leagues",        label: "Leagues",        icon: Globe },
              { value: "markets",        label: "Markets",        icon: TrendingUp },
              { value: "currency",       label: "Currency",       icon: Coins },
              { value: "subscriptions",  label: "Subscriptions",  icon: CreditCard },
              { value: "system",         label: "System",         icon: Settings },
              { value: "audit",          label: "Audit",          icon: ShieldCheck },
            ].map(tab => (
              <TabsTrigger key={tab.value} value={tab.value}
                className="data-[state=active]:bg-cyan-500 data-[state=active]:text-black flex items-center gap-1.5 text-gray-300 px-3 py-1.5">
                <tab.icon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{tab.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="dashboard"><DashboardTab /></TabsContent>
          <TabsContent value="users"><UsersTab /></TabsContent>
          <TabsContent value="kyc"><KYCTab /></TabsContent>
          <TabsContent value="models"><ModelsTab /></TabsContent>
          <TabsContent value="calibration"><CalibrationTab /></TabsContent>
          <TabsContent value="leagues"><LeaguesTab /></TabsContent>
          <TabsContent value="markets"><MarketsTab /></TabsContent>
          <TabsContent value="currency"><CurrencyTab /></TabsContent>
          <TabsContent value="subscriptions"><SubscriptionsTab /></TabsContent>
          <TabsContent value="system"><SystemTab /></TabsContent>
          <TabsContent value="audit"><AuditTab /></TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function CalibrationTab() {
  const [window, setWindow] = useState(50);
  const [busy, setBusy] = useState(false);
  const reportQ = useQuery<any>({
    queryKey: ["ai-accuracy-report", window],
    queryFn: () => apiGet(`/api/ai-engine/accuracy/report?window=${window}`),
  });
  const { data: aiPerformance } = useGetAiPerformance();
  const { data: aiReport } = useGetAiReport();

  async function refit() {
    setBusy(true);
    try {
      const res = await apiPost<any>(
        `/api/ai-engine/accuracy/enhance?window=${window}`, {},
      );
      const fit = res?.temperature_fit;
      if (fit?.fitted) {
        toast.success(
          `Temperature refit: T=${fit.best_T} (NLL ${fit.pre_nll?.toFixed(4)} → ${fit.best_nll?.toFixed(4)})`,
        );
      } else {
        toast.message(fit?.reason || "Temperature not refit");
      }
      reportQ.refetch();
    } catch (e: any) {
      toast.error(e?.message || "Re-fit failed");
    } finally {
      setBusy(false);
    }
  }

  const data = reportQ.data;
  const models: any[] = data?.models || [];
  const T = data?.current_temperature ?? 1.0;

  return (
    <div className="space-y-4">
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
                value={window}
                onChange={(e) => setWindow(Math.max(10, Math.min(500, Number(e.target.value) || 50)))}
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
            <div className="text-gray-400 text-sm">
              No settled predictions yet. Wait for matches to settle, then a report will appear here.
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

      {/* AI Performance */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            AI Source Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          {aiPerformance && Object.keys(aiPerformance).length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="py-2 px-2">Source</th>
                    <th className="py-2 px-2 text-right">Samples</th>
                    <th className="py-2 px-2 text-right">Accuracy</th>
                    <th className="py-2 px-2 text-right">Avg Confidence</th>
                    <th className="py-2 px-2 text-right">Last Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(aiPerformance).map(([source, data]: [string, any]) => (
                    <tr key={source} className="border-b border-gray-800/50">
                      <td className="py-2 px-2 font-mono text-purple-300">{source}</td>
                      <td className="py-2 px-2 text-right text-gray-300">{data.sample_size || 0}</td>
                      <td className="py-2 px-2 text-right text-gray-200">
                        {data.accuracy != null ? `${(data.accuracy * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-blue-400">
                        {data.avg_confidence != null ? `${(data.avg_confidence * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-2 px-2 text-right text-gray-400 text-xs">
                        {data.last_updated ? new Date(data.last_updated).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-gray-400 text-sm text-center py-4">
              No AI performance data available yet.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
