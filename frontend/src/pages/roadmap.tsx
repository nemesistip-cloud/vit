import { useState } from "react";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckCircle2, Circle, Clock, Rocket, Lock,
  Brain, Coins, Globe, Cpu, Shield, Zap, Database,
  GitBranch, Network, Code2, Activity, Layers,
  ChevronDown, ChevronUp, Star, ArrowRight, Sparkles,
  Vote, ShieldCheck, BarChart2, Key, Server, Radio,
  FlaskConical, Target, BookOpen, CreditCard,
  TrendingUp, Blocks, Link2, Atom, Triangle,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

type ItemStatus = "done" | "in-progress" | "planned" | "vision";

interface RoadmapItem {
  label: string;
  status: ItemStatus;
  icon: typeof CheckCircle2;
  detail?: string;
}

interface RoadmapPhase {
  id: string;
  phase: number;
  title: string;
  subtitle: string;
  status: "complete" | "active" | "upcoming" | "vision";
  eta: string;
  icon: typeof Rocket;
  color: string;
  borderColor: string;
  bgColor: string;
  glowColor: string;
  techStack: string[];
  items: RoadmapItem[];
  architectureNote?: string;
}

// ─── Data ────────────────────────────────────────────────────────────────────

const STATUS_META: Record<ItemStatus, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  done:        { label: "Live",        color: "text-emerald-400",  icon: CheckCircle2 },
  "in-progress": { label: "Building",  color: "text-amber-400",   icon: Clock },
  planned:     { label: "Planned",     color: "text-blue-400",    icon: Circle },
  vision:      { label: "Vision",      color: "text-purple-400",  icon: Star },
};

