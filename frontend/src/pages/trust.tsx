import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { apiGet, apiPost, apiPatch } from "@/lib/apiClient";
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import {
  ShieldCheck, ShieldAlert, ShieldOff, AlertTriangle, Activity,
  BarChart2, Clock, CheckCircle2, RefreshCw, Users, Flag,
} from "lucide-react";
import { format } from "date-fns";

// ─── Types ───────────────────────────────────────────────────────────────────
interface TrustScore {
  user_id: number;
  composite_score: number;
  transaction_score: number;
  prediction_score: number;
  activity_score: number;
  fraud_penalty: number;
  risk_tier: string;
  total_flags: number;
  open_flags: number;
  last_calculated_at: string | null;
}

interface FraudFlag {
  id: number;
  user_id: number;
  flagged_by: string;
  category: string;
  severity: string;
  rule_code: string;
  title: string;
  detail: string | null;
  status: string;
  evidence: Record<string, unknown> | null;
  reviewed_at: string | null;
  resolution_note: string | null;
  created_at: string | null;
}

interface RiskEvent {
  id: number;
  user_id: number;
  rule_code: string;
  score_impact: number;
  detail: string | null;
  evidence: Record<string, unknown> | null;
  created_at: string | null;
}

interface PlatformStats {
  total_users_scored: number;
  critical_tier: number;
  high_tier: number;
  medium_tier: number;
  low_tier: number;
  open_flags: number;
  flags_today: number;
  avg_composite: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
const TIER_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  low:      { color: "text-emerald-400", icon: <ShieldCheck className="h-5 w-5" />,  label: "Low Risk" },
  medium:   { color: "text-yellow-400",  icon: <ShieldAlert className="h-5 w-5" />,  label: "Medium Risk" },
  high:     { color: "text-orange-400",  icon: <AlertTriangle className="h-5 w-5" />, label: "High Risk" },
  critical: { color: "text-red-500",     icon: <ShieldOff className="h-5 w-5" />,    label: "Critical Risk" },
};

const SEVERITY_COLOR: Record<string, string> = {
  low:      "bg-blue-500/20 text-blue-300",
  medium:   "bg-yellow-500/20 text-yellow-300",
  high:     "bg-orange-500/20 text-orange-300",
  critical: "bg-red-500/20 text-red-400",
};

const STATUS_COLOR: Record<string, string> = {
  open:      "bg-red-500/20 text-red-300",
  reviewed:  "bg-blue-500/20 text-blue-300",
  dismissed: "bg-gray-500/20 text-gray-400",
  actioned:  "bg-emerald-500/20 text-emerald-300",
};

const fmtDate = (d: string | null) =>
  d ? format(new Date(d), "MMM d, yyyy HH:mm") : "—";

const scoreBar = (label: string, value: number, color: string) => (
  <div className="space-y-1">
    <div className="flex justify-between text-xs text-muted-foreground">
      <span>{label}</span>
      <span className={color}>{value.toFixed(1)}</span>
    </div>
    <Progress value={value} className="h-2" />
  </div>
);

// ─── TrustScoreCard ───────────────────────────────────────────────────────────
function TrustScoreCard({ score }: { score: TrustScore }) {
  const cfg = TIER_CONFIG[score.risk_tier] ?? TIER_CONFIG.medium;

  return (
    <Card className="border-border/60">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <span className={cfg.color}>{cfg.icon}</span>
          Trust Score
          <Badge className={`ml-auto ${SEVERITY_COLOR[score.risk_tier] ?? ""}`}>
            {cfg.label}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-end gap-2">
          <span className={`text-5xl font-bold ${cfg.color}`}>
            {score.composite_score.toFixed(0)}
          </span>
          <span className="text-muted-foreground text-sm mb-1">/ 100</span>
        </div>
        <div className="space-y-2">
          {scoreBar("Transaction Health",  score.transaction_score,  "text-blue-400")}
          {scoreBar("Prediction Accuracy", score.prediction_score,   "text-purple-400")}
          {scoreBar("Activity Score",      score.activity_score,     "text-emerald-400")}
        </div>
        {score.fraud_penalty > 0 && (
          <div className="flex items-center gap-2 p-2 rounded bg-red-500/10 text-red-400 text-xs">
            <AlertTriangle className="h-3 w-3 shrink-0" />
            Fraud penalty deducted: −{score.fraud_penalty.toFixed(1)} points
          </div>
        )}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <div className="text-center p-2 rounded bg-muted/30">
            <p className="text-xs text-muted-foreground">Total Flags</p>
            <p className="text-lg font-semibold">{score.total_flags}</p>
          </div>
          <div className="text-center p-2 rounded bg-muted/30">
            <p className="text-xs text-muted-foreground">Open Flags</p>
            <p className={`text-lg font-semibold ${score.open_flags > 0 ? "text-red-400" : "text-emerald-400"}`}>
              {score.open_flags}
            </p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground text-right">
          Last updated {fmtDate(score.last_calculated_at)}
        </p>
      </CardContent>
    </Card>
  );
}

