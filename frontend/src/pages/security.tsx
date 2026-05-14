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
  ShieldAlert, AlertTriangle, Lock, Users, Activity,
  CheckCircle, XCircle, Clock, Fingerprint, Eye, Zap
} from "lucide-react";

interface SecurityDashboard {
  total_fraud_alerts: number;
  open_alerts: number;
  critical_alerts: number;
  active_wallet_freezes: number;
  pending_multisig_operations: number;
  high_risk_users: number;
}

interface SybilResult {
  user_id: number;
  risk_level: string;
  anomaly_score: number;
  prediction_velocity: number;
  stake_velocity: number;
  device_fingerprints: number;
  referral_cluster_score: number;
  last_evaluated_at: string | null;
}

interface MultiSigResult {
  operation_id: number;
  operation_type: string;
  status: string;
  threshold: number;
  expires_at: string | null;
}

const RISK_COLORS: Record<string, string> = {
  clean: "bg-green-500/20 text-green-400 border-green-500/30",
  low: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  flagged: "bg-red-500/20 text-red-400 border-red-500/30",
  banned: "bg-red-900/20 text-red-300 border-red-900/30",
};

export default function SecurityPage() {
  const { toast } = useToast();
  const qc = useQueryClient();

  const [sybilUserId, setSybilUserId] = useState("");
  const [sybilPredVel, setSybilPredVel] = useState("");
  const [sybilStakeVel, setSybilStakeVel] = useState("");
  const [sybilAge, setSybilAge] = useState("");
  const [sybilResult, setSybilResult] = useState<SybilResult | null>(null);

  const [msOpType, setMsOpType] = useState("");
  const [msDesc, setMsDesc] = useState("");
  const [msPayload, setMsPayload] = useState("{}");
  const [msThreshold, setMsThreshold] = useState("2");
  const [msResult, setMsResult] = useState<MultiSigResult | null>(null);

  const [freezeUserId, setFreezeUserId] = useState("");
  const [freezeReason, setFreezeReason] = useState("");

  const { data: dashboard, isLoading } = useQuery({
    queryKey: [API.securityDashboard],
    queryFn: () => apiGet<SecurityDashboard>(API.securityDashboard),
    refetchInterval: 15_000,
  });

  const sybilMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => apiPost<SybilResult>(API.sybilEvaluate, data),
    onSuccess: (d) => {
      setSybilResult(d);
      if (d.risk_level === "flagged" || d.risk_level === "high") {
        toast({ title: `⚠️ High risk detected`, description: `Score: ${d.anomaly_score}`, variant: "destructive" });
      } else {
        toast({ title: `Risk evaluation: ${d.risk_level}`, description: `Anomaly score: ${d.anomaly_score}` });
      }
    },
  });

  const multisigMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => apiPost<MultiSigResult>(API.multisigPropose, data),
    onSuccess: (d) => {
      setMsResult(d);
      toast({ title: "Multi-sig operation proposed", description: `ID: ${d.operation_id} — ${d.status}` });
    },
    onError: (e: Error) => toast({ title: "Failed", description: e.message, variant: "destructive" }),
  });

  const freezeMutation = useMutation({
    mutationFn: (data: { user_id: number; reason: string }) =>
      apiPost<{ freeze_id: number; status: string }>(API.walletFreeze, data),
    onSuccess: (d) => {
      toast({ title: "Wallet frozen", description: `Freeze #${d.freeze_id} active` });
      qc.invalidateQueries({ queryKey: [API.securityDashboard] });
    },
    onError: (e: Error) => toast({ title: "Freeze failed", description: e.message, variant: "destructive" }),
  });

  function runSybilEval() {
    const data: Record<string, unknown> = { user_id: parseInt(sybilUserId) };
    if (sybilPredVel) data.prediction_velocity = parseFloat(sybilPredVel);
    if (sybilStakeVel) data.stake_velocity = parseFloat(sybilStakeVel);
    if (sybilAge) data.account_age_days = parseInt(sybilAge);
    sybilMutation.mutate(data);
  }

  const stats = [
    { label: "Total Alerts", value: dashboard?.total_fraud_alerts ?? 0, icon: AlertTriangle, color: "text-yellow-400", urgent: false },
    { label: "Open Alerts", value: dashboard?.open_alerts ?? 0, icon: Eye, color: "text-orange-400", urgent: (dashboard?.open_alerts ?? 0) > 0 },
    { label: "Critical", value: dashboard?.critical_alerts ?? 0, icon: ShieldAlert, color: "text-red-400", urgent: (dashboard?.critical_alerts ?? 0) > 0 },
    { label: "Frozen Wallets", value: dashboard?.active_wallet_freezes ?? 0, icon: Lock, color: "text-blue-400", urgent: false },
    { label: "Pending Multi-sig", value: dashboard?.pending_multisig_operations ?? 0, icon: Zap, color: "text-violet-400", urgent: false },
    { label: "High-Risk Users", value: dashboard?.high_risk_users ?? 0, icon: Users, color: "text-red-400", urgent: (dashboard?.high_risk_users ?? 0) > 0 },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <ShieldAlert className="w-6 h-6 text-red-400" />
          Security Layer
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Anti-Sybil detection, fraud alerts, multi-signature operations, wallet freeze
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {stats.map((s) => (
          <Card key={s.label} className={`bg-muted/20 border ${s.urgent ? "border-red-500/40" : "border-border"}`}>
            <CardContent className="p-4 flex items-center gap-3">
              <s.icon className={`w-8 h-8 ${s.color}`} />
              <div>
                <div className={`text-2xl font-bold ${s.urgent ? "text-red-400" : "text-foreground"}`}>{s.value}</div>
                <div className="text-xs text-muted-foreground">{s.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="sybil">
        <TabsList className="bg-muted/20 border border-border">
          <TabsTrigger value="sybil">Anti-Sybil</TabsTrigger>
          <TabsTrigger value="multisig">Multi-Sig</TabsTrigger>
          <TabsTrigger value="freeze">Wallet Freeze</TabsTrigger>
        </TabsList>

        <TabsContent value="sybil" className="mt-4">
          <div className="grid md:grid-cols-2 gap-6">
            <Card className="bg-muted/20 border-border">
              <CardHeader>
                <CardTitle className="text-foreground text-base flex items-center gap-2">
                  <Fingerprint className="w-4 h-4 text-orange-400" />
                  Sybil Risk Evaluation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <Label className="text-foreground/80">User ID</Label>
                  <Input value={sybilUserId} onChange={(e) => setSybilUserId(e.target.value)}
                    placeholder="123" className="bg-card border-border text-foreground mt-1" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-foreground/80 text-xs">Prediction Velocity</Label>
                    <Input value={sybilPredVel} onChange={(e) => setSybilPredVel(e.target.value)}
                      placeholder="0–50+" className="bg-card border-border text-foreground mt-1 text-sm" />
                  </div>
                  <div>
                    <Label className="text-foreground/80 text-xs">Stake Velocity</Label>
                    <Input value={sybilStakeVel} onChange={(e) => setSybilStakeVel(e.target.value)}
                      placeholder="0–20+" className="bg-card border-border text-foreground mt-1 text-sm" />
                  </div>
                </div>
                <div>
                  <Label className="text-foreground/80">Account Age (days)</Label>
                  <Input value={sybilAge} onChange={(e) => setSybilAge(e.target.value)}
                    placeholder="0–365" className="bg-card border-border text-foreground mt-1" />
                </div>
                <Button onClick={runSybilEval} disabled={sybilMutation.isPending || !sybilUserId}
                  className="bg-orange-700 hover:bg-orange-600 text-foreground w-full">
                  {sybilMutation.isPending ? "Evaluating…" : "Evaluate Risk"}
                </Button>
              </CardContent>
            </Card>

            {sybilResult && (
              <Card className={`border ${RISK_COLORS[sybilResult.risk_level] ?? ""} bg-muted/20`}>
                <CardHeader>
                  <CardTitle className="text-foreground text-base">Evaluation Result</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-foreground/80">Risk Level</span>
                    <Badge className={`${RISK_COLORS[sybilResult.risk_level]} border capitalize`}>
                      {sybilResult.risk_level}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-foreground/80">Anomaly Score</span>
                    <span className="text-foreground font-bold">{(sybilResult.anomaly_score * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-muted/40 rounded-full h-2">
                    <div className="h-2 rounded-full bg-orange-500" style={{ width: `${sybilResult.anomaly_score * 100}%` }} />
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {[
                      ["Pred Velocity", sybilResult.prediction_velocity.toFixed(1)],
                      ["Stake Velocity", sybilResult.stake_velocity.toFixed(1)],
                      ["Device FPs", String(sybilResult.device_fingerprints)],
                      ["Referral Cluster", sybilResult.referral_cluster_score.toFixed(3)],
                    ].map(([label, val]) => (
                      <div key={label} className="bg-card rounded p-2">
                        <div className="text-muted-foreground">{label}</div>
                        <div className="text-foreground font-semibold">{val}</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="multisig" className="mt-4">
          <div className="grid md:grid-cols-2 gap-6">
            <Card className="bg-muted/20 border-border">
              <CardHeader>
                <CardTitle className="text-foreground text-base flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-violet-400" />
                  Propose Multi-Sig Operation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <Label className="text-foreground/80">Operation Type</Label>
                  <Input value={msOpType} onChange={(e) => setMsOpType(e.target.value)}
                    placeholder="treasury_spend / contract_upgrade / etc." className="bg-card border-border text-foreground mt-1" />
                </div>
                <div>
                  <Label className="text-foreground/80">Description</Label>
                  <Input value={msDesc} onChange={(e) => setMsDesc(e.target.value)}
                    placeholder="Detailed description of operation" className="bg-card border-border text-foreground mt-1" />
                </div>
                <div>
                  <Label className="text-foreground/80">Payload (JSON)</Label>
                  <textarea value={msPayload} onChange={(e) => setMsPayload(e.target.value)}
                    className="w-full mt-1 p-2 bg-card border border-border rounded text-foreground/80 text-sm font-mono h-20 resize-none" />
                </div>
                <div>
                  <Label className="text-foreground/80">Approval Threshold</Label>
                  <Input value={msThreshold} onChange={(e) => setMsThreshold(e.target.value)}
                    type="number" min="1" max="10" className="bg-card border-border text-foreground mt-1" />
                </div>
                <Button
                  onClick={() => multisigMutation.mutate({ operation_type: msOpType, description: msDesc, payload: msPayload, threshold: parseInt(msThreshold), required_signers: parseInt(msThreshold) + 1 })}
                  disabled={multisigMutation.isPending || !msOpType}
                  className="bg-violet-700 hover:bg-violet-600 text-foreground w-full"
                >
                  {multisigMutation.isPending ? "Proposing…" : "Propose Operation"}
                </Button>
              </CardContent>
            </Card>

            {msResult && (
              <Card className="bg-muted/20 border-violet-500/30">
                <CardHeader><CardTitle className="text-foreground text-base">Operation #{msResult.operation_id}</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between"><span className="text-muted-foreground">Type</span><span className="text-foreground">{msResult.operation_type}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Status</span>
                    <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/30">{msResult.status}</Badge>
                  </div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Threshold</span><span className="text-foreground">{msResult.threshold} signatures</span></div>
                  {msResult.expires_at && <div className="flex justify-between"><span className="text-muted-foreground">Expires</span><span className="text-foreground/80 text-xs">{new Date(msResult.expires_at).toLocaleString()}</span></div>}
                  <p className="text-xs text-muted-foreground">Signers can now call POST /api/security/multisig/{"{"}operation_id{"}"}/sign to approve.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="freeze" className="mt-4">
          <Card className="bg-muted/20 border-border max-w-md">
            <CardHeader>
              <CardTitle className="text-foreground text-base flex items-center gap-2">
                <Lock className="w-4 h-4 text-blue-400" />
                Freeze Wallet
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Instantly freeze a user wallet for fraud investigation. Requires admin access in production.
              </p>
              <div>
                <Label className="text-foreground/80">User ID</Label>
                <Input value={freezeUserId} onChange={(e) => setFreezeUserId(e.target.value)}
                  placeholder="123" className="bg-card border-border text-foreground mt-1" />
              </div>
              <div>
                <Label className="text-foreground/80">Reason</Label>
                <Input value={freezeReason} onChange={(e) => setFreezeReason(e.target.value)}
                  placeholder="Suspicious activity / Sybil detection / etc." className="bg-card border-border text-foreground mt-1" />
              </div>
              <Button
                onClick={() => freezeMutation.mutate({ user_id: parseInt(freezeUserId), reason: freezeReason })}
                disabled={freezeMutation.isPending || !freezeUserId || !freezeReason}
                className="bg-red-700 hover:bg-red-600 text-foreground w-full"
              >
                {freezeMutation.isPending ? "Freezing…" : "Freeze Wallet"}
              </Button>
              <p className="text-xs text-muted-foreground">Active freezes: {dashboard?.active_wallet_freezes ?? 0}</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
