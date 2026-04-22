import { useState } from "react";
import {
  useListValidators, useGetEconomy, useGetMyValidator, useApplyAsValidator,
  useAdminListValidators, useAdminApproveValidator, useAdminRejectValidator,
  useAdminSuspendValidator, useAdminReactivateValidator, useAdminSlashValidator,
  useWithdrawValidator,
} from "@/api-client";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ShieldCheck, Trophy, Activity, CheckCircle2, Coins, Lock, AlertTriangle, Ban, Play, Pause, Hourglass } from "lucide-react";
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
    <Card className="bg-card/50 backdrop-blur border-amber-500/30 shadow-[0_0_25px_rgba(245,158,11,0.08)]">
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
        <h1 className="text-3xl font-mono font-bold uppercase tracking-tight">Validator Network</h1>
        <p className="text-muted-foreground font-mono text-sm">Decentralized intelligence consensus nodes</p>
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-card/50 backdrop-blur border-border">
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
            <Card className="bg-card/50 backdrop-blur border-primary/20">
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
            <Card className="bg-card/50 backdrop-blur border-secondary/20 shadow-[0_0_20px_rgba(255,215,0,0.05)]">
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

          <Card className="bg-card/50 backdrop-blur border-border">
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