// ─── FlagRow ──────────────────────────────────────────────────────────────────
function FlagRow({
  flag, onReview, isAdmin,
}: { flag: FraudFlag; onReview?: (f: FraudFlag) => void; isAdmin: boolean }) {
  return (
    <div className="border border-border/40 rounded-lg p-3 space-y-2 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge className={SEVERITY_COLOR[flag.severity]}>{flag.severity}</Badge>
          <Badge className={STATUS_COLOR[flag.status]}>{flag.status}</Badge>
          <Badge variant="outline" className="text-xs font-mono">{flag.rule_code}</Badge>
        </div>
        {isAdmin && flag.status === "open" && onReview && (
          <Button size="sm" variant="outline" onClick={() => onReview(flag)}>Review</Button>
        )}
      </div>
      <p className="font-medium">{flag.title}</p>
      {flag.detail && <p className="text-muted-foreground text-xs">{flag.detail}</p>}
      {flag.evidence && (
        <pre className="text-xs bg-muted/30 rounded p-2 overflow-x-auto max-h-24">
          {JSON.stringify(flag.evidence, null, 2)}
        </pre>
      )}
      <p className="text-xs text-muted-foreground">
        {flag.category} · flagged by {flag.flagged_by} · {fmtDate(flag.created_at)}
        {flag.reviewed_at && ` · reviewed ${fmtDate(flag.reviewed_at)}`}
      </p>
      {flag.resolution_note && (
        <p className="text-xs bg-muted/20 rounded p-2 italic">
          Resolution: {flag.resolution_note}
        </p>
      )}
    </div>
  );
}

