import { useState, useEffect } from "react";
import { Link } from "wouter";
import {
  Trophy, Zap, TrendingUp, Shield, BarChart2, Brain,
  ArrowRight, Check, Star, ChevronRight, Activity,
  Users, Coins, Globe, Lock, Sparkles
} from "lucide-react";
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
    title: `${modelCount}-Model AI Ensemble`,
    desc: `Random Forest, LSTM, XGBoost and ${Math.max(modelCount - 3, 0)} more models vote on every prediction. No black boxes.`,
    color: "text-cyan-400",
    border: "border-cyan-500/20",
    bg: "bg-cyan-500/5",
    glow: "hover:border-cyan-500/40 hover:shadow-[0_0_20px_rgba(0,245,255,0.08)]",
  },
  {
    icon: TrendingUp,
    title: "CLV Tracking",
    desc: "Measure your edge against closing line value. Know exactly when you're beating the market.",
    color: "text-yellow-400",
    border: "border-yellow-500/20",
    bg: "bg-yellow-500/5",
    glow: "hover:border-yellow-500/40 hover:shadow-[0_0_20px_rgba(255,215,0,0.08)]",
  },
  {
    icon: Shield,
    title: "Blockchain Verified",
    desc: "Results settled on-chain by a decentralized validator network. Zero manipulation possible.",
    color: "text-purple-400",
    border: "border-purple-500/20",
    bg: "bg-purple-500/5",
    glow: "hover:border-purple-500/40 hover:shadow-[0_0_20px_rgba(168,85,247,0.08)]",
  },
  {
    icon: Coins,
    title: "VITCoin Economy",
    desc: "Earn, stake, and earn revenue share as an Elite validator. Real value, not just points.",
    color: "text-amber-400",
    border: "border-amber-500/20",
    bg: "bg-amber-500/5",
    glow: "hover:border-amber-500/40 hover:shadow-[0_0_20px_rgba(245,158,11,0.08)]",
  },
  {
    icon: BarChart2,
    title: "Bankroll Management",
    desc: "Kelly Criterion, fractional staking, drawdown alerts. Built-in money management tools.",
    color: "text-emerald-400",
    border: "border-emerald-500/20",
    bg: "bg-emerald-500/5",
    glow: "hover:border-emerald-500/40 hover:shadow-[0_0_20px_rgba(52,211,153,0.08)]",
  },
  {
    icon: Zap,
    title: "Real-Time Intelligence",
    desc: "Live odds monitoring, line movement alerts, and arbitrage detection all in one place.",
    color: "text-orange-400",
    border: "border-orange-500/20",
    bg: "bg-orange-500/5",
    glow: "hover:border-orange-500/40 hover:shadow-[0_0_20px_rgba(249,115,22,0.08)]",
  },
];

