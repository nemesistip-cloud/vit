import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
  ShieldCheck, Fingerprint, BadgeCheck, User, Globe,
  RefreshCcw, ExternalLink, Lock, Zap, Star, Crown
} from "lucide-react";
import { Link } from "wouter";

interface SystemIDData {
  sid: string;
  display_name: string;
  tier: "basic" | "standard" | "verified" | "elite";
  avatar_initials: string;
  did: string | null;
  badges: Record<string, boolean>;
  issued_at: string;
  expires_at: string | null;
  revoked: boolean;
  email: string;
  role: string;
  subscription_tier: string;
  is_verified: boolean;
  kyc_status: string;
}

const TIER_CONFIG = {
  basic:    { label: "Basic",    color: "text-muted-foreground", bg: "bg-muted/30",     border: "border-border",          icon: User,       gradient: "from-zinc-800 to-zinc-900" },
  standard: { label: "Standard", color: "text-blue-400",         bg: "bg-blue-500/10",  border: "border-blue-500/30",     icon: ShieldCheck,gradient: "from-blue-900 to-zinc-900" },
  verified: { label: "Verified", color: "text-emerald-400",      bg: "bg-emerald-500/10",border: "border-emerald-500/30", icon: BadgeCheck, gradient: "from-emerald-900 to-zinc-900" },
  elite:    { label: "Elite",    color: "text-amber-400",        bg: "bg-amber-500/10", border: "border-amber-500/30",    icon: Crown,      gradient: "from-amber-900 to-zinc-900" },
};

const BADGE_CONFIG: Record<string, { label: string; icon: typeof ShieldCheck; color: string }> = {
  email_verified:  { label: "Email Verified",  icon: BadgeCheck, color: "text-blue-400" },
  kyc_verified:    { label: "KYC Verified",    icon: ShieldCheck, color: "text-emerald-400" },
  two_fa_enabled:  { label: "2FA Active",      icon: Lock,       color: "text-purple-400" },
  validator:       { label: "Validator",       icon: Zap,        color: "text-yellow-400" },
  admin:           { label: "Admin",           icon: Star,       color: "text-red-400" },
  pro_subscriber:  { label: "Pro Subscriber",  icon: Crown,      color: "text-amber-400" },
};

function IDCardSkeleton() {
  return (
    <div className="max-w-md w-full mx-auto space-y-4">
      <Skeleton className="h-64 w-full rounded-2xl" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-full rounded-xl" />
      </div>
    </div>
  );
}

