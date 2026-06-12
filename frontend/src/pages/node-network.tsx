import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import {
  HardDrive, Zap, Shield, TrendingUp, Globe, CheckCircle2,
  Plus, RefreshCw, Trash2, CloudUpload, Coins, Activity,
  Server, Database, AlertTriangle, ChevronDown, ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface StorageNode {
  id: number;
  provider: string;
  provider_label: string;
  alias: string;
  status: string;
  gb_contributed: number;
  gb_used: number;
  tsc_earned: number;
  tsc_pending: number;
  reliability_score: number;
  verification_count: number;
  verification_pass: number;
  last_verified_at: string | null;
  created_at: string;
  uptime_pct: number;
  estimated_daily_tsc: number;
}

interface NetworkStats {
  total_nodes: number;
  active_nodes: number;
  total_tb_contributed: number;
  total_gb_contributed: number;
  gb_in_use: number;
  utilization_pct: number;
  tsc_distributed_total: number;
  provider_breakdown: Record<string, number>;
  tsc_rate_per_gb_day: number;
  snapshot_at: string;
}

interface Earnings {
  total_tsc_earned: number;
  total_tsc_pending: number;
  total_gb_contributed: number;
  active_nodes: number;
  avg_reliability: number;
  estimated_daily_tsc: number;
  estimated_monthly_tsc: number;
  can_claim: boolean;
  min_claim: number;
  nodes: { id: number; alias: string; provider: string; tsc_earned: number; tsc_pending: number; gb_contributed: number }[];
}

const PROVIDER_CONFIG: Record<string, {
  label: string; color: string; icon: string;
  fields: { key: string; label: string; placeholder: string; isTextarea?: boolean }[];
}> = {
  gdrive: {
    label: "Google Drive", color: "text-blue-400 bg-blue-500/10 border-blue-500/20", icon: "G",
    fields: [{ key: "service_account_json", label: "Service Account JSON", placeholder: '{"type":"service_account",...}', isTextarea: true }],
  },
  dropbox: {
    label: "Dropbox", color: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20", icon: "D",
    fields: [
      { key: "access_token", label: "Access Token", placeholder: "sl.xxxxxxx..." },
      { key: "app_key", label: "App Key", placeholder: "App key from Dropbox console" },
      { key: "app_secret", label: "App Secret", placeholder: "App secret" },
      { key: "refresh_token", label: "Refresh Token (optional)", placeholder: "Refresh token for long-lived access" },
    ],
  },
  onedrive: {
    label: "OneDrive / SharePoint", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20", icon: "O",
    fields: [
      { key: "client_id", label: "Client ID", placeholder: "Azure app client ID" },
      { key: "client_secret", label: "Client Secret", placeholder: "Azure app secret" },
      { key: "tenant_id", label: "Tenant ID", placeholder: "Directory (tenant) ID" },
      { key: "user_id", label: "User / Drive ID", placeholder: "User or shared drive ID" },
    ],
  },
};

const STATUS_STYLE: Record<string, { label: string; cls: string; dot: string }> = {
  active:    { label: "Active",    cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", dot: "bg-emerald-400 animate-pulse" },
  pending:   { label: "Pending",   cls: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",   dot: "bg-yellow-400" },
  offline:   { label: "Offline",   cls: "text-red-400 bg-red-500/10 border-red-500/20",             dot: "bg-red-400" },
  suspended: { label: "Suspended", cls: "text-zinc-400 bg-zinc-500/10 border-zinc-500/20",          dot: "bg-zinc-400" },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.offline;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${s.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function ReliabilityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 90 ? "bg-emerald-500" : pct >= 70 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-zinc-400 w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function NodeNetworkPage() {
  const qc = useQueryClient();
  const [registerOpen, setRegisterOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState("gdrive");
  const [alias, setAlias] = useState("");
  const [gbContributed, setGbContributed] = useState("5");
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());

  const { data: myNodes, isLoading: nodesLoading } = useQuery<{ nodes: StorageNode[]; count: number }>({
    queryKey: ["my-storage-nodes"],
    queryFn: () => apiGet("/api/tachyon/node/my-nodes"),
    refetchInterval: 60_000,
  });

  const { data: netStats } = useQuery<NetworkStats>({
    queryKey: ["storage-node-network-stats"],
    queryFn: () => apiGet("/api/tachyon/node/network-stats"),
    refetchInterval: 120_000,
  });

  const { data: earnings, refetch: refetchEarnings } = useQuery<Earnings>({
    queryKey: ["storage-node-earnings"],
    queryFn: () => apiGet("/api/tachyon/node/earnings"),
    refetchInterval: 60_000,
  });

  const registerMut = useMutation({
    mutationFn: (payload: object) => apiPost("/api/tachyon/node/register", payload),
    onSuccess: (data: any) => {
      toast.success(data.message || "Node registered!");
      qc.invalidateQueries({ queryKey: ["my-storage-nodes"] });
      qc.invalidateQueries({ queryKey: ["storage-node-earnings"] });
      qc.invalidateQueries({ queryKey: ["storage-node-network-stats"] });
      setRegisterOpen(false);
      setCredentials({});
      setAlias("");
    },
    onError: (e: any) => toast.error(e.message || "Registration failed"),
  });

  const verifyMut = useMutation({
    mutationFn: (nodeId: number) => apiPost(`/api/tachyon/node/${nodeId}/verify`),
    onSuccess: (data: any) => {
      toast.success(
        data.passed
          ? `Verification passed! +${data.tsc_awarded} TSC awarded`
          : "Verification failed — check node credentials",
      );
      qc.invalidateQueries({ queryKey: ["my-storage-nodes"] });
      qc.invalidateQueries({ queryKey: ["storage-node-earnings"] });
    },
    onError: (e: any) => toast.error(e.message || "Verify failed"),
  });

  const claimMut = useMutation({
    mutationFn: (nodeId: number) => apiPost(`/api/tachyon/node/${nodeId}/claim`),
    onSuccess: (data: any) => {
      toast.success(data.message || "TSC claimed!");
      qc.invalidateQueries({ queryKey: ["my-storage-nodes"] });
      qc.invalidateQueries({ queryKey: ["storage-node-earnings"] });
    },
    onError: (e: any) => toast.error(e.message || "Claim failed"),
  });

  const removeMut = useMutation({
    mutationFn: (nodeId: number) => apiDelete(`/api/tachyon/node/${nodeId}`),
    onSuccess: () => {
      toast.success("Node removed");
      qc.invalidateQueries({ queryKey: ["my-storage-nodes"] });
      qc.invalidateQueries({ queryKey: ["storage-node-earnings"] });
      qc.invalidateQueries({ queryKey: ["storage-node-network-stats"] });
    },
  });

  const provConfig = PROVIDER_CONFIG[selectedProvider];
  const nodes = myNodes?.nodes ?? [];

  const handleRegister = () => {
    registerMut.mutate({
      provider: selectedProvider,
      alias: alias || `My ${provConfig.label}`,
      gb_contributed: parseFloat(gbContributed) || 5,
      credentials,
    });
  };

  const toggleExpand = (id: number) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold font-mono tracking-tight flex items-center gap-2">
            <Server className="w-6 h-6 text-cyan-400" />
            Storage Node Network
          </h1>
          <p className="text-sm text-muted-foreground font-mono uppercase tracking-widest">
            Contribute idle cloud storage · Power the Tachyon swarm · Earn VIT
          </p>
        </div>
        <Button onClick={() => setRegisterOpen(true)} className="gap-2 bg-cyan-600 hover:bg-cyan-500">
          <Plus className="w-4 h-4" /> Contribute Storage
        </Button>
      </div>

      {/* How it works banner */}
      <Card className="bg-gradient-to-r from-cyan-950/40 to-violet-950/40 border-cyan-800/30">
        <CardContent className="p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { icon: CloudUpload, title: "Link Your Account", desc: "Connect Google Drive, Dropbox, or OneDrive — any unused quota counts" },
              { icon: Database, title: "Power the Swarm", desc: "Your storage becomes a node. VIT files are sharded and distributed across all nodes" },
              { icon: Shield, title: "Proof-of-Storage", desc: "Regular challenges verify your node holds its assigned fragments" },
              { icon: Coins, title: "Earn VITCoin", desc: `${(netStats?.tsc_rate_per_gb_day ?? 0.5).toFixed(1)} TSC per GB per day — claimed directly to your VIT wallet` },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex flex-col gap-2">
                <div className="p-2 w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                  <Icon className="w-4 h-4 text-cyan-400" />
                </div>
                <p className="text-sm font-semibold text-foreground">{title}</p>
                <p className="text-xs text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Network + Earnings stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Network Nodes", value: netStats?.active_nodes ?? "—", sub: `${netStats?.total_nodes ?? 0} registered`, icon: Globe, color: "text-cyan-400" },
          { label: "Total Contributed", value: netStats ? `${netStats.total_tb_contributed.toFixed(2)} TB` : "—", sub: `${netStats?.utilization_pct ?? 0}% utilised`, icon: HardDrive, color: "text-violet-400" },
          { label: "TSC Distributed", value: netStats ? netStats.tsc_distributed_total.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "—", sub: "Lifetime", icon: Coins, color: "text-yellow-400" },
          { label: "Est. Daily (Mine)", value: earnings ? `${earnings.estimated_daily_tsc.toFixed(2)} TSC` : "—", sub: `${earnings?.estimated_monthly_tsc?.toFixed(0) ?? 0} TSC/mo`, icon: TrendingUp, color: "text-emerald-400" },
        ].map(({ label, value, sub, icon: Icon, color }) => (
          <Card key={label} className="bg-card/50 border-border/40">
            <CardContent className="p-4 flex items-center gap-3">
              <div className={`p-2 rounded-lg bg-background/50 ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">{label}</p>
                <p className="text-lg font-bold font-mono">{value}</p>
                <p className="text-[10px] text-muted-foreground">{sub}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Earnings panel */}
      {earnings && earnings.total_tsc_pending > 0 && (
        <Card className="border-yellow-600/30 bg-yellow-950/20">
          <CardContent className="p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-yellow-400" />
              <div>
                <p className="text-sm font-semibold">Claimable TSC</p>
                <p className="text-xs text-muted-foreground">
                  {earnings.total_tsc_pending.toFixed(4)} TSC pending across {earnings.nodes.filter(n => n.tsc_pending > 0).length} node(s)
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              {earnings.nodes.filter(n => n.tsc_pending >= earnings.min_claim).map(n => (
                <Button key={n.id} size="sm" variant="outline" className="border-yellow-600/40 text-yellow-400 hover:bg-yellow-500/10"
                  onClick={() => claimMut.mutate(n.id)} disabled={claimMut.isPending}>
                  Claim {n.tsc_pending.toFixed(2)} TSC — {n.alias}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Provider breakdown */}
      {netStats && Object.keys(netStats.provider_breakdown).length > 0 && (
        <Card className="bg-card/50 border-border/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono">Network Composition</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            {Object.entries(netStats.provider_breakdown).map(([prov, count]) => (
              <div key={prov} className="flex items-center gap-2 bg-background/50 rounded-lg px-3 py-2">
                <Activity className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-sm font-mono">{prov}</span>
                <Badge variant="outline" className="text-xs">{count} nodes</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* My Nodes */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-mono text-muted-foreground uppercase tracking-widest">My Nodes ({nodes.length})</h2>
          <Button variant="ghost" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ["my-storage-nodes"] })}>
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>

        {nodesLoading && <p className="text-sm text-muted-foreground">Loading nodes…</p>}

        {!nodesLoading && nodes.length === 0 && (
          <Card className="border-dashed border-border/40">
            <CardContent className="p-12 flex flex-col items-center gap-4 text-center">
              <HardDrive className="w-12 h-12 text-muted-foreground/30" />
              <div>
                <p className="font-semibold">No nodes yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Link your first cloud account to start contributing to the VIT swarm and earning TSC rewards
                </p>
              </div>
              <Button onClick={() => setRegisterOpen(true)} className="gap-2 bg-cyan-600 hover:bg-cyan-500">
                <Plus className="w-4 h-4" /> Add Your First Node
              </Button>
            </CardContent>
          </Card>
        )}

        {nodes.map((node) => {
          const expanded = expandedNodes.has(node.id);
          return (
            <Card key={node.id} className="bg-card/50 border-border/40">
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <div className={cn("w-10 h-10 rounded-lg border flex items-center justify-center font-bold text-lg flex-shrink-0", PROVIDER_CONFIG[node.provider]?.color ?? "text-zinc-400 bg-zinc-800 border-zinc-700")}>
                    {PROVIDER_CONFIG[node.provider]?.icon ?? "?"}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm truncate">{node.alias}</span>
                      <StatusBadge status={node.status} />
                      <span className="text-xs text-muted-foreground">{node.provider_label}</span>
                    </div>
                    <div className="mt-1.5">
                      <ReliabilityBar score={node.reliability_score} />
                    </div>
                  </div>

                  <div className="hidden md:grid grid-cols-3 gap-6 text-center flex-shrink-0">
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">Contributed</p>
                      <p className="font-mono text-sm">{node.gb_contributed.toFixed(1)} GB</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">Earned</p>
                      <p className="font-mono text-sm text-yellow-400">{node.tsc_earned.toFixed(2)} TSC</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">Est. Daily</p>
                      <p className="font-mono text-sm text-emerald-400">{node.estimated_daily_tsc.toFixed(3)} TSC</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Button size="sm" variant="outline" onClick={() => verifyMut.mutate(node.id)} disabled={verifyMut.isPending}>
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Verify
                    </Button>
                    {node.tsc_pending >= 1 && (
                      <Button size="sm" variant="outline" className="border-yellow-600/40 text-yellow-400" onClick={() => claimMut.mutate(node.id)} disabled={claimMut.isPending}>
                        Claim {node.tsc_pending.toFixed(2)}
                      </Button>
                    )}
                    <Button size="icon" variant="ghost" className="text-muted-foreground h-8 w-8" onClick={() => toggleExpand(node.id)}>
                      {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </Button>
                    <Button size="icon" variant="ghost" className="text-red-400 h-8 w-8" onClick={() => removeMut.mutate(node.id)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>

                {expanded && (
                  <div className="mt-4 pt-4 border-t border-border/40 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    {[
                      { label: "Verifications", value: `${node.verification_pass}/${node.verification_count} passed` },
                      { label: "Uptime", value: `${node.uptime_pct.toFixed(1)}%` },
                      { label: "GB In Use", value: `${node.gb_used.toFixed(2)} / ${node.gb_contributed.toFixed(1)} GB` },
                      { label: "Last Verified", value: node.last_verified_at ? new Date(node.last_verified_at).toLocaleString() : "Never" },
                      { label: "Total Earned", value: `${node.tsc_earned.toFixed(4)} TSC` },
                      { label: "Pending", value: `${node.tsc_pending.toFixed(4)} TSC` },
                      { label: "Registered", value: new Date(node.created_at).toLocaleDateString() },
                      { label: "Reliability", value: `${(node.reliability_score * 100).toFixed(1)}%` },
                    ].map(({ label, value }) => (
                      <div key={label}>
                        <p className="text-[10px] text-muted-foreground uppercase">{label}</p>
                        <p className="font-mono text-xs">{value}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Register Node Dialog */}
      <Dialog open={registerOpen} onOpenChange={setRegisterOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CloudUpload className="w-5 h-5 text-cyan-400" /> Contribute Your Storage
            </DialogTitle>
            <DialogDescription>
              Link a cloud account. Its idle space becomes a Tachyon swarm node and earns you TSC rewards.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Provider</Label>
              <Select value={selectedProvider} onValueChange={(v) => { setSelectedProvider(v); setCredentials({}); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(PROVIDER_CONFIG).map(([key, cfg]) => (
                    <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Node Name (alias)</Label>
              <Input value={alias} onChange={(e) => setAlias(e.target.value)}
                placeholder={`My ${provConfig.label} — Work Account`} />
            </div>

            <div className="space-y-1.5">
              <Label>Storage to Contribute (GB)</Label>
              <Input type="number" min="0.5" max="2000" step="0.5"
                value={gbContributed} onChange={(e) => setGbContributed(e.target.value)} />
              <p className="text-xs text-muted-foreground">
                Est. reward: <span className="text-yellow-400 font-mono">
                  {(0.5 * parseFloat(gbContributed || "0")).toFixed(2)} TSC/day
                </span>
              </p>
            </div>

            {provConfig.fields.map((f) => (
              <div key={f.key} className="space-y-1.5">
                <Label>{f.label}</Label>
                {f.isTextarea ? (
                  <textarea
                    className="w-full min-h-[80px] px-3 py-2 text-xs font-mono bg-background border border-input rounded-md resize-y"
                    placeholder={f.placeholder}
                    value={credentials[f.key] ?? ""}
                    onChange={(e) => setCredentials((p) => ({ ...p, [f.key]: e.target.value }))}
                  />
                ) : (
                  <Input type="password" placeholder={f.placeholder}
                    value={credentials[f.key] ?? ""}
                    onChange={(e) => setCredentials((p) => ({ ...p, [f.key]: e.target.value }))} />
                )}
              </div>
            ))}

            <div className="flex items-start gap-2 text-xs text-muted-foreground bg-muted/30 rounded-lg p-3">
              <Shield className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
              <span>
                Credentials are stored encrypted in the VIT platform database and are only used to write/read
                assigned Tachyon fragments. VIT never reads, deletes, or modifies any other files in your account.
              </span>
            </div>

            <Button className="w-full gap-2 bg-cyan-600 hover:bg-cyan-500"
              onClick={handleRegister} disabled={registerMut.isPending}>
              {registerMut.isPending ? <><RefreshCw className="w-4 h-4 animate-spin" /> Registering…</> : <><Plus className="w-4 h-4" /> Register Node &amp; Start Earning</>}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
