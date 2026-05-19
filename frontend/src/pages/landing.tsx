import { useState, useEffect } from "react";
import { Link } from "wouter";
import {
  Zap, TrendingUp, Shield, BarChart2, Brain,
  ArrowRight, Check, Star, ChevronRight, Activity,
  Coins, Lock, Network, Target, FlaskConical,
  Award, LineChart, Fingerprint, Layers, GitBranch,
  Gauge, BookOpen, Cpu, ChevronDown, ChevronUp
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
    title: `${modelCount}-Model AI Ensemble`,
    desc: `Random Forest, XGBoost, Poisson Goals, Elo Rating, Dixon-Coles and ${Math.max(modelCount - 5, 0)} more — every model votes on every prediction with calibrated weights.`,
    color: "text-primary",
    bg: "bg-primary/10 border-primary/20",
    tag: "CORE ENGINE",
  },
  {
    icon: Target,
    title: "Per-Market Confidence Scoring",
    desc: "1X2, Over/Under, BTTS, Asian Handicap and Correct Score each receive an independent confidence score computed from their own probability distribution — not a flat multiplier.",
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
    tag: "INTELLIGENCE",
  },
  {
    icon: Gauge,
    title: "Match Quality Rating",
    desc: "Every prediction gets a 0–100 quality grade (A–D) based on model agreement, confidence interval width, model participation rate, and league data quality.",
    color: "text-teal-400",
    bg: "bg-teal-500/10 border-teal-500/20",
    tag: "INTELLIGENCE",
  },
  {
    icon: TrendingUp,
    title: "CLV & Closing Line Value",
    desc: "Measure your long-run edge against the closing line. Beat the market price? You're winning. VIT tracks your CLV on every settled prediction automatically.",
    color: "text-secondary",
    bg: "bg-secondary/10 border-secondary/20",
    tag: "ANALYTICS",
  },
  {
    icon: Shield,
    title: "Blockchain-Verified Results",
    desc: "Results are settled through a decentralised validator oracle network and anchored on-chain. Every outcome is cryptographically verifiable — zero manipulation possible.",
    color: "text-purple-400",
    bg: "bg-purple-500/10 border-purple-500/20",
    tag: "TRUST",
  },
  {
    icon: Coins,
    title: "VITCoin Economy",
    desc: "Earn VITCoin for accurate predictions, stake to become a validator, and earn a share of platform revenue. A real incentive layer built around prediction merit.",
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    tag: "ECONOMY",
  },
  {
    icon: BarChart2,
    title: "Kelly & Bankroll Management",
    desc: "Full Kelly criterion calculator, fractional staking, daily loss limits, drawdown alerts, and a 30-day P&L chart. Institutional risk management for every user.",
    color: "text-green-400",
    bg: "bg-green-500/10 border-green-500/20",
    tag: "RISK",
  },
  {
    icon: LineChart,
    title: "Quant Research Terminal",
    desc: "Walk-forward backtesting, Monte Carlo simulations, an Expected Value scanner, and a strategy optimizer — the same tools used by professional quant funds.",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10 border-indigo-500/20",
    tag: "RESEARCH",
  },
  {
    icon: FlaskConical,
    title: "Per-League Home Advantage",
    desc: "The ensemble applies league-specific home advantage biases — Premier League (5.8%), Bundesliga (5.1%), MLS (3.5%) — not a one-size-fits-all constant.",
    color: "text-orange-400",
    bg: "bg-orange-500/10 border-orange-500/20",
    tag: "ACCURACY",
  },
  {
    icon: Network,
    title: "22-Agent Intelligence Network",
    desc: "Live-match tracker, news sentinel, odds anomaly detector, performance monitor and 18 more autonomous agents run continuously, feeding signals into the ensemble.",
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
    tag: "NETWORK",
  },
  {
    icon: Award,
    title: "Merit Protocol & Leaderboard",
    desc: "Seven merit tiers from Unranked to Sovereign. Earn badges, climb the leaderboard, and unlock VIT bonuses. Your reputation is permanently recorded on-chain.",
    color: "text-yellow-400",
    bg: "bg-yellow-500/10 border-yellow-500/20",
    tag: "GAMIFICATION",
  },
  {
    icon: Lock,
    title: "KYC & System Identity",
    desc: "Offline rule-based KYC with risk scoring (0–100). Every verified user receives a deterministic VIT-YYYY-XXXXXX System ID, W3C DID, and verifiable credentials.",
    color: "text-slate-400",
    bg: "bg-slate-500/10 border-slate-500/20",
    tag: "COMPLIANCE",
  },
];

