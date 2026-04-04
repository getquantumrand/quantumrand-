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

  // Gaming
  gamingRoll(sides?: number, count?: number): Promise<Record<string, any>>;
  gamingSeed(bits?: number): Promise<Record<string, any>>;
  gamingShuffle(items: any[]): Promise<Record<string, any>>;
  gamingLoot(items: Array<{ name: string; weight: number }>): Promise<Record<string, any>>;
  gamingProvable(gameId: string, roundId: string): Promise<Record<string, any>>;

  // Healthcare
  healthRecordSeal(recordId: string, recordHash: string, providerId: string): Promise<Record<string, any>>;
  healthRxSign(prescriptionId: string, patientHash: string, providerId: string): Promise<Record<string, any>>;
  healthAccessLog(recordId: string, accessorId: string, accessType: string): Promise<Record<string, any>>;
  healthConsentSeal(patientHash: string, consentType: string, providerId: string): Promise<Record<string, any>>;
  healthDeviceId(deviceType: string, manufacturerId: string): Promise<Record<string, any>>;

  // Legal
  legalTimestamp(documentHash: string, documentId: string, partyId: string): Promise<Record<string, any>>;
  legalEvidenceSeal(evidenceId: string, evidenceHash: string, caseId: string): Promise<Record<string, any>>;
  legalContractSign(contractId: string, contractHash: string, signatories: string[]): Promise<Record<string, any>>;
  legalClaimToken(claimId: string, policyId: string, claimantHash: string): Promise<Record<string, any>>;
  legalNotarize(documentHash: string, documentId: string, notaryId: string): Promise<Record<string, any>>;

  // Cybersecurity
  securityKeygen(algorithm?: string, purpose?: string): Promise<Record<string, any>>;
  securityEntropyAudit(sampleSize?: number): Promise<Record<string, any>>;
  securityToken(length?: number, format?: string): Promise<Record<string, any>>;
  securitySalt(length?: number, purpose?: string): Promise<Record<string, any>>;
  securityChallenge(sessionId: string, ttlSeconds?: number): Promise<Record<string, any>>;

  // IoT
  iotDeviceId(deviceType: string, manufacturerId: string, batchId?: string): Promise<Record<string, any>>;
  iotFirmwareSign(firmwareHash: string, deviceType: string, version: string): Promise<Record<string, any>>;
  iotSessionKey(deviceId: string, sessionDurationSeconds?: number): Promise<Record<string, any>>;
  iotProvision(fleetId: string, deviceType: string, provisioningTtlSeconds?: number): Promise<Record<string, any>>;
  iotTelemetrySeal(deviceId: string, dataHash: string, readingCount: number): Promise<Record<string, any>>;

  // Finance
  financeTxid(): Promise<Record<string, any>>;
  financeOtp(digits?: number): Promise<Record<string, any>>;
  financeNonce(ttlSeconds?: number): Promise<Record<string, any>>;
  financeKeypair(): Promise<Record<string, any>>;
  financeAuditSign(payload: any): Promise<Record<string, any>>;
}