const PHASES: RoadmapPhase[] = [
  {
    id: "p1",
    phase: 1,
    title: "AI Foundation",
    subtitle: "Prediction infrastructure · Auth · Payments · Wallet",
    status: "complete",
    eta: "Delivered — May 2025",
    icon: Brain,
    color: "text-emerald-400",
    borderColor: "border-emerald-500/40",
    bgColor: "bg-emerald-500/5",
    glowColor: "/10",
    techStack: ["FastAPI", "PostgreSQL", "React/Vite", "Redis", "Python ML", "WebSockets"],
    architectureNote: "Full-stack AI platform running 22+ autonomous prediction models. All core infrastructure including payments and wallet logic is live and production-ready in v5.5.0.",
    items: [
      { label: "22-model AI orchestrator (Native Ensemble)", status: "done",  icon: Brain },
      { label: "Tachyon Fabric: EEC-swarm storage coordination", status: "done", icon: Database },
      { label: "Market Classification Layer (Niche vs Sports)", status: "done", icon: Layers },
      { label: "Real-time WebSocket predictions with JWT authentication",               status: "done",  icon: Activity },
      { label: "JWT auth system with 2FA (TOTP) & Role-based access", status: "done", icon: Shield },
      { label: "Multi-currency wallet: NGN · USD · USDT · VITCoin",                    status: "done",  icon: Coins },
      { label: "Stripe (USD) + Paystack (NGN) payments live",       status: "done",  icon: CreditCard },
      { label: "Governance system: proposals · voting · execution engine",     status: "done",  icon: Vote },
      { label: "Trust & safety engine: automated scoring & merit",    status: "done",  icon: ShieldCheck },
      { label: "Prophecy Chain: Game-ified progression engine", status: "done", icon: Sparkles },
      { label: "VIT Oracle: data feeds · on-chain hash anchoring",                     status: "done",  icon: Database },
      { label: "Production deployment: Render Cloud / GCR optimized",        status: "done",  icon: Server },
    ],
  },
  {
    id: "p2",
    phase: 2,
    title: "Ecosystem Expansion",
    subtitle: "Sports Intelligence · Niche Markets · Remittance · Base L2",
    status: "active",
    eta: "Q3 - Q4 2025",
    icon: Rocket,
    color: "text-amber-400",
    borderColor: "border-amber-500/40",
    bgColor: "bg-amber-500/5",
    glowColor: "/10",
    techStack: ["Base L2", "Sports APIs", "Solidity", "Hardhat", "Wagmi", "Web3.py"],
    architectureNote: "Expanding into a dual-layer intelligence marketplace. Sports infrastructure functions via affiliate redirection, while niche markets (Governance, Elections) utilize internal treasury and settlement.",
    items: [
      { label: "Sports Oracle: Verifiable fixture & odds sync", status: "done", icon: TrendingUp },
      { label: "Affiliate Deep-Link Generator: Betway/SportyBet integration", status: "in-progress", icon: Link2 },
      { label: "Elections & Policy sentiment analysis engine", status: "done", icon: Radio },
      { label: "Wallet Protection Layer: Segregated financial flows", status: "done", icon: Lock },
      { label: "Cross-border Remittance: Blockchain liquidity rails", status: "in-progress", icon: Coins },
      { label: "MetaMask / WalletConnect integration", status: "done", icon: Link2 },
      { label: "Deploy VITCoin ERC-20 contract on Base L2", status: "planned", icon: Coins },
      { label: "On-chain prediction settlement: AI hash anchoring", status: "in-progress", icon: CheckCircle2 },
      { label: "Native KYC verification engine", status: "done", icon: ShieldCheck },
      { label: "Ecosystem airdrop: merit-weighted distribution", status: "planned", icon: Star },
    ],
  },
  {
    id: "p3",
    phase: 3,
    title: "VIT Cosmos Chain",
    subtitle: "Sovereign app-chain · Validators · CosmWasm · IBC",
    status: "upcoming",
    eta: "Q1 2026",
    icon: Atom,
    color: "text-blue-400",
    borderColor: "border-blue-500/40",
    bgColor: "bg-blue-500/5",
    glowColor: "/10",
    techStack: ["Cosmos SDK", "CometBFT", "CosmWasm", "Rust", "Ethermint", "IBC", "Go"],
    architectureNote: "VIT becomes a sovereign Cosmos app-chain. Custom consensus rules, low predictable fees, AI-native execution environment, and IBC interoperability with the entire Cosmos ecosystem.",
    items: [
      { label: "VIT Cosmos SDK app-chain genesis",                                    status: "vision", icon: Atom },
      { label: "CometBFT (Tendermint) consensus with VIT validator set",               status: "vision", icon: GitBranch },
      { label: "CosmWasm smart contracts in Rust — staking & governance", status: "vision", icon: Code2 },
      { label: "AI oracle module: prediction hashes anchored natively",       status: "vision", icon: Brain },
      { label: "Reputation module: on-chain merit scores + trust actions",             status: "vision", icon: ShieldCheck },
      { label: "IBC integration: cross-chain liquidity + interoperability",            status: "vision", icon: Network },
      { label: "Ethermint EVM layer: Solidity contract compatibility",    status: "vision", icon: Globe },
      { label: "Validator incentive program: AI contribution scoring",       status: "vision", icon: Target },
      { label: "Data availability via Celestia integration",      status: "vision", icon: Database },
    ],
  },
  {
    id: "p4",
    phase: 4,
    title: "AI-Native Blockchain",
    subtitle: "Autonomous agents · Decentralized compute · ZK-Inference",
    status: "vision",
    eta: "2026 → beyond",
    icon: Sparkles,
    color: "text-purple-400",
    borderColor: "border-purple-500/40",
    bgColor: "bg-purple-500/5",
    glowColor: "/10",
    techStack: ["Rust", "Python", "Kafka", "WASM", "ZK Proofs", "Federated Learning"],
    architectureNote: "The consensus mechanism itself is informed by AI oracle outputs. Validators, agents, and models form a unified analytics economy with trustless inference.",
    items: [
      { label: "AI subnets: specialized prediction zones",    status: "vision", icon: Brain },
      { label: "Decentralized AI compute marketplace (GPU Rental)",     status: "vision", icon: Cpu },
      { label: "Federated ML training across validator nodes",          status: "vision", icon: BookOpen },
      { label: "Autonomous prediction agents with execution rights",           status: "vision", icon: Brain },
      { label: "ZK-proof verification of AI model outputs",      status: "vision", icon: Shield },
      { label: "Professional analytics API: Hedge fund grade data",      status: "vision", icon: TrendingUp },
      { label: "AI-weighted consensus: rewards scaled by accuracy",    status: "vision", icon: Triangle },
      { label: "Decentralized analytics index: AI performance ledger",     status: "vision", icon: BarChart2 },
    ],
  },
];

// ─── Architecture stack table ─────────────────────────────────────────────────

const ARCH_STACK = [
  { layer: "Core Blockchain",      tech: "Cosmos SDK",          phase: 3 },
  { layer: "High-Performance",     tech: "Rust modules",        phase: 3 },
  { layer: "Smart Contracts",      tech: "CosmWasm",            phase: 3 },
  { layer: "Consensus",            tech: "CometBFT",            phase: 3 },
  { layer: "AI Execution",         tech: "Agent Swarm (22+)",   phase: 1 },
  { layer: "Oracle Layer",         tech: "Tachyon Fabric",      phase: 1 },
  { layer: "Storage EEC",          tech: "Reed-Solomon / XOR",  phase: 1 },
  { layer: "Market Mapping",       tech: "Sports + Niche",      phase: 2 },
  { layer: "Affiliate Layer",      tech: "Sports Redirection",  phase: 2 },
  { layer: "Cross-chain",          tech: "IBC Protocol",        phase: 3 },
  { layer: "Validators",           tech: "Cosmos validators",   phase: 3 },
  { layer: "Data Streaming",       tech: "Redis + WebSockets",  phase: 1 },
  { layer: "Frontend",             tech: "React 19 / Tailwind", phase: 1 },
];

