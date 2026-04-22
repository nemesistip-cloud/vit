import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPatch, apiDelete } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Key, Copy, Trash2, EyeOff, Code2, Loader2, CheckCircle2, AlertCircle, BookOpen } from "lucide-react";

interface APIKey {
  id: number;
  name: string;
  key_prefix: string;
  key?: string;
  plan: string;
  rate_limit_rpm: number;
  rate_limit_rpd: number;
  is_active: boolean;
  total_requests: number;
  total_vitcoin_billed: string;
  last_used_at: string | null;
  created_at: string;
}

interface Plan {
  name: string;
  display_name: string;
  rate_limit_rpm: number;
  rate_limit_rpd: number;
  price_vitcoin_per_1k: string;
  description: string;
}

interface UsageSummary {
  total_api_calls: number;
  successful_calls: number;
  error_calls: number;
  success_rate: number;
  total_keys: number;
  active_keys: number;
}

interface UsageLog {
  id: number;
  endpoint: string;
  method: string;
  status_code: number;
  latency_ms: number | null;
  vitcoin_billed: string;
  called_at: string;
}

interface DocEndpoint {
  method: string;
  path: string;
  description: string;
}

interface DocsData {
  openapi_url: string;
  redoc_url: string;
  sdk_typescript_url: string;
  sdk_python_url: string;
  base_api_url: string;
  authentication: string;
  endpoints: DocEndpoint[];
}

const PLAN_COLORS: Record<string, string> = {
  free:       "bg-muted text-muted-foreground",
  starter:    "bg-blue-500/10 text-blue-400",
  pro:        "bg-primary/10 text-primary",
  enterprise: "bg-purple-500/10 text-purple-400",
};

