import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { ArrowLeftRight, Clock, CheckCircle2, XCircle, Loader2, TrendingUp } from "lucide-react";

interface BridgePool {
  id: number;
  asset_from: string;
  asset_to: string;
  chain_from: string;
  chain_to: string;
  exchange_rate: string;
  fee_pct: string;
  min_amount: string;
  max_amount: string;
  pool_liquidity: string;
  is_active: boolean;
}

interface BridgeTx {
  id: number;
  pool_id: number;
  tx_hash: string;
  direction: string;
  amount_in: string;
  amount_out: string;
  fee: string;
  exchange_rate: string;
  destination_address: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

interface BridgeStats {
  total_transactions: number;
  completed_transactions: number;
  total_volume_vitcoin: number;
  total_fees_collected: number;
  active_pools: number;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending:   { label: "Pending",   color: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20", icon: <Clock className="w-3 h-3" /> },
  locked:    { label: "Locked",    color: "bg-blue-500/10 text-blue-400 border-blue-500/20",       icon: <Loader2 className="w-3 h-3 animate-spin" /> },
  confirmed: { label: "Confirmed", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", icon: <CheckCircle2 className="w-3 h-3" /> },
  completed: { label: "Completed", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", icon: <CheckCircle2 className="w-3 h-3" /> },
  failed:    { label: "Failed",    color: "bg-red-500/10 text-red-400 border-red-500/20",           icon: <XCircle className="w-3 h-3" /> },
  disputed:  { label: "Disputed",  color: "bg-orange-500/10 text-orange-400 border-orange-500/20",  icon: <XCircle className="w-3 h-3" /> },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: "bg-muted text-muted-foreground", icon: null };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
      {cfg.icon}{cfg.label}
    </span>
  );
}

export default function BridgePage() {
  const qc = useQueryClient();
  const [selectedPool, setSelectedPool] = useState<string>("");
  const [amountIn, setAmountIn] = useState("");
  const [destAddress, setDestAddress] = useState("");

  const { data: pools = [] } = useQuery<BridgePool[]>({
    queryKey: ["bridge-pools"],
    queryFn: () => apiGet<BridgePool[]>("/api/bridge/pools"),
  });

  const { data: txs = [] } = useQuery<BridgeTx[]>({
    queryKey: ["bridge-my-txs"],
    queryFn: () => apiGet<BridgeTx[]>("/api/bridge/transactions/my"),
  });

  const { data: stats } = useQuery<BridgeStats>({
    queryKey: ["bridge-stats"],
    queryFn: () => apiGet<BridgeStats>("/api/bridge/stats"),
  });

  const initiateMutation = useMutation({
    mutationFn: (payload: { pool_id: number; amount_in: string; destination_address: string }) =>
      apiPost<BridgeTx>("/api/bridge/initiate", payload),
    onSuccess: () => {
      toast.success("Bridge transfer initiated successfully");
      qc.invalidateQueries({ queryKey: ["bridge-my-txs"] });
      qc.invalidateQueries({ queryKey: ["bridge-stats"] });
      setAmountIn("");
      setDestAddress("");
    },
    onError: (err: Error) => {
      toast.error(err.message ?? "Failed to initiate bridge transfer");
    },
  });

  const pool = pools.find(p => p.id === Number(selectedPool));
  const estimatedOut = pool && amountIn
    ? (parseFloat(amountIn) * (1 - parseFloat(pool.fee_pct)) * parseFloat(pool.exchange_rate)).toFixed(6)
    : null;
  const fee = pool && amountIn
    ? (parseFloat(amountIn) * parseFloat(pool.fee_pct)).toFixed(4)
    : null;

  const handleBridge = () => {
    if (!selectedPool || !amountIn || !destAddress) {
      toast.error("Please fill in all fields");
      return;
    }
    initiateMutation.mutate({
      pool_id: Number(selectedPool),
      amount_in: amountIn,
      destination_address: destAddress,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Cross-Chain Bridge</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Transfer VITCoin to external chains. Phase 9 — Module J.
        </p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Active Pools",    value: stats.active_pools },
            { label: "Total Transfers", value: stats.total_transactions },
            { label: "Completed",       value: stats.completed_transactions },
            { label: "Volume (VIT)",    value: stats.total_volume_vitcoin.toFixed(2) },
          ].map(s => (
            <Card key={s.label} className="border border-border">
              <CardContent className="pt-4 pb-4">
                <p className="text-xs text-muted-foreground">{s.label}</p>
                <p className="text-xl font-bold text-foreground">{s.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bridge Form */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ArrowLeftRight className="w-4 h-4 text-primary" />
              Initiate Bridge Transfer
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Select Bridge Pool</label>
              <Select value={selectedPool} onValueChange={setSelectedPool}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose pool..." />
                </SelectTrigger>
                <SelectContent>
                  {pools.filter(p => p.is_active).map(p => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {p.asset_from} → {p.asset_to} ({p.chain_from} → {p.chain_to})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {pool && (
              <div className="rounded-lg border border-border bg-muted/30 p-3 text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Exchange rate</span>
                  <span className="font-mono">1 {pool.asset_from} = {parseFloat(pool.exchange_rate).toFixed(6)} {pool.asset_to}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Bridge fee</span>
                  <span className="font-mono">{(parseFloat(pool.fee_pct) * 100).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Min / Max</span>
                  <span className="font-mono">{parseFloat(pool.min_amount).toFixed(0)} / {parseFloat(pool.max_amount).toFixed(0)} {pool.asset_from}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Pool liquidity</span>
                  <span className="font-mono">{parseFloat(pool.pool_liquidity).toFixed(2)} {pool.asset_to}</span>
                </div>
              </div>
            )}

            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Amount ({pool?.asset_from ?? "VIT"})
              </label>
              <Input
                type="number"
                min="0"
                value={amountIn}
                onChange={e => setAmountIn(e.target.value)}
                placeholder="0.00"
              />
              {estimatedOut && (
                <p className="text-xs text-muted-foreground mt-1">
                  You receive ≈ <span className="text-primary font-mono">{estimatedOut} {pool?.asset_to}</span>
                  {" "}(fee: <span className="font-mono">{fee} {pool?.asset_from}</span>)
                </p>
              )}
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Destination Address ({pool?.chain_to ?? "target chain"})
              </label>
              <Input
                value={destAddress}
                onChange={e => setDestAddress(e.target.value)}
                placeholder="0x... or target chain address"
                className="font-mono text-xs"
              />
            </div>

            <Button
              className="w-full"
              onClick={handleBridge}
              disabled={initiateMutation.isPending || !selectedPool || !amountIn || !destAddress}
            >
              {initiateMutation.isPending ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Initiating...</>
              ) : (
                <><ArrowLeftRight className="w-4 h-4 mr-2" />Bridge Now</>
              )}
            </Button>

            <p className="text-xs text-muted-foreground text-center">
              Transfers are processed by the VIT relayer network.
              Cross-chain settlements typically complete within 5–30 minutes.
            </p>
          </CardContent>
        </Card>

        {/* Pools */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Available Pools
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pools.length === 0 && (
                <p className="text-muted-foreground text-sm text-center py-6">No pools available</p>
              )}
              {pools.map(p => (
                <div
                  key={p.id}
                  className={`rounded-lg border p-3 cursor-pointer transition-colors ${
                    selectedPool === String(p.id)
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/40"
                  }`}
                  onClick={() => setSelectedPool(String(p.id))}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">
                      {p.asset_from} → {p.asset_to}
                    </span>
                    <Badge variant={p.is_active ? "default" : "secondary"}>
                      {p.is_active ? "Active" : "Paused"}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 text-xs text-muted-foreground">
                    <span>Rate: <span className="font-mono text-foreground">{parseFloat(p.exchange_rate).toFixed(6)}</span></span>
                    <span>Fee: <span className="font-mono text-foreground">{(parseFloat(p.fee_pct) * 100).toFixed(1)}%</span></span>
                    <span className="col-span-2">{p.chain_from} → {p.chain_to}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Transaction History */}
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="text-base">My Bridge History</CardTitle>
        </CardHeader>
        <CardContent>
          {txs.length === 0 ? (
            <p className="text-muted-foreground text-sm text-center py-8">No bridge transfers yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground text-xs">
                    <th className="text-left py-2 font-medium">Tx Hash</th>
                    <th className="text-left py-2 font-medium">Amount In</th>
                    <th className="text-left py-2 font-medium">Amount Out</th>
                    <th className="text-left py-2 font-medium">Fee</th>
                    <th className="text-left py-2 font-medium">Status</th>
                    <th className="text-left py-2 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {txs.map(tx => (
                    <tr key={tx.id} className="hover:bg-muted/30">
                      <td className="py-2 font-mono text-xs text-primary">
                        {tx.tx_hash.slice(0, 18)}…
                      </td>
                      <td className="py-2 font-mono">{parseFloat(tx.amount_in).toFixed(4)}</td>
                      <td className="py-2 font-mono">{parseFloat(tx.amount_out).toFixed(6)}</td>
                      <td className="py-2 font-mono text-muted-foreground">{parseFloat(tx.fee).toFixed(4)}</td>
                      <td className="py-2"><StatusBadge status={tx.status} /></td>
                      <td className="py-2 text-muted-foreground">
                        {new Date(tx.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
