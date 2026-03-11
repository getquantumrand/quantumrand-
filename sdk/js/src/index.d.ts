export class QuantumRandError extends Error {
  statusCode: number;
  requestId: string;
  constructor(message: string, statusCode?: number, requestId?: string);
}

export interface ClientOptions {
  apiKey: string;
  baseUrl?: string;
  backend?: "aer_simulator" | "origin_cloud" | "origin_wuyuan" | "ibm_hardware";
  timeout?: number;
  hmacSecret?: string;
}

export interface BatchRequest {
  type: "bits" | "hex" | "integer" | "key";
  params?: Record<string, any>;
}

export interface BatchResult {
  index: number;
  type: string;
  data?: Record<string, any>;
  error?: string;
}

export interface WebhookResponse {
  job_id: string;
  callback_url: string;
  type: string;
  status: string;
  message: string;
}

export interface UsageStats {
  total_calls: number;
  total_bits: number;
  calls_today: number;
  calls_this_month: number;
  tier: string;
  rate_limit: { calls_per_day: number; max_bits: number };
}

export interface KeyInfo {
  name: string;
  email: string;
  tier: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  rate_limit: { calls_per_day: number; max_bits: number };
}

export interface HealthStatus {
  status: string;
  environment: string;
  version: string;
  uptime_seconds: number;
  database: string;
  quantum_engine: string;
}

export class QuantumRandClient {
  constructor(options: ClientOptions);
  bits(n?: number): Promise<string>;
  hex(n?: number): Promise<string>;
  integer(min?: number, max?: number): Promise<number>;
  key(bits?: number): Promise<string>;
  batch(requests: BatchRequest[]): Promise<BatchResult[]>;
  webhook(callbackUrl: string, type?: string, params?: Record<string, any>): Promise<WebhookResponse>;
  stats(): Promise<UsageStats>;
  me(): Promise<KeyInfo>;
  health(): Promise<HealthStatus>;
}