function IDCard({ data }: { data: SystemIDData }) {
  const tier = TIER_CONFIG[data.tier] || TIER_CONFIG.basic;
  const TierIcon = tier.icon;

  return (
    <div className={`relative rounded-2xl border ${tier.border} overflow-hidden bg-gradient-to-br ${tier.gradient} p-px`}>
      <div className="rounded-2xl bg-card/80 backdrop-blur-sm p-6 space-y-5">
        {/* Header row */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl ${tier.bg} border ${tier.border} flex items-center justify-center`}>
              <span className={`font-bold text-lg ${tier.color}`}>{data.avatar_initials}</span>
            </div>
            <div>
              <p className="font-semibold text-foreground">{data.display_name}</p>
              <p className="text-xs text-muted-foreground">{data.email}</p>
            </div>
          </div>
          <Badge variant="outline" className={`${tier.color} ${tier.bg} border-0 gap-1`}>
            <TierIcon className="w-3 h-3" />
            {tier.label}
          </Badge>
        </div>

        {/* SID */}
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground uppercase tracking-widest font-mono">System ID</p>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xl font-bold tracking-wider text-foreground">{data.sid}</span>
            <Fingerprint className={`w-5 h-5 ${tier.color}`} />
          </div>
        </div>

        {/* DID */}
        {data.did && (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-widest font-mono">Decentralized ID</p>
            <p className="font-mono text-xs text-muted-foreground truncate">{data.did}</p>
          </div>
        )}

        {/* Badges */}
        {Object.keys(data.badges).length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground uppercase tracking-widest font-mono">Credentials</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(data.badges)
                .filter(([, v]) => v)
                .map(([key]) => {
                  const cfg = BADGE_CONFIG[key];
                  if (!cfg) return null;
                  const Icon = cfg.icon;
                  return (
                    <div key={key} className={`flex items-center gap-1.5 px-2 py-1 rounded-lg bg-muted/30 border border-border text-xs ${cfg.color}`}>
                      <Icon className="w-3 h-3" />
                      {cfg.label}
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-border/50">
          <div>
            <p className="text-xs text-muted-foreground">Issued</p>
            <p className="font-mono text-xs text-foreground">
              {new Date(data.issued_at).toLocaleDateString()}
            </p>
          </div>
          {data.expires_at && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Expires</p>
              <p className="font-mono text-xs text-foreground">
                {new Date(data.expires_at).toLocaleDateString()}
              </p>
            </div>
          )}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Globe className="w-3 h-3" />
            VIT NETWORK
          </div>
        </div>
      </div>
    </div>
  );
}

export default function IdentityPage() {
  const { user } = useAuth();
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery<SystemIDData>({
    queryKey: ["/api/identity/me"],
    queryFn: () => apiGet<SystemIDData>("/api/identity/me"),
    staleTime: 30_000,
  });

  const refreshMutation = useMutation({
    mutationFn: () => apiPost<SystemIDData>("/api/identity/refresh", {}),
    onSuccess: (d) => {
      qc.setQueryData(["/api/identity/me"], d);
      toast.success("Identity card refreshed");
    },
    onError: (e: any) => toast.error(e?.message ?? "Refresh failed"),
  });

  if (isLoading) return <IDCardSkeleton />;
  if (error || !data) return (
    <div className="flex items-center justify-center min-h-[40vh]">
      <p className="text-muted-foreground">Could not load identity card.</p>
    </div>
  );

  const kycVerified = data.kyc_status === "approved";
  const kycPending  = ["pending", "manual_review", "auto_approved"].includes(data.kyc_status);

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Fingerprint className="w-6 h-6 text-primary" />
            System Identity
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Your unique on-platform identity — cryptographically derived, immutable.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="gap-2"
        >
          <RefreshCcw className={`w-4 h-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* ID card */}
      <IDCard data={data} />

      {/* KYC status banner */}
      {!kycVerified && (
        <Card className={kycPending ? "border-yellow-500/30 bg-yellow-500/5" : "border-orange-500/30 bg-orange-500/5"}>
          <CardContent className="py-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <ShieldCheck className={`w-5 h-5 ${kycPending ? "text-yellow-400" : "text-orange-400"}`} />
                <div>
                  <p className="font-medium text-sm">
                    {kycPending ? "KYC Under Review" : "Identity Not Verified"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {kycPending
                      ? "Your submission is being processed. Tier will upgrade once approved."
                      : "Verify your identity to unlock Verified tier and full platform features."}
                  </p>
                </div>
              </div>
              {!kycPending && (
                <Link href="/kyc">
                  <Button size="sm" className="shrink-0 gap-2">
                    <ShieldCheck className="w-4 h-4" />
                    Verify Now
                  </Button>
                </Link>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* DID info */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Globe className="w-4 h-4 text-primary" />
            Decentralized Identity (DID)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.did ? (
            <div className="font-mono text-xs bg-muted/30 rounded-lg p-3 break-all text-muted-foreground">
              {data.did}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No DID registered yet. A DID is automatically created when you verify your identity.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Tier guide */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Identity Tiers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(Object.entries(TIER_CONFIG) as [keyof typeof TIER_CONFIG, typeof TIER_CONFIG["basic"]][]).map(([key, cfg]) => {
            const Icon = cfg.icon;
            const isActive = data.tier === key;
            return (
              <div key={key} className={`flex items-center gap-3 rounded-lg p-2.5 ${isActive ? `${cfg.bg} border ${cfg.border}` : "opacity-50"}`}>
                <Icon className={`w-4 h-4 ${cfg.color}`} />
                <div className="flex-1">
                  <p className={`text-sm font-medium ${cfg.color}`}>{cfg.label}</p>
                </div>
                {isActive && <Badge variant="outline" className={`text-xs ${cfg.color} border-0 ${cfg.bg}`}>Current</Badge>}
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
