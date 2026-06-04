import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { API } from "@/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  Vault, TrendingUp, TrendingDown, PiggyBank, BarChart3,
  Plus, Send, CheckCircle, XCircle, Clock, DollarSign
} from "lucide-react";

interface Pool {
  pool_type: string;
  balance: number;
  total_deposited: number;
  total_spent: number;
  allocation_pct: number;
  share_of_treasury: number;
  utilization_pct: number;
  auto_refill: boolean;
}

interface TreasuryOverview {
  total_balance_vit: number;
  total_deposited_vit: number;
  total_spent_vit: number;
  utilization_pct: number;
  pending_grant_proposals: number;
  pools: Pool[];
}

const POOL_COLORS: Record<string, string> = {
  validator_rewards: "bg-green-500",
  ai_infrastructure: "bg-blue-500",
  ecosystem_grants: "bg-purple-500",
  reserve: "bg-slate-500",
  oracle_incentives: "bg-yellow-500",
  prediction_liquidity: "bg-cyan-500",
  bug_bounty: "bg-red-500",
  team_vesting: "bg-orange-500",
};

const POOL_ICONS: Record<string, string> = {
  validator_rewards: "⚡",
  ai_infrastructure: "🤖",
  ecosystem_grants: "🌱",
  reserve: "🏦",
  oracle_incentives: "🔮",
  prediction_liquidity: "💹",
  bug_bounty: "🐛",
  team_vesting: "👥",
};

