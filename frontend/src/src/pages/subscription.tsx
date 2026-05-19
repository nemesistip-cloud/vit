import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Crown, Zap, Star, Check, Minus, ExternalLink, AlertCircle } from "lucide-react";
import { useLocation } from "wouter";
import { usePublicConfig } from "@/lib/usePublicConfig";

const PLAN_ICONS: Record<string, React.ElementType> = {
  free:      Star,
  analyst:   Zap,
  pro:       Zap,
  validator: Crown,
  elite:     Crown,
};

const PLAN_COLORS: Record<string, { border: string; glow: string; badge: string }> = {
  free:      { border: "border-muted",             glow: "",                               badge: "bg-muted text-muted-foreground"         },
  analyst:   { border: "border-blue-500/50",        glow: "shadow-blue-500/10 shadow-lg",   badge: "bg-blue-500/20 text-blue-400"           },
  pro:       { border: "border-primary/50",         glow: "shadow-primary/10 shadow-lg",    badge: "bg-primary/20 text-primary"             },
  validator: { border: "border-secondary/60",       glow: "shadow-secondary/10 shadow-lg",  badge: "bg-secondary/20 text-secondary"         },
  elite:     { border: "border-secondary/60",       glow: "shadow-secondary/10 shadow-lg",  badge: "bg-secondary/20 text-secondary"         },
};

// PLAN_ORDER and FEATURE_LABELS now come from /config/public via usePublicConfig().
// Local fallbacks below are used only on first paint while the config is loading.
const FALLBACK_PLAN_ORDER = ["free", "analyst", "pro", "validator", "elite"];
const FALLBACK_FEATURE_LABELS: Record<string, string> = {
  predictions:          "Match Predictions",
  basic_history:        "Prediction History",
  over_under:           "Over/Under Markets",
  btts:                 "BTTS & Asian Handicap",
  advanced_analytics:   "Advanced Analytics",
  ai_insights:          "Multi-Agent AI Insights",
  accumulator_builder:  "Accumulator Builder",
  model_breakdown:      "Model Breakdown",
  telegram_alerts:      "Telegram Alerts",
  bankroll_tools:       "Bankroll Tools",
  csv_upload:           "CSV Data Upload",
  priority_support:     "Priority Support",
  submit_predictions:   "Submit Predictions (influence consensus)",
  validator_rewards:    "Earn from Settlement Pool (40%)",
  governance_voting:    "Governance Voting",
};

interface Plan {
  name: string;
  display_name: string;
  price_monthly: number;
  price_yearly: number;
  features: Record<string, boolean>;
  description: string;
  limits: { predictions_per_day: number | null; history_rows: number | null };
}

