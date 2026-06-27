import { useState, useEffect } from "react";
import { Link } from "wouter";
import {
  Zap, TrendingUp, Shield, BarChart2, Brain,
  ArrowRight, Check, Star, ChevronRight, Activity,
  Coins, Network, Target, LineChart, Fingerprint,
  Cpu, ChevronDown, ChevronUp, Vote, Scale, Wallet,
  Sparkles, Globe, BookOpen
} from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { usePublicConfig } from "@/lib/usePublicConfig";

type LandingTickerItem = { match: string; edge: string; outcome: string; confidence: number };
type LandingTestimonial = { user: string; role: string; stars: number; text: string };
type LandingPlan = { name: string; price: string; period: string; desc: string; features: string[]; cta: string; highlight: boolean };
type LandingModel = { name: string; confidence: number; weight: number; ready: boolean; trained_count: number };
type LandingData = {
  stats: {
    predictions_display: string;
    accuracy_display: string;
    total_staked_display: string;
    ai_models: number;
    ai_models_ready: number;
  };
  ticker: LandingTickerItem[];
  testimonials: LandingTestimonial[];
  model_consensus: { models: LandingModel[]; average_confidence: number };
  plans: LandingPlan[];
};

const buildFeatures = (modelCount: number) => [
  {
    icon: Brain, title: "VIT Brain AI Ensemble",
    desc: `A ${modelCount}-model ensemble with calibrated weights, domain-specific fine-tuning, and VIT Memory (RAG) for maximum signal precision.`,
    color: "text-primary", bg: "bg-primary/10 border-primary/20", tag: "CORE ANALYTICS",
  },
  {
    icon: Vote, title: "Elections",
    desc: "Real-time sentiment analytics and outcome prediction for global elections using on-chain data and the VIT Nerve orchestrator.",
    color: "text-cyan-400", bg: "bg-cyan-500/10 border-cyan-500/20", tag: "APP",
  },
  {
    icon: Scale, title: "Policy & Governance",
    desc: "Predictive modeling for legislative changes and policy impacts with high-fidelity analytics for professional decision-making.",
    color: "text-teal-400", bg: "bg-teal-500/10 border-teal-500/20", tag: "APP",
  },
  {
    icon: Wallet, title: "DeFi & Remittance",
    desc: "Low-cost cross-border remittance, staking rewards for validators, and a transparent on-chain treasury powered by VITCoin.",
    color: "text-secondary", bg: "bg-secondary/10 border-secondary/20", tag: "FINANCE",
  },
  {
    icon: Shield, title: "Blockchain-Verified Analytics",
    desc: "All signals and results are anchored on-chain and verified by a decentralized validator network. Zero manipulation.",
    color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20", tag: "TRUST",
  },
  {
    icon: Network, title: "Autonomous Agent Network",
    desc: "Match trackers, news sentinels, and sentiment crawlers running 24/7. Autonomous agents feed VIT Brain continuously.",
    color: "text-rose-400", bg: "bg-rose-500/10 border-rose-500/20", tag: "NETWORK",
  },
  {
    icon: BarChart2, title: "Kelly & Risk Management",
    desc: "Full Kelly criterion calculator, fractional staking, and automated bankroll management for sustainable long-term results.",
    color: "text-green-400", bg: "bg-green-500/10 border-green-500/20", tag: "RISK",
  },
  {
    icon: LineChart, title: "Quant Research Terminal",
    desc: "Walk-forward backtesting, Monte Carlo simulations, and strategy optimization for sports, elections, and financial markets.",
    color: "text-indigo-400", bg: "bg-indigo-500/10 border-indigo-500/20", tag: "RESEARCH",
  },
];

