export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  admin_role?: string | null;
  subscription_tier: string;
  is_banned?: boolean;
  is_active: boolean;
  is_verified?: boolean;
  created_at: string;
  last_login?: string | null;
  permissions?: string[];
}

export interface Match {
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff_time: string;
  status?: string;
  home_goals?: number | null;
  away_goals?: number | null;
  home_prob?: number | null;
  draw_prob?: number | null;
  away_prob?: number | null;
  over_25_prob?: number | null;
  under_25_prob?: number | null;
  btts_prob?: number | null;
  no_btts_prob?: number | null;
  consensus_prob?: number | null;
  recommended_stake?: number | null;
  final_ev?: number | null;
  edge?: number | null;
  confidence?: number | null;
  bet_side?: string | null;
  entry_odds?: number | null;
  actual_outcome?: string | null;
  ft_score?: string | null;
  clv?: number | null;
  profit?: number | null;
  timestamp?: string | null;
  odds?: { home?: number | null; draw?: number | null; away?: number | null } | null;
  predictions_count?: number;
  enabled_markets?: any[];
  model_contributions?: any[];
  model_summary?: any;
  consensus_breakdown?: any;
  recent_form?: any;
  head_to_head?: any;
}

export interface Prediction {
  id?: string;
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff_time: string;
  home_prob?: number;
  draw_prob?: number;
  away_prob?: number;
  bet_side?: string;
  confidence?: number;
  edge?: number;
  entry_odds?: number;
  recommended_stake?: number;
  final_ev?: number;
  consensus_prob?: number;
  over_25_prob?: number;
  under_25_prob?: number;
  btts_prob?: number;
  no_btts_prob?: number;
  actual_outcome?: string;
  ft_score?: string;
  clv?: number;
  profit?: number;
  timestamp?: string;
  created_at?: string;
}

export interface Wallet {
  ngn_balance: number;
  usd_balance: number;
  usdt_balance: number;
  pi_balance: number;
  vitcoin_balance: number;
  is_frozen: boolean;
  kyc_verified: boolean;
}

export interface Transaction {
  id: string;
  type: string;
  currency: string;
  amount: number;
  direction: string;
  status: string;
  reference?: string;
  fee_amount: number;
  created_at: string;
}

export interface Validator {
  username: string;
  trust_score: number;
  stake: number;
  total_predictions: number;
  accuracy_rate: number;
  influence_score: number;
  joined_at: string;
}

export interface TrainingJob {
  job_id: string;
  status: string;
  avg_accuracy?: number | null;
  avg_over_under_accuracy?: number | null;
  models_trained?: number;
  models_failed?: number;
  version?: string | null;
  is_production?: boolean;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  summary?: Record<string, unknown>;
}

export interface DashboardSummary {
  total_predictions: number;
  accuracy_rate: number;
  roi: number;
  active_matches: number;
  wallet_balance: number;
}
