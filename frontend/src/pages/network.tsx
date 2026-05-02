import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Activity, Award, CheckCircle2, Clock, Cpu, Globe,
  Key, Network, RefreshCw, Shield, TrendingUp, User, Zap,
} from "lucide-react";
import { apiGet } from "@/lib/apiClient";

// ─── Types ───────────────────────────────────────────────────────────────────

interface NetworkStats {
  total_nodes: number; active_nodes: number;
  total_contributions: number; contributions_24h: number;
  oracle_submissions_24h: number; network_health_score: number;
  growth_rate_24h_pct: number;
  activity_breakdown_24h: Record<string, number>;
  snapshot_at: string;
}

interface GrowthBucket { hour: string; timestamp: string; contributions: number; }
interface GrowthData { hours: number; total: number; buckets: GrowthBucket[]; }

interface NetworkNode {
  node_id: string; node_name: string; node_type: string;
  total_contributions: number; contributions_24h: number;
  total_score: number; last_active: string | null; online: boolean; status: string;
}

interface DIDIdentity {
  did: string; id: string; subject_type: string;
  agent_name: string | null; user_id: number | null;
  credential_count: number; credential_types: string[];
  created_at: string;
}

interface DIDRegistry { identities: DIDIdentity[]; count: number; }

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M`
  : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K`
  : String(n);

const timeAgo = (iso: string | null) => {
  if (!iso) return "Never";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
};

const MAX_BAR = (buckets: GrowthBucket[]) =>
  Math.max(1, ...buckets.map(b => b.contributions));

// ─── Components ──────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon, label, value, sub, color = "text-foreground",
}: {
  icon: React.ElementType; label: string; value: string | number;
  sub?: string; color?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Icon className={`h-5 w-5 ${color}`} />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function HealthBar({ score }: { score: number }) {
  const color =
    score >= 80 ? "bg-green-500" :
    score >= 50 ? "bg-yellow-500" :
    "bg-red-500";
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">Network Health</span>
        <span className="font-bold">{score.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
    </div>
  );
}

function NodeRow({ node }: { node: NetworkNode }) {
  const typeIcon = node.node_type === "agent" ? Cpu : node.node_type === "oracle" ? Shield : User;
  const Icon = typeIcon;
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg border hover:bg-muted/30 transition-colors">
      <div className="p-1.5 rounded bg-muted">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium truncate">{node.node_name}</p>
          <div className={`w-2 h-2 rounded-full shrink-0 ${node.online ? "bg-green-500" : "bg-muted-foreground/40"}`} />
        </div>
        <p className="text-xs text-muted-foreground truncate">{node.node_id}</p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-sm font-semibold">{node.contributions_24h}</p>
        <p className="text-xs text-muted-foreground">24h acts</p>
      </div>
      <div className="text-right shrink-0 hidden md:block">
        <p className="text-sm font-semibold text-primary">{node.total_score.toFixed(1)}</p>
        <p className="text-xs text-muted-foreground">score</p>
      </div>
    </div>
  );
}

