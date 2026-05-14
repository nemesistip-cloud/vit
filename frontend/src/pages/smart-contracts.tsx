import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAccount, useChainId } from "wagmi";
import { base } from "wagmi/chains";
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
  FileCode2, Zap, Activity, Clock, Flame, ChevronRight,
  Play, Eye, TrendingUp, Shield, Layers, RefreshCw,
  Wifi, WifiOff, Link2, AlertTriangle
} from "lucide-react";
import { WalletConnectButton } from "@/components/wallet-connect-button";

interface Contract {
  address: string;
  name: string;
  version: string;
  status: string;
  is_builtin: boolean;
  total_calls: number;
  total_gas_used: number;
  vit_locked: number;
  deployed_at: string;
  abi_methods: string[];
}

interface CallRecord {
  id: number;
  method: string;
  params: Record<string, unknown>;
  result: unknown;
  status: string;
  gas_used: number;
  tx_hash: string;
  error: string | null;
  called_at: string;
}

interface ContractEvent {
  id: number;
  event_name: string;
  topic: string;
  data: Record<string, unknown>;
  block_number: number;
  emitted_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/20 text-green-400 border-green-500/30",
  paused: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  terminated: "bg-red-500/20 text-red-400 border-red-500/30",
};

const CALL_STATUS_COLORS: Record<string, string> = {
  success: "bg-green-500/20 text-green-400",
  reverted: "bg-red-500/20 text-red-400",
  out_of_gas: "bg-orange-500/20 text-orange-400",
};

