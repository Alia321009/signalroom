// Mirrors app/schemas.py -- hand-maintained, not codegen'd.

export interface Subscription {
  tier: "none" | "broker_referral" | "paid" | "trial";
  status: "pending" | "active" | "expired" | "revoked";
  broker: "exness" | "xm" | null;
  paid_until: string | null;
  last_trade_activity_at: string | null;
}

export interface Member {
  id: number;
  email: string;
  role: "admin" | "member";
  is_active: boolean;
  created_at: string;
  subscription: Subscription | null;
}

export type CallStatus =
  | "pending"
  | "active"
  | "tp1_hit"
  | "tp2_hit"
  | "tp3_hit"
  | "sl_hit"
  | "expired"
  | "cancelled";

export interface Call {
  id: number;
  created_by: number;
  symbol: string;
  direction: "buy" | "sell";
  entry: number;
  sl: number;
  tp1: number;
  tp2: number | null;
  tp3: number | null;
  valid_until: string;
  status: CallStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  outcome_r: number | null;
}

export interface PublicCall {
  id: number;
  symbol: string;
  direction: "buy" | "sell";
  status: CallStatus;
  outcome_r: number | null;
  closed_at: string | null;
}

export interface BotSettings {
  enabled: boolean;
  risk_pct: number;
  max_daily_loss_pct: number;
  symbols: string[];
  magic: number;
}

export type WsMessage = { type: "call_new" | "call_updated"; call: Call };
