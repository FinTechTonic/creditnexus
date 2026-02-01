/**
 * x402 facilitator API types (verify/settle).
 * Compatible with x402 and CDP-style request/response (camelCase and snake_case).
 */

/** Aptos payload shape: BCS transaction + senderAuthenticator (arrays of bytes). */
export interface AptosPayload {
  transaction: number[];
  senderAuthenticator: number[];
}

export interface PaymentPayload {
  x402Version?: number;
  scheme: string;
  network: string;
  payload: AptosPayload | string; // string = base64 or JSON string
}

export interface PaymentRequirements {
  scheme: string;
  network: string;
  amount: string | number;
  asset: string;
  payTo: string;
  resource?: string;
  description?: string;
  extra?: Record<string, unknown>;
}

export interface VerifyRequest {
  paymentPayload: PaymentPayload;
  paymentRequirements: PaymentRequirements;
}

export interface VerifyResponse {
  isValid: boolean;
  payer: string;
  invalidReason?: string;
}

export interface SettleRequest {
  paymentPayload: PaymentPayload;
  paymentRequirements?: PaymentRequirements;
  verification: VerifyResponse;
}

export interface SettleResponse {
  success: boolean;
  transaction?: string;
  network?: string;
  payer?: string;
  errorReason?: string;
}