const CAPABILITY_PILLS = [
  { label: "VIT Intelligence Engine", color: "text-primary border-primary/30 bg-primary/8"       },
  { label: "VIT Memory (RAG)",        color: "text-teal-400 border-teal-400/30 bg-teal-400/8"    },
  { label: "VIT Autonomous Network",  color: "text-cyan-400 border-cyan-400/30 bg-cyan-400/8"    },
  { label: "Elections",               color: "text-purple-400 border-purple-400/30 bg-purple-400/8" },
  { label: "Policy Sentiment",        color: "text-indigo-400 border-indigo-400/30 bg-indigo-400/8" },
  { label: "VITCoin Economy",         color: "text-green-400 border-green-400/30 bg-green-400/8"  },
  { label: "On-Chain Verification",   color: "text-amber-400 border-amber-400/30 bg-amber-400/8"  },
  { label: "Finance & Transfers",     color: "text-secondary border-secondary/30 bg-secondary/8"  },
  { label: "VIT Identity",            color: "text-slate-400 border-slate-400/30 bg-slate-400/8"  },
  { label: "Signal Marketplace",      color: "text-yellow-400 border-yellow-400/30 bg-yellow-400/8" },
];

function TickerTape({ items }: { items: LandingTickerItem[] }) {
  if (items.length === 0) return null;
  const doubled = [...items, ...items];
  return (
    <div className="border-y border-border/50 py-2.5 bg-card/30 vit-ticker-wrap">
      <div className="vit-ticker-content gap-0">
        {doubled.map((item, i) => (
          <span key={i} className="inline-flex items-center gap-2 text-xs font-mono mr-10 flex-shrink-0 px-2">
            <span className="text-muted-foreground">{item.match}</span>
            <span className="text-primary font-medium">{item.edge}</span>
            <span className="text-muted-foreground/60">AI:{item.confidence}%</span>
            <span className={
              item.outcome === "WIN" ? "font-bold text-emerald-400" :
              item.outcome === "LOSS" ? "font-bold text-rose-400" :
              "text-muted-foreground"
            }>
              {item.outcome}
            </span>
            <span className="text-border/60">·</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function StatCounter({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-3xl md:text-4xl font-bold font-mono vit-gradient-text">{value}</div>
      <div className="text-xs text-muted-foreground font-mono mt-1 uppercase tracking-wider">{label}</div>
    </div>
  );
}

export default function LandingPage() {
  const [activeTestimonial, setActiveTestimonial] = useState(0);
  const [showAllFeatures, setShowAllFeatures] = useState(false);

  const { data } = useQuery<LandingData>({
    queryKey: ["public-landing"],
    queryFn: () => apiGet("/api/public/landing"),
  });
  const { data: publicCfg } = usePublicConfig();
  const modelCount   = publicCfg?.platform.model_count       ?? 13;
  const welcomeBonus = publicCfg?.platform.welcome_bonus_vit ?? 100;
  const FEATURES     = buildFeatures(modelCount);
  const visibleFeatures = showAllFeatures ? FEATURES : FEATURES.slice(0, 6);

  const stats         = data?.stats;
  const testimonials  = data?.testimonials ?? [];
  const plans         = data?.plans ?? [];
  const consensusModels = data?.model_consensus?.models ?? [];

  useEffect(() => {
    if (testimonials.length === 0) return;
    const interval = setInterval(() => {
      setActiveTestimonial((prev) => (prev + 1) % testimonials.length);
    }, 6000);
    return () => clearInterval(interval);
  }, [testimonials]);

  return (
    <div className="vit-page-container">

      {/* ── Navbar ── */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/40 bg-background/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
          <BrandLogo withWordmark size={28} />
          <div className="hidden md:flex items-center gap-8 text-[11px] font-mono tracking-[0.15em] uppercase text-muted-foreground">
            <a href="#features" className="hover:text-primary transition-colors">Analytics</a>
            <a href="#ai"       className="hover:text-primary transition-colors">VIT Brain</a>
            <a href="#pricing"  className="hover:text-primary transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" className="font-mono text-[11px] uppercase tracking-widest h-9">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="font-mono text-[11px] uppercase tracking-widest h-9 px-5">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative pt-36 pb-28 px-4 md:px-8 overflow-hidden">
        {/* Background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-20 left-1/4 w-[200px] h-[200px] bg-violet-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center relative">
          <Badge
            variant="outline"
            className="mb-8 font-mono py-1.5 px-4 text-[10px] tracking-[0.3em] uppercase border-primary/25 bg-primary/6 text-primary"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse inline-block mr-2" />
            {publicCfg?.platform.version || 'v5.5.0'} — Intelligence Operating System
          </Badge>

          <h1 className="text-5xl sm:text-7xl md:text-9xl font-bold font-display uppercase tracking-tighter mb-6 leading-[0.88] text-foreground">
            VIT{" "}
            <span className="text-primary">Network</span>
          </h1>

          <p className="text-muted-foreground text-base md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            The unified intelligence layer for{" "}
            <span className="text-foreground font-semibold">Sports</span>,{" "}
            <span className="text-foreground font-semibold">Elections</span>,{" "}
            <span className="text-foreground font-semibold">Policy</span>,{" "}
            <span className="text-foreground font-semibold">Finance</span>, and{" "}
            <span className="text-foreground font-semibold">Identity</span>.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/register">
              <Button size="lg" className="font-mono gap-2 px-8 h-12 text-sm w-full sm:w-auto">
                Access the Network
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <a href="#signals">
              <Button size="lg" variant="outline" className="font-mono px-8 h-12 text-sm bg-transparent border-border/60 hover:border-border w-full sm:w-auto">
                View Live Signals
              </Button>
            </a>
          </div>

          <div className="mt-14 flex flex-wrap justify-center gap-2 max-w-3xl mx-auto">
            {CAPABILITY_PILLS.map((pill) => (
              <span
                key={pill.label}
                className={`px-3 py-1 rounded-full border text-[10px] font-mono uppercase tracking-wider ${pill.color}`}
              >
                {pill.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Ticker ── */}
      <section id="signals">
        <TickerTape items={data?.ticker ?? []} />
      </section>

      {/* ── Stats ── */}
      <section className="py-16 border-b border-border/40">
        <div className="max-w-5xl mx-auto px-4 md:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <StatCounter value={stats?.predictions_display ?? "—"} label="Signals Generated" />
            <StatCounter value={stats?.accuracy_display ?? "—"}    label="Signal Accuracy"   />
            <StatCounter value={stats?.total_staked_display ?? "—"} label="Total Staked"     />
            <StatCounter value={`${modelCount}`}                        label="AI Models Active"  />
          </div>
        </div>
      </section>

      {/* ── Features Grid ── */}
      <section id="features" className="py-20 px-4 md:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-14">
            <p className="text-xs font-mono text-primary uppercase tracking-[0.3em] mb-3">Platform</p>
            <h2 className="text-3xl md:text-4xl font-bold font-mono mb-3 tracking-tight">The VIT Stack</h2>
            <p className="text-muted-foreground max-w-xl mx-auto text-sm leading-relaxed">
              A multi-layered analytics ecosystem combining local AI reasoning with blockchain-enforced integrity.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {visibleFeatures.map((f) => (
              <div
                key={f.title}
                className="group p-5 rounded-2xl border border-border/60 bg-card/40 hover:bg-card hover:border-primary/25 transition-all duration-300 hover:-translate-y-0.5"
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-5 border transition-transform group-hover:scale-105 ${f.bg}`}>
                  <f.icon className={`w-5 h-5 ${f.color}`} />
                </div>
                <div className="text-[9px] font-mono text-muted-foreground tracking-[0.2em] uppercase mb-2">{f.tag}</div>
                <h3 className="text-sm font-bold font-mono mb-2 text-foreground">{f.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-10 text-center">
            <Button
              variant="ghost"
              className="font-mono text-xs uppercase tracking-widest gap-2 text-muted-foreground hover:text-foreground"
              onClick={() => setShowAllFeatures(!showAllFeatures)}
            >
              {showAllFeatures ? "Show Less" : "View Full Stack"}
              {showAllFeatures ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </Button>
          </div>
        </div>
      </section>

      {/* ── AI Deep Dive ── */}
      <section id="ai" className="py-20 px-4 md:px-8 bg-primary/4 border-y border-primary/10 overflow-hidden relative">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full -translate-y-1/2 translate-x-1/4 blur-3xl pointer-events-none" />

        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-14 items-center">
          {/* Left: copy */}
          <div>
            <Badge className="mb-5 bg-primary/10 text-primary border-primary/20 font-mono text-[10px] tracking-widest">
              INTERNAL ARCHITECTURE
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold font-mono tracking-tight mb-5">
              VIT Brain:<br />Local AI Reasoning
            </h2>
            <p className="text-muted-foreground mb-7 leading-relaxed text-sm">
              Unlike platforms that rely on centralized LLM APIs, VIT runs an internal private AI stack.
              Our <strong className="text-foreground">VIT Nerve</strong> orchestrator coordinates{" "}
              <strong className="text-foreground">VIT Brain</strong> (Local Mistral) and{" "}
              <strong className="text-foreground">VIT Memory</strong> (Persistent RAG) so your analytics never leaves the network.
            </p>
            <ul className="space-y-3 mb-8">
              {[
                "Local inference for total data privacy",
                "Domain-specific fine-tuning for high accuracy",
                `Real-time RAG updates from ${modelCount} live agents`,
                "On-chain verification for every model output",
              ].map((item) => (
                <li key={item} className="flex items-center gap-3 text-sm font-mono text-muted-foreground">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
            <Link href="/register">
              <Button className="font-mono gap-2 h-10 px-5 text-sm">
                View Model Leaderboard <ChevronRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>

          {/* Right: live model panel */}
          <div className="relative">
            <div className="absolute -inset-px bg-gradient-to-r from-primary/20 to-teal-400/10 rounded-2xl blur-sm" />
            <div className="relative rounded-2xl border border-border/80 bg-background p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2.5">
                  <Cpu className="w-4 h-4 text-primary" />
                  <span className="font-mono text-xs font-bold uppercase tracking-wider">Model Status</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider">Live</span>
                </div>
              </div>

              <div className="space-y-5">
                {consensusModels.length === 0
                  ? Array.from({ length: 4 }).map((_, i) => (
                      <div key={i} className="space-y-2 opacity-40">
                        <div className="h-3 bg-muted rounded w-1/3 animate-pulse" />
                        <div className="h-1.5 bg-muted rounded-full" />
                      </div>
                    ))
                  : consensusModels.slice(0, 5).map((m) => (
                      <div key={m.name} className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono text-foreground">{m.name}</span>
                          <span className="text-xs font-mono text-primary font-bold">{m.confidence.toFixed(1)}%</span>
                        </div>
                        <div className="h-1 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{
                              width: `${Math.min(100, Math.max(0, m.confidence))}%`,
                              background: "linear-gradient(90deg, hsl(var(--primary)) 0%, #00F5C8 100%)",
                            }}
                          />
                        </div>
                      </div>
                    ))
                }

                <div className="pt-4 border-t border-border flex items-center justify-between">
                  <div>
                    <p className="text-xs font-mono text-muted-foreground">Ensemble Avg</p>
                    <p className="text-[10px] font-mono text-muted-foreground/50 mt-0.5">Range: 62–88%</p>
                  </div>
                  <span className="text-2xl font-bold font-mono text-primary">
                    {(data?.model_consensus?.average_confidence ?? 0).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Testimonials ── */}
      <section className="py-20 px-4 md:px-8">
        <div className="max-w-2xl mx-auto text-center">
          <p className="text-xs font-mono text-primary uppercase tracking-[0.3em] mb-3">Reviews</p>
          <h2 className="text-2xl md:text-3xl font-bold font-mono mb-10">Trusted Analytics</h2>

          <div className="relative min-h-[160px]">
            {testimonials.length === 0 ? (
              <div className="rounded-xl border border-border bg-card/40 p-8 text-sm font-mono text-muted-foreground">
                Verified network reviews will appear here after users rate live agents.
              </div>
            ) : (
              testimonials.map((t, i) => (
                <div
                  key={i}
                  className={`absolute inset-0 transition-all duration-500 ${
                    i === activeTestimonial ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3 pointer-events-none"
                  }`}
                >
                  <div className="flex justify-center mb-3 gap-0.5">
                    {Array.from({ length: t.stars }).map((_, s) => (
                      <Star key={s} className="w-3.5 h-3.5 text-secondary fill-secondary" />
                    ))}
                  </div>
                  <blockquote className="text-base text-foreground mb-4 leading-relaxed">
                    "{t.text}"
                  </blockquote>
                  <div className="text-sm font-mono">
                    <span className="text-primary">{t.user}</span>
                    <span className="text-muted-foreground"> · {t.role}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {testimonials.length > 1 && (
            <div className="flex justify-center gap-1.5 mt-6">
              {testimonials.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveTestimonial(i)}
                  className={`h-1.5 rounded-full transition-all duration-200 ${
                    i === activeTestimonial ? "bg-primary w-5" : "bg-muted-foreground/30 w-1.5"
                  }`}
                  aria-label={`Testimonial ${i + 1}`}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="py-20 px-4 md:px-8 bg-card/20 border-y border-border/40">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-xs font-mono text-primary uppercase tracking-[0.3em] mb-3">Pricing</p>
            <h2 className="text-2xl md:text-3xl font-bold font-mono mb-3">Transparent Tiers</h2>
            <p className="text-muted-foreground text-sm">Start free. Upgrade when you're ready to scale.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-2xl border p-5 flex flex-col transition-all duration-200 hover:-translate-y-0.5 ${
                  plan.highlight
                    ? "border-primary/40 bg-primary/5 shadow-lg shadow-primary/5"
                    : "border-border/60 bg-card/50"
                }`}
              >
                {plan.highlight && (
                  <Badge className="self-start mb-3 font-mono text-[9px] bg-primary/15 text-primary border-primary/30 uppercase tracking-widest">
                    Most Popular
                  </Badge>
                )}
                <div className="mb-5">
                  <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-1">{plan.name}</div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-bold font-mono text-foreground">{plan.price}</span>
                    <span className="text-xs text-muted-foreground font-mono">{plan.period}</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{plan.desc}</div>
                </div>

                <ul className="space-y-2 flex-1 mb-5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-muted-foreground">
                      <Check className="w-3 h-3 text-primary flex-shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link href="/register">
                  <Button
                    className="w-full font-mono text-xs uppercase tracking-widest h-8"
                    variant={plan.highlight ? "default" : "outline"}
                    size="sm"
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="py-24 px-4 md:px-8">
        <div className="max-w-2xl mx-auto text-center">
          <div className="flex justify-center mb-6">
            <BrandLogo size={52} iconOnly />
          </div>
          <h2 className="text-3xl md:text-4xl font-bold font-mono tracking-tight mb-4">
            Ready to gain the edge?
          </h2>
          <p className="text-muted-foreground mb-8 text-sm leading-relaxed max-w-md mx-auto">
            Join a live network of AI agents to beat the market. Free to start. No credit card required.
          </p>
          <Link href="/register">
            <Button size="lg" className="font-mono gap-2 px-10 h-12 text-sm">
              Create Free Account
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
          <p className="text-xs text-muted-foreground mt-4 font-mono">
            {welcomeBonus} VITCoin welcome bonus · No credit card required
          </p>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border/40 py-10 px-4 md:px-8 bg-card/20">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-start justify-between gap-8 mb-8">
            <div className="space-y-3">
              <BrandLogo size={26} withWordmark />
              <p className="text-xs text-muted-foreground max-w-xs leading-relaxed font-mono">
                Unified ecosystem for predictive analytics, policy simulation, and global remittance.
                Secured by VIT Blockchain and a decentralised validator network.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-8 text-xs font-mono">
              <div className="space-y-2">
                <div className="text-foreground font-bold uppercase tracking-widest text-[9px] mb-3">Platform</div>
                <Link href="/register"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Get Started</span></Link>
                <Link href="/login"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Sign In</span></Link>
                <a href="#pricing" className="block text-muted-foreground hover:text-primary transition-colors">Pricing</a>
              </div>
              <div className="space-y-2">
                <div className="text-foreground font-bold uppercase tracking-widest text-[9px] mb-3">Product</div>
                <a href="#features" className="block text-muted-foreground hover:text-primary transition-colors">Analytics</a>
                <a href="#ai"       className="block text-muted-foreground hover:text-primary transition-colors">VIT Brain</a>
                <a href="#signals"  className="block text-muted-foreground hover:text-primary transition-colors">Network</a>
              </div>
              <div className="space-y-2">
                <div className="text-foreground font-bold uppercase tracking-widest text-[9px] mb-3">Legal</div>
                <Link href="/privacy"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Privacy</span></Link>
                <Link href="/terms"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Terms</span></Link>
                <Link href="/contact"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Contact</span></Link>
              </div>
            </div>
          </div>

          <div className="border-t border-border/30 pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs font-mono text-muted-foreground/50">
            <span>© {new Date().getFullYear()} VIT Network. All rights reserved.</span>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                All systems operational
              </span>
              <span>{publicCfg?.platform.version || 'v5.5.0'}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