export default function SmartContractsPage() {
  const { toast } = useToast();
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const qc = useQueryClient();
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [callMethod, setCallMethod] = useState("");
  const [callParams, setCallParams] = useState("{}");
  const [activeTab, setActiveTab] = useState("contracts");

  const { data: contractsData, isLoading } = useQuery({
    queryKey: [API.contracts],
    queryFn: () => apiGet<{ contracts: Contract[]; total: number }>(API.contracts),
    refetchInterval: 15_000,
  });

  const { data: eventsData } = useQuery({
    queryKey: [selectedContract?.address, "events"],
    queryFn: () => apiGet<{ events: ContractEvent[] }>(
      API.contractEvents(selectedContract!.address)
    ),
    enabled: !!selectedContract,
  });

  const { data: callsData } = useQuery({
    queryKey: [selectedContract?.address, "calls"],
    queryFn: () => apiGet<{ calls: CallRecord[] }>(
      API.contractCalls(selectedContract!.address)
    ),
    enabled: !!selectedContract,
  });

  const bootstrapMutation = useMutation({
    mutationFn: () => apiPost<{ created: number }>(API.contractBootstrap, {}),
    onSuccess: (d) => {
      toast({ title: "Contracts bootstrapped", description: `${d.created} built-in contracts deployed` });
      qc.invalidateQueries({ queryKey: [API.contracts] });
    },
  });

  const callMutation = useMutation({
    mutationFn: (data: { address: string; method: string; params: Record<string, unknown> }) =>
      apiPost<{ success: boolean; result: unknown; gas_used: number; tx_hash: string }>(
        API.contractCall(data.address), { method: data.method, params: data.params }
      ),
    onSuccess: (d) => {
      toast({ title: `✅ ${callMethod} executed`, description: `Gas: ${d.gas_used.toLocaleString()} | TX: ${d.tx_hash.slice(0, 12)}…` });
      qc.invalidateQueries({ queryKey: [selectedContract?.address, "calls"] });
      qc.invalidateQueries({ queryKey: [selectedContract?.address, "events"] });
      qc.invalidateQueries({ queryKey: [API.contracts] });
    },
    onError: (e: Error) => toast({ title: "Call reverted", description: e.message, variant: "destructive" }),
  });

  const contracts = contractsData?.contracts ?? [];

  function handleCall() {
    if (!selectedContract || !callMethod) return;
    let params: Record<string, unknown> = {};
    try { params = JSON.parse(callParams); } catch {
      toast({ title: "Invalid JSON params", variant: "destructive" }); return;
    }
    callMutation.mutate({ address: selectedContract.address, method: callMethod, params });
  }

  const totalCalls = contracts.reduce((s, c) => s + c.total_calls, 0);
  const totalGas = contracts.reduce((s, c) => s + c.total_gas_used, 0);
  const totalLocked = contracts.reduce((s, c) => s + c.vit_locked, 0);

  const isBaseChain = chainId === base.id;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <FileCode2 className="w-6 h-6 text-violet-400" />
            Smart Contract Engine
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            VIT rule-based deterministic contract execution — 5 built-in contracts
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <WalletConnectButton />
          <Button
            onClick={() => bootstrapMutation.mutate()}
            disabled={bootstrapMutation.isPending}
            variant="outline"
            className="border-violet-500/30 text-violet-300"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${bootstrapMutation.isPending ? "animate-spin" : ""}`} />
            Bootstrap
          </Button>
        </div>
      </div>

      {/* Chain connection status bar */}
      <div className={`rounded-xl border p-3 flex items-center gap-3 flex-wrap ${
        isConnected && isBaseChain
          ? "border-emerald-500/20 bg-emerald-500/5"
          : isConnected
          ? "border-amber-500/20 bg-amber-500/5"
          : "border-border bg-muted/20"
      }`}>
        {isConnected ? (
          isBaseChain ? (
            <Wifi className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          )
        ) : (
          <WifiOff className="w-4 h-4 text-muted-foreground shrink-0" />
        )}

        <div className="flex-1 min-w-0">
          {isConnected ? (
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-xs font-semibold ${isBaseChain ? "text-emerald-400" : "text-amber-400"}`}>
                {isBaseChain ? "Connected to Base Mainnet" : "Wrong Network — switch to Base"}
              </span>
              {address && (
                <span className="font-mono text-[10px] text-muted-foreground">
                  {address.slice(0, 8)}…{address.slice(-6)}
                </span>
              )}
            </div>
          ) : (
            <span className="text-xs text-muted-foreground">
              Internal VIT contracts are fully operational — external wallet required only for Base L2 bridging
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <Link2 className="w-3 h-3 text-muted-foreground" />
          <span className="text-[10px] font-mono text-muted-foreground">Base L2 · Chain 8453</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Contracts", value: contracts.length, icon: FileCode2, color: "text-violet-400" },
          { label: "Total Calls", value: totalCalls.toLocaleString(), icon: Zap, color: "text-blue-400" },
          { label: "Total Gas", value: (totalGas / 1_000_000).toFixed(2) + "M", icon: Flame, color: "text-orange-400" },
          { label: "VIT Locked", value: totalLocked.toFixed(0), icon: Shield, color: "text-green-400" },
        ].map((stat) => (
          <Card key={stat.label} className="bg-muted/20 border-border">
            <CardContent className="p-4 flex items-center gap-3">
              <stat.icon className={`w-8 h-8 ${stat.color}`} />
              <div>
                <div className="text-lg font-bold text-foreground">{stat.value}</div>
                <div className="text-xs text-muted-foreground">{stat.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-muted/20 border border-border">
          <TabsTrigger value="contracts">Contracts</TabsTrigger>
          <TabsTrigger value="call" disabled={!selectedContract}>Call</TabsTrigger>
          <TabsTrigger value="events" disabled={!selectedContract}>Events</TabsTrigger>
          <TabsTrigger value="history" disabled={!selectedContract}>Call History</TabsTrigger>
        </TabsList>

        <TabsContent value="contracts" className="space-y-3 mt-4">
          {isLoading ? (
            <div className="text-muted-foreground text-center py-8">Loading contracts…</div>
          ) : contracts.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No contracts deployed.{" "}
              <button onClick={() => bootstrapMutation.mutate()} className="text-violet-400 hover:underline">
                Bootstrap built-in contracts
              </button>
            </div>
          ) : (
            contracts.map((c) => (
              <Card
                key={c.address}
                className={`bg-muted/20 border cursor-pointer transition-colors ${
                  selectedContract?.address === c.address
                    ? "border-violet-500/60"
                    : "border-border hover:border-border"
                }`}
                onClick={() => { setSelectedContract(c); setActiveTab("call"); }}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-foreground">{c.name}</span>
                        <Badge className="text-xs" variant="outline">v{c.version}</Badge>
                        {c.is_builtin && (
                          <Badge className="text-xs bg-violet-500/20 text-violet-300 border-violet-500/30">Built-in</Badge>
                        )}
                        <Badge className={`text-xs border ${STATUS_COLORS[c.status] ?? "text-muted-foreground"}`}>
                          {c.status}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground font-mono">{c.address}</div>
                      <div className="flex gap-4 text-xs text-muted-foreground mt-2">
                        <span><Zap className="w-3 h-3 inline mr-1" />{c.total_calls} calls</span>
                        <span><Flame className="w-3 h-3 inline mr-1" />{c.total_gas_used.toLocaleString()} gas</span>
                        <span>Methods: {c.abi_methods.join(", ")}</span>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-muted-foreground mt-1" />
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="call" className="mt-4">
          {selectedContract && (
            <Card className="bg-muted/20 border-border">
              <CardHeader>
                <CardTitle className="text-foreground text-base flex items-center gap-2">
                  <Play className="w-4 h-4 text-green-400" />
                  Call: {selectedContract.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-foreground/80">Method</Label>
                  <div className="flex gap-2 mt-1 flex-wrap">
                    {selectedContract.abi_methods.map((m) => (
                      <Button
                        key={m}
                        size="sm"
                        variant={callMethod === m ? "default" : "outline"}
                        className={callMethod === m ? "bg-violet-600" : "border-border text-foreground/80"}
                        onClick={() => setCallMethod(m)}
                      >
                        {m}
                      </Button>
                    ))}
                  </div>
                </div>
                <div>
                  <Label className="text-foreground/80">Parameters (JSON)</Label>
                  <textarea
                    value={callParams}
                    onChange={(e) => setCallParams(e.target.value)}
                    className="w-full mt-1 p-3 bg-card border border-border rounded-md text-sm text-foreground/80 font-mono h-28 resize-none focus:outline-none focus:border-violet-500"
                    placeholder='{"key": "value"}'
                  />
                </div>
                <Button
                  onClick={handleCall}
                  disabled={callMutation.isPending || !callMethod}
                  className="bg-violet-600 hover:bg-violet-500 text-foreground"
                >
                  {callMutation.isPending ? "Executing…" : "Execute Call"}
                </Button>
                {callMutation.data && (
                  <div className="bg-card rounded-md p-3 border border-green-500/30">
                    <div className="text-xs text-green-400 font-semibold mb-1">Result</div>
                    <pre className="text-xs text-foreground/80 overflow-auto">
                      {JSON.stringify(callMutation.data.result, null, 2)}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="events" className="mt-4 space-y-2">
          {(eventsData?.events ?? []).length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No events emitted yet</div>
          ) : (
            (eventsData?.events ?? []).map((e) => (
              <Card key={e.id} className="bg-muted/20 border-border">
                <CardContent className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30 text-xs">{e.event_name}</Badge>
                    <span className="text-xs text-muted-foreground">Block #{e.block_number}</span>
                  </div>
                  <div className="text-xs font-mono text-muted-foreground mb-1">{e.topic.slice(0, 20)}…</div>
                  <pre className="text-xs text-foreground/80 bg-card p-2 rounded overflow-auto">
                    {JSON.stringify(e.data, null, 2)}
                  </pre>
                  <div className="text-xs text-muted-foreground mt-1">{new Date(e.emitted_at).toLocaleString()}</div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="history" className="mt-4 space-y-2">
          {(callsData?.calls ?? []).length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No calls recorded yet</div>
          ) : (
            (callsData?.calls ?? []).map((c) => (
              <Card key={c.id} className="bg-muted/20 border-border">
                <CardContent className="p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge className={`text-xs ${CALL_STATUS_COLORS[c.status] ?? ""}`}>{c.status}</Badge>
                      <span className="text-sm font-semibold text-foreground">{c.method}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{c.gas_used.toLocaleString()} gas</span>
                  </div>
                  <div className="text-xs font-mono text-muted-foreground mt-1">{c.tx_hash.slice(0, 24)}…</div>
                  {c.error && <div className="text-xs text-red-400 mt-1">{c.error}</div>}
                  <div className="text-xs text-muted-foreground mt-1">{new Date(c.called_at).toLocaleString()}</div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
