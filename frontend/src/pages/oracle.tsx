import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  AlertTriangle, CheckCircle2, Clock, Database, Eye, RefreshCw,
  Server, Shield, Zap, Activity, GitMerge, Hash,
} from "lucide-react";
import { apiRequest } from "@/lib/queryClient";

// ─── Types ───────────────────────────────────────────────────────────────────

interface OracleStats {
  total_submissions: number;
  accepted_submissions: number;
  disputed_submissions: number;
  pending_submissions: number;
  settlements_triggered: number;
  consensus_rate_pct: number;
  sources: { source: string; count: number; accepted: number }[];
  recent: {
    id: string; match_id: string; source: string; result: string;
    is_accepted: boolean; dispute_flag: boolean; submitted_at: string;
  }[];
  snapshot_at: string;
}

interface OracleDisputes {
  disputes: Record<string, { source: string; result: string; submitted_at: string }[]>;
  total_matches: number;
}

interface NetworkNode {
  node_id: string; node_name: string; node_type: string;
  total_contributions: number; contributions_24h: number;
  total_score: number; last_active: string | null; online: boolean; status: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M`
  : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K`
  : String(n);

const timeAgo = (iso: string) => {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
};

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

function ResultBadge({ result }: { result: string }) {
  const map: Record<string, string> = {
    home: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    draw: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    away: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${map[result] ?? "bg-muted"}`}>
      {result.toUpperCase()}
    </span>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function OraclePage() {
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery<OracleStats>({
    queryKey: ["oracle-stats"],
    queryFn: () => apiRequest("GET", "/api/oracle/stats").then(r => r.json()),
    refetchInterval: 30_000,
  });

  const { data: disputes } = useQuery<OracleDisputes>({
    queryKey: ["oracle-disputes"],
    queryFn: () => apiRequest("GET", "/api/admin/oracle/disputes").then(r => r.json()),
    refetchInterval: 60_000,
  });

  const { data: networkData } = useQuery<{ nodes: NetworkNode[] }>({
    queryKey: ["network-nodes-oracle"],
    queryFn: () => apiRequest("GET", "/api/network/nodes?node_type=agent&limit=5").then(r => r.json()),
    refetchInterval: 60_000,
  });

  const oracleNode = networkData?.nodes?.find(n => n.node_name === "oracle-node");

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="h-8 w-8 text-primary" />
            VIT Oracle
          </h1>
          <p className="text-muted-foreground mt-1">
            Consensus-based match result verification — 2-of-3 agreement required for settlement
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetchStats()} className="gap-2">
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
      ) : stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon={Database}
            label="Total Submissions"
            value={fmt(stats.total_submissions)}
            sub="All oracle sources"
          />
          <StatCard
            icon={CheckCircle2}
            label="Accepted"
            value={fmt(stats.accepted_submissions)}
            sub={`${stats.consensus_rate_pct?.toFixed(1) ?? 0}% consensus rate`}
            color="text-green-500"
          />
          <StatCard
            icon={AlertTriangle}
            label="Disputes"
            value={fmt(stats.disputed_submissions)}
            sub="Require admin resolution"
            color={stats.disputed_submissions > 0 ? "text-red-500" : "text-muted-foreground"}
          />
          <StatCard
            icon={Zap}
            label="Settlements"
            value={fmt(stats.settlements_triggered)}
            sub="Auto-triggered by consensus"
            color="text-yellow-500"
          />
        </div>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Oracle Node status */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Server className="h-4 w-4 text-primary" /> Oracle Node Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Internal node */}
            <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/30">
              <div>
                <p className="text-sm font-medium">vit-node-internal</p>
                <p className="text-xs text-muted-foreground">did:vit:agent:oracle-node</p>
              </div>
              <Badge
                variant={oracleNode?.online ? "default" : "secondary"}
                className={oracleNode?.online ? "bg-green-500/20 text-green-500 border-green-500/30" : ""}
              >
                {oracleNode?.online ? "Online" : "Idle"}
              </Badge>
            </div>

            {oracleNode && (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Contributions (24h)</span>
                  <span className="font-medium">{oracleNode.contributions_24h}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Score</span>
                  <span className="font-medium">{oracleNode.total_score.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Active</span>
                  <span className="font-medium">
                    {oracleNode.last_active ? timeAgo(oracleNode.last_active) : "Never"}
                  </span>
                </div>
              </div>
            )}

            <Separator />

            {/* Source breakdown */}
            {stats?.sources && stats.sources.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Active Sources
                </p>
                {stats.sources.map(s => (
                  <div key={s.source} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground truncate max-w-[120px]">{s.source}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-green-500">{s.accepted}✓</span>
                      <span className="font-medium">{s.count}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Oracle mechanism */}
            <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground space-y-1">
              <div className="flex items-center gap-1.5 font-medium text-foreground">
                <GitMerge className="h-3.5 w-3.5 text-primary" /> Consensus Rules
              </div>
              <p>2-of-3 sources must agree to settle</p>
              <p>3-way conflict → admin dispute queue</p>
              <p>Settlement triggers VITCoin distribution</p>
            </div>
          </CardContent>
        </Card>

        {/* Recent submissions */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" /> Recent Oracle Submissions
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!stats?.recent || stats.recent.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
                <Eye className="h-8 w-8 opacity-40" />
                <p className="text-sm">No oracle submissions yet</p>
                <p className="text-xs">The oracle-node agent submits results for finished matches</p>
              </div>
            ) : (
              <div className="space-y-2">
                {stats.recent.map(r => (
                  <div
                    key={r.id}
                    className={`flex items-center justify-between p-3 rounded-lg border text-sm transition-colors ${
                      r.dispute_flag
                        ? "border-red-500/30 bg-red-500/5"
                        : r.is_accepted
                        ? "border-green-500/30 bg-green-500/5"
                        : "bg-muted/30"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {r.dispute_flag ? (
                        <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
                      ) : r.is_accepted ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      ) : (
                        <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
                      )}
                      <div className="min-w-0">
                        <p className="font-medium truncate">Match #{r.match_id}</p>
                        <p className="text-xs text-muted-foreground">{r.source}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <ResultBadge result={r.result} />
                      <span className="text-xs text-muted-foreground">
                        {timeAgo(r.submitted_at)}
                      </span>
                      {r.dispute_flag && (
                        <Badge variant="destructive" className="text-xs">Dispute</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Disputes section */}
      {disputes && disputes.total_matches > 0 && (
        <Card className="border-red-500/30">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2 text-red-500">
              <AlertTriangle className="h-4 w-4" />
              Active Disputes ({disputes.total_matches} match{disputes.total_matches !== 1 ? "es" : ""})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(disputes.disputes).map(([matchId, submissions]) => (
                <div key={matchId} className="rounded-lg border border-red-500/20 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Hash className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">Match #{matchId}</span>
                    <Badge variant="destructive" className="text-xs ml-auto">Awaiting Admin</Badge>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    {submissions.map((s, i) => (
                      <div key={i} className="text-sm p-2 rounded bg-muted/50">
                        <p className="font-medium">{s.source}</p>
                        <p className="text-muted-foreground">
                          Result: <span className="font-semibold text-foreground">{s.result.toUpperCase()}</span>
                        </p>
                        <p className="text-xs text-muted-foreground">{timeAgo(s.submitted_at)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* How oracle works */}
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">How the VIT Oracle Works</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
            {[
              {
                step: "1", icon: Server, title: "Result Submission",
                desc: "The oracle-node agent monitors finished matches in the DB and submits results to the consensus pool as source 'vit-node-internal'.",
              },
              {
                step: "2", icon: GitMerge, title: "2-of-3 Consensus",
                desc: "When any 2 of 3 oracle sources agree on the outcome (home/draw/away), consensus is reached and settlement is triggered automatically.",
              },
              {
                step: "3", icon: Zap, title: "VITCoin Settlement",
                desc: "The settlement engine distributes staking rewards: 40% validators, 30% treasury, 20% burn, 10% AI fund.",
              },
            ].map(({ step, icon: Icon, title, desc }) => (
              <div key={step} className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-bold shrink-0">
                  {step}
                </div>
                <div>
                  <div className="flex items-center gap-1.5 font-medium mb-1">
                    <Icon className="h-4 w-4 text-primary" /> {title}
                  </div>
                  <p className="text-muted-foreground text-xs leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