function TickerTape({ items }: { items: LandingTickerItem[] }) {
  if (items.length === 0) return null;
  const tickerItems = [...items, ...items];
  return (
    <div className="vit-ticker-wrap border-y border-white/5 py-2.5 overflow-hidden bg-white/[0.02]">
      <div className="vit-ticker-content gap-8 px-4">
        {tickerItems.map((item, i) => (
          <span key={i} className="inline-flex items-center gap-2 text-xs font-mono mr-8 flex-shrink-0">
            <span className="text-muted-foreground">{item.match}</span>
            <span className="text-cyan-400 font-bold">{item.edge}</span>
            <span className="text-muted-foreground/60">AI: {item.confidence}%</span>
            <span className={`font-bold ${item.outcome === "WIN" ? "text-emerald-400" : item.outcome === "LOSS" ? "text-rose-400" : "text-muted-foreground"}`}>
              {item.outcome}
            </span>
            <span className="text-foreground/10">•</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function StatCounter({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center group">
      <div className="text-3xl md:text-4xl font-bold font-mono vit-gradient-text group-hover:scale-105 transition-transform">{value}</div>
      <div className="text-xs text-muted-foreground font-mono mt-1.5 uppercase tracking-widest">{label}</div>
    </div>
  );
}

export default function LandingPage() {
  const [activeTestimonial, setActiveTestimonial] = useState(0);
  const { data } = useQuery<LandingData>({
    queryKey: ["public-landing"],
    queryFn: () => apiGet("/api/public/landing"),
  });
  const { data: publicCfg } = usePublicConfig();
  const modelCount   = publicCfg?.platform.model_count       ?? 13;
  const welcomeBonus = publicCfg?.platform.welcome_bonus_vit ?? 100;
  const FEATURES     = buildFeatures(modelCount);

  const stats = data?.stats;
  const testimonials = data?.testimonials ?? [];
  const plans = data?.plans ?? [];
  const consensusModels = data?.model_consensus?.models ?? [];

  useEffect(() => {
    if (testimonials.length === 0) return;
    const t = setInterval(() => setActiveTestimonial((n) => (n + 1) % testimonials.length), 5000);
    return () => clearInterval(t);
  }, [testimonials.length]);

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">

      {/* ── Nav ─────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 backdrop-blur-xl bg-background/80">
        <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-primary/10 border border-primary/30 rounded-lg flex items-center justify-center vit-glow-cyan-s">
              <Zap className="w-4 h-4 text-primary" />
            </div>
            <span className="font-bold font-mono tracking-tight">
              VIT<span className="text-primary">_OS</span>
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-xs font-mono text-muted-foreground uppercase tracking-widest">
            <a href="#features" className="hover:text-primary transition-colors">Features</a>
            <a href="#ai" className="hover:text-primary transition-colors">AI Engine</a>
            <a href="#pricing" className="hover:text-primary transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm" className="font-mono text-xs">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="font-mono text-xs gap-1.5 vit-glow-cyan-s">
                Start Predicting <ArrowRight className="w-3 h-3" />
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────── */}
      <section className="relative pt-32 pb-20 md:pt-44 md:pb-28 px-4 md:px-8 overflow-hidden">
        {/* Radial grid */}
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: 'linear-gradient(to right, rgba(0,245,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,245,255,0.04) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, black, transparent)',
        }} />
        {/* Glow orbs */}
        <div className="absolute top-16 left-1/4 w-[500px] h-[500px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-24 right-1/4 w-[400px] h-[400px] bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-full h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        <div className="relative max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 mb-8 px-4 py-1.5 rounded-full border border-primary/25 bg-primary/8 text-xs font-mono text-primary">
            <span className="vit-live-dot" style={{ width: 5, height: 5 }} />
            {modelCount} AI Models · Live Predictions · Blockchain Verified
          </div>

          <h1 className="text-5xl md:text-6xl lg:text-8xl font-bold font-mono tracking-tight leading-[0.95] mb-8">
            <span className="block text-foreground">Institutional-Grade</span>
            <span className="block vit-gradient-text mt-2">Sports Intelligence</span>
          </h1>

          <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto mb-12 leading-relaxed">
            A {modelCount}-model AI ensemble analyses every match with machine learning precision.
            Real edge. Real transparency. Real results.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-16">
            <Link href="/register">
              <Button size="lg" className="font-mono gap-2 px-10 h-13 text-sm shadow-xl vit-glow-cyan">
                Start Predicting Free
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline" className="font-mono gap-2 px-10 h-13 text-sm border-white/10 hover:border-white/20 bg-white/[0.03] hover:bg-white/[0.06]">
                Sign In
              </Button>
            </Link>
          </div>

          {/* Social proof */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-2xl mx-auto p-6 rounded-2xl border border-white/5 bg-white/[0.02] backdrop-blur">
            <StatCounter value={stats?.predictions_display ?? "0"} label="Predictions" />
            <StatCounter value={stats?.accuracy_display ?? "Live"} label="Accuracy" />
            <StatCounter value={stats?.total_staked_display ?? "$0"} label="Total Staked" />
            <StatCounter value={String(stats?.ai_models ?? 13)} label="AI Models" />
          </div>
        </div>
      </section>

      {/* ── Live ticker ─────────────────────────────────── */}
      <TickerTape items={data?.ticker ?? []} />

      {/* ── Features ────────────────────────────────────── */}
      <section id="features" className="py-24 px-4 md:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <Badge className="mb-4 font-mono text-xs border-white/10 bg-white/5 text-muted-foreground px-3 py-1">
              Platform Features
            </Badge>
            <h2 className="text-3xl md:text-5xl font-bold font-mono tracking-tight mb-4">
              Everything you need to win
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto text-sm leading-relaxed">
              Built by quants and traders, for bettors who demand an edge.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f) => (
              <div key={f.title} className={`rounded-xl border ${f.border} ${f.bg} p-6 transition-all duration-300 cursor-default ${f.glow}`}>
                <div className={`w-10 h-10 rounded-lg border ${f.border} bg-background/60 flex items-center justify-center mb-5`}>
                  <f.icon className={`w-5 h-5 ${f.color}`} />
                </div>
                <h3 className="font-bold font-mono text-sm mb-2 text-foreground">{f.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── AI Ensemble Visualization ───────────────────── */}
      <section id="ai" className="py-24 px-4 md:px-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-white/[0.01] pointer-events-none" />
        <div className="absolute inset-0 border-y border-white/5 pointer-events-none" />
        <div className="max-w-7xl mx-auto relative">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <Badge className="mb-5 font-mono text-xs border-primary/25 bg-primary/8 text-primary px-3 py-1">
                AI Transparency
              </Badge>
              <h2 className="text-3xl md:text-4xl font-bold font-mono tracking-tight mb-5">
                See exactly why every prediction is made
              </h2>
              <p className="text-muted-foreground mb-8 leading-relaxed text-sm">
                Unlike black-box systems, VIT shows you the confidence score of each of its {modelCount} models,
                their historical accuracy, and the weighted consensus that drives the final call.
              </p>
              <ul className="space-y-3 mb-10">
                {[
                  "Per-model confidence breakdown",
                  "Agreement/disagreement visualization",
                  "Historical accuracy by model",
                  "Expandable 'Why this prediction?' section",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm">
                    <div className="w-5 h-5 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center flex-shrink-0">
                      <Check className="w-3 h-3 text-primary" />
                    </div>
                    <span className="text-muted-foreground font-mono text-xs">{item}</span>
                  </li>
                ))}
              </ul>
              <Link href="/register">
                <Button className="font-mono gap-2 vit-glow-cyan-s">
                  Try it now <ChevronRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>

            <div className="rounded-2xl border border-white/8 bg-card/40 backdrop-blur p-6 space-y-4 shadow-2xl">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Model Consensus</span>
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono border border-primary/25 bg-primary/10 text-primary">
                  <span className="vit-live-dot" style={{ width: 5, height: 5 }} />
                  {stats?.ai_models_ready ?? 0}/{stats?.ai_models ?? 13} READY
                </span>
              </div>
              {consensusModels.length === 0 ? (
                <div className="py-12 text-center space-y-3">
                  <Brain className="w-10 h-10 text-muted-foreground/20 mx-auto" />
                  <p className="text-xs font-mono text-muted-foreground/50">
                    Model telemetry loads after the ensemble initialises.
                  </p>
                </div>
              ) : (
                consensusModels.map((m) => (
                  <div key={m.name} className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-mono text-foreground/80">{m.name}</span>
                      <span className="text-xs font-mono text-primary font-bold">{m.confidence.toFixed(1)}%</span>
                    </div>
                    <div className="h-1 bg-muted/40 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-primary to-purple-400 rounded-full transition-all duration-700"
                        style={{ width: `${Math.min(100, Math.max(0, m.confidence))}%` }}
                      />
                    </div>
                  </div>
                ))
              )}
              <div className="pt-3 border-t border-white/5 flex items-center justify-between">
                <span className="text-xs font-mono text-muted-foreground">Ensemble Consensus</span>
                <span className="text-xl font-bold font-mono text-primary">
                  {(data?.model_consensus?.average_confidence ?? 0).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Testimonials ────────────────────────────────── */}
      {testimonials.length > 0 && (
        <section className="py-24 px-4 md:px-8">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-3xl font-bold font-mono mb-14">Trusted by serious bettors</h2>
            <div className="relative min-h-[180px]">
              {testimonials.map((t, i) => (
                <div
                  key={i}
                  className={`absolute inset-0 transition-all duration-500 ${
                    i === activeTestimonial ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"
                  }`}
                >
                  <div className="flex justify-center mb-4 gap-1">
                    {Array.from({ length: t.stars }).map((_, s) => (
                      <Star key={s} className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                    ))}
                  </div>
                  <blockquote className="text-lg text-foreground/90 mb-5 leading-relaxed font-light">"{t.text}"</blockquote>
                  <div className="text-sm font-mono">
                    <span className="text-primary font-bold">{t.user}</span>
                    <span className="text-muted-foreground"> · {t.role}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-center gap-2 mt-8">
              {testimonials.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveTestimonial(i)}
                  className={`h-1 rounded-full transition-all duration-300 ${i === activeTestimonial ? "bg-primary w-8" : "bg-white/15 w-2"}`}
                />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Pricing ─────────────────────────────────────── */}
      {plans.length > 0 && (
        <section id="pricing" className="py-24 px-4 md:px-8 relative">
          <div className="absolute inset-0 border-y border-white/5 bg-white/[0.01] pointer-events-none" />
          <div className="max-w-5xl mx-auto relative">
            <div className="text-center mb-16">
              <Badge className="mb-4 font-mono text-xs border-white/10 bg-white/5 text-muted-foreground px-3 py-1">
                Pricing
              </Badge>
              <h2 className="text-3xl md:text-5xl font-bold font-mono mb-3">Transparent Pricing</h2>
              <p className="text-muted-foreground text-sm">Start free. Upgrade when you're ready.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {plans.map((plan) => (
                <div
                  key={plan.name}
                  className={`rounded-xl border p-6 flex flex-col transition-all duration-300 ${
                    plan.highlight
                      ? "border-primary/40 bg-primary/5 shadow-[0_0_30px_rgba(0,245,255,0.08)]"
                      : "border-white/8 bg-white/[0.02] hover:border-white/12"
                  }`}
                >
                  {plan.highlight && (
                    <span className="self-start mb-3 px-2 py-0.5 rounded text-[10px] font-mono border border-primary/30 bg-primary/10 text-primary uppercase tracking-widest">
                      Popular
                    </span>
                  )}
                  <div className="mb-5">
                    <div className="text-xs font-mono text-muted-foreground mb-1.5 uppercase tracking-widest">{plan.name}</div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-bold font-mono">{plan.price}</span>
                      <span className="text-xs text-muted-foreground">{plan.period}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1.5">{plan.desc}</div>
                  </div>
                  <ul className="space-y-2.5 flex-1 mb-6">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Check className="w-3 h-3 text-primary flex-shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Link href="/register">
                    <Button
                      className="w-full font-mono text-xs"
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
      )}

      {/* ── Trust Strip ─────────────────────────────────── */}
      <section className="py-16 px-4 md:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { icon: Lock, title: "Bank-grade security", desc: "JWT auth, rate limiting, encrypted storage" },
              { icon: Globe, title: "Live data feeds", desc: "Real-time odds from multiple sportsbooks" },
              { icon: Sparkles, title: "AI + Human edge", desc: "Models trained on millions of historical outcomes" },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex items-start gap-4 p-5 rounded-xl border border-white/5 bg-white/[0.02]">
                <div className="w-10 h-10 rounded-lg border border-white/10 bg-white/5 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4.5 h-4.5 text-muted-foreground" style={{ width: 18, height: 18 }} />
                </div>
                <div>
                  <div className="font-mono text-sm font-semibold mb-1">{title}</div>
                  <div className="text-xs text-muted-foreground leading-relaxed">{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────── */}
      <section className="py-28 px-4 md:px-8 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: 'radial-gradient(ellipse 60% 50% at 50% 100%, rgba(0,245,255,0.06), transparent)',
        }} />
        <div className="max-w-3xl mx-auto text-center relative">
          <h2 className="text-4xl md:text-6xl font-bold font-mono tracking-tight mb-5">
            Ready to gain the edge?
          </h2>
          <p className="text-muted-foreground mb-10 text-base">
            Join a live network using AI to beat the market. Free to start. No credit card required.
          </p>
          <Link href="/register">
            <Button size="lg" className="font-mono gap-2 px-12 h-14 text-base shadow-2xl vit-glow-cyan">
              Create Free Account
              <ArrowRight className="w-5 h-5" />
            </Button>
          </Link>
          <p className="text-xs text-muted-foreground/60 mt-5 font-mono">
            {welcomeBonus} VITCoin bonus on signup · No credit card required
          </p>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-10 px-4 md:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-5 text-xs font-mono text-muted-foreground/60">
          <div className="flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-primary" />
            <span className="text-muted-foreground">VIT Sports Intelligence Network</span>
          </div>
          <div className="flex gap-6">
            <Link href="/privacy"><span className="cursor-pointer hover:text-primary transition-colors">Privacy</span></Link>
            <Link href="/terms"><span className="cursor-pointer hover:text-primary transition-colors">Terms</span></Link>
            <Link href="/contact"><span className="cursor-pointer hover:text-primary transition-colors">Contact</span></Link>
            <Link href="/about"><span className="cursor-pointer hover:text-primary transition-colors">About</span></Link>
          </div>
          <span>© {new Date().getFullYear()} VIT Network</span>
        </div>
      </footer>
    </div>
  );
}
