import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
  ShieldCheck, AlertTriangle, CheckCircle2, Clock,
  XCircle, Upload, Camera, FileText, User, Calendar,
  Globe, CreditCard, ChevronRight, Info
} from "lucide-react";

interface KYCStatus {
  id?: number;
  status: string;
  risk_score?: number;
  risk_level?: string;
  risk_flags?: string[];
  submitted_at?: string;
  reviewed_at?: string | null;
  approved_at?: string | null;
  expires_at?: string | null;
  rule_checks?: Record<string, { passed: boolean; note: string }>;
  review_note?: string | null;
  rejection_reason?: string | null;
  message?: string;
}

const DOCUMENT_TYPES = [
  { value: "national_id",      label: "National ID Card" },
  { value: "passport",         label: "International Passport" },
  { value: "drivers_license",  label: "Driver's License" },
  { value: "voter_card",       label: "Voter's Card" },
  { value: "resident_permit",  label: "Resident Permit" },
  { value: "bvn",              label: "BVN (Nigeria)" },
  { value: "nin",              label: "NIN (Nigeria)" },
];

const STATUS_CONFIG: Record<string, { label: string; icon: typeof ShieldCheck; color: string; bg: string; border: string }> = {
  none:          { label: "Not Submitted",    icon: AlertTriangle, color: "text-muted-foreground", bg: "bg-muted/20",          border: "border-border" },
  pending:       { label: "Under Review",     icon: Clock,         color: "text-yellow-400",        bg: "bg-yellow-500/10",     border: "border-yellow-500/30" },
  auto_approved: { label: "Auto Verified",    icon: CheckCircle2,  color: "text-emerald-400",       bg: "bg-emerald-500/10",    border: "border-emerald-500/30" },
  manual_review: { label: "Manual Review",    icon: Clock,         color: "text-blue-400",          bg: "bg-blue-500/10",       border: "border-blue-500/30" },
  approved:      { label: "Verified",         icon: ShieldCheck,   color: "text-emerald-400",       bg: "bg-emerald-500/10",    border: "border-emerald-500/30" },
  rejected:      { label: "Rejected",         icon: XCircle,       color: "text-red-400",           bg: "bg-red-500/10",        border: "border-red-500/30" },
};