export default function SubscriptionPage() {
  const qc = useQueryClient();
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [location] = useLocation();
  const { data: publicCfg } = usePublicConfig();
  const PLAN_ORDER = publicCfg?.plan_order ?? FALLBACK_PLAN_ORDER;
  const FEATURE_LABELS = publicCfg?.plan_feature_labels ?? FALLBACK_FEATURE_LABELS;

  const params = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
  const upgradedPlan = params.get("upgraded");
  const cancelledPlan = params.get("cancelled");

  const { data: plansData, isLoading: loadingPlans } = useQuery({
    queryKey: ["subscription-plans"],
    queryFn: () => apiGet<{ plans: Plan[] }>("/subscription/plans"),
  });

  const { data: myPlanData } = useQuery({
    queryKey: ["my-plan"],
    queryFn: () => apiGet<{ plan: Plan; subscription: unknown; usage: { predictions_today: number; limit_today: number | null } }>("/subscription/my-plan"),
  });

  const checkoutMutation = useMutation({
    mutationFn: ({ plan, billing }: { plan: string; billing: string }) =>
      apiPost<{ checkout_url: string; amount_usd: number }>("/subscription/create-checkout", { plan, billing }),
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
    onError: (err: any) => {
      const msg = err?.message || "Checkout failed. Please try again.";
      const display =
        !msg || msg.startsWith("{") || msg === "[object Object]"
          ? "Payment error. Please try again or contact support."
          : msg;
      setError(display);
      setUpgrading(null);
    },
  });

  const handleUpgrade = (plan: string) => {
    setUpgrading(plan);
    setMessage("");
    setError("");
    checkoutMutation.mutate({ plan, billing });
  };

  const plans = plansData?.plans || [];
  const currentPlan = myPlanData?.plan?.name || "free";
  const usage = myPlanData?.usage;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-mono font-bold uppercase tracking-tight">Subscription Plans</h1>
        <p className="text-muted-foreground font-mono text-sm">Unlock the full power of VIT Sports Intelligence.</p>
      </div>

      {upgradedPlan && (
        <div className="p-4 rounded-lg border border-primary/40 bg-primary/10 text-primary font-mono text-sm flex items-center gap-2">
          <Check className="w-4 h-4 flex-shrink-0" />
          Payment received! Your {upgradedPlan} plan is being activated. It may take a moment to update.
        </div>
      )}
      {cancelledPlan && (
        <div className="p-3 rounded-lg border border-border bg-card/50 text-muted-foreground font-mono text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          Checkout cancelled. Your current plan is unchanged.
        </div>
      )}

      {usage && (
        <div className="flex flex-wrap gap-4 p-4 bg-card/50 border border-border rounded-lg font-mono text-sm">
          <span className="text-muted-foreground">Current plan: <span className="text-primary font-bold uppercase">{currentPlan}</span></span>
          <span className="text-muted-foreground">Today: <span className="text-foreground font-bold">{usage.predictions_today}/{usage.limit_today ?? "∞"} predictions</span></span>
        </div>
      )}

      {/* Billing toggle */}
      <div className="flex items-center justify-center gap-3 font-mono text-sm">
        <button
          className={`px-4 py-1.5 rounded-full border transition-colors ${billing === "monthly" ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-primary/50"}`}
          onClick={() => setBilling("monthly")}
        >
          Monthly
        </button>
        <button
          className={`px-4 py-1.5 rounded-full border transition-colors ${billing === "yearly" ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-primary/50"}`}
          onClick={() => setBilling("yearly")}
        >
          Yearly <span className="text-xs text-green-400 ml-1">Save 25%</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg border border-red-500/40 bg-red-900/20 text-red-400 font-mono text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-bold mb-1">Payment Error</p>
            <p>{error}</p>
            {error.includes("not configured") || error.includes("configuration") ? (
              <p className="mt-2 text-xs text-red-300">Admin: Set STRIPE_SECRET_KEY (format: sk_test_... or sk_live_...) in Replit Secrets.</p>
            ) : null}
          </div>
        </div>
      )}
      {message && (
        <div className="p-3 rounded-lg border border-primary/40 bg-primary/10 text-primary font-mono text-sm">
          ✓ {message}
        </div>
      )}

      {loadingPlans ? (
        <div className="text-muted-foreground font-mono text-center py-12">Loading plans...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {plans.map((plan) => {
            const colors = PLAN_COLORS[plan.name] || PLAN_COLORS.free;
            const Icon = PLAN_ICONS[plan.name] || Star;
            const isCurrent = currentPlan === plan.name;
            const isUpgrade = PLAN_ORDER.indexOf(plan.name) > PLAN_ORDER.indexOf(currentPlan);

            return (
              <Card
                key={plan.name}
                className={`bg-card/50 backdrop-blur flex flex-col relative ${colors.border} ${colors.glow} ${isCurrent ? "ring-1 ring-primary/40" : ""}`}
              >
                {isCurrent && (
                  <div className="absolute -top-3 right-4">
                    <Badge className="bg-primary text-primary-foreground font-mono text-xs">ACTIVE PLAN</Badge>
                  </div>
                )}
                {plan.name === "pro" && !isCurrent && (
                  <div className="absolute -top-3 right-4">
                    <Badge className="bg-blue-500 text-white font-mono text-xs">MOST POPULAR</Badge>
                  </div>
                )}

                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className={`w-5 h-5 ${
                      plan.name === "validator" || plan.name === "elite" ? "text-secondary"
                      : plan.name === "pro" ? "text-primary"
                      : plan.name === "analyst" ? "text-blue-400"
                      : "text-muted-foreground"
                    }`} />
                    <CardTitle className="font-mono font-bold uppercase tracking-wider">{plan.display_name}</CardTitle>
                  </div>
                  <p className="text-muted-foreground font-mono text-xs">{plan.description}</p>
                </CardHeader>

                <CardContent className="flex-1 space-y-4">
                  <div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-bold font-mono">
                        {plan.price_monthly === 0
                          ? "Free"
                          : billing === "yearly"
                          ? `$${plan.price_yearly}`
                          : `$${plan.price_monthly}`}
                      </span>
                      {plan.price_monthly > 0 && (
                        <span className="text-muted-foreground text-sm font-mono">/{billing === "yearly" ? "yr" : "mo"}</span>
                      )}
                    </div>
                    {plan.price_monthly > 0 && billing === "monthly" && (
                      <p className="text-xs text-muted-foreground font-mono mt-1">
                        or ${plan.price_yearly}/yr (save {Math.round((1 - plan.price_yearly / (plan.price_monthly * 12)) * 100)}%)
                      </p>
                    )}
                    {plan.price_monthly > 0 && billing === "yearly" && (
                      <p className="text-xs text-green-400 font-mono mt-1">
                        Save ${((plan.price_monthly * 12) - plan.price_yearly).toFixed(2)} vs monthly
                      </p>
                    )}
                  </div>

                  <div className="rounded-md bg-background/50 p-2 text-xs font-mono">
                    {plan.limits.predictions_per_day != null
                      ? <span className="text-muted-foreground">{plan.limits.predictions_per_day} predictions/day</span>
                      : <span className="text-primary">∞ Unlimited predictions</span>
                    }
                  </div>

                  <div className="space-y-1.5">
                    {Object.entries(FEATURE_LABELS).map(([key, label]) => {
                      const included = plan.features?.[key];
                      return (
                        <div key={key} className="flex items-center gap-2 text-xs font-mono">
                          {included
                            ? <Check className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                            : <Minus className="w-3.5 h-3.5 text-muted-foreground/30 flex-shrink-0" />
                          }
                          <span className={included ? "text-foreground" : "text-muted-foreground/50"}>{label}</span>
                        </div>
                      );
                    })}
                  </div>

                  <div className="pt-2">
                    {isCurrent ? (
                      <div className="text-center py-2 text-xs font-mono text-primary border border-primary/30 rounded-md">
                        ✓ Your current plan
                      </div>
                    ) : isUpgrade ? (
                      <Button
                        className="w-full font-mono text-xs gap-1.5"
                        variant={plan.name === "validator" || plan.name === "elite" ? "secondary" : "default"}
                        onClick={() => handleUpgrade(plan.name)}
                        disabled={upgrading === plan.name || checkoutMutation.isPending}
                      >
                        <ExternalLink className="w-3 h-3" />
                        {upgrading === plan.name ? "Redirecting to payment..." : `Upgrade to ${plan.display_name}`}
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <div className="p-4 rounded-lg bg-card/30 border border-secondary/20 font-mono text-xs text-muted-foreground space-y-1">
        <div><span className="text-secondary font-bold">PAYMENT:</span> Secured by Stripe. You'll be redirected to Stripe's hosted checkout page to complete your payment securely.</div>
        <div className="text-muted-foreground/60">Cards accepted: Visa, Mastercard, Amex, and more. Cancel anytime.</div>
      </div>
    </div>
  );
}