export default function DeveloperPage() {
  const qc = useQueryClient();
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyPlan, setNewKeyPlan] = useState("free");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"keys" | "usage" | "docs">("keys");

  const { data: keys = [] } = useQuery<APIKey[]>({
    queryKey: ["dev-keys"],
    queryFn: () => apiGet<APIKey[]>("/api/developer/keys"),
  });

  const { data: plans = [] } = useQuery<Plan[]>({
    queryKey: ["dev-plans"],
    queryFn: () => apiGet<Plan[]>("/api/developer/plans"),
  });

  const { data: summary } = useQuery<UsageSummary>({
    queryKey: ["dev-usage-summary"],
    queryFn: () => apiGet<UsageSummary>("/api/developer/usage/summary"),
  });

  const { data: usageLogs = [] } = useQuery<UsageLog[]>({
    queryKey: ["dev-usage-logs"],
    queryFn: () => apiGet<UsageLog[]>("/api/developer/usage?limit=50"),
    enabled: activeTab === "usage",
  });

  const { data: docs } = useQuery<DocsData>({
    queryKey: ["dev-docs"],
    queryFn: () => apiGet<DocsData>("/api/developer/docs"),
    enabled: activeTab === "docs",
  });

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; plan: string }) =>
      apiPost<APIKey>("/api/developer/keys", payload),
    onSuccess: (data: APIKey) => {
      toast.success("API key created — copy it now, it won't be shown again!");
      if (data.key) setRevealedKey(data.key);
      qc.invalidateQueries({ queryKey: ["dev-keys"] });
      qc.invalidateQueries({ queryKey: ["dev-usage-summary"] });
      setNewKeyName("");
    },
    onError: (err: Error) => {
      toast.error(err.message ?? "Failed to create key");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (keyId: number) =>
      apiDelete<void>(`/api/developer/keys/${keyId}`),
    onSuccess: () => {
      toast.success("API key deleted");
      qc.invalidateQueries({ queryKey: ["dev-keys"] });
      qc.invalidateQueries({ queryKey: ["dev-usage-summary"] });
    },
    onError: () => toast.error("Failed to delete key"),
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: number) =>
      apiPatch<APIKey>(`/api/developer/keys/${keyId}/revoke`),
    onSuccess: () => {
      toast.success("API key revoked");
      qc.invalidateQueries({ queryKey: ["dev-keys"] });
    },
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const tabs = [
    { key: "keys",  label: "API Keys",      icon: Key },
    { key: "usage", label: "Usage Logs",    icon: Code2 },
    { key: "docs",  label: "Documentation", icon: BookOpen },
  ] as const;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Developer Platform</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Manage API keys, monitor usage, and explore SDK documentation. Phase 10 — Module L.
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Active Keys",     value: summary.active_keys },
            { label: "Total API Calls", value: summary.total_api_calls },
            { label: "Success Rate",    value: `${summary.success_rate}%` },
            { label: "Errors",          value: summary.error_calls },
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

      {/* Revealed Key Banner */}
      {revealedKey && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-yellow-400 mb-1">Your new API key — copy it now!</p>
              <p className="font-mono text-xs bg-background rounded px-3 py-2 border border-border break-all">{revealedKey}</p>
            </div>
            <div className="flex gap-2 flex-shrink-0 mt-4">
              <Button size="sm" variant="outline" onClick={() => copyToClipboard(revealedKey)}>
                <Copy className="w-3 h-3 mr-1" />Copy
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setRevealedKey(null)}>
                <EyeOff className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === t.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <t.icon className="w-3.5 h-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Keys Tab */}
      {activeTab === "keys" && (
        <div className="space-y-4">
          {/* Create Key Form */}
          <Card className="border border-border">
            <CardHeader>
              <CardTitle className="text-base">Create New API Key</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-3">
                <Input
                  placeholder="Key name (e.g. My App)"
                  value={newKeyName}
                  onChange={e => setNewKeyName(e.target.value)}
                  className="flex-1"
                />
                <Select value={newKeyPlan} onValueChange={setNewKeyPlan}>
                  <SelectTrigger className="w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {plans.map(p => (
                      <SelectItem key={p.name} value={p.name}>{p.display_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  onClick={() => createMutation.mutate({ name: newKeyName, plan: newKeyPlan })}
                  disabled={!newKeyName || createMutation.isPending}
                >
                  {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4 mr-1" />}
                  Generate Key
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Plans Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {plans.map(p => (
              <Card
                key={p.name}
                className={`border ${newKeyPlan === p.name ? "border-primary" : "border-border"} cursor-pointer`}
                onClick={() => setNewKeyPlan(p.name)}
              >
                <CardContent className="pt-4 pb-4">
                  <Badge className={`${PLAN_COLORS[p.name] ?? ""} mb-2 text-xs`}>{p.display_name}</Badge>
                  <p className="text-xs text-muted-foreground">{p.description}</p>
                  <p className="text-xs mt-2">
                    <span className="font-mono font-semibold">{p.price_vitcoin_per_1k}</span>
                    <span className="text-muted-foreground"> VIT / 1k calls</span>
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Keys List */}
          <Card className="border border-border">
            <CardHeader>
              <CardTitle className="text-base">Your API Keys</CardTitle>
            </CardHeader>
            <CardContent>
              {keys.length === 0 ? (
                <p className="text-muted-foreground text-sm text-center py-8">No API keys yet. Create one above.</p>
              ) : (
                <div className="space-y-3">
                  {keys.map(k => (
                    <div key={k.id} className="flex items-center gap-3 p-3 rounded-lg border border-border hover:border-border/80">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm">{k.name}</span>
                          <Badge className={`${PLAN_COLORS[k.plan] ?? ""} text-xs`}>{k.plan}</Badge>
                          {!k.is_active && <Badge variant="destructive" className="text-xs">Revoked</Badge>}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span className="font-mono">{k.key_prefix}••••••••••••</span>
                          <span>{k.rate_limit_rpm} rpm</span>
                          <span>{k.total_requests.toLocaleString()} calls</span>
                          {k.last_used_at && <span>Last used {new Date(k.last_used_at).toLocaleDateString()}</span>}
                        </div>
                      </div>
                      <div className="flex gap-1">
                        {k.is_active && (
                          <Button size="sm" variant="ghost" onClick={() => revokeMutation.mutate(k.id)}>
                            <EyeOff className="w-3.5 h-3.5 text-muted-foreground" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => deleteMutation.mutate(k.id)}
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Usage Logs Tab */}
      {activeTab === "usage" && (
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="text-base">Recent API Calls</CardTitle>
          </CardHeader>
          <CardContent>
            {usageLogs.length === 0 ? (
              <p className="text-muted-foreground text-sm text-center py-8">No API calls logged yet</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground text-xs">
                      <th className="text-left py-2 font-medium">Method</th>
                      <th className="text-left py-2 font-medium">Endpoint</th>
                      <th className="text-left py-2 font-medium">Status</th>
                      <th className="text-left py-2 font-medium">Latency</th>
                      <th className="text-left py-2 font-medium">Called At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {usageLogs.map(log => (
                      <tr key={log.id} className="hover:bg-muted/30">
                        <td className="py-2">
                          <span className="font-mono text-xs font-semibold text-primary">{log.method}</span>
                        </td>
                        <td className="py-2 font-mono text-xs truncate max-w-xs">{log.endpoint}</td>
                        <td className="py-2">
                          <span className={`inline-flex items-center gap-1 text-xs ${
                            log.status_code < 400 ? "text-emerald-400" : "text-red-400"
                          }`}>
                            {log.status_code < 400
                              ? <CheckCircle2 className="w-3 h-3" />
                              : <AlertCircle className="w-3 h-3" />}
                            {log.status_code}
                          </span>
                        </td>
                        <td className="py-2 text-muted-foreground text-xs">
                          {log.latency_ms ? `${log.latency_ms}ms` : "—"}
                        </td>
                        <td className="py-2 text-muted-foreground text-xs">
                          {new Date(log.called_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Docs Tab */}
      {activeTab === "docs" && docs && (
        <div className="space-y-4">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle className="text-base">Authentication</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">{docs.authentication}</p>
              <div className="rounded-lg bg-muted/50 border border-border p-3 font-mono text-xs">
                <span className="text-muted-foreground">curl</span>{" "}
                <span className="text-primary">https://api.vit.network/predict</span>{" "}
                <span className="text-yellow-400">\</span>
                <br />
                {"  "}<span className="text-muted-foreground">-H</span>{" "}
                <span className="text-emerald-400">"X-API-Key: vit_your_key_here"</span>
              </div>
              <div className="flex gap-3">
                <a href={docs.openapi_url} target="_blank" rel="noreferrer">
                  <Button variant="outline" size="sm">OpenAPI Spec</Button>
                </a>
                <a href={docs.redoc_url} target="_blank" rel="noreferrer">
                  <Button variant="outline" size="sm">ReDoc</Button>
                </a>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-border">
            <CardHeader>
              <CardTitle className="text-base">SDK Downloads</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid sm:grid-cols-2 gap-3">
                {[
                  { label: "TypeScript SDK", url: docs.sdk_typescript_url, lang: "npm install @vit-network/sdk" },
                  { label: "Python SDK",     url: docs.sdk_python_url,     lang: "pip install vit-network" },
                ].map(s => (
                  <div key={s.label} className="rounded-lg border border-border p-3">
                    <p className="font-medium text-sm mb-2">{s.label}</p>
                    <code className="text-xs bg-muted px-2 py-1 rounded font-mono">{s.lang}</code>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border border-border">
            <CardHeader>
              <CardTitle className="text-base">Available Endpoints</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {docs.endpoints.map(ep => (
                  <div key={ep.path} className="flex items-center gap-3 text-sm py-2 border-b border-border last:border-0">
                    <span className={`font-mono text-xs font-bold w-12 ${
                      ep.method === "GET"    ? "text-emerald-400" :
                      ep.method === "POST"   ? "text-blue-400" :
                      ep.method === "DELETE" ? "text-red-400" :
                      "text-yellow-400"
                    }`}>{ep.method}</span>
                    <code className="font-mono text-xs flex-1">{ep.path}</code>
                    <span className="text-muted-foreground text-xs">{ep.description}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