function StatusBanner({ status }: { status: KYCStatus }) {
  const cfg = STATUS_CONFIG[status.status] ?? STATUS_CONFIG.none;
  const Icon = cfg.icon;
  const isApproved = ["approved", "auto_approved"].includes(status.status);

  return (
    <Card className={`${cfg.bg} ${cfg.border} border`}>
      <CardContent className="py-5">
        <div className="flex items-start gap-4">
          <div className={`w-10 h-10 rounded-xl ${cfg.bg} border ${cfg.border} flex items-center justify-center shrink-0`}>
            <Icon className={`w-5 h-5 ${cfg.color}`} />
          </div>
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <span className={`font-semibold ${cfg.color}`}>{cfg.label}</span>
              {status.risk_level && !isApproved && (
                <Badge variant="outline" className={`text-xs ${cfg.color} border-0 ${cfg.bg}`}>
                  {status.risk_level} risk
                </Badge>
              )}
            </div>
            {status.status === "none" && (
              <p className="text-sm text-muted-foreground">
                Submit your identity documents to get verified. All verification is done securely on-platform — no external services required.
              </p>
            )}
            {status.status === "pending" && (
              <p className="text-sm text-muted-foreground">
                Your submission has been received and is under review. You'll be notified once processed.
              </p>
            )}
            {status.status === "manual_review" && (
              <p className="text-sm text-muted-foreground">
                Your submission requires manual review by our compliance team. This typically takes 1-2 business days.
              </p>
            )}
            {isApproved && (
              <p className="text-sm text-emerald-400/80">
                Your identity has been verified. You now have access to all platform features.
                {status.expires_at && (
                  <span className="text-muted-foreground"> Expires: {new Date(status.expires_at).toLocaleDateString()}</span>
                )}
              </p>
            )}
            {status.status === "rejected" && (
              <div className="space-y-1">
                {status.rejection_reason && (
                  <p className="text-sm text-red-400/80">{status.rejection_reason}</p>
                )}
                {status.review_note && (
                  <p className="text-xs text-muted-foreground">{status.review_note}</p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  Please review your information and resubmit.
                </p>
              </div>
            )}
            {status.risk_flags && status.risk_flags.length > 0 && !isApproved && (
              <div className="mt-2 space-y-1">
                {status.risk_flags.map((flag, i) => (
                  <p key={i} className="text-xs text-muted-foreground flex items-center gap-1">
                    <Info className="w-3 h-3 shrink-0" />
                    {flag}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Rule checks breakdown */}
        {status.rule_checks && Object.keys(status.rule_checks).length > 0 && !isApproved && (
          <div className="mt-4 pt-4 border-t border-border/50 grid grid-cols-2 gap-2">
            {Object.entries(status.rule_checks).map(([rule, check]) => (
              <div key={rule} className="flex items-center gap-2 text-xs">
                {check.passed
                  ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  : <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />}
                <span className={check.passed ? "text-foreground" : "text-red-400"}>
                  {rule.replace(/_/g, " ")}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function KYCForm({ onSuccess }: { onSuccess: () => void }) {
  const [form, setForm] = useState({
    full_name:       "",
    date_of_birth:   "",
    nationality:     "",
    document_type:   "",
    document_number: "",
    address:         "",
  });

  const submit = useMutation({
    mutationFn: (payload: typeof form) =>
      apiPost<KYCStatus>("/api/kyc/submit", payload),
    onSuccess: (data) => {
      if (data.status === "auto_approved") {
        toast.success("Identity verified successfully!");
      } else if (data.status === "rejected") {
        toast.error(data.message ?? "Verification failed. Please check your details.");
      } else {
        toast.info(data.message ?? "Submission received — under review.");
      }
      onSuccess();
    },
    onError: (e: any) => toast.error(e?.detail ?? e?.message ?? "Submission failed"),
  });

  const handleChange = (field: string, value: string) => {
    setForm(f => ({ ...f, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.full_name || !form.date_of_birth || !form.nationality || !form.document_type || !form.document_number) {
      toast.error("Please fill in all required fields.");
      return;
    }
    submit.mutate(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Personal Info */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground uppercase tracking-wider">
          <User className="w-4 h-4" />
          Personal Information
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="full_name">Full Legal Name *</Label>
            <Input
              id="full_name"
              placeholder="As it appears on your document"
              value={form.full_name}
              onChange={e => handleChange("full_name", e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground">Must include at least first and last name</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="date_of_birth">Date of Birth *</Label>
            <Input
              id="date_of_birth"
              type="date"
              value={form.date_of_birth}
              onChange={e => handleChange("date_of_birth", e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="nationality">Nationality *</Label>
            <Input
              id="nationality"
              placeholder="e.g. Nigerian"
              value={form.nationality}
              onChange={e => handleChange("nationality", e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="address">Residential Address</Label>
            <Input
              id="address"
              placeholder="Optional"
              value={form.address}
              onChange={e => handleChange("address", e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Document Info */}
      <div className="space-y-4 pt-2 border-t border-border">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground uppercase tracking-wider">
          <CreditCard className="w-4 h-4" />
          Identity Document
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Document Type *</Label>
            <Select
              value={form.document_type}
              onValueChange={v => handleChange("document_type", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select document type" />
              </SelectTrigger>
              <SelectContent>
                {DOCUMENT_TYPES.map(dt => (
                  <SelectItem key={dt.value} value={dt.value}>{dt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="document_number">Document Number *</Label>
            <Input
              id="document_number"
              placeholder="e.g. A1234567"
              value={form.document_number}
              onChange={e => handleChange("document_number", e.target.value.toUpperCase())}
              className="font-mono uppercase"
              required
            />
          </div>
        </div>
      </div>

      {/* Privacy notice */}
      <div className="rounded-lg bg-muted/30 border border-border p-3 flex items-start gap-2">
        <ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
        <p className="text-xs text-muted-foreground">
          All identity verification is performed entirely on-platform using our offline rule engine.
          Your data is encrypted at rest and never shared with third-party services.
          Submitted information is used solely for compliance verification.
        </p>
      </div>

      <Button
        type="submit"
        className="w-full gap-2"
        disabled={submit.isPending}
      >
        {submit.isPending ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Verifying...
          </>
        ) : (
          <>
            <ShieldCheck className="w-4 h-4" />
            Submit for Verification
          </>
        )}
      </Button>
    </form>
  );
}

export default function KYCPage() {
  const qc = useQueryClient();

  const { data: status, isLoading } = useQuery<KYCStatus>({
    queryKey: ["/api/kyc/status"],
    queryFn: () => apiGet<KYCStatus>("/api/kyc/status"),
    staleTime: 15_000,
  });

  const handleSuccess = () => {
    qc.invalidateQueries({ queryKey: ["/api/kyc/status"] });
    qc.invalidateQueries({ queryKey: ["/api/identity/me"] });
    qc.invalidateQueries({ queryKey: ["/api/wallet/me"] });
  };

  const canResubmit = status?.status === "none" || status?.status === "rejected";
  const isApproved  = ["approved", "auto_approved"].includes(status?.status ?? "");

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto py-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-primary" />
          Identity Verification
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Verify your identity to unlock full platform access. No external APIs — verified entirely on-platform.
        </p>
      </div>

      {/* Status banner */}
      {status && <StatusBanner status={status} />}

      {/* What you get */}
      {!isApproved && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">What you unlock after verification</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              "Withdraw funds and process payments",
              "Verified tier on your System ID card",
              "Verifiable Credential (VC) issued to your DID",
              "Higher staking limits on predictions",
              "Validator eligibility",
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                <ChevronRight className="w-4 h-4 text-primary" />
                {item}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Submission form */}
      {canResubmit && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" />
              {status?.status === "rejected" ? "Resubmit Identity Verification" : "Submit Identity Verification"}
            </CardTitle>
            <CardDescription>
              All fields are required. Enter information exactly as it appears on your official documents.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <KYCForm onSuccess={handleSuccess} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