export default function TreasuryPage() {
  const { toast } = useToast();
  const qc = useQueryClient();
  const [grantTitle, setGrantTitle] = useState("");
  const [grantDesc, setGrantDesc] = useState("");
  const [grantAmount, setGrantAmount] = useState("");
  const [grantPool, setGrantPool] = useState("ecosystem_grants");
  const [depositPool, setDepositPool] = useState("validator_rewards");
  const [depositAmount, setDepositAmount] = useState("");
  const [depositSource, setDepositSource] = useState("");
  const [epochReward, setEpochReward] = useState("1000");

  const { data: overview, isLoading } = useQuery({
    queryKey: [API.treasuryOverview],
    queryFn: () => apiGet<TreasuryOverview>(API.treasuryOverview),
    refetchInterval: 20_000,
  });

  const bootstrapMutation = useMutation({
    mutationFn: () => apiPost<{ created: number }>("/api/treasury/bootstrap", {}),
    onSuccess: (d) => {
      toast({ title: "Treasury bootstrapped", description: `${d.created} pools created` });
      qc.invalidateQueries({ queryKey: [API.treasuryOverview] });
    },
  });

  const depositMutation = useMutation({
    mutationFn: (data: { pool_type: string; amount: number; source: string }) =>
      apiPost<{ new_balance: number }>(API.treasuryDeposit, data),
    onSuccess: (d) => {
      toast({ title: "Deposit successful", description: `New balance: ${d.new_balance.toFixed(2)} VIT` });
      qc.invalidateQueries({ queryKey: [API.treasuryOverview] });
    },
    onError: (e: Error) => toast({ title: "Deposit failed", description: e.message, variant: "destructive" }),
  });

  const epochMutation = useMutation({
    mutationFn: (total: number) => apiPost<{ distributed: Record<string, number> }>("/api/treasury/distribute-epoch", { total_block_reward: total }),
    onSuccess: (d) => {
      toast({ title: "Epoch rewards distributed", description: `Across ${Object.keys(d.distributed).length} pools` });
      qc.invalidateQueries({ queryKey: [API.treasuryOverview] });
    },
  });

  const grantMutation = useMutation({
    mutationFn: (data: { title: string; description: string; pool_type: string; requested_amount: number }) =>
      apiPost<{ proposal_id: number; status: string }>(API.treasuryGrants, data),
    onSuccess: (d) => {
      toast({ title: "Grant proposal submitted", description: `Protocol Proposal #${d.proposal_id} — ${d.status}` });
      setGrantTitle(""); setGrantDesc(""); setGrantAmount("");
    },
    onError: (e: Error) => toast({ title: "Submission failed", description: e.message, variant: "destructive" }),
  });

  const pools = overview?.pools ?? [];
  const totalBalance = overview?.total_balance_vit ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Vault className="w-6 h-6 text-yellow-400" />
            VIT Treasury
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Governance-controlled multi-pool treasury — 8 allocation pools
          </p>
        </div>
        <Button onClick={() => bootstrapMutation.mutate()} variant="outline" className="border-yellow-500/30 text-yellow-300">
          Initialize Pools
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Balance", value: `${(totalBalance / 1000).toFixed(1)}K VIT`, icon: PiggyBank, color: "text-yellow-400" },
          { label: "Total Deposited", value: `${((overview?.total_deposited_vit ?? 0) / 1000).toFixed(1)}K VIT`, icon: TrendingUp, color: "text-green-400" },
          { label: "Total Spent", value: `${((overview?.total_spent_vit ?? 0) / 1000).toFixed(1)}K VIT`, icon: TrendingDown, color: "text-red-400" },
          { label: "Pending Grants", value: overview?.pending_grant_proposals ?? 0, icon: Clock, color: "text-blue-400" },
        ].map((s) => (
          <Card key={s.label} className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <s.icon className={`w-8 h-8 ${s.color}`} />
              <div>
                <div className="text-lg font-bold text-white">{s.value}</div>
                <div className="text-xs text-slate-400">{s.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="pools">
        <TabsList className="bg-slate-800 border border-slate-700">
          <TabsTrigger value="pools">Pools</TabsTrigger>
          <TabsTrigger value="deposit">Deposit</TabsTrigger>
          <TabsTrigger value="epoch">Epoch Rewards</TabsTrigger>
          <TabsTrigger value="grants">Grant Protocol Proposals</TabsTrigger>
        </TabsList>

        <TabsContent value="pools" className="mt-4 space-y-3">
          {isLoading ? (
            <div className="text-slate-400 text-center py-8">Loading pools…</div>
          ) : pools.length === 0 ? (
            <div className="text-center py-12 text-slate-400">No pools. Click Initialize Pools.</div>
          ) : (
            <div className="grid md:grid-cols-2 gap-3">
              {pools.map((pool) => (
                <Card key={pool.pool_type} className="bg-slate-800/50 border-slate-700">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{POOL_ICONS[pool.pool_type] ?? "💰"}</span>
                        <div>
                          <div className="font-semibold text-white capitalize text-sm">
                            {pool.pool_type.replace(/_/g, " ")}
                          </div>
                          <div className="text-xs text-slate-500">{pool.allocation_pct}% allocation</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-white">{pool.balance.toFixed(2)}</div>
                        <div className="text-xs text-slate-400">VIT</div>
                      </div>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-1.5 mb-2">
                      <div
                        className={`h-1.5 rounded-full ${POOL_COLORS[pool.pool_type] ?? "bg-slate-500"}`}
                        style={{ width: `${Math.min(pool.utilization_pct, 100)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>{pool.share_of_treasury.toFixed(1)}% of treasury</span>
                      <span>{pool.utilization_pct.toFixed(1)}% utilized</span>
                    </div>
                    {pool.auto_refill && (
                      <Badge className="mt-2 text-xs bg-green-500/10 text-green-400 border-green-500/20">Auto-refill</Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="deposit" className="mt-4">
          <Card className="bg-slate-800/50 border-slate-700 max-w-md">
            <CardHeader>
              <CardTitle className="text-white text-base">Deposit to Pool</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-slate-300">Pool</Label>
                <select
                  value={depositPool}
                  onChange={(e) => setDepositPool(e.target.value)}
                  className="w-full mt-1 p-2 bg-slate-900 border border-slate-600 rounded text-slate-300 text-sm"
                >
                  {pools.map((p) => (
                    <option key={p.pool_type} value={p.pool_type}>
                      {POOL_ICONS[p.pool_type]} {p.pool_type.replace(/_/g, " ")} ({p.balance.toFixed(2)} VIT)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-slate-300">Amount (VIT)</Label>
                <Input value={depositAmount} onChange={(e) => setDepositAmount(e.target.value)}
                  placeholder="1000" className="bg-slate-900 border-slate-600 text-white mt-1" />
              </div>
              <div>
                <Label className="text-slate-300">Source</Label>
                <Input value={depositSource} onChange={(e) => setDepositSource(e.target.value)}
                  placeholder="validator_fee / protocol_revenue / etc." className="bg-slate-900 border-slate-600 text-white mt-1" />
              </div>
              <Button
                onClick={() => depositMutation.mutate({ pool_type: depositPool, amount: parseFloat(depositAmount), source: depositSource })}
                disabled={depositMutation.isPending || !depositAmount || !depositSource}
                className="bg-yellow-600 hover:bg-yellow-500 text-white w-full"
              >
                {depositMutation.isPending ? "Processing…" : "Deposit"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="epoch" className="mt-4">
          <Card className="bg-slate-800/50 border-slate-700 max-w-md">
            <CardHeader>
              <CardTitle className="text-white text-base">Distribute Epoch Reward</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-slate-400">
                Distribute a block reward across all pools by their configured allocation percentages.
              </p>
              <div>
                <Label className="text-slate-300">Total Block Reward (VIT)</Label>
                <Input value={epochReward} onChange={(e) => setEpochReward(e.target.value)}
                  placeholder="1000" className="bg-slate-900 border-slate-600 text-white mt-1" />
              </div>
              <Button
                onClick={() => epochMutation.mutate(parseFloat(epochReward))}
                disabled={epochMutation.isPending}
                className="bg-green-700 hover:bg-green-600 text-white w-full"
              >
                {epochMutation.isPending ? "Distributing…" : "Distribute Rewards"}
              </Button>
              {epochMutation.data && (
                <div className="bg-slate-900 rounded p-3 border border-green-500/20 space-y-1">
                  {Object.entries(epochMutation.data.distributed).map(([pool, amount]) => (
                    <div key={pool} className="flex justify-between text-xs">
                      <span className="text-slate-400 capitalize">{pool.replace(/_/g, " ")}</span>
                      <span className="text-green-400">+{(amount as number).toFixed(2)} VIT</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="grants" className="mt-4">
          <Card className="bg-slate-800/50 border-slate-700 max-w-lg">
            <CardHeader>
              <CardTitle className="text-white text-base">Submit Grant Protocol Proposal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-slate-300">Title</Label>
                <Input value={grantTitle} onChange={(e) => setGrantTitle(e.target.value)}
                  placeholder="VIT Ecosystem Development Grant" className="bg-slate-900 border-slate-600 text-white mt-1" />
              </div>
              <div>
                <Label className="text-slate-300">Description</Label>
                <textarea
                  value={grantDesc}
                  onChange={(e) => setGrantDesc(e.target.value)}
                  className="w-full mt-1 p-3 bg-slate-900 border border-slate-600 rounded-md text-sm text-slate-300 h-24 resize-none"
                  placeholder="Detailed description of how the grant will be used…"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-slate-300">Pool</Label>
                  <select
                    value={grantPool}
                    onChange={(e) => setGrantPool(e.target.value)}
                    className="w-full mt-1 p-2 bg-slate-900 border border-slate-600 rounded text-slate-300 text-sm"
                  >
                    {["ecosystem_grants", "ai_infrastructure", "bug_bounty"].map((p) => (
                      <option key={p} value={p}>{p.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label className="text-slate-300">Amount (VIT)</Label>
                  <Input value={grantAmount} onChange={(e) => setGrantAmount(e.target.value)}
                    placeholder="5000" className="bg-slate-900 border-slate-600 text-white mt-1" />
                </div>
              </div>
              <Button
                onClick={() => grantMutation.mutate({ title: grantTitle, description: grantDesc, pool_type: grantPool, requested_amount: parseFloat(grantAmount) })}
                disabled={grantMutation.isPending || !grantTitle || !grantAmount}
                className="bg-purple-700 hover:bg-purple-600 text-white w-full"
              >
                {grantMutation.isPending ? "Submitting…" : "Submit Protocol Proposal"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