const PHASE_COLOR: Record<number, string> = {
  1: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  2: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  3: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  4: "text-purple-400 bg-purple-500/10 border-purple-500/30",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: ItemStatus }) {
  const meta = STATUS_META[status];
  const colorMap: Record<ItemStatus, string> = {
    done:          "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    "in-progress": "bg-amber-500/15 text-amber-400 border-amber-500/30",
    planned:       "bg-blue-500/15 text-blue-400 border-blue-500/30",
    vision:        "bg-purple-500/15 text-purple-400 border-purple-500/30",
  };
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded border ${colorMap[status]}`}>
      <meta.icon className="w-2.5 h-2.5" />
      {meta.label}
    </span>
  );
}

function PhaseCard({ phase, defaultOpen }: { phase: RoadmapPhase; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const done = phase.items.filter(i => i.status === "done").length;
  const total = phase.items.length;
  const pct = Math.round((done / total) * 100);

  return (
    <Card className={`border ${phase.borderColor} ${phase.bgColor}  ${phase.glowColor}`}>
      <CardHeader
        className="pb-4 cursor-pointer select-none"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-start justify-between gap-4">
          <div className={`w-10 h-10 rounded-xl border ${phase.borderColor} ${phase.bgColor} flex items-center justify-center shrink-0`}>
            <phase.icon className={`w-5 h-5 ${phase.color}`} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-mono font-bold uppercase tracking-wider ${phase.color}`}>
                Phase {phase.phase}
              </span>
              <Badge className={`text-[10px] uppercase border ${
                phase.status === 'complete' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                phase.status === 'active'   ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' :
                'bg-blue-500/10 text-blue-400 border-blue-500/30'
              }`}>
                {phase.status}
              </Badge>
            </div>
            <h3 className="text-lg font-bold text-white truncate">{phase.title}</h3>
            <p className="text-xs text-gray-400 truncate">{phase.subtitle}</p>

            <div className="mt-3 flex items-center gap-3">
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    phase.status === "complete" ? "bg-emerald-500" :
                    phase.status === "active"   ? "bg-amber-500"   :
                    "bg-blue-500"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs font-mono text-gray-500 shrink-0">
                {done}/{total} <span className={phase.color}>({pct}%)</span>
              </span>
            </div>

            <div className="flex items-center gap-2 mt-2">
              <Clock className="w-3 h-3 text-gray-500" />
              <span className="text-xs text-gray-500">{phase.eta}</span>
            </div>
          </div>

          <button className={`p-1 rounded ${phase.color} opacity-60 hover:opacity-100 transition-opacity shrink-0`}>
            {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        <div className="flex flex-wrap gap-1.5 mt-3 ml-14">
          {phase.techStack.map(t => (
            <span key={t} className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 border border-gray-700 text-gray-400">
              {t}
            </span>
          ))}
        </div>
      </CardHeader>

      {open && (
        <CardContent className="pt-0">
          {phase.architectureNote && (
            <div className={`ml-14 mb-4 p-3 rounded-lg border ${phase.borderColor} ${phase.bgColor} text-xs text-gray-300 leading-relaxed`}>
              {phase.architectureNote}
            </div>
          )}

          <div className="ml-14 space-y-2">
            {phase.items.map((item, i) => (
              <div
                key={i}
                className={`flex items-start gap-3 p-2.5 rounded-lg transition-colors ${
                  item.status === "done" ? "bg-emerald-500/5 border border-emerald-500/10" : "border border-transparent hover:bg-gray-800/40"
                }`}
              >
                <item.icon className={`w-4 h-4 mt-0.5 shrink-0 ${STATUS_META[item.status].color}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-sm ${item.status === "done" ? "text-white" : "text-gray-300"}`}>
                      {item.label}
                    </span>
                    <StatusBadge status={item.status} />
                  </div>
                  {item.detail && (
                    <p className="text-xs text-gray-500 mt-0.5">{item.detail}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RoadmapPage() {
  const { data: config } = usePublicConfig();
  const platformVersion = config?.platform?.version || "5.5.0";
  const totalDone    = PHASES.flatMap(p => p.items).filter(i => i.status === "done").length;
  const totalItems   = PHASES.flatMap(p => p.items).length;
  const inProgress   = PHASES.flatMap(p => p.items).filter(i => i.status === "in-progress").length;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-xs font-mono text-primary uppercase tracking-widest">
          <Rocket className="w-3 h-3" /> Ecosystem Roadmap v{platformVersion}
        </div>
        <h1 className="text-3xl md:text-4xl font-bold text-white">
          VIT Analytics Network
        </h1>
        <p className="text-gray-400 max-w-2xl mx-auto text-sm leading-relaxed">
          From AI-native prediction infrastructure to a sovereign Cosmos app-chain.
          An AI-native blockchain built for analytics coordination — not just transactions.
        </p>
      </div>

      {/* ── Progress stats ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Shipped",      value: totalDone,            color: "text-emerald-400", bg: "border-emerald-500/20 bg-emerald-500/5",  icon: CheckCircle2 },
          { label: "Building",     value: inProgress,           color: "text-amber-400",   bg: "border-amber-500/20 bg-amber-500/5",      icon: Clock },
          { label: "Total Items",  value: totalItems,           color: "text-blue-400",    bg: "border-blue-500/20 bg-blue-500/5",        icon: Layers },
          { label: "Phases",       value: PHASES.length,        color: "text-purple-400",  bg: "border-purple-500/20 bg-purple-500/5",    icon: GitBranch },
        ].map(s => (
          <div key={s.label} className={`border rounded-xl p-4 text-center ${s.bg}`}>
            <s.icon className={`w-5 h-5 mx-auto mb-1 ${s.color}`} />
            <div className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</div>
            <div className="text-xs text-gray-500 font-mono">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Timeline connector label ────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-gradient-to-r from-emerald-500/30 via-amber-500/20 via-blue-500/20 to-purple-500/30" />
        <span className="text-xs font-mono text-gray-500 uppercase tracking-widest shrink-0">Build Timeline</span>
        <div className="h-px flex-1 bg-gradient-to-l from-emerald-500/30 via-amber-500/20 via-blue-500/20 to-purple-500/30" />
      </div>

      {/* ── Phase cards ────────────────────────────────────────────── */}
      <div className="space-y-4">
        {PHASES.map((phase, i) => (
          <div key={phase.id} className="relative">
            {/* Vertical connector between phases */}
            {i < PHASES.length - 1 && (
              <div className="absolute left-5 top-full w-px h-4 bg-gradient-to-b from-gray-600 to-transparent z-10" />
            )}
            <PhaseCard phase={phase} defaultOpen={phase.status === "complete" || phase.status === "active"} />
          </div>
        ))}
      </div>

      {/* ── Architecture stack table ────────────────────────────────── */}
      <Card className="bg-gray-900 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-base">
            <Cpu className="w-4 h-4 text-cyan-400" /> Target Architecture Stack
          </CardTitle>
          <p className="text-xs text-gray-400">
            The full recommended stack for VIT as an AI-native sovereign chain.
            Phase column shows when each layer comes online.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {ARCH_STACK.map(row => (
              <div key={row.layer} className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-800/50 border border-gray-800">
                <div>
                  <span className="text-xs text-gray-500 font-mono">{row.layer}</span>
                  <div className="text-sm text-white font-medium">{row.tech}</div>
                </div>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${PHASE_COLOR[row.phase]}`}>
                  P{row.phase}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ── On-chain vs Off-chain ───────────────────────────────────── */}
      <div className="grid md:grid-cols-2 gap-4">
        {[
          {
            title: "On-Chain (Phase 3+)",
            color: "text-blue-400",
            border: "border-blue-500/30 bg-blue-500/5",
            icon: Blocks,
            items: [
              "Staking + validator bonding",
              "Governance proposals + votes",
              "Reputation scores",
              "Treasury management",
              "Oracle proof anchoring",
              "Validator performance scoring",
              "AI result hashes (not inference)",
              "Prediction settlement",
            ],
          },
          {
            title: "Off-Chain (Always)",
            color: "text-emerald-400",
            border: "border-emerald-500/30 bg-emerald-500/5",
            icon: Brain,
            items: [
              "AI model training + inference",
              "Monte Carlo simulations",
              "Neural network computation",
              "Large-scale analytics",
              "Real-time prediction engine",
              "Agent orchestration",
              "Kafka event streaming",
              "ML feature engineering",
            ],
          },
        ].map(col => (
          <Card key={col.title} className={`border ${col.border}`}>
            <CardHeader className="pb-3">
              <CardTitle className={`text-sm flex items-center gap-2 ${col.color}`}>
                <col.icon className="w-4 h-4" /> {col.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1.5">
                {col.items.map(item => (
                  <div key={item} className="flex items-center gap-2 text-xs text-gray-300">
                    <ArrowRight className={`w-3 h-3 shrink-0 ${col.color} opacity-60`} />
                    {item}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── Legend ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap justify-center gap-4 pt-2">
        {Object.entries(STATUS_META).map(([key, meta]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs text-gray-500">
            <meta.icon className={`w-3.5 h-3.5 ${meta.color}`} />
            <span>{meta.label}</span>
          </div>
        ))}
      </div>

    </div>
  );
}
