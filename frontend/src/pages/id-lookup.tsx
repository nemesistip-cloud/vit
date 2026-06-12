import { useState, useEffect, FormEvent } from "react";
import { useParams, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Fingerprint, ShieldCheck, BadgeCheck, User, Globe,
  Lock, Zap, Star, Crown, Search, Copy, Check,
  ExternalLink, AlertTriangle, XCircle, ChevronRight,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────

interface PublicIDCard {
  sid:             string;
  display_name:    string;
  tier:            "basic" | "standard" | "verified" | "elite";
  avatar_initials: string;
  did:             string | null;
  badges:          Record<string, boolean>;
  issued_at:       string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const TIER_CONFIG = {
  basic:    { label: "Basic",    color: "text-zinc-400",    bg: "bg-zinc-500/10",   border: "border-zinc-700",         icon: User,        gradient: "from-zinc-800 to-zinc-900" },
  standard: { label: "Standard", color: "text-blue-400",    bg: "bg-blue-500/10",   border: "border-blue-500/30",      icon: ShieldCheck, gradient: "from-blue-950 to-zinc-900" },
  verified: { label: "Verified", color: "text-emerald-400", bg: "bg-emerald-500/10",border: "border-emerald-500/30",   icon: BadgeCheck,  gradient: "from-emerald-950 to-zinc-900" },
  elite:    { label: "Elite",    color: "text-amber-400",   bg: "bg-amber-500/10",  border: "border-amber-500/30",     icon: Crown,       gradient: "from-amber-950 to-zinc-900" },
};

const BADGE_CONFIG: Record<string, { label: string; icon: typeof ShieldCheck; color: string }> = {
  email_verified: { label: "Email Verified",  icon: BadgeCheck,  color: "text-blue-400"    },
  kyc_verified:   { label: "KYC Verified",    icon: ShieldCheck, color: "text-emerald-400" },
  two_fa_enabled: { label: "2FA Active",      icon: Lock,        color: "text-purple-400"  },
  validator:      { label: "Validator",       icon: Zap,         color: "text-yellow-400"  },
  admin:          { label: "Admin",           icon: Star,        color: "text-red-400"     },
  pro_subscriber: { label: "Pro Subscriber",  icon: Crown,       color: "text-amber-400"   },
};

const SID_REGEX = /^VIT-\d{4}-[A-Z0-9]{6}$/i;

// ── Helpers ────────────────────────────────────────────────────────────────

function normaliseSid(raw: string): string {
  return raw.trim().toUpperCase();
}

async function fetchPublicCard(sid: string): Promise<PublicIDCard> {
  const res = await fetch(`/api/identity/${encodeURIComponent(sid)}`);
  if (res.status === 404) throw new Error("ID not found");
  if (res.status === 410) throw new Error("ID has been revoked");
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? "Lookup failed");
  }
  return res.json();
}

// ── Sub-components ─────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <div className="max-w-md w-full mx-auto space-y-4 animate-pulse">
      <div className="h-64 rounded-2xl bg-muted/40" />
      <div className="space-y-2">
        <div className="h-3 w-40 rounded bg-muted/40" />
        <div className="h-5 w-full rounded bg-muted/40" />
        <div className="h-5 w-2/3 rounded bg-muted/40" />
      </div>
    </div>
  );
}

