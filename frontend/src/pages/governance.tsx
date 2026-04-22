import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { Vote, Plus, CheckCircle2, XCircle, Clock, Loader2, Settings, BarChart2 } from "lucide-react";
import { usePublicConfig } from "@/lib/usePublicConfig";

interface Proposal {
  id: number;
  proposer_id: number;
  title: string;
  description: string;
  category: string;
  status: string;
  voting_starts_at: string | null;
  voting_ends_at: string | null;
  votes_for: number;
  votes_against: number;
  votes_abstain: number;
  total_votes: number;
  approval_pct: number;
  quorum_required: number;
  timelock_seconds: number;
  executed_at: string | null;
  execution_note: string | null;
  created_at: string;
}

interface GovConfig {
  key: string;
  value: string;
  data_type: string;
  description: string;
  updated_at: string | null;
}

interface GovStats {
  total_proposals: number;
  active_proposals: number;
  passed_proposals: number;
  rejected_proposals: number;
  total_votes: number;
  total_voting_power_cast: number;
}

interface ProposalsResponse {
  items: Proposal[];
  total: number;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  draft:    { label: "Draft",    color: "bg-muted text-muted-foreground border-border",              icon: <Clock className="w-3 h-3" /> },
  active:   { label: "Active",   color: "bg-blue-500/10 text-blue-400 border-blue-500/20",           icon: <Vote className="w-3 h-3" /> },
  passed:   { label: "Passed",   color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",  icon: <CheckCircle2 className="w-3 h-3" /> },
  rejected: { label: "Rejected", color: "bg-red-500/10 text-red-400 border-red-500/20",              icon: <XCircle className="w-3 h-3" /> },
  cancelled:{ label: "Cancelled",color: "bg-muted text-muted-foreground border-border",              icon: <XCircle className="w-3 h-3" /> },
  executed: { label: "Executed", color: "bg-purple-500/10 text-purple-400 border-purple-500/20",     icon: <CheckCircle2 className="w-3 h-3" /> },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: "bg-muted text-muted-foreground border-border", icon: null };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
      {cfg.icon}{cfg.label}
    </span>
  );
}

