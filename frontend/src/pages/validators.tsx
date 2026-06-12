import { useState, type ReactNode } from "react";
import {
  useListValidators, useGetEconomy, useGetMyValidator, useApplyAsValidator,
  useAdminListValidators, useAdminApproveValidator, useAdminRejectValidator,
  useAdminSuspendValidator, useAdminReactivateValidator, useAdminSlashValidator,
  useWithdrawValidator, useGetNetworkAnalytics, useGetValidatorLeaderboard,
  useGetSlashHistory,
} from "@/api-client";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { ShieldCheck, Trophy, Activity, CheckCircle2, Coins, Lock, AlertTriangle, Ban, Play, Pause, Hourglass, BarChart3, Flame, Database, Zap, TrendingUp } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";

const STATUS_BADGE: Record<string, { label: string; cls: string; icon: any }> = {
  pending:   { label: "Pending review",  cls: "bg-amber-500/15 text-amber-400 border-amber-500/30", icon: Hourglass },
  active:    { label: "Active",          cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", icon: CheckCircle2 },
  suspended: { label: "Suspended",       cls: "bg-orange-500/15 text-orange-400 border-orange-500/30", icon: Pause },
  slashed:   { label: "Slashed",         cls: "bg-red-500/15 text-red-400 border-red-500/30", icon: Ban },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_BADGE[status?.toLowerCase()] || STATUS_BADGE.pending;
  const Icon = s.icon;
  return (
    <Badge variant="outline" className={`text-[10px] uppercase font-mono gap-1 ${s.cls}`}>
      <Icon className="w-3 h-3" /> {s.label}
    </Badge>
  );
}

// ── Admin management panel ─────────────────────────────────────────────
function AdminValidatorPanel() {
  const [tab, setTab] = useState<"pending" | "active" | "suspended" | "slashed" | "all">("pending");
  const filter = tab === "all" ? undefined : tab;
  const { data, isLoading, refetch } = useAdminListValidators(filter);
  const approve = useAdminApproveValidator();
  const reject = useAdminRejectValidator();
  const suspend = useAdminSuspendValidator();
  const reactivate = useAdminReactivateValidator();
  const slash = useAdminSlashValidator();

  const list = data?.validators ?? [];

  const run = async (action: () => Promise<any>, label: string) => {
    try { await action(); toast.success(label); refetch(); }
    catch (e: any) { toast.error(e?.message || `${label} failed`); }
  };

  return (
    <Card className="bg-card/50  border-amber-500/30 ">
      <CardHeader className="border-b border-border/50 pb-4">
        <CardTitle className="font-mono uppercase flex items-center text-amber-400">
          <Lock className="w-5 h-5 mr-2" /> Admin · Validator Management
        </CardTitle>
        <CardDescription className="font-mono">
          Approve applications, suspend, reactivate, or slash validators
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <Tabs value={tab} onValueChange={(v) => setTab(v as any)}>
          <TabsList className="grid grid-cols-5 font-mono text-xs">
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="suspended">Suspended</TabsTrigger>
            <TabsTrigger value="slashed">Slashed</TabsTrigger>
            <TabsTrigger value="all">All</TabsTrigger>
          </TabsList>
          <TabsContent value={tab} className="pt-4">
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground font-mono text-sm">Loading…</div>
            ) : list.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground font-mono text-sm">
                No {tab} validators
              </div>
            ) : (
              <div className="divide-y divide-border/50">
                {list.map((v: any) => (
                  <div key={v.id} className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-mono font-bold flex items-center gap-2">
                        {v.username}
                        <StatusBadge status={v.status} />
                        <span className="text-[10px] text-muted-foreground uppercase">{v.role}</span>
                      </div>
                      <div className="text-xs text-muted-foreground font-mono mt-1">
                        {v.email} · Stake {Number(v.stake_amount).toLocaleString()} VIT · Trust {(v.trust_score * 100).toFixed(0)}/100 · Applied {format(new Date(v.joined_at), "yyyy-MM-dd HH:mm")}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {v.status === "pending" && (
                        <>
                          <Button size="sm" variant="default" disabled={approve.isPending}
                            onClick={() => run(() => approve.mutateAsync(v.id), "Validator approved")}>
                            <CheckCircle2 className="w-3 h-3 mr-1" /> Approve
                          </Button>
                          <Button size="sm" variant="destructive" disabled={reject.isPending}
                            onClick={() => {
                              if (confirm(`Reject ${v.username}'s application and refund ${v.stake_amount} VIT?`))
                                run(() => reject.mutateAsync(v.id), "Application rejected, stake refunded");
                            }}>
                            Reject + Refund
                          </Button>
                        </>
                      )}
                      {v.status === "active" && (
                        <>
                          <Button size="sm" variant="outline" disabled={suspend.isPending}
                            onClick={() => run(() => suspend.mutateAsync(v.id), "Validator suspended")}>
                            <Pause className="w-3 h-3 mr-1" /> Suspend
                          </Button>
                          <Button size="sm" variant="destructive" disabled={slash.isPending}
                            onClick={() => {
                              const reason = prompt(`Slash ${v.username}? This burns their entire ${v.stake_amount} VIT stake. Enter a reason:`);
                              if (reason)
                                run(() => slash.mutateAsync({ id: v.id, burn_pct: 1.0, reason }), "Validator slashed, stake burned");
                            }}>
                            <Ban className="w-3 h-3 mr-1" /> Slash
                          </Button>
                        </>
                      )}
                      {v.status === "suspended" && (
                        <>
                          <Button size="sm" variant="default" disabled={reactivate.isPending}
                            onClick={() => run(() => reactivate.mutateAsync(v.id), "Validator reactivated")}>
                            <Play className="w-3 h-3 mr-1" /> Reactivate
                          </Button>
                          <Button size="sm" variant="destructive" disabled={slash.isPending}
                            onClick={() => {
                              const reason = prompt(`Slash ${v.username}? Burns ${v.stake_amount} VIT. Enter a reason:`);
                              if (reason)
                                run(() => slash.mutateAsync({ id: v.id, burn_pct: 1.0, reason }), "Validator slashed");
                            }}>
                            <Ban className="w-3 h-3 mr-1" /> Slash
                          </Button>
                        </>
                      )}
                      {v.status === "slashed" && (
                        <span className="text-xs text-muted-foreground font-mono italic flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> Terminal — stake burned
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

// ── Network Analytics Panel ─────────────────────────────────────────────
function NetworkAnalyticsPanel({ isAdmin = false }: { isAdmin?: boolean }) {
  const { data: net, isLoading } = useGetNetworkAnalytics();
  const { data: lb } = useGetValidatorLeaderboard(5);
  const { data: slashHist } = useGetSlashHistory(isAdmin ? { limit: 5 } : undefined);
  const [tab, setTab] = useState<"overview" | "leaderboard" | "slashing">("overview");
  const tabs = isAdmin
    ? (["overview", "leaderboard", "slashing"] as const)
    : (["overview", "leaderboard"] as const);

  if (isLoading) {
    return (
      <div className="text-center py-6 text-muted-foreground font-mono text-sm animate-pulse">
        Fetching network telemetry…
      </div>
    );
  }

  const v = net?.validators ?? {};
  const c = net?.consensus ?? {};
  const s = net?.settlements ?? {};
  const o = net?.oracle ?? {};
  const sk = net?.staking ?? {};
  const sl = net?.slashing ?? {};
  const acc = net?.validator_accuracy ?? {};

  const statCell = (label: string, val: ReactNode, sub?: string, accent?: string) => (
    <div className="rounded-lg border border-border bg-background/40 p-3 space-y-0.5">
      <div className="text-[9px] font-mono text-muted-foreground uppercase">{label}</div>
      <div className={`text-base font-bold font-mono ${accent ?? ""}`}>{val}</div>
      {sub && <div className="text-[9px] text-muted-foreground font-mono">{sub}</div>}
    </div>
  );

  const leaderboard = Array.isArray(lb?.leaderboard) ? lb.leaderboard : [];
  const slashes = Array.isArray(slashHist?.events) ? slashHist.events : [];

  return (
    <Card className="bg-card/50  border-primary/20 ">
      <CardHeader className="border-b border-border/50 pb-4">
        <CardTitle className="font-mono uppercase flex items-center text-primary">
          <BarChart3 className="w-5 h-5 mr-2" /> Network Analytics
        </CardTitle>
        <CardDescription className="font-mono text-xs">
          Live blockchain consensus network statistics
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        <div className="flex gap-1 bg-background/50 rounded-lg p-0.5 border border-border/40">
          {tabs.map((t) => (
            <button key={t} type="button" onClick={() => setTab(t as any)}
              className={`flex-1 text-[10px] font-mono uppercase py-1.5 rounded transition-all ${
                tab === t
                  ? "bg-primary/20 text-primary border border-primary/40"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "overview" ? "Overview" : t === "leaderboard" ? "Leaderboard" : "Slashings"}
            </button>
          ))}
        </div>

        {tab === "overview" && (
          <div className="space-y-3">
            <div>
              <div className="text-[9px] font-mono text-muted-foreground uppercase mb-2 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Validators
              </div>
              <div className="grid grid-cols-3 gap-2">
                {statCell("Active", v.active ?? 0, `of ${v.total ?? 0} total`, "text-emerald-400")}
                {statCell("Staked VIT", Number(v.total_staked_vit ?? 0).toLocaleString())}
                {statCell("Avg Trust", `${((v.avg_trust_score ?? 0) * 100).toFixed(0)}/100`)}
              </div>
            </div>
            <div>
              <div className="text-[9px] font-mono text-muted-foreground uppercase mb-2 flex items-center gap-1">
                <Zap className="w-3 h-3" /> Consensus & Oracle
              </div>
              <div className="grid grid-cols-3 gap-2">
                {statCell("Open", c.open ?? 0, "consensus rounds")}
                {statCell("Settled", c.settled ?? 0, `of ${c.total ?? 0}`)}
                {statCell("Oracle Accept", `${((o.acceptance_rate ?? 0) * 100).toFixed(0)}%`, `${o.total_reports ?? 0} reports`)}
              </div>
            </div>
            <div>
              <div className="text-[9px] font-mono text-muted-foreground uppercase mb-2 flex items-center gap-1">
                <Database className="w-3 h-3" /> Settlement & Staking
              </div>
              <div className="grid grid-cols-3 gap-2">
                {statCell("Pool Settled", `${Number(s.total_pool_vit ?? 0).toLocaleString()} VIT`)}
                {statCell("Burned", `${Number(s.total_burned_vit ?? 0).toLocaleString()} VIT`, undefined, "text-red-400")}
                {statCell("Active Stakes", sk.active_stakes ?? 0)}
              </div>
            </div>
            {(acc.total_settled ?? 0) > 0 && (
              <div className="space-y-1">
                <div className="flex justify-between font-mono text-xs">
                  <span className="text-muted-foreground uppercase">Validator Accuracy</span>
                  <span className="text-primary">{((acc.accuracy_rate ?? 0) * 100).toFixed(1)}%</span>
                </div>
                <Progress value={(acc.accuracy_rate ?? 0) * 100} className="h-1.5 bg-muted [&>div]:bg-primary" />
                <div className="text-[9px] text-muted-foreground font-mono text-right">
                  {acc.accurate ?? 0} accurate / {acc.total_settled ?? 0} settled predictions
                </div>
              </div>
            )}
            {(sl.total_events ?? 0) > 0 && (
              <div className="flex items-center justify-between rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 font-mono text-xs">
                <span className="flex items-center gap-1 text-red-400">
                  <Flame className="w-3 h-3" /> Slash Events
                </span>
                <span className="text-red-400 font-bold">{sl.total_events} · {Number(sl.total_volume_vit ?? 0).toLocaleString()} VIT burned</span>
              </div>
            )}
          </div>
        )}

        {tab === "leaderboard" && (
          <div className="space-y-1">
            {leaderboard.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground font-mono text-sm">
                No validator data yet — apply to become the first.
              </div>
            ) : leaderboard.map((v: any, i: number) => (
              <div key={v.validator_id ?? i} className="flex items-center gap-3 py-2 px-2 rounded-lg hover:bg-muted/10 transition-colors">
                <div className={`w-7 h-7 rounded flex items-center justify-center font-mono font-bold text-xs flex-shrink-0 ${
                  i === 0 ? "bg-secondary/20 text-secondary border border-secondary/50" :
                  i === 1 ? "bg-muted text-muted-foreground border border-border" :
                  i === 2 ? "bg-amber-900/20 text-amber-600 border border-amber-900/50" :
                  "text-muted-foreground"
                }`}>#{i + 1}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-mono font-bold text-sm truncate">{v.username}</div>
                  <div className="flex gap-2 text-[9px] text-muted-foreground font-mono">
                    <span>{((v.accuracy_rate ?? 0) * 100).toFixed(1)}% ACC</span>
                    <span>{Number(v.stake_amount ?? 0).toLocaleString()} VIT</span>
                  </div>
                </div>
                <div className="text-right font-mono flex-shrink-0">
                  <div className="text-sm font-bold text-primary">{Number(v.influence_score ?? 0).toFixed(3)}</div>
                  <div className="text-[9px] text-muted-foreground uppercase">influence</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "slashing" && (
          <div className="space-y-2">
            {slashes.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground font-mono text-sm">
                No slash events recorded.
              </div>
            ) : slashes.map((e: any, i: number) => (
              <div key={e.id ?? i} className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <div className="font-mono text-xs font-bold text-red-400 truncate">{e.validator_username ?? e.validator_id?.slice(0, 12)}</div>
                  <Badge variant="outline" className="text-[9px] font-mono border-red-500/30 text-red-400">
                    -{(Number(e.slash_pct ?? 0) * 100).toFixed(0)}% stake
                  </Badge>
                </div>
                <div className="text-[9px] text-muted-foreground font-mono">{e.slash_reason}</div>
                <div className="flex justify-between text-[9px] text-muted-foreground font-mono">
                  <span>{Number(e.slash_amount ?? 0).toLocaleString()} VIT burned</span>
                  <span>{e.slashed_at ? format(new Date(e.slashed_at), "yyyy-MM-dd HH:mm") : "—"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ───────────────────────────────────────────────────────────────
export default function ValidatorsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const { data: validators, isLoading: isLoadingVal } = useListValidators();
  const { data: economy, isLoading: isLoadingEcon } = useGetEconomy();
  const { data: myValidator } = useGetMyValidator();
  const apply = useApplyAsValidator();
  const withdraw = useWithdrawValidator();
  const [stakeInput, setStakeInput] = useState("100");

  if (isLoadingVal || isLoadingEcon) {
    return <div className="h-full flex items-center justify-center font-mono text-muted-foreground">Scanning consensus nodes…</div>;
  }

  const handleApply = async () => {
    try {
      await apply.mutateAsync({ stake_amount: parseFloat(stakeInput) });
      toast.success("Application submitted — awaiting admin review");
    } catch (e: any) {
      toast.error(e?.message || "Application failed");
    }
  };

  const handleWithdraw = async () => {
    if (!confirm("Withdraw your validator profile? Your locked stake will be refunded to your wallet.")) return;
    try {
      const r: any = await withdraw.mutateAsync();
      toast.success(`Withdrawn — ${Number(r.refunded || 0).toLocaleString()} VIT refunded`);
    } catch (e: any) {
      toast.error(e?.message || "Withdraw failed");
    }
  };

  const validatorList = Array.isArray(validators) ? validators : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">Network Validator System</h1>
        <p className="text-muted-foreground font-mono text-sm">Decentralized analytics consensus nodes</p>
      </div>

      {economy && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-lg border border-border bg-card/30 p-4">
            <div className="text-xs font-mono text-muted-foreground uppercase mb-1">Active Validators</div>
            <div className="text-xl font-bold font-mono">{economy.active_validators ?? 0}</div>
          </div>
          <div className="rounded-lg border border-secondary/30 bg-secondary/5 p-4">
            <div className="text-xs font-mono text-muted-foreground uppercase mb-1">Total Staked</div>
            <div className="text-xl font-bold font-mono text-secondary">
              {Number(economy.total_staked_vitcoin ?? 0).toLocaleString()} VIT
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card/30 p-4">
            <div className="text-xs font-mono text-muted-foreground uppercase mb-1">VIT Price (USD)</div>
            <div className="text-xl font-bold font-mono text-primary">
              ${Number(economy.vitcoin_price_usd ?? 0).toFixed(6)}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card/30 p-4">
            <div className="text-xs font-mono text-muted-foreground uppercase mb-1">Matches Settled</div>
            <div className="text-xl font-bold font-mono">{economy.matches_settled ?? 0}</div>
          </div>
        </div>
      )}

      {isAdmin && <AdminValidatorPanel />}

      <NetworkAnalyticsPanel isAdmin={isAdmin} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-card/50  border-border">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase flex items-center">
                <ShieldCheck className="w-5 h-5 mr-2 text-primary" />
                Active Nodes
              </CardTitle>
              <CardDescription className="font-mono">Real-time status of consensus participants</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border/50">
                {validatorList.map((validator: any, idx: number) => (
                  <div key={validator.username + idx} className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-muted/10 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="relative">
                        <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center font-mono font-bold text-lg border border-border">
                          {validator.username.substring(0, 2).toUpperCase()}
                        </div>
                        <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-background flex items-center justify-center">
                          <div
                            className={`w-2.5 h-2.5 rounded-full ${
                              validator.accuracy_rate >= 0.55
                                ? "bg-emerald-500 animate-pulse"
                                : validator.accuracy_rate > 0
                                ? "bg-amber-400"
                                : "bg-gray-500"
                            }`}
                            title={
                              validator.accuracy_rate >= 0.55
                                ? "High accuracy · Online"
                                : validator.accuracy_rate > 0
                                ? "Active · Low accuracy"
                                : "No predictions yet"
                            }
                          />
                        </div>
                      </div>
                      <div>
                        <div className="font-bold text-lg font-mono flex items-center gap-2">
                          {validator.username}
                          {validator.trust_score > 0.9 && <CheckCircle2 className="w-4 h-4 text-primary" />}
                        </div>
                        <div className="text-xs text-muted-foreground font-mono uppercase mt-1">
                          Joined {format(new Date(validator.joined_at), "yyyy-MM-dd")}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-8 items-center text-sm font-mono">
                      <div>
                        <div className="text-muted-foreground uppercase text-xs mb-1">Stake</div>
                        <div className="font-bold text-secondary">{Number(validator.stake).toLocaleString()} VIT</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground uppercase text-xs mb-1">Accuracy</div>
                        <div className="font-bold text-primary">{(validator.accuracy_rate * 100).toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground uppercase text-xs mb-1">Trust</div>
                        <div className="font-bold">{(validator.trust_score * 100).toFixed(0)}/100</div>
                      </div>
                    </div>
                  </div>
                ))}
                {validatorList.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground font-mono text-sm">
                    No active validators yet — be the first to apply.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {myValidator ? (
            <Card className="bg-card/50  border-primary/20">
              <CardHeader className="border-b border-border/50 pb-4">
                <CardTitle className="font-mono uppercase text-sm flex items-center justify-between">
                  <span className="flex items-center"><CheckCircle2 className="w-4 h-4 mr-2 text-primary" /> My Validator Profile</span>
                  <StatusBadge status={myValidator.status} />
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-3 font-mono text-sm">
                {myValidator.status === "pending" && (
                  <div className="rounded border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
                    Your application is awaiting admin review. You'll be notified once approved.
                  </div>
                )}
                {myValidator.status === "suspended" && (
                  <div className="rounded border border-orange-500/30 bg-orange-500/10 p-3 text-xs text-orange-300">
                    Your validator is currently suspended. Contact an admin for reinstatement.
                  </div>
                )}
                {myValidator.status === "slashed" && (
                  <div className="rounded border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
                    Your validator has been slashed. Stake forfeited and predictions disabled.
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">Staked</span>
                  <span className="font-bold text-secondary">{Number(myValidator.stake_amount).toLocaleString()} VIT</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">Trust Score</span>
                  <span className="font-bold">{(myValidator.trust_score * 100).toFixed(0)}/100</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">Predictions</span>
                  <span className="font-bold">{myValidator.total_predictions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">Accuracy</span>
                  <span className="font-bold text-primary">{(myValidator.accuracy_rate * 100).toFixed(1)}%</span>
                </div>
                {myValidator.status !== "slashed" && (
                  <Button variant="outline" className="w-full mt-3" size="sm"
                    onClick={handleWithdraw} disabled={withdraw.isPending}>
                    {withdraw.isPending ? "Withdrawing…" : "Withdraw & Refund Stake"}
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-card/50  border-secondary/20 ">
              <CardHeader className="border-b border-border/50 pb-4">
                <CardTitle className="font-mono uppercase flex items-center text-secondary">
                  <Trophy className="w-5 h-5 mr-2" />
                  Become a Validator
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                <p className="text-xs font-mono text-muted-foreground">
                  Stake VITCoin to join the consensus network and earn rewards for accurate predictions.
                  Applications require admin approval before activation.
                </p>
                <Dialog>
                  <DialogTrigger asChild>
                    <Button className="w-full font-mono" variant="secondary">
                      <Coins className="w-4 h-4 mr-2" />
                      Apply as Validator
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="font-mono">
                    <DialogHeader>
                      <DialogTitle className="font-mono uppercase">Validator Application</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 pt-2">
                      <div>
                        <label className="text-xs text-muted-foreground uppercase mb-1 block">
                          Stake Amount (VITCoin, min 100)
                        </label>
                        <Input
                          type="number"
                          value={stakeInput}
                          onChange={(e) => setStakeInput(e.target.value)}
                          min="100"
                          className="font-mono"
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Requires Analyst, Pro, Elite, or Admin tier. Your VITCoin will be locked until an admin approves or rejects your application.
                      </p>
                      <Button
                        className="w-full"
                        variant="secondary"
                        onClick={handleApply}
                        disabled={apply.isPending || parseFloat(stakeInput) < 100}
                      >
                        {apply.isPending ? "Submitting…" : "Submit Application"}
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </CardContent>
            </Card>
          )}

          <Card className="bg-card/50  border-border">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <Activity className="w-4 h-4 mr-2" />
                Top Validators
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border/50">
                {validatorList.slice(0, 5).map((v: any, idx: number) => (
                  <div key={v.username + idx} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-8 h-8 rounded flex items-center justify-center font-mono font-bold text-sm ${
                        idx === 0 ? "bg-secondary/20 text-secondary border border-secondary/50" :
                        idx === 1 ? "bg-muted text-muted-foreground border border-border" :
                        idx === 2 ? "bg-amber-900/20 text-amber-600 border border-amber-900/50" :
                        "text-muted-foreground"
                      }`}>
                        #{idx + 1}
                      </div>
                      <div>
                        <div className="font-bold font-mono text-sm">{v.username}</div>
                        <div className="text-xs text-muted-foreground font-mono flex items-center gap-2">
                          <Activity className="w-3 h-3" />
                          {(v.accuracy_rate * 100).toFixed(1)}% ACC
                        </div>
                      </div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="font-bold text-sm text-secondary">
                        {Number(v.influence_score).toFixed(2)}
                      </div>
                      <div className="text-[10px] text-muted-foreground uppercase">Influence</div>
                    </div>
                  </div>
                ))}
                {validatorList.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground font-mono text-sm">No data yet</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
