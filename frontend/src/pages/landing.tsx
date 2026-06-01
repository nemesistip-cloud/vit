import { useState, useEffect } from "react";
import { Link } from "wouter";
import {
  Zap, TrendingUp, Shield, BarChart2, Brain,
  ArrowRight, Check, Star, ChevronRight, Activity,
  Coins, Lock, Network, Target, FlaskConical,
  Award, LineChart, Fingerprint, Layers, GitBranch,
  Gauge, BookOpen, Cpu, ChevronDown, ChevronUp,
  Globe, Vote, Scale, Wallet
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
  model_consensus: {
    models: LandingModel[];
    average_confidence: number;
  };
  plans: LandingPlan[];
};

const buildFeatures = (modelCount: number) => [
  {
    icon: Brain,
    title: "VIT Brain AI Ensemble",
    desc: `Powered by an internal Mistral/Ollama core and VIT Memory (RAG). Every signal is processed through ${modelCount} specialized AI agents with calibrated weights for maximum precision.`,
    color: "text-primary",
    bg: "bg-primary/10 border-primary/20",
    tag: "CORE ANALYTICS",
  },
  {
    icon: Vote,
    title: "Elections",
    desc: "Real-time sentiment analytics and outcome prediction for global elections. Leveraging on-chain data and the VIT Nerve orchestrator to detect shifts in public sentiment before they hit the polls.",
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
    tag: "APP",
  },
  {
    icon: Scale,
    title: "Policy & Governance",
    desc: "Predictive modeling for legislative changes and policy impacts. Our agents monitor global policy shifts to provide high-fidelity analytics for governance and professional decision-making.",
    color: "text-teal-400",
    bg: "bg-teal-500/10 border-teal-500/20",
    tag: "APP",
  },
  {
    icon: Wallet,
    title: "DeFi & Remittance",
    desc: "Modernizing finance with the VITCoin economy. Low-cost cross-border remittance, staking rewards for validators, and a transparent on-chain treasury for the App ecosystem.",
    color: "text-secondary",
    bg: "bg-secondary/10 border-secondary/20",
    tag: "FINANCE",
  },
  {
    icon: Shield,
    title: "Blockchain-Verified Analytics",
    desc: "All analytics signals and prediction results are anchored on-chain and verified by a decentralized validator network. Zero manipulation, total transparency.",
    color: "text-purple-400",
    bg: "bg-purple-500/10 border-purple-500/20",
    tag: "TRUST",
  },
  {
    icon: Network,
    title: "22-Agent Network",
    desc: "Live trackers, news sentinels, sentiment crawlers, and anomaly detectors. 22 autonomous agents feed continuous data streams into the VIT Brain to maintain our competitive edge.",
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
    tag: "NETWORK",
  },
  {
    icon: BarChart2,
    title: "Kelly & Risk Management",
    desc: "Professional risk tools for every user. Full Kelly criterion calculator, fractional staking, and automated bankroll management to ensure long-term sustainability.",
    color: "text-green-400",
    bg: "bg-green-500/10 border-green-500/20",
    tag: "RISK",
  },
  {
    icon: LineChart,
    title: "Quant Research Terminal",
    desc: "Walk-forward backtesting, Monte Carlo simulations, and a strategy optimizer. Professional quant tools now available for sports, elections, and financial markets.",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10 border-indigo-500/20",
    tag: "RESEARCH",
  },
];

const CAPABILITY_PILLS = [
  { label: "VIT Brain (Mistral/Ollama)", color: "text-primary  border-primary/30  bg-primary/8"  },
  { label: "VIT Memory (RAG)",         color: "text-teal-400 border-teal-400/30 bg-teal-400/8" },
  { label: "22 Live Agents",           color: "text-cyan-400 border-cyan-400/30 bg-cyan-400/8" },
  { label: "Elections",         color: "text-purple-400 border-purple-400/30 bg-purple-400/8" },
  { label: "Policy Sentiment",         color: "text-indigo-400 border-indigo-400/30 bg-indigo-400/8" },
  { label: "VITCoin Economy",          color: "text-green-400 border-green-400/30 bg-green-400/8" },
  { label: "On-Chain Verification",    color: "text-amber-400 border-amber-400/30 bg-amber-400/8" },
  { label: "Remittance Layer",         color: "text-secondary border-secondary/30 bg-secondary/8" },
  { label: "W3C DIDs",                 color: "text-slate-400 border-slate-400/30 bg-slate-400/8" },
  { label: "Signal Marketplace",       color: "text-yellow-400 border-yellow-400/30 bg-yellow-400/8" },
];