// ─── ReviewDialog ─────────────────────────────────────────────────────────────
function ReviewDialog({
  flag, open, onClose,
}: { flag: FraudFlag | null; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [status, setStatus] = useState("reviewed");
  const [note, setNote] = useState("");

  const mutation = useMutation({
    mutationFn: (body: { status: string; resolution_note: string }) =>
      apiPatch(`/api/trust/admin/flags/${flag!.id}/review`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/trust"] });
      onClose();
      setNote("");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Review Flag #{flag?.id}</DialogTitle>
        </DialogHeader>
        {flag && (
          <div className="space-y-3 text-sm">
            <p className="font-medium">{flag.title}</p>
            <p className="text-muted-foreground">{flag.detail}</p>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="reviewed">Reviewed (no action)</SelectItem>
                <SelectItem value="dismissed">Dismissed (false positive)</SelectItem>
                <SelectItem value="actioned">Actioned (sanction applied)</SelectItem>
              </SelectContent>
            </Select>
            <Textarea
              placeholder="Resolution note (optional)…"
              value={note}
              onChange={e => setNote(e.target.value)}
              rows={3}
            />
          </div>
        )}
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate({ status, resolution_note: note })}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Saving…" : "Submit Review"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── AdminPanel ───────────────────────────────────────────────────────────────
function AdminPanel() {
  const qc = useQueryClient();
  const [reviewFlag, setReviewFlag] = useState<FraudFlag | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("open");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const statsQ = useQuery<PlatformStats>({
    queryKey: ["/api/trust/admin/stats"],
    queryFn: () => apiGet<PlatformStats>("/api/trust/admin/stats"),
    refetchInterval: 30000,
  });

  const params = new URLSearchParams();
  if (statusFilter !== "all") params.set("status", statusFilter);
  if (severityFilter !== "all") params.set("severity", severityFilter);

  const flagsQ = useQuery<FraudFlag[]>({
    queryKey: ["/api/trust/admin/flags", statusFilter, severityFilter],
    queryFn: () => apiGet<FraudFlag[]>(`/api/trust/admin/flags?${params}`),
  });

  const batchMut = useMutation({
    mutationFn: () => apiPost("/api/trust/admin/batch-refresh"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/trust"] }),
  });

  const stats = statsQ.data;

  return (
    <div className="space-y-6">
      {/* Platform stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Users Scored",   value: stats.total_users_scored, icon: <Users className="h-4 w-4" />,    color: "text-blue-400" },
            { label: "Avg Trust Score",value: stats.avg_composite,      icon: <BarChart2 className="h-4 w-4" />,color: "text-purple-400" },
            { label: "Open Flags",     value: stats.open_flags,         icon: <Flag className="h-4 w-4" />,     color: stats.open_flags > 0 ? "text-red-400" : "text-emerald-400" },
            { label: "Flags Today",    value: stats.flags_today,        icon: <Clock className="h-4 w-4" />,    color: "text-yellow-400" },
          ].map(s => (
            <Card key={s.label} className="border-border/60">
              <CardContent className="p-3 flex items-center gap-3">
                <span className={s.color}>{s.icon}</span>
                <div>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className={`text-xl font-bold ${s.color}`}>
                    {typeof s.value === "number" ? s.value.toFixed(s.label === "Avg Trust Score" ? 1 : 0) : s.value}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Tier breakdown */}
      {stats && (
        <Card className="border-border/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Risk Tier Distribution</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-4 gap-3 text-center">
            {[
              { tier: "critical", count: stats.critical_tier, color: "text-red-400" },
              { tier: "high",     count: stats.high_tier,     color: "text-orange-400" },
              { tier: "medium",   count: stats.medium_tier,   color: "text-yellow-400" },
              { tier: "low",      count: stats.low_tier,      color: "text-emerald-400" },
            ].map(t => (
              <div key={t.tier} className="p-2 rounded bg-muted/20">
                <p className="text-xs text-muted-foreground capitalize">{t.tier}</p>
                <p className={`text-2xl font-bold ${t.color}`}>{t.count}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Flags table */}
      <Card className="border-border/60">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle className="text-sm">Fraud Flags Queue</CardTitle>
            <div className="flex gap-2 flex-wrap">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-8 w-32 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="reviewed">Reviewed</SelectItem>
                  <SelectItem value="dismissed">Dismissed</SelectItem>
                  <SelectItem value="actioned">Actioned</SelectItem>
                </SelectContent>
              </Select>
              <Select value={severityFilter} onValueChange={setSeverityFilter}>
                <SelectTrigger className="h-8 w-32 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Severity</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
              <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => batchMut.mutate()} disabled={batchMut.isPending}>
                <RefreshCw className={`h-3 w-3 mr-1 ${batchMut.isPending ? "animate-spin" : ""}`} />
                Refresh All
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 max-h-[500px] overflow-y-auto">
          {flagsQ.isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}
          {flagsQ.data?.length === 0 && (
            <div className="flex flex-col items-center py-8 text-muted-foreground gap-2">
              <CheckCircle2 className="h-8 w-8 text-emerald-500" />
              <p className="text-sm">No flags match this filter</p>
            </div>
          )}
          {flagsQ.data?.map(f => (
            <FlagRow key={f.id} flag={f} isAdmin onReview={setReviewFlag} />
          ))}
        </CardContent>
      </Card>

      <ReviewDialog
        flag={reviewFlag}
        open={!!reviewFlag}
        onClose={() => setReviewFlag(null)}
      />
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function TrustPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const scoreQ = useQuery<TrustScore>({
    queryKey: ["/api/trust/me"],
    queryFn: () => apiGet<TrustScore>("/api/trust/me"),
    refetchInterval: 60000,
  });

  const flagsQ = useQuery<FraudFlag[]>({
    queryKey: ["/api/trust/me/flags"],
    queryFn: () => apiGet<FraudFlag[]>("/api/trust/me/flags"),
  });

  const eventsQ = useQuery<RiskEvent[]>({
    queryKey: ["/api/trust/me/events"],
    queryFn: () => apiGet<RiskEvent[]>("/api/trust/me/events"),
  });

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-emerald-400" />
          Trust & Reputation
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Your composite trust score, fraud flags, and activity risk events.
        </p>
      </div>

      <Tabs defaultValue={isAdmin ? "admin" : "score"}>
        <TabsList>
          <TabsTrigger value="score">My Score</TabsTrigger>
          <TabsTrigger value="flags">
            My Flags
            {(flagsQ.data?.filter(f => f.status === "open").length ?? 0) > 0 && (
              <span className="ml-1.5 rounded-full bg-red-500 text-white text-xs px-1.5">
                {flagsQ.data!.filter(f => f.status === "open").length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="events">Risk Events</TabsTrigger>
          {isAdmin && <TabsTrigger value="admin">Admin Queue</TabsTrigger>}
        </TabsList>

        {/* My Score */}
        <TabsContent value="score">
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <div>
              {scoreQ.isLoading && <p className="text-muted-foreground text-sm">Calculating…</p>}
              {scoreQ.data && <TrustScoreCard score={scoreQ.data} />}
            </div>
            <Card className="border-border/60">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">How Your Score Is Calculated</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground space-y-2">
                {[
                  { label: "Transaction Health (30%)", desc: "Frequency, diversity, and success rate of wallet activity." },
                  { label: "Prediction Accuracy (30%)", desc: "Validator submission consistency and historical correctness." },
                  { label: "Activity Score (20%)", desc: "Account age, login recency, verification status, and role." },
                  { label: "Fraud Signals (20%)", desc: "Deductions applied for open fraud flags by severity." },
                ].map(item => (
                  <div key={item.label} className="p-2 rounded bg-muted/20">
                    <p className="font-medium text-foreground/80 text-xs">{item.label}</p>
                    <p className="text-xs mt-0.5">{item.desc}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* My Flags */}
        <TabsContent value="flags">
          <div className="mt-4 space-y-2">
            {flagsQ.isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}
            {flagsQ.data?.length === 0 && (
              <div className="flex flex-col items-center py-12 text-muted-foreground gap-2">
                <ShieldCheck className="h-12 w-12 text-emerald-500" />
                <p>No fraud flags on your account</p>
              </div>
            )}
            {flagsQ.data?.map(f => (
              <FlagRow key={f.id} flag={f} isAdmin={false} />
            ))}
          </div>
        </TabsContent>

        {/* Risk Events */}
        <TabsContent value="events">
          <div className="mt-4 space-y-2">
            {eventsQ.isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}
            {eventsQ.data?.length === 0 && (
              <div className="flex flex-col items-center py-12 text-muted-foreground gap-2">
                <Activity className="h-12 w-12 text-blue-500" />
                <p>No risk events recorded</p>
              </div>
            )}
            {eventsQ.data?.map(e => (
              <div key={e.id} className="border border-border/40 rounded-lg p-3 text-sm space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">{e.rule_code}</Badge>
                  <span className={e.score_impact < 0 ? "text-red-400 text-xs" : "text-emerald-400 text-xs"}>
                    {e.score_impact >= 0 ? "+" : ""}{e.score_impact.toFixed(1)} pts
                  </span>
                </div>
                {e.detail && <p className="text-muted-foreground text-xs">{e.detail}</p>}
                {e.evidence && (
                  <pre className="text-xs bg-muted/30 rounded p-2 overflow-x-auto max-h-20">
                    {JSON.stringify(e.evidence, null, 2)}
                  </pre>
                )}
                <p className="text-xs text-muted-foreground">{fmtDate(e.created_at)}</p>
              </div>
            ))}
          </div>
        </TabsContent>

        {/* Admin */}
        {isAdmin && (
          <TabsContent value="admin">
            <div className="mt-4">
              <AdminPanel />
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
