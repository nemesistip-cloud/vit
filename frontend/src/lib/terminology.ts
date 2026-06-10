export const TERMS = {
  platform: {
    name: "VIT Network",
    shortName: "VIT Network",
    tagline: "Institutional-Grade Sports Intelligence",
    version: "v5.5.0",
  },
  tiers: {
    free: "Free",
    analyst: "Analyst",
    pro: "Pro",
    validator: "Validator",
    elite: "Pro",
    viewer: "Free",
  },
  currency: {
    name: "VITCoin",
    symbol: "VIT",
  },
  signals: {
    high: "Elite Signal",
    edge: "Edge",
    clv: "CLV",
    accumulator: "Multi-Signal Accumulator",
  },
  wallet: {
    fund: "Fund Account",
    withdraw: "Transfer Out",
    stake: "Lock to Network",
    unstake: "Release Stake",
  },
  agents: {
    "live-match-tracker": "Live Match Tracker",
    "match-scout": "Pre-Match Scout Agent",
    "news-sentinel": "Injury & News Sentinel",
    "odds-anomaly": "Market Anomaly Detector",
    "analytics-reporter": "Daily Analytics Agent",
    "performance-monitor": "Model Performance Monitor",
    "weight-optimizer": "Weight Calibration Agent",
    "retrain-trigger": "Retraining Trigger Agent",
    "fixture-gap": "Fixture Gap Scanner",
    "accumulator-publisher": "Accumulator Publisher Agent",
    "revenue-optimizer": "Revenue Optimizer",
    "governance-executor": "Protocol Execution Agent",
    "self-healing": "Network Self-Healing Agent",
    "audit-sentinel": "Security Audit Agent",
    "prediction-moderator": "Signal Moderation Agent",
    "kyc-screener": "Identity Screening Agent",
    "fraud-review": "Fraud Review Agent",
    "withdrawal-gatekeeper": "Withdrawal Risk Agent",
    "marketplace-audit": "Marketplace Audit Agent",
    "model-promoter": "Model Promotion Agent",
    "oracle-node": "Oracle Submission Agent",
    "network-guardian": "Network Guardian Agent",
  },
  statuses: {
    live: "LIVE",
    upcoming: "UPCOMING",
    completed: "COMPLETED",
    pending: "PENDING",
    failed: "FAILED",
    processing: "PROCESSING",
  },
} as const;

// Helper: get canonical agent display name
export function agentDisplayName(nodeId: string): string {
  const key = nodeId.replace("did:vit:agent:", "") as keyof typeof TERMS.agents;
  return TERMS.agents[key] ?? nodeId;
}

// Helper: get tier badge classes
export function tierClasses(tier: string): string {
  const map: Record<string, string> = {
    free:      "text-zinc-400 border-zinc-600",
    analyst:   "text-blue-400 border-blue-500/40 bg-blue-500/10",
    pro:       "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
    elite:     "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
    validator: "text-amber-400 border-amber-500/40 bg-amber-500/10",
  };
  return map[tier?.toLowerCase()] ?? map.free;
}

// Helper: get confidence colour
export function confidenceColor(pct: number): string {
  if (pct >= 0.8) return "text-emerald-400";
  if (pct >= 0.6) return "text-yellow-400";
  return "text-zinc-400";
}