function TickerTape({ items }: { items: LandingTickerItem[] }) {
  if (items.length === 0) return null;
  const tickerItems = [...items, ...items];
  return (
    <div className="vit-ticker-wrap bg-vit-gray-900 border-y border-border/50 py-2 overflow-hidden">
      <div className="vit-ticker-content gap-8 px-4">
        {tickerItems.map((item, i) => (
          <span key={i} className="inline-flex items-center gap-2 text-xs font-mono mr-8 flex-shrink-0">
            <span className="text-muted-foreground">{item.match}</span>
            <span className="text-primary">{item.edge}</span>
            <span className="text-muted-foreground">AI: {item.confidence}%</span>
            <span className={`font-bold ${item.outcome === "WIN" ? "text-green-400" : item.outcome === "LOSS" ? "text-destructive" : "text-muted-foreground"}`}>
              {item.outcome}
            </span>
            <span className="text-border">•</span>
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
      <div className="text-sm text-muted-foreground font-mono mt-1">{label}</div>
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
  const modelCount   = publicCfg?.platform.model_count       ?? 22;
  const welcomeBonus = publicCfg?.platform.welcome_bonus_vit ?? 100;
  const FEATURES     = buildFeatures(modelCount);
  const visibleFeatures = showAllFeatures ? FEATURES : FEATURES.slice(0, 6);

  const stats = data?.stats;
  const testimonials = data?.testimonials ?? [];
  const plans = data?.plans ?? [];
  const consensusModels = data?.model_consensus?.models ?? [];

  useEffect(() => {
    if (testimonials.length === 0) return;
    const interval = setInterval(() => {
      setActiveTestimonial((prev) => (prev + 1) % testimonials.length);
    }, 6000);
    return () => clearInterval(interval);
  }, [testimonials]);

  return (
    <div className="min-h-screen bg-background text-foreground vit-page-container">
      {/* ── Navbar ──────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
          <BrandLogo withWordmark size={30} />
          <div className="hidden md:flex items-center gap-8 text-xs font-mono tracking-widest uppercase">
            <a href="#features" className="hover:text-primary transition-colors">Analytics</a>
            <a href="#ai" className="hover:text-primary transition-colors">VIT Brain</a>
            <a href="#pricing" className="hover:text-primary transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost" className="font-mono text-xs uppercase tracking-widest">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="font-mono text-xs uppercase tracking-widest px-6 vit-glow-cyan">Get Started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero Section ────────────────────────────────── */}
      <section className="relative pt-32 pb-20 px-4 md:px-8 overflow-hidden">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/5 rounded-full blur-[120px] -z-10" />
        <div className="max-w-5xl mx-auto text-center">
          <Badge variant="outline" className="mb-6 font-mono py-1.5 px-4 text-[10px] tracking-[0.2em] uppercase border-primary/30 bg-primary/5 text-primary">
            v5.2.0 — The Analytics App
          </Badge>
          <h1 className="text-5xl md:text-7xl font-bold font-mono tracking-tight mb-6 leading-[1.1]">
            Professional <br />
            <span className="vit-gradient-text">Analytics Analytics</span>
          </h1>
          <p className="text-muted-foreground text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            A decentralised network providing professional AI analytics across sports,
            elections, finance, and policy. Secured by VIT Blockchain.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register">
              <Button size="lg" className="font-mono gap-2 px-8 h-14 text-md shadow-xl vit-glow-cyan">
                Launch App
                <ArrowRight className="w-5 h-5" />
              </Button>
            </Link>
            <a href="#features">
              <Button size="lg" variant="outline" className="font-mono px-8 h-14 text-md bg-background/50 backdrop-blur-sm border-white/5">
                Explore Network
              </Button>
            </a>
          </div>

          <div className="mt-16 flex flex-wrap justify-center gap-3 max-w-4xl mx-auto opacity-70">
            {CAPABILITY_PILLS.map((pill) => (
              <span key={pill.label} className={`px-3 py-1 rounded-full border text-[10px] font-mono uppercase tracking-wider ${pill.color}`}>
                {pill.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Ticker ──────────────────────────────────────── */}
      <TickerTape items={data?.ticker ?? []} />

      {/* ── Stats ───────────────────────────────────────── */}
      <section className="py-20 border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 md:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <StatCounter value={stats?.predictions_display ?? "1.2M+"} label="Predictions On-Chain" />
            <StatCounter value={stats?.accuracy_display ?? "84.2%"} label="Verified Accuracy" />
            <StatCounter value={stats?.total_staked_display ?? "$4.8M"} label="Total Value Locked" />
            <StatCounter value={`${modelCount}`} label="Active AI Agents" />
          </div>
        </div>
      </section>

      {/* ── Features Grid ───────────────────────────────── */}
      <section id="features" className="py-24 px-4 md:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold font-mono mb-4 tracking-tight">The VIT Stack</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              We've built a multi-layered analytics ecosystem that combines local AI reasoning
              with blockchain-enforced integrity.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {visibleFeatures.map((f, i) => (
              <div
                key={f.title}
                className="group p-6 rounded-2xl border border-white/5 bg-card/50 hover:bg-card hover:border-primary/20 transition-all duration-300"
              >
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-6 transition-transform group-hover:scale-110 ${f.bg}`}>
                  <f.icon className={`w-6 h-6 ${f.color}`} />
                </div>
                <div className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-2">{f.tag}</div>
                <h3 className="text-lg font-bold font-mono mb-3">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-12 text-center">
            <Button
              variant="ghost"
              className="font-mono text-xs uppercase tracking-widest gap-2"
              onClick={() => setShowAllFeatures(!showAllFeatures)}
            >
              {showAllFeatures ? "Show Less" : "View Full Stack"}
              {showAllFeatures ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </section>

      {/* ── AI Engine Deep Dive ─────────────────────────── */}
      <section id="ai" className="py-24 px-4 md:px-8 bg-primary/5 border-y border-primary/10 overflow-hidden relative">
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/4" />
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <Badge className="mb-4 bg-primary text-primary-foreground font-mono">INTERNAL ARCHITECTURE</Badge>
            <h2 className="text-4xl md:text-5xl font-bold font-mono tracking-tight mb-6">
              VIT Brain: <br />
              Local AI Reasoning
            </h2>
            <p className="text-muted-foreground text-lg mb-8 leading-relaxed">
              Unlike other platforms that rely on centralized LLM APIs, VIT runs an internal,
              private AI stack. Our <strong>VIT Nerve</strong> orchestrator coordinates
              <strong>VIT Brain</strong> (Local Mistral) and <strong>VIT Memory</strong> (Persistent RAG)
              to ensure your analytics never leaves the network.
            </p>
            <ul className="space-y-4 mb-10">
              {[
                "Local inference for total data privacy",
                "Domain-specific fine-tuning for high accuracy",
                "Real-time RAG updates from 22 live agents",
                "On-chain verification for every model output"
              ].map((item) => (
                <li key={item} className="flex items-center gap-3 text-sm font-mono">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  {item}
                </li>
              ))}
            </ul>
            <Link href="/register">
              <Button className="font-mono gap-2 h-12 px-6 vit-glow-cyan">
                View Model Leaderboard
                <ChevronRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>

          <div className="relative">
            <div className="absolute -inset-1 bg-gradient-to-r from-primary to-cyan-500 rounded-3xl blur opacity-20" />
            <div className="relative rounded-3xl border border-white/10 bg-vit-gray-950 p-8 shadow-2xl">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <Cpu className="w-5 h-5 text-primary" />
                  <span className="font-mono text-sm font-bold uppercase tracking-wider">Model Status</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-[10px] font-mono text-green-400 uppercase">Live Inference</span>
                </div>
              </div>

              <div className="space-y-6">
                {consensusModels.length === 0 ? (
                  Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="space-y-2 opacity-50">
                      <div className="h-4 bg-muted rounded w-1/3 animate-pulse" />
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden" />
                    </div>
                  ))
                ) : (
                  consensusModels.slice(0, 5).map((m) => (
                    <div key={m.name} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-medium">{m.name}</span>
                        <span className="text-xs font-mono text-primary font-bold">{(m.confidence).toFixed(1)}%</span>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${Math.min(100, Math.max(0, m.confidence))}%`,
                            background: `linear-gradient(90deg, var(--color-primary) 0%, #00F5C8 100%)`,
                          }}
                        />
                      </div>
                    </div>
                  ))
                )}
                <div className="pt-3 border-t border-border flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono text-muted-foreground">Ensemble Avg Confidence</span>
                    <div className="text-[10px] font-mono text-muted-foreground/50 mt-0.5">Calibrated range 62–88%</div>
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

      {/* ── Testimonials ────────────────────────────────── */}
      <section className="py-20 px-4 md:px-8 bg-card/10">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold font-mono mb-12">Trusted Analytics</h2>
          <div className="relative min-h-[160px]">
            {testimonials.length === 0 ? (
              <div className="rounded-xl border border-border bg-card/40 p-8 text-sm font-mono text-muted-foreground">
                Verified network reviews will appear here after users rate live agents.
              </div>
            ) : testimonials.map((t, i) => (
              <div
                key={i}
                className={`absolute inset-0 transition-all duration-500 ${
                  i === activeTestimonial ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"
                }`}
              >
                <div className="flex justify-center mb-3">
                  {Array.from({ length: t.stars }).map((_, s) => (
                    <Star key={s} className="w-4 h-4 text-secondary fill-secondary" />
                  ))}
                </div>
                <blockquote className="text-lg text-foreground mb-4 leading-relaxed">"{t.text}"</blockquote>
                <div className="text-sm font-mono">
                  <span className="text-primary">{t.user}</span>
                  <span className="text-muted-foreground"> · {t.role}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-center gap-2 mt-6">
            {testimonials.map((_, i) => (
              <button
                key={i}
                onClick={() => setActiveTestimonial(i)}
                className={`w-2 h-2 rounded-full transition-all ${i === activeTestimonial ? "bg-primary w-6" : "bg-muted-foreground/30"}`}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ─────────────────────────────────────── */}
      <section id="pricing" className="py-20 px-4 md:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold font-mono mb-3">Transparent Tiers</h2>
            <p className="text-muted-foreground">Start free. Upgrade when you are ready to scale your analytics.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-xl border p-6 flex flex-col transition-all duration-250 hover:-translate-y-1 ${
                  plan.highlight
                    ? "border-primary/40 bg-primary/5 shadow-lg vit-glow-cyan"
                    : "border-border bg-card/50"
                }`}
              >
                {plan.highlight && (
                  <Badge className="self-start mb-3 font-mono text-xs bg-primary text-primary-foreground">
                    Most Popular
                  </Badge>
                )}
                <div className="mb-4">
                  <div className="text-sm font-mono text-muted-foreground mb-1">{plan.name}</div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold font-mono">{plan.price}</span>
                    <span className="text-sm text-muted-foreground">{plan.period}</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">{plan.desc}</div>
                </div>
                <ul className="space-y-2 flex-1 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Check className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link href="/register">
                  <Button
                    className="w-full font-mono"
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

      {/* ── Final CTA ───────────────────────────────────── */}
      <section className="py-24 px-4 md:px-8 bg-card/10">
        <div className="max-w-3xl mx-auto text-center">
          <div className="flex justify-center mb-6">
            <BrandLogo size={56} iconOnly />
          </div>
          <h2 className="text-4xl md:text-5xl font-bold font-mono tracking-tight mb-4">
            Ready to gain the edge?
          </h2>
          <p className="text-muted-foreground mb-8 text-lg">
            Join a live network of AI agents to beat the market. Free to start. No credit card required.
          </p>
          <Link href="/register">
            <Button size="lg" className="font-mono gap-2 px-10 h-14 text-lg shadow-xl vit-glow-cyan">
              Create Free Account
              <ArrowRight className="w-5 h-5" />
            </Button>
          </Link>
          <p className="text-xs text-muted-foreground mt-4 font-mono">
            {welcomeBonus} VITCoin bonus on first prediction · No credit card required
          </p>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────── */}
      <footer className="border-t border-border/50 py-10 px-4 md:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-start justify-between gap-8 mb-8">
            <div className="space-y-3">
              <BrandLogo size={28} withWordmark />
              <p className="text-xs text-muted-foreground max-w-xs leading-relaxed font-mono">
                Unified ecosystem for predictive analytics, policy simulation, and global remittance.
                Secured by VIT Blockchain and a decentralised validator network.
              </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-8 text-xs font-mono">
              <div className="space-y-2">
                <div className="text-foreground font-bold uppercase tracking-widest text-[10px] mb-3">Platform</div>
                <Link href="/register"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Get Started</span></Link>
                <Link href="/login"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Sign In</span></Link>
                <a href="#pricing" className="block text-muted-foreground hover:text-primary transition-colors">Pricing</a>
              </div>
              <div className="space-y-2">
                <div className="text-foreground font-bold uppercase tracking-widest text-[10px] mb-3">Product</div>
                <a href="#features" className="block text-muted-foreground hover:text-primary transition-colors">Analytics</a>
                <a href="#ai" className="block text-muted-foreground hover:text-primary transition-colors">VIT Brain</a>
                <a href="#capabilities" className="block text-muted-foreground hover:text-primary transition-colors">Network</a>
              </div>
              <div className="space-y-2">
                <div className="text-foreground font-bold uppercase tracking-widest text-[10px] mb-3">Legal</div>
                <Link href="/privacy"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Privacy Policy</span></Link>
                <Link href="/terms"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Terms of Service</span></Link>
                <Link href="/contact"><span className="block text-muted-foreground hover:text-primary cursor-pointer transition-colors">Contact</span></Link>
              </div>
            </div>
          </div>
          <div className="border-t border-border/40 pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs font-mono text-muted-foreground/60">
            <span>© {new Date().getFullYear()} VIT. All rights reserved.</span>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                All systems operational
              </span>
              <span>v5.2.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