function IDCard({ card }: { card: PublicIDCard }) {
  const [copied, setCopied] = useState(false);
  const tier = TIER_CONFIG[card.tier] ?? TIER_CONFIG.basic;
  const TierIcon = tier.icon;

  const shareUrl = `${window.location.origin}/id/${card.sid}`;
  function copyLink() {
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const activeBadges = Object.entries(card.badges).filter(([, v]) => v);

  return (
    <div className="max-w-md w-full mx-auto space-y-4">
      {/* Card */}
      <div className={`relative rounded-2xl border ${tier.border} overflow-hidden bg-gradient-to-br ${tier.gradient} p-px`}>
        <div className="rounded-2xl bg-card/90  p-6 space-y-5">

          {/* Header */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className={`w-14 h-14 rounded-xl ${tier.bg} border ${tier.border} flex items-center justify-center flex-shrink-0`}>
                <span className={`font-bold text-xl ${tier.color}`}>{card.avatar_initials}</span>
              </div>
              <div>
                <p className="font-bold text-foreground text-lg leading-tight">{card.display_name}</p>
                <p className="text-xs text-muted-foreground font-mono mt-0.5">VIT Network Member</p>
              </div>
            </div>
            <Badge variant="outline" className={`${tier.color} ${tier.bg} border-0 gap-1 shrink-0 mt-1`}>
              <TierIcon className="w-3 h-3" />
              {tier.label}
            </Badge>
          </div>

          {/* SID */}
          <div className="space-y-1">
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-mono">System ID</p>
            <div className="flex items-center gap-2">
              <span className="font-mono text-2xl font-bold tracking-wider text-foreground">{card.sid}</span>
              <Fingerprint className={`w-5 h-5 ${tier.color} flex-shrink-0`} />
            </div>
          </div>

          {/* DID */}
          {card.did && (
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-mono">Decentralized ID</p>
              <p className="font-mono text-xs text-muted-foreground break-all">{card.did}</p>
            </div>
          )}

          {/* Badges */}
          {activeBadges.length > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-mono">Verified Credentials</p>
              <div className="flex flex-wrap gap-2">
                {activeBadges.map(([key]) => {
                  const cfg = BADGE_CONFIG[key];
                  if (!cfg) return null;
                  const Icon = cfg.icon;
                  return (
                    <div key={key} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-muted/30 border border-border text-xs font-mono ${cfg.color}`}>
                      <Icon className="w-3 h-3" />
                      {cfg.label}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-3 border-t border-border/50">
            <div>
              <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wide">Issued</p>
              <p className="font-mono text-xs text-foreground">
                {new Date(card.issued_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-mono">
              <Globe className="w-3 h-3" />
              VIT NETWORK
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Button variant="outline" size="sm" className="gap-2 flex-1 font-mono text-xs" onClick={copyLink}>
          {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied!" : "Copy Link"}
        </Button>
        <Button variant="outline" size="sm" className="gap-2 font-mono text-xs" asChild>
          <a href={shareUrl} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="w-3.5 h-3.5" />
            Open
          </a>
        </Button>
      </div>

      {/* Tier legend */}
      <div className="rounded-xl border border-border bg-muted/10 p-4 space-y-2">
        <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-3">Identity Tier Levels</p>
        {(Object.entries(TIER_CONFIG) as [keyof typeof TIER_CONFIG, typeof TIER_CONFIG["basic"]][]).map(([key, cfg]) => {
          const Icon = cfg.icon;
          const isActive = card.tier === key;
          return (
            <div key={key} className={`flex items-center gap-3 rounded-lg px-3 py-2 ${isActive ? `${cfg.bg} border ${cfg.border}` : "opacity-40"}`}>
              <Icon className={`w-4 h-4 ${cfg.color}`} />
              <span className={`text-xs font-mono font-medium ${cfg.color}`}>{cfg.label}</span>
              {isActive && (
                <Badge variant="outline" className={`text-[10px] ml-auto ${cfg.color} border-0 ${cfg.bg}`}>
                  This ID
                </Badge>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  const isRevoked = message.includes("revoked");
  const isNotFound = message.includes("not found");
  const Icon = isRevoked ? XCircle : isNotFound ? AlertTriangle : AlertTriangle;
  const color = isRevoked ? "text-red-400" : "text-amber-400";
  const borderColor = isRevoked ? "border-red-500/30 bg-red-500/5" : "border-amber-500/30 bg-amber-500/5";

  return (
    <div className={`max-w-md w-full mx-auto rounded-2xl border ${borderColor} p-6 flex flex-col items-center gap-3 text-center`}>
      <Icon className={`w-10 h-10 ${color}`} />
      <div>
        <p className={`font-bold text-base ${color}`}>
          {isRevoked ? "Identity Revoked" : isNotFound ? "ID Not Found" : "Lookup Failed"}
        </p>
        <p className="text-sm text-muted-foreground mt-1">{message}</p>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function IDLookupPage() {
  const params = useParams<{ sid?: string }>();
  const [, navigate] = useLocation();

  // The SID can come from the URL param or the search input
  const urlSid = params?.sid ? normaliseSid(params.sid) : "";
  const [input, setInput] = useState(urlSid);
  const [activeSid, setActiveSid] = useState(urlSid);

  // Keep input in sync if user navigates directly to /id/VIT-…
  useEffect(() => {
    if (urlSid) {
      setInput(urlSid);
      setActiveSid(urlSid);
    }
  }, [urlSid]);

  const validInput = SID_REGEX.test(normaliseSid(input));
  const shouldFetch = SID_REGEX.test(activeSid);

  const { data, isLoading, error, isFetching } = useQuery<PublicIDCard>({
    queryKey: ["public-id", activeSid],
    queryFn: () => fetchPublicCard(activeSid),
    enabled: shouldFetch,
    retry: false,
    staleTime: 30_000,
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const sid = normaliseSid(input);
    if (!SID_REGEX.test(sid)) return;
    setActiveSid(sid);
    navigate(`/id/${sid}`, { replace: true });
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top bar */}
      <header className="border-b border-border/50 bg-card/60 ">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2 group">
            <Fingerprint className="w-5 h-5 text-primary" />
            <span className="font-mono font-bold text-sm tracking-tight">VIT_ID</span>
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground transition-colors" />
            <span className="font-mono text-xs text-muted-foreground">Resolver</span>
          </a>
          <a href="/login" className="text-xs font-mono text-muted-foreground hover:text-foreground transition-colors">
            Sign in
          </a>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 flex flex-col items-center px-4 py-10 gap-8">

        {/* Hero */}
        <div className="text-center space-y-2 max-w-md">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-mono mb-2">
            <Globe className="w-3 h-3" />
            Public Identity Resolver
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">
            VIT System ID Lookup
          </h1>
          <p className="text-sm text-muted-foreground">
            Paste any <span className="font-mono text-foreground">VIT-YYYY-XXXXXX</span> code to view a user's public identity card and verified credential claims.
          </p>
        </div>

        {/* Search form */}
        <form onSubmit={handleSubmit} className="w-full max-w-md">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value.toUpperCase())}
                placeholder="VIT-2025-A3F9K1"
                className="pl-9 font-mono tracking-wider uppercase placeholder:normal-case"
                maxLength={16}
                autoCorrect="off"
                autoCapitalize="characters"
                spellCheck={false}
                aria-label="VIT System ID"
              />
            </div>
            <Button type="submit" disabled={!validInput || isFetching} className="font-mono shrink-0">
              {isFetching ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                  Looking up…
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <Search className="w-3.5 h-3.5" />
                  Look Up
                </span>
              )}
            </Button>
          </div>
          {input.length > 0 && !validInput && (
            <p className="text-xs text-amber-400 font-mono mt-1.5 px-1">
              Format must be VIT-YYYY-XXXXXX (e.g. VIT-2025-A3F9K1)
            </p>
          )}
        </form>

        {/* Results */}
        {isLoading && <CardSkeleton />}
        {!isLoading && error && <ErrorCard message={(error as Error).message} />}
        {!isLoading && !error && data && <IDCard card={data} />}

        {/* Empty state hint */}
        {!activeSid && (
          <div className="max-w-md w-full text-center space-y-3 mt-2">
            <div className="rounded-xl border border-border/50 bg-muted/10 p-6 space-y-3">
              <Fingerprint className="w-8 h-8 text-muted-foreground/40 mx-auto" />
              <p className="text-sm text-muted-foreground">
                Enter a VIT System ID above to resolve a public identity card.
              </p>
              <p className="text-xs text-muted-foreground/60 font-mono">
                System IDs are issued to all VIT Network members. They are publicly resolvable but contain no private information.
              </p>
            </div>

            {/* Tier breakdown */}
            <div className="rounded-xl border border-border/50 bg-muted/10 p-4 text-left space-y-2">
              <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-2">What the tiers mean</p>
              {(Object.entries(TIER_CONFIG) as [keyof typeof TIER_CONFIG, typeof TIER_CONFIG["basic"]][]).map(([key, cfg]) => {
                const Icon = cfg.icon;
                const desc: Record<string, string> = {
                  basic:    "Email confirmed. Entry-level platform member.",
                  standard: "Identity verification submitted and under review.",
                  verified: "Full KYC approved. Identity confirmed.",
                  elite:    "KYC verified + Pro/Elite subscriber or Admin/Validator.",
                };
                return (
                  <div key={key} className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${cfg.color} flex-shrink-0`} />
                    <div>
                      <span className={`text-xs font-mono font-semibold ${cfg.color}`}>{cfg.label}</span>
                      <span className="text-xs text-muted-foreground ml-2">{desc[key]}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/30 bg-card/30 py-4">
        <p className="text-center text-[10px] font-mono text-muted-foreground/50 tracking-wide">
          VIT SPORTS INTELLIGENCE NETWORK · PUBLIC ID RESOLVER · NO AUTHENTICATION REQUIRED
        </p>
      </footer>
    </div>
  );
}