export default function GovernancePage() {
  const qc = useQueryClient();
  const { data: publicCfg } = usePublicConfig();
  const CATEGORIES = (publicCfg?.governance_categories ?? []).map((c) => c.id);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [activeTab, setActiveTab] = useState<"proposals" | "config" | "stats">("proposals");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null);

  const [form, setForm] = useState({
    title: "", description: "", category: "general", voting_period_days: "7",
  });
  const [voteChoice, setVoteChoice] = useState<string>("");
  const [voteReason, setVoteReason] = useState("");

  const { data: proposals = [] } = useQuery<Proposal[]>({
    queryKey: ["gov-proposals", filterStatus],
    queryFn: async () => {
      const params = filterStatus !== "all" ? `?status=${filterStatus}` : "";
      const res = await apiGet<ProposalsResponse | Proposal[]>(`/api/governance/proposals${params}`);
      if (res && typeof res === "object" && "items" in res) return res.items;
      return res as Proposal[];
    },
  });

  const { data: configs = [] } = useQuery<GovConfig[]>({
    queryKey: ["gov-configs"],
    queryFn: () => apiGet<GovConfig[]>("/api/governance/config"),
    enabled: activeTab === "config",
  });

  const { data: stats } = useQuery<GovStats>({
    queryKey: ["gov-stats"],
    queryFn: () => apiGet<GovStats>("/api/governance/stats"),
  });

  const createMutation = useMutation({
    mutationFn: (payload: typeof form) =>
      apiPost<Proposal>("/api/governance/proposals", {
        ...payload,
        voting_period_days: Number(payload.voting_period_days),
      }),
    onSuccess: () => {
      toast.success("Proposal created and voting period started");
      qc.invalidateQueries({ queryKey: ["gov-proposals"] });
      qc.invalidateQueries({ queryKey: ["gov-stats"] });
      setShowCreateForm(false);
      setForm({ title: "", description: "", category: "general", voting_period_days: "7" });
    },
    onError: (err: Error) => toast.error(err.message ?? "Failed to create proposal"),
  });

  const voteMutation = useMutation({
    mutationFn: ({ id, choice, reason }: { id: number; choice: string; reason: string }) =>
      apiPost<Proposal>(`/api/governance/proposals/${id}/vote`, { choice, reason }),
    onSuccess: () => {
      toast.success("Vote cast successfully");
      qc.invalidateQueries({ queryKey: ["gov-proposals"] });
      qc.invalidateQueries({ queryKey: ["gov-stats"] });
      setSelectedProposal(null);
      setVoteChoice("");
      setVoteReason("");
    },
    onError: (err: Error) => toast.error(err.message ?? "Failed to cast vote"),
  });

  const tabs = [
    { key: "proposals", label: "Proposals",      icon: Vote },
    { key: "config",    label: "Protocol Config", icon: Settings },
    { key: "stats",     label: "Stats",           icon: BarChart2 },
  ] as const;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Governance</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Vote on protocol changes. Voting power = VITCoin staked × trust score. Phase 11 — Module M.
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(v => !v)}>
          <Plus className="w-4 h-4 mr-1" />New Proposal
        </Button>
      </div>

      {/* Stats Strip */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Total Proposals",   value: stats.total_proposals },
            { label: "Active",            value: stats.active_proposals },
            { label: "Passed / Executed", value: stats.passed_proposals },
            { label: "Total Votes Cast",  value: stats.total_votes },
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

      {/* Create Form */}
      {showCreateForm && (
        <Card className="border border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="text-base">Create Governance Proposal</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="Proposal title"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            />
            <Textarea
              placeholder="Full description — explain the rationale, expected impact, and any risks..."
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={4}
            />
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground mb-1 block">Category</label>
                <Select value={form.category} onValueChange={v => setForm(f => ({ ...f, category: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(c => (
                      <SelectItem key={c} value={c}>{c.replace("_", " ")}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1">
                <label className="text-xs text-muted-foreground mb-1 block">Voting Period (days)</label>
                <Input
                  type="number"
                  min="1"
                  max="30"
                  value={form.voting_period_days}
                  onChange={e => setForm(f => ({ ...f, voting_period_days: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => createMutation.mutate(form)}
                disabled={!form.title || !form.description || createMutation.isPending}
              >
                {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Submit Proposal"}
              </Button>
              <Button variant="ghost" onClick={() => setShowCreateForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
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

      {/* Proposals Tab */}
      {activeTab === "proposals" && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            {["all", "active", "passed", "rejected", "executed"].map(s => (
              <Button
                key={s}
                size="sm"
                variant={filterStatus === s ? "default" : "outline"}
                onClick={() => setFilterStatus(s)}
                className="capitalize"
              >
                {s}
              </Button>
            ))}
          </div>

          {proposals.length === 0 ? (
            <Card className="border border-border">
              <CardContent className="py-16 text-center text-muted-foreground text-sm">
                No proposals found. Be the first to create one.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {proposals.map(p => (
                <Card key={p.id} className="border border-border hover:border-border/80 transition-colors">
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <StatusBadge status={p.status} />
                          <Badge variant="outline" className="text-xs capitalize">
                            {p.category.replace("_", " ")}
                          </Badge>
                          <span className="text-xs text-muted-foreground">#{p.id}</span>
                        </div>
                        <h3 className="font-semibold text-sm mb-1">{p.title}</h3>
                        <p className="text-xs text-muted-foreground line-clamp-2">{p.description}</p>
                      </div>
                      {p.status === "active" && (
                        <Button size="sm" onClick={() => setSelectedProposal(p)}>
                          <Vote className="w-3.5 h-3.5 mr-1" />Vote
                        </Button>
                      )}
                    </div>

                    {p.total_votes > 0 && (
                      <div className="mt-3 space-y-1">
                        <div className="flex justify-between text-xs text-muted-foreground mb-1">
                          <span>For: <span className="text-emerald-400 font-mono">{p.votes_for.toFixed(1)}</span></span>
                          <span>{p.approval_pct}% approval</span>
                          <span>Against: <span className="text-red-400 font-mono">{p.votes_against.toFixed(1)}</span></span>
                        </div>
                        <Progress value={p.approval_pct} className="h-1.5" />
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>Total: {p.total_votes.toFixed(1)} power</span>
                          <span>Quorum: {p.quorum_required}</span>
                        </div>
                      </div>
                    )}

                    {p.voting_ends_at && p.status === "active" && (
                      <p className="text-xs text-muted-foreground mt-2">
                        Voting ends: {new Date(p.voting_ends_at).toLocaleDateString()} {new Date(p.voting_ends_at).toLocaleTimeString()}
                      </p>
                    )}
                    {p.execution_note && (
                      <p className="text-xs text-muted-foreground mt-2 italic">Execution: {p.execution_note}</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Config Tab */}
      {activeTab === "config" && (
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="text-base">Protocol Parameters</CardTitle>
          </CardHeader>
          <CardContent>
            {configs.length === 0 ? (
              <p className="text-muted-foreground text-sm text-center py-8">Loading configuration...</p>
            ) : (
              <div className="divide-y divide-border">
                {configs.map(c => (
                  <div key={c.key} className="flex items-center justify-between py-3 gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-sm font-medium">{c.key}</p>
                      <p className="text-xs text-muted-foreground">{c.description}</p>
                    </div>
                    <div className="text-right">
                      <span className="font-mono text-sm font-semibold text-primary">{c.value}</span>
                      <p className="text-xs text-muted-foreground">{c.data_type}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-4 border-t border-border pt-3">
              Protocol parameters can only be changed by passed governance proposals.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Stats Tab */}
      {activeTab === "stats" && stats && (
        <div className="grid sm:grid-cols-2 gap-4">
          <Card className="border border-border">
            <CardHeader><CardTitle className="text-base">Proposal Outcomes</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: "Active",          value: stats.active_proposals,   color: "bg-blue-400" },
                { label: "Passed/Executed", value: stats.passed_proposals,   color: "bg-emerald-400" },
                { label: "Rejected",        value: stats.rejected_proposals, color: "bg-red-400" },
              ].map(item => (
                <div key={item.label}>
                  <div className="flex justify-between text-xs text-muted-foreground mb-1">
                    <span>{item.label}</span>
                    <span>{item.value} / {stats.total_proposals}</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${item.color}`}
                      style={{ width: `${stats.total_proposals ? (item.value / stats.total_proposals) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="border border-border">
            <CardHeader><CardTitle className="text-base">Participation</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {[
                { label: "Total Votes Cast",        value: stats.total_votes },
                { label: "Total Voting Power Used", value: stats.total_voting_power_cast.toFixed(2) },
                { label: "Avg Power / Vote",        value: stats.total_votes ? (stats.total_voting_power_cast / stats.total_votes).toFixed(2) : "0" },
              ].map(s => (
                <div key={s.label} className="flex justify-between py-2 border-b border-border last:border-0">
                  <span className="text-sm text-muted-foreground">{s.label}</span>
                  <span className="font-mono font-semibold text-sm">{s.value}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Vote Modal */}
      {selectedProposal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <Card className="w-full max-w-md border border-border bg-background">
            <CardHeader>
              <CardTitle className="text-base">Cast Your Vote</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg bg-muted/30 border border-border p-3">
                <p className="font-semibold text-sm">{selectedProposal.title}</p>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-3">{selectedProposal.description}</p>
              </div>

              <div className="grid grid-cols-3 gap-2">
                {(["for", "against", "abstain"] as const).map(choice => (
                  <Button
                    key={choice}
                    variant={voteChoice === choice ? "default" : "outline"}
                    onClick={() => setVoteChoice(choice)}
                    className={`capitalize ${
                      voteChoice === choice
                        ? choice === "for"     ? "bg-emerald-600 hover:bg-emerald-700"
                        : choice === "against" ? "bg-red-600 hover:bg-red-700"
                        :                        ""
                        : ""
                    }`}
                  >
                    {choice === "for"     && <CheckCircle2 className="w-3.5 h-3.5 mr-1" />}
                    {choice === "against" && <XCircle className="w-3.5 h-3.5 mr-1" />}
                    {choice}
                  </Button>
                ))}
              </div>

              <Textarea
                placeholder="Reason (optional) — explain your vote to the community..."
                value={voteReason}
                onChange={e => setVoteReason(e.target.value)}
                rows={3}
              />

              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  disabled={!voteChoice || voteMutation.isPending}
                  onClick={() => voteMutation.mutate({
                    id: selectedProposal.id,
                    choice: voteChoice,
                    reason: voteReason,
                  })}
                >
                  {voteMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Submit Vote"}
                </Button>
                <Button variant="ghost" onClick={() => { setSelectedProposal(null); setVoteChoice(""); setVoteReason(""); }}>
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
