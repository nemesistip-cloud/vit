import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
  ShieldCheck, Fingerprint, BadgeCheck, User, Globe,
  RefreshCcw, Lock, Zap, Star, Crown, Copy, CheckCircle2
} from "lucide-react";
import { Link } from "wouter";
import { useState } from "react";

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
  basic:    { label: "Basic",    color: "text-white/50",    bg: "bg-white/5",     border: "border-white/10",        icon: User,       glow: "",                       desc: "Default access — sign up completed" },
  standard: { label: "Standard", color: "text-blue-400",    bg: "bg-blue-500/10", border: "border-blue-500/30",     icon: ShieldCheck,glow: "shadow-blue-500/10",     desc: "Email verified — basic trust level" },
  verified: { label: "Verified", color: "text-[#00E676]",   bg: "bg-[#00E676]/10",border: "border-[#00E676]/30",    icon: BadgeCheck, glow: "shadow-[#00E676]/10",    desc: "KYC approved — full platform access" },
  elite:    { label: "Elite",    color: "text-amber-400",   bg: "bg-amber-400/10",border: "border-amber-400/30",    icon: Crown,      glow: "shadow-amber-400/10",     desc: "Top validator — governance rights" },
};

const BADGE_CONFIG: Record<string, { label: string; icon: typeof ShieldCheck; color: string; bg: string }> = {
  email_verified: { label: "Email Verified",  icon: BadgeCheck, color: "text-blue-400",   bg: "bg-blue-400/10 border-blue-400/20" },
  kyc_verified:   { label: "KYC Verified",    icon: ShieldCheck,color: "text-[#00E676]",  bg: "bg-[#00E676]/10 border-[#00E676]/20" },
  two_fa_enabled: { label: "2FA Active",      icon: Lock,       color: "text-[#8B5CF6]",  bg: "bg-[#8B5CF6]/10 border-[#8B5CF6]/20" },
  validator:      { label: "Validator",       icon: Zap,        color: "text-yellow-400", bg: "bg-yellow-400/10 border-yellow-400/20" },
  admin:          { label: "Admin",           icon: Star,       color: "text-red-400",    bg: "bg-red-400/10 border-red-400/20" },
  pro_subscriber: { label: "Pro Subscriber",  icon: Crown,      color: "text-amber-400",  bg: "bg-amber-400/10 border-amber-400/20" },
};

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-['JetBrains_Mono'] text-[9px] uppercase tracking-[0.2em] text-white/30 mb-2">{children}</p>
  );
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <button onClick={handleCopy} className="p-1 rounded text-white/30 hover:text-[#00E676] transition-colors">
      {copied ? <CheckCircle2 size={13} className="text-[#00E676]" /> : <Copy size={13} />}
    </button>
  );
}

function IDCard({ data }: { data: SystemIDData }) {
  const tier = TIER_CONFIG[data.tier] || TIER_CONFIG.basic;
  const TierIcon = tier.icon;

  return (
    <div className={`relative rounded-2xl border ${tier.border} overflow-hidden bg-[#0b1018]`}>
      {/* Top accent bar */}
      <div className={`h-0.5 w-full ${tier.border.replace("border-", "bg-").replace("/30", "/60")}`} />

      <div className="p-5 space-y-5">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl ${tier.bg} border ${tier.border} flex items-center justify-center shrink-0`}>
              <span className={`font-['Barlow_Condensed'] font-bold text-xl ${tier.color}`}>{data.avatar_initials}</span>
            </div>
            <div>
              <p className="font-['Barlow_Condensed'] text-lg font-bold uppercase tracking-wide text-white leading-none">{data.display_name}</p>
              <p className="font-['Outfit'] text-xs text-white/35 mt-0.5">{data.email}</p>
            </div>
          </div>
          <div className={`flex items-center gap-1.5 rounded-lg ${tier.bg} border ${tier.border} px-2.5 py-1.5`}>
            <TierIcon size={12} className={tier.color} />
            <span className={`font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wide ${tier.color}`}>{tier.label}</span>
          </div>
        </div>

        {/* SID */}
        <div>
          <SectionLabel>System ID</SectionLabel>
          <div className="flex items-center gap-2">
            <span className="font-['JetBrains_Mono'] text-2xl font-bold tracking-wider text-white">{data.sid}</span>
            <Fingerprint size={18} className={tier.color} />
          </div>
        </div>

        {/* Credentials badges */}
        {Object.keys(data.badges).length > 0 && (
          <div>
            <SectionLabel>Credentials</SectionLabel>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(data.badges)
                .filter(([, v]) => v)
                .map(([key]) => {
                  const cfg = BADGE_CONFIG[key];
                  if (!cfg) return null;
                  const Icon = cfg.icon;
                  return (
                    <div key={key} className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border ${cfg.bg} text-xs ${cfg.color}`}>
                      <Icon size={11} />
                      <span className="font-['Outfit'] text-[11px] font-medium">{cfg.label}</span>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-white/6">
          <div>
            <p className="font-['Outfit'] text-[10px] text-white/25 uppercase tracking-wider">Issued</p>
            <p className="font-['JetBrains_Mono'] text-xs text-white/60 mt-0.5">{new Date(data.issued_at).toLocaleDateString()}</p>
          </div>
          {data.expires_at && (
            <div className="text-right">
              <p className="font-['Outfit'] text-[10px] text-white/25 uppercase tracking-wider">Expires</p>
              <p className="font-['JetBrains_Mono'] text-xs text-white/60 mt-0.5">{new Date(data.expires_at).toLocaleDateString()}</p>
            </div>
          )}
          <div className="flex items-center gap-1 text-white/20">
            <Globe size={11} />
            <span className="font-['Barlow_Condensed'] text-[10px] font-semibold uppercase tracking-widest">VIT Network</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-white/8 bg-[#0b1018] ${className}`}>
      {children}
    </div>
  );
}

function PanelHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-4 pt-4 pb-3 border-b border-white/6">
      {children}
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
    onSuccess: (d) => { qc.setQueryData(["/api/identity/me"], d); toast.success("Identity refreshed"); },
    onError: (e: any) => toast.error(e?.message ?? "Refresh failed"),
  });

  if (isLoading) {
    return (
      <div className="p-4 max-w-2xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48 bg-white/5" />
        <Skeleton className="h-60 w-full rounded-2xl bg-white/5" />
        <Skeleton className="h-24 w-full rounded-xl bg-white/5" />
        <Skeleton className="h-40 w-full rounded-xl bg-white/5" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
        <Fingerprint size={32} className="text-white/15" />
        <p className="font-['Outfit'] text-sm text-white/30">Could not load identity card.</p>
      </div>
    );
  }

  const kycVerified = data.kyc_status === "approved";
  const kycPending  = ["pending", "manual_review", "auto_approved"].includes(data.kyc_status);

  return (
    <div className="max-w-2xl mx-auto space-y-4 p-4 pb-8">

      {/* Page header */}
      <div className="flex items-center justify-between pt-1">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="h-px w-4 bg-[#00E676]/40" />
            <span className="font-['JetBrains_Mono'] text-[9px] text-[#00E676]/60 uppercase tracking-[0.2em]">vit_id</span>
          </div>
          <h1 className="font-['Barlow_Condensed'] text-3xl font-bold uppercase tracking-[0.05em] text-white flex items-center gap-2 leading-none">
            <Fingerprint size={24} className="text-[#00E676]" />
            VIT Identity
          </h1>
          <p className="font-['Outfit'] text-[11px] text-white/30 mt-1">
            Cryptographically derived · Immutable · On-chain
          </p>
        </div>
        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/4 px-3 py-2 font-['Outfit'] text-xs text-white/40 hover:border-[#00E676]/30 hover:text-[#00E676] transition-colors disabled:opacity-40"
        >
          <RefreshCcw size={12} className={refreshMutation.isPending ? "animate-spin" : ""} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* ID card */}
      <IDCard data={data} />

      {/* KYC status banner */}
      {!kycVerified && (
        <div className={`rounded-xl border p-4 flex items-center justify-between gap-4 ${kycPending ? "border-yellow-400/25 bg-yellow-400/5" : "border-orange-500/25 bg-orange-500/5"}`}>
          <div className="flex items-center gap-3 min-w-0">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${kycPending ? "bg-yellow-400/10 border border-yellow-400/20" : "bg-orange-500/10 border border-orange-500/20"}`}>
              <ShieldCheck size={16} className={kycPending ? "text-yellow-400" : "text-orange-400"} />
            </div>
            <div className="min-w-0">
              <p className="font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wide text-white/80">
                {kycPending ? "KYC Under Review" : "Identity Not Verified"}
              </p>
              <p className="font-['Outfit'] text-xs text-white/35 mt-0.5 leading-relaxed">
                {kycPending
                  ? "Your submission is being processed."
                  : "Verify to unlock Verified tier and full features."}
              </p>
            </div>
          </div>
          {!kycPending && (
            <Link href="/kyc">
              <button className="shrink-0 flex items-center gap-1.5 rounded-lg bg-[#00E676] px-3 py-2 font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-black hover:bg-[#00c864] transition-colors">
                <ShieldCheck size={12} />
                Verify Now
              </button>
            </Link>
          )}
        </div>
      )}

      {/* DID info */}
      <Panel>
        <PanelHeader>
          <div className="flex items-center gap-2">
            <Globe size={14} className="text-[#00E676]" />
            <h3 className="font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wide text-white/70">
              Decentralized Identity (DID)
            </h3>
          </div>
        </PanelHeader>
        <div className="p-4">
          {data.did ? (
            <div className="flex items-center gap-2 rounded-lg bg-white/4 border border-white/6 p-3">
              <p className="font-['JetBrains_Mono'] text-[10px] text-white/40 break-all flex-1">{data.did}</p>
              <CopyButton value={data.did} />
            </div>
          ) : (
            <div className="text-center py-4">
              <Globe size={24} className="text-white/10 mx-auto mb-2" />
              <p className="font-['Outfit'] text-xs text-white/35">No DID registered yet.</p>
              <p className="font-['JetBrains_Mono'] text-[9px] text-white/20 mt-1 uppercase tracking-wider">
                Automatically created on identity verification
              </p>
            </div>
          )}
        </div>
      </Panel>

      {/* Identity Tiers */}
      <Panel>
        <PanelHeader>
          <h3 className="font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wide text-white/70">
            Identity Tiers
          </h3>
        </PanelHeader>
        <div className="p-3 space-y-2">
          {(Object.entries(TIER_CONFIG) as [keyof typeof TIER_CONFIG, typeof TIER_CONFIG["basic"]][]).map(([key, cfg], idx) => {
            const Icon = cfg.icon;
            const isActive = data.tier === key;
            const isPast = ["basic","standard","verified","elite"].indexOf(data.tier) >= ["basic","standard","verified","elite"].indexOf(key);
            return (
              <div
                key={key}
                className={`flex items-center gap-3 rounded-lg border px-3.5 py-3 transition-all ${
                  isActive
                    ? `${cfg.bg} ${cfg.border}`
                    : isPast
                    ? "border-white/6 bg-white/2"
                    : "border-white/4 bg-transparent"
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${isActive || isPast ? cfg.bg : "bg-white/3"} border ${isActive ? cfg.border : "border-white/6"}`}>
                  <Icon size={14} className={isActive || isPast ? cfg.color : "text-white/20"} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wide ${isActive || isPast ? cfg.color : "text-white/25"}`}>
                    {cfg.label}
                  </p>
                  <p className={`font-['Outfit'] text-[10px] mt-0.5 ${isActive || isPast ? "text-white/40" : "text-white/18"}`}>
                    {cfg.desc}
                  </p>
                </div>
                {isActive && (
                  <span className={`shrink-0 rounded-md border ${cfg.border} ${cfg.bg} px-2 py-0.5 font-['JetBrains_Mono'] text-[9px] font-bold uppercase tracking-wider ${cfg.color}`}>
                    Current
                  </span>
                )}
                {isPast && !isActive && (
                  <CheckCircle2 size={14} className={`shrink-0 ${cfg.color} opacity-60`} />
                )}
              </div>
            );
          })}
        </div>
      </Panel>

      {/* Security Checklist */}
      <Panel>
        <PanelHeader>
          <h3 className="font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wide text-white/70">
            Security Checklist
          </h3>
        </PanelHeader>
        <div className="p-3 space-y-2">
          {[
            { key: "email_verified", label: "Email Verified",      desc: "Confirmed your email address" },
            { key: "kyc_verified",   label: "Identity Verified",   desc: "KYC document check approved" },
            { key: "two_fa_enabled", label: "2FA Enabled",         desc: "Two-factor authentication active" },
          ].map(item => {
            const done = !!data.badges[item.key];
            return (
              <div key={item.key} className={`flex items-center gap-3 rounded-lg border px-3.5 py-2.5 ${done ? "border-[#00E676]/15 bg-[#00E676]/4" : "border-white/6 bg-white/2"}`}>
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${done ? "bg-[#00E676]/15 border border-[#00E676]/25" : "bg-white/4 border border-white/8"}`}>
                  <CheckCircle2 size={13} className={done ? "text-[#00E676]" : "text-white/20"} />
                </div>
                <div className="flex-1">
                  <p className={`font-['Outfit'] text-xs font-semibold ${done ? "text-white/75" : "text-white/35"}`}>{item.label}</p>
                  <p className={`font-['Outfit'] text-[10px] ${done ? "text-white/35" : "text-white/18"}`}>{item.desc}</p>
                </div>
                <span className={`font-['JetBrains_Mono'] text-[9px] uppercase tracking-wider ${done ? "text-[#00E676]" : "text-white/20"}`}>
                  {done ? "Done" : "—"}
                </span>
              </div>
            );
          })}
        </div>
      </Panel>

    </div>
  );
}
