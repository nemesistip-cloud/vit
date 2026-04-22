import { useState } from "react";
import {
  useListValidators, useGetEconomy, useGetMyValidator, useApplyAsValidator,
} from "@/api-client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ShieldCheck, Trophy, Activity, CheckCircle2, Coins } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";

export default function ValidatorsPage() {
  const { data: validators, isLoading: isLoadingVal } = useListValidators();
  const { data: economy, isLoading: isLoadingEcon } = useGetEconomy();
  const { data: myValidator } = useGetMyValidator();
  const apply = useApplyAsValidator();
  const [stakeInput, setStakeInput] = useState("100");

  if (isLoadingVal || isLoadingEcon) {
    return <div className="h-full flex items-center justify-center font-mono text-muted-foreground">SCANNING_NODES...</div>;
  }

  const handleApply = async () => {
    try {
      await apply.mutateAsync({ stake_amount: parseFloat(stakeInput) });
      toast.success("Validator application submitted");
    } catch (e: any) {
      toast.error(e.message || "Application failed");
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
                {validatorList.map((validator, idx) => (
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
                  <div className="text-center py-12 text-muted-foreground font-mono">NO_ACTIVE_VALIDATORS</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {myValidator ? (
            <Card className="bg-card/50 backdrop-blur border-primary/20">
              <CardHeader className="border-b border-border/50 pb-4">
                <CardTitle className="font-mono uppercase text-sm flex items-center">
                  <CheckCircle2 className="w-4 h-4 mr-2 text-primary" />
                  My Validator Profile
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-3 font-mono text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground uppercase text-xs">Status</span>
                  <Badge variant="outline" className="text-xs uppercase">{myValidator.status}</Badge>
                </div>
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
                        Requires Analyst role or higher. Your VITCoin will be locked as stake.
                      </p>
                      <Button
                        className="w-full"
                        variant="secondary"
                        onClick={handleApply}
                        disabled={apply.isPending || parseFloat(stakeInput) < 100}
                      >
                        {apply.isPending ? "SUBMITTING..." : "SUBMIT_APPLICATION"}
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
                {validatorList.slice(0, 5).map((v, idx) => (
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
                  <div className="text-center py-8 text-muted-foreground font-mono text-sm">NO_DATA</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
