export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  admin_role?: string;
  tier?: string;
  subscription_tier?: string;
  merit_score?: number;
  current_streak?: number;
  vitcoin_balance?: number;
  permissions?: string[];
}

export interface Match {
  id: string;
  home_team: string;
  away_team: string;
  kickoff_time: string;
  status: string;
  competition?: string;
  league?: string;
  odds?: { home: number; draw: number; away: number };
  market_type?: string;
}

export interface Prediction {
  id: string;
  match_id: string;
  prediction_side: string;
  confidence: number;
  reasoning?: string;
}

export interface Wallet {
  vitcoin_balance: number;
  total_balance_usd: number;
  usdt_balance: number;
  ngn_balance: number;
  pi_balance: number;
}

export interface Transaction {
  id: string;
  type: string;
  amount: number;
  created_at: string;
}

export interface Validator {
  id: string;
  username: string;
  influence_score: number;
  accuracy_rate: number;
}

export interface TrainingJob {
  id: string;
  type: string;
  status: string;
  progress: number;
}

export interface DashboardSummary {
  vit_balance: number;
  ensemble_accuracy: number;
}

export interface StorageStats {
  total_stored_bytes: number;
  total_capacity_bytes: number;
  total_stored_gb: number;
  total_capacity_gb: number;
  utilization_pct: number;
}