function DIDRow({ identity }: { identity: DIDIdentity }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center gap-3 p-3 hover:bg-muted/30 text-left transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <Key className="h-4 w-4 text-primary shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-mono truncate">{identity.did}</p>
          <p className="text-xs text-muted-foreground">
            {identity.subject_type === "agent" ? `Agent: ${identity.agent_name}` : `User #${identity.user_id}`}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant="outline" className="text-xs">{identity.credential_count} VCs</Badge>
          <span className="text-xs text-muted-foreground">{timeAgo(identity.created_at)}</span>
        </div>
      </button>
      {expanded && (
        <div className="border-t bg-muted/20 p-3 space-y-2">
          <p className="text-xs text-muted-foreground font-medium">DID: {identity.did}</p>
          <div className="flex flex-wrap gap-1.5">
            {identity.credential_types.map(ct => (
              <Badge key={ct} variant="secondary" className="text-xs gap-1">
                <CheckCircle2 className="h-3 w-3 text-green-500" /> {ct}
              </Badge>
            ))}
            {identity.credential_types.length === 0 && (
              <span className="text-xs text-muted-foreground">No credentials issued yet</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function NetworkPage() {
  const { data: stats, isLoading: statsLoading, refetch } = useQuery<NetworkStats>({
    queryKey: ["network-stats"],
    queryFn: () => apiGet<NetworkStats>("/api/network/stats"),
    refetchInterval: 30_000,
  });

  const { data: nodesData, isLoading: nodesLoading } = useQuery<{ nodes: NetworkNode[]; count: number }>({
    queryKey: ["network-nodes"],
    queryFn: () => apiGet<{ nodes: NetworkNode[]; count: number }>("/api/network/nodes?limit=50"),
    refetchInterval: 30_000,
  });

  const { data: growth } = useQuery<GrowthData>({
    queryKey: ["network-growth"],
    queryFn: () => apiGet<GrowthData>("/api/network/growth?hours=24"),
    refetchInterval: 60_000,
  });

  const { data: registry } = useQuery<DIDRegistry>({
    queryKey: ["did-registry"],
    queryFn: () => apiGet<DIDRegistry>("/api/did/registry?limit=30"),
    refetchInterval: 60_000,
  });

  const maxBar = growth ? MAX_BAR(growth.buckets) : 1;

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Network className="h-8 w-8 text-primary" />
            VIT Network
          </h1>
          <p className="text-muted-foreground mt-1">
            Decentralized node registry, DID identity layer, and network growth metrics
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} className="gap-2">
          <RefreshCw className="h-4 w-4" /> Refresh
        </Button>
      </div>

      {/* Stats grid */}
      {statsLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}><CardContent className="pt-6 h-24 animate-pulse bg-muted/30" /></Card>
          ))}
        </div>
      ) : stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={Globe} label="Total Nodes" value={fmt(stats.total_nodes)} sub="Registered on network" />
          <StatCard
            icon={Activity} label="Active Now"
            value={fmt(stats.active_nodes)}
            sub="Activity in last hour"
            color="text-green-500"
          />
          <StatCard
            icon={Zap} label="Contributions (24h)"
            value={fmt(stats.contributions_24h)}
            sub={`${fmt(stats.total_contributions)} lifetime`}
            color="text-yellow-500"
          />
          <StatCard
            icon={TrendingUp} label="Growth Rate"
            value={`${stats.growth_rate_24h_pct >= 0 ? "+" : ""}${stats.growth_rate_24h_pct.toFixed(1)}%`}
            sub="vs previous snapshot"
            color={stats.growth_rate_24h_pct >= 0 ? "text-green-500" : "text-red-500"}
          />
        </div>
      )}

      {/* Health + Activity */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader><CardTitle className="text-base">Network Health</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <HealthBar score={stats.network_health_score} />
              <Separator />
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Activity Breakdown (24h)
                </p>
                {Object.entries(stats.activity_breakdown_24h).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground capitalize">{type.replace(/_/g, " ")}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
                {Object.keys(stats.activity_breakdown_24h).length === 0 && (
                  <p className="text-sm text-muted-foreground">No activity recorded yet</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Growth chart */}
          <Card>
            <CardHeader><CardTitle className="text-base">Contribution Timeline (24h)</CardTitle></CardHeader>
            <CardContent>
              {!growth || growth.buckets.every(b => b.contributions === 0) ? (
                <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
                  Collecting data...
                </div>
              ) : (
                <div className="flex items-end gap-1 h-32">
                  {growth.buckets.map((bucket, i) => (
                    <div
                      key={i}
                      title={`${bucket.hour}: ${bucket.contributions}`}
                      className="flex-1 bg-primary/60 rounded-t hover:bg-primary transition-colors cursor-help"
                      style={{ height: `${(bucket.contributions / maxBar) * 100}%`, minHeight: "2px" }}
                    />
                  ))}
                </div>
              )}
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span>24h ago</span>
                <span className="font-medium">{growth ? fmt(growth.total) : 0} total</span>
                <span>Now</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs: Nodes | DID Registry */}
      <Tabs defaultValue="nodes">
        <TabsList>
          <TabsTrigger value="nodes" className="gap-2">
            <Cpu className="h-4 w-4" /> Agent Nodes
            {nodesData && <Badge variant="secondary" className="ml-1 text-xs">{nodesData.count}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="did" className="gap-2">
            <Key className="h-4 w-4" /> DID Registry
            {registry && <Badge variant="secondary" className="ml-1 text-xs">{registry.count}</Badge>}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="nodes" className="mt-4 space-y-2">
          {nodesLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 rounded-lg border animate-pulse bg-muted/30" />
              ))}
            </div>
          ) : nodesData?.nodes && nodesData.nodes.length > 0 ? (
            <>
              <div className="flex items-center justify-between text-sm mb-3">
                <span className="text-muted-foreground">
                  {nodesData.nodes.filter(n => n.online).length} online of {nodesData.count} nodes
                </span>
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-green-500" />Online</span>
                  <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-muted-foreground/40" />Idle</span>
                </div>
              </div>
              {nodesData.nodes.map(node => <NodeRow key={node.node_id} node={node} />)}
            </>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Cpu className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No node activity yet</p>
                <p className="text-xs mt-1">Agents will appear here after their first cycle completes</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="did" className="mt-4 space-y-3">
          {/* DID explanation */}
          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground flex gap-3">
            <Shield className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-foreground mb-1">Decentralized Identity (DID)</p>
              <p>Each agent and user has a unique <code className="text-xs bg-muted px-1 rounded">did:vit:</code> identifier.
              The network guardian agent issues Verifiable Credentials (VCs) to active nodes — including
              NodeContributionCredential, OracleNodeCredential, and NetworkGuardianCredential.
              W3C DID Core compliant.</p>
            </div>
          </div>

          {registry?.identities && registry.identities.length > 0 ? (
            <div className="space-y-2">
              {/* Agent DIDs */}
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Agent Nodes ({registry.identities.filter(i => i.subject_type === "agent").length})
              </p>
              {registry.identities
                .filter(i => i.subject_type === "agent")
                .map(identity => <DIDRow key={identity.id} identity={identity} />)}

              {/* User DIDs */}
              {registry.identities.filter(i => i.subject_type === "user").length > 0 && (
                <>
                  <Separator className="my-4" />
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    User DIDs ({registry.identities.filter(i => i.subject_type === "user").length})
                  </p>
                  {registry.identities
                    .filter(i => i.subject_type === "user")
                    .map(identity => <DIDRow key={identity.id} identity={identity} />)}
                </>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Key className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">DID registry is empty</p>
                <p className="text-xs mt-1">Agent DIDs are created when the network-guardian runs its first cycle</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* VC credential types */}
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Award className="h-4 w-4 text-primary" /> Verifiable Credential Types
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
            {[
              { type: "NodeContributionCredential", desc: "Issued to agents with 24h activity. Tier: bronze/silver/gold/platinum.", icon: Zap, color: "text-yellow-500" },
              { type: "NetworkGuardianCredential", desc: "Issued to the guardian node. Grants DID/VC issuance capabilities.", icon: Shield, color: "text-blue-500" },
              { type: "KYCCredential", desc: "Issued to users after KYC approval. Links identity to human verification.", icon: User, color: "text-green-500" },
              { type: "ValidatorCredential", desc: "Issued to active consensus validators. Enables staking rewards.", icon: CheckCircle2, color: "text-purple-500" },
            ].map(({ type, desc, icon: Icon, color }) => (
              <div key={type} className="p-3 rounded-lg border space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Icon className={`h-4 w-4 ${color}`} />
                  <p className="font-medium text-xs">{type}</p>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