const CAPABILITY_PILLS = [
  { label: "13 AI Models",        color: "text-primary  border-primary/30  bg-primary/8"  },
  { label: "5 Prediction Markets",color: "text-teal-400 border-teal-400/30 bg-teal-400/8" },
  { label: "22 Live Agents",      color: "text-cyan-400 border-cyan-400/30 bg-cyan-400/8" },
  { label: "Blockchain Oracle",   color: "text-purple-400 border-purple-400/30 bg-purple-400/8" },
  { label: "Walk-Forward Backtest", color: "text-indigo-400 border-indigo-400/30 bg-indigo-400/8" },
  { label: "Kelly Criterion",     color: "text-green-400 border-green-400/30 bg-green-400/8" },
  { label: "Match Quality A–D",   color: "text-amber-400 border-amber-400/30 bg-amber-400/8" },
  { label: "CLV Tracking",        color: "text-secondary border-secondary/30 bg-secondary/8" },
  { label: "W3C DIDs",            color: "text-slate-400 border-slate-400/30 bg-slate-400/8" },
  { label: "Merit Leaderboard",   color: "text-yellow-400 border-yellow-400/30 bg-yellow-400/8" },
  { label: "Monte Carlo Sim",     color: "text-rose-400  border-rose-400/30  bg-rose-400/8" },
  { label: "Per-League HA Bias",  color: "text-orange-400 border-orange-400/30 bg-orange-400/8" },
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
  const modelCount   = publicCfg?.platform.model_count       ?? 13;
  const welcomeBonus = publicCfg?.platform.welcome_bonus_vit ?? 100;
  const FEATURES     = buildFeatures(modelCount);
  const visibleFeatures = showAllFeatures ? FEATURES : FEATURES.slice(0, 6);

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
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <BrandLogo size={30} withWordmark />
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-mono text-muted-foreground">
            <a href="#features"      className="hover:text-foreground transition-colors">Features</a>
            <a href="#capabilities"  className="hover:text-foreground transition-colors">Platform</a>
            <a href="#ai"            className="hover:text-foreground transition-colors">AI Engine</a>
            <a href="#pricing"       className="hover:text-foreground transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm" className="font-mono text-xs">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="font-mono text-xs gap-1">
                Start Predicting <ArrowRight className="w-3 h-3" />
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────── */}
      <section className="relative pt-32 pb-16 md:pt-40 md:pb-24 px-4 md:px-8">
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: 'linear-gradient(to right, rgba(0,245,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,245,255,0.04) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, black, transparent)',
        }} />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-32 right-1/4 w-64 h-64 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          {/* Logo mark above headline */}
          <div className="flex justify-center mb-6">
            <BrandLogo size={72} iconOnly />
          </div>

          <Badge className="mb-6 font-mono text-xs border-primary/30 bg-primary/10 text-primary px-4 py-1.5">
            <Activity className="w-3 h-3 mr-1.5 inline animate-pulse" />
            {modelCount} AI Models · Live Predictions · Blockchain Verified
          </Badge>

          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold font-mono tracking-tight leading-tight mb-6">
            <span className="block text-foreground">Institutional-Grade</span>
            <span className="block vit-gradient-text">Sports Intelligence</span>
          </h1>

          <p className="text-base md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            A {modelCount}-model AI ensemble analyses every match with machine learning precision.
            Real edge. Real transparency. Real results.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-12">
            <Link href="/register">
              <Button size="lg" className="font-mono gap-2 px-8 h-12 text-base shadow-lg vit-glow-cyan">
                Start Predicting Free
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline" className="font-mono gap-2 px-8 h-12 text-base border-border/60">
                Sign In
              </Button>
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-2xl mx-auto">
            <StatCounter value={stats?.predictions_display ?? "0"}    label="Predictions" />
            <StatCounter value={stats?.accuracy_display   ?? "Live"}  label="Accuracy Rate" />
            <StatCounter value={stats?.total_staked_display ?? "$0"}  label="Total Staked" />
            <StatCounter value={String(stats?.ai_models ?? modelCount)} label="AI Models" />
          </div>
        </div>
      </section>

      {/* ── Live ticker ─────────────────────────────────── */}
      <TickerTape items={data?.ticker ?? []} />

      {/* ── Capability pills ─────────────────────────────── */}
      <section id="capabilities" className="py-12 px-4 md:px-8 border-y border-border/30 bg-card/10">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-6">
            <p className="text-xs font-mono uppercase tracking-widest text-muted-foreground/60">Platform Capabilities</p>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            {CAPABILITY_PILLS.map((pill) => (
              <span
                key={pill.label}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-mono font-medium ${pill.color}`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
                {pill.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ────────────────────────────────────── */}
      <section id="features" className="py-20 px-4 md:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <Badge className="mb-4 font-mono text-xs border-primary/30 bg-primary/10 text-primary">
              <Layers className="w-3 h-3 mr-1.5 inline" /> Full Stack Intelligence
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold font-mono tracking-tight mb-3">
              Everything you need to win
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Built by quants and traders. Every feature earns its place — no filler, no black boxes.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {visibleFeatures.map((f) => (
              <div
                key={f.title}
                className={`rounded-xl border p-6 ${f.bg} transition-all duration-250 hover:-translate-y-1 hover:shadow-lg cursor-default group`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-background/50 border border-border/50 flex items-center justify-center">
                    <f.icon className={`w-5 h-5 ${f.color}`} />
                  </div>
                  <span className={`text-[9px] font-mono font-bold tracking-widest px-2 py-0.5 rounded border ${f.color} border-current opacity-60`}>
                    {f.tag}
                  </span>
                </div>
                <h3 className="font-bold font-mono text-sm mb-2">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>

          {/* Show more / less toggle */}
          <div className="flex justify-center mt-8">
            <Button
              variant="outline"
              size="sm"
              className="font-mono text-xs gap-2 border-border/50"
              onClick={() => setShowAllFeatures((v) => !v)}
            >
              {showAllFeatures ? (
                <><ChevronUp className="w-3.5 h-3.5" /> Show fewer features</>
              ) : (
                <><ChevronDown className="w-3.5 h-3.5" /> Show all {FEATURES.length} features</>
              )}
            </Button>
          </div>
        </div>
      </section>

      {/* ── Why VIT is Different (comparison strip) ────── */}
      <section className="py-16 px-4 md:px-8 bg-card/20 border-y border-border/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl md:text-3xl font-bold font-mono tracking-tight mb-2">
              Why VIT is different
            </h2>
            <p className="text-muted-foreground text-sm">Quant-grade infrastructure, not a tipster site.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: GitBranch,
                label: "Ensemble Voting",
                sub: "13 independent models vote on every prediction — no single model can dominate the output.",
                color: "text-primary",
              },
              {
                icon: Cpu,
                label: "AI Transparency",
                sub: "See each model's confidence, weight, and contribution to the final call. No black boxes.",
                color: "text-teal-400",
              },
              {
                icon: Fingerprint,
                label: "Cryptographic Proof",
                sub: "Every prediction is hashed, anchored, and verifiable. Your track record can never be altered.",
                color: "text-purple-400",
              },
              {
                icon: BookOpen,
                label: "Research Grade Tools",
                sub: "Walk-forward backtest, Monte Carlo, EV scanner. The tools quant funds use, open to everyone.",
                color: "text-indigo-400",
              },
              {
                icon: Gauge,
                label: "Match Quality Score",
                sub: "Every prediction is graded A–D for reliability before you stake. Know your edge quality upfront.",
                color: "text-amber-400",
              },
              {
                icon: Award,
                label: "Merit-Based Rewards",
                sub: "Accuracy is rewarded. VITCoin bonuses scale with your merit tier — from Unranked to Sovereign.",
                color: "text-yellow-400",
              },
            ].map((item) => (
              <div key={item.label} className="flex gap-4 items-start p-4 rounded-xl border border-border/40 bg-background/30 hover:bg-background/50 transition-colors">
                <div className={`w-9 h-9 rounded-lg border border-border/50 bg-background/50 flex items-center justify-center flex-shrink-0`}>
                  <item.icon className={`w-4.5 h-4.5 ${item.color}`} />
                </div>
                <div>
                  <div className="font-mono font-bold text-sm mb-1">{item.label}</div>
                  <div className="text-xs text-muted-foreground leading-relaxed">{item.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── AI Ensemble Visualization ───────────────────── */}
      <section id="ai" className="py-20 px-4 md:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <Badge className="mb-4 font-mono text-xs border-primary/30 bg-primary/10 text-primary">
                AI Transparency
              </Badge>
              <h2 className="text-3xl md:text-4xl font-bold font-mono tracking-tight mb-4">
                See exactly why every prediction is made
              </h2>
              <p className="text-muted-foreground mb-6 leading-relaxed">
                Unlike black-box systems, VIT shows you the confidence score of each of its {modelCount} models,
                their calibrated accuracy, and the weighted consensus that drives the final call —
                including a per-market breakdown for 1X2, O/U, BTTS, Asian Handicap and Correct Score.
              </p>
              <ul className="space-y-3 mb-8">
                {[
                  "Per-model confidence breakdown (62–88% calibrated range)",
                  "Per-market confidence: 1X2, O/U, BTTS, AH, Correct Score",
                  "Match quality grade A–D with component breakdown",
                  "Bootstrap confidence intervals (95% CI) on every prediction",
                  "Model agreement % and ensemble diversity score",
                  "Expandable 'Why this prediction?' section per match",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm">
                    <div className="w-5 h-5 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center flex-shrink-0">
                      <Check className="w-3 h-3 text-primary" />
                    </div>
                    <span className="text-muted-foreground">{item}</span>
                  </li>
                ))}
              </ul>
              <Link href="/register">
                <Button className="font-mono gap-2">
                  Try it now <ChevronRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>

            <div className="rounded-2xl border border-border bg-card/50 backdrop-blur p-6 space-y-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Model Consensus</span>
                <Badge className="text-primary border-primary/30 bg-primary/10 font-mono text-xs">
                  {stats?.ai_models_ready ?? 0}/{stats?.ai_models ?? modelCount} READY
                </Badge>
              </div>
              {consensusModels.length === 0 ? (
                <p className="text-xs font-mono text-muted-foreground py-8 text-center">
                  Model telemetry will appear after the ensemble loads.
                </p>
              ) : (
                consensusModels.map((m) => (
                  <div key={m.name} className="space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-mono text-foreground">{m.name}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-muted-foreground/60">
                          w={typeof m.weight === "number" ? m.weight.toFixed(2) : "—"}
                        </span>
                        <span className="text-xs font-mono text-primary font-bold">{m.confidence.toFixed(1)}%</span>
                      </div>
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
      </section>

      {/* ── Testimonials ────────────────────────────────── */}
      <section className="py-20 px-4 md:px-8 bg-card/10">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold font-mono mb-12">Trusted by serious bettors</h2>
          <div className="relative min-h-[160px]">
            {testimonials.length === 0 ? (
              <div className="rounded-xl border border-border bg-card/40 p-8 text-sm font-mono text-muted-foreground">
                Verified marketplace reviews will appear here after users rate live models.
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
            <h2 className="text-3xl md:text-4xl font-bold font-mono mb-3">Transparent Pricing</h2>
            <p className="text-muted-foreground">Start free. Upgrade when you're ready.</p>
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
            Join a live network using AI to beat the market. Free to start. No credit card required.
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
                Institutional-grade sports intelligence powered by a {modelCount}-model AI ensemble,
                blockchain verification, and a decentralised validator network.
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
                <a href="#features" className="block text-muted-foreground hover:text-primary transition-colors">Features</a>
                <a href="#ai" className="block text-muted-foreground hover:text-primary transition-colors">AI Engine</a>
                <a href="#capabilities" className="block text-muted-foreground hover:text-primary transition-colors">Capabilities</a>
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
            <span>© {new Date().getFullYear()} VIT Network. All rights reserved.</span>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                All systems operational
              </span>
              <span>v5.0.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
