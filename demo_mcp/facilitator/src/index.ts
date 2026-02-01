/**
 * Standalone x402 facilitator (Aptos + EVM).
 * POST /verify, POST /settle, GET /supported, GET /health.
 * Optional: PayTo allowlist (FACILITATOR_MODE=creditnexus).
 */

import "dotenv/config";
import cors from "cors";
import express from "express";
import { verifyAptos, settleAptos, getFeePayerAddress } from "./aptos.js";
import { verifyEvm, settleEvm } from "./evm.js";
import type {
  PaymentPayload,
  PaymentRequirements,
  VerifyResponse,
} from "./types.js";

const PORT = Number(process.env.PORT) || 4022;
const FACILITATOR_MODE = (process.env.FACILITATOR_MODE || "community").toLowerCase();
const PAY_TO_ALLOWLIST = (process.env.PAY_TO_ALLOWLIST || "")
  .split(",")
  .map((s) => s.trim().toLowerCase().replace(/^0x/, ""))
  .filter(Boolean);
const USE_FACILITATOR_PREFIX = process.env.USE_FACILITATOR_PREFIX === "true";

/** Normalize Aptos/EVM address to 64-char hex for comparison (short vs long form). */
function normalizePayTo(addr: string): string {
  const hex = (addr || "").replace(/^0x/, "").toLowerCase();
  if (hex.length >= 64) return hex.slice(-64);
  return hex.padStart(64, "0");
}

function checkPayToAllowlist(payTo: string): boolean {
  if (FACILITATOR_MODE !== "creditnexus" || PAY_TO_ALLOWLIST.length === 0) {
    return true;
  }
  const norm = normalizePayTo(payTo);
  return PAY_TO_ALLOWLIST.some((entry) => normalizePayTo(entry) === norm);
}

const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));

const verifyHandler = async (
  req: express.Request,
  res: express.Response
): Promise<void> => {
  const paymentPayload: PaymentPayload =
    req.body.paymentPayload ?? req.body.payment_payload;
  const paymentRequirements: PaymentRequirements =
    req.body.paymentRequirements ?? req.body.payment_requirements;
  if (!paymentPayload || !paymentRequirements) {
    res.status(400).json({
      isValid: false,
      payer: "",
      invalidReason: "missing_payment_payload_or_requirements",
    });
    return;
  }
  const payTo =
    paymentRequirements.payTo ?? (paymentPayload as unknown as { payTo?: string }).payTo;
  if (!checkPayToAllowlist(payTo || "")) {
    res.status(200).json({
      isValid: false,
      payer: "",
      invalidReason: "pay_to_not_allowed",
    });
    return;
  }
  const network =
    (paymentPayload.network ?? paymentRequirements.network ?? "").toLowerCase();
  if (network.startsWith("eip155:")) {
    const result = await verifyEvm(paymentPayload, paymentRequirements);
    res.status(200).json(result);
    return;
  }
  if (!network.startsWith("aptos:")) {
    res.status(501).json({
      isValid: false,
      payer: "",
      invalidReason: "unsupported_network",
    });
    return;
  }
  const result = await verifyAptos(paymentPayload, paymentRequirements);
  res.status(200).json(result);
};

const settleHandler = async (
  req: express.Request,
  res: express.Response
): Promise<void> => {
  const paymentPayload: PaymentPayload =
    req.body.paymentPayload ?? req.body.payment_payload;
  const verification: VerifyResponse =
    req.body.verification ?? req.body.verification_result;
  const paymentRequirements: PaymentRequirements =
    req.body.paymentRequirements ?? req.body.payment_requirements;
  if (!paymentPayload || !verification?.isValid) {
    res.status(400).json({
      success: false,
      errorReason: "missing_payload_or_invalid_verification",
    });
    return;
  }
  const reqs = paymentRequirements ?? {};
  const payTo = reqs.payTo ?? "";
  if (!checkPayToAllowlist(payTo)) {
    res.status(400).json({
      success: false,
      errorReason: "pay_to_not_allowed",
    });
    return;
  }
  const network = (paymentPayload.network ?? reqs.network ?? "").toLowerCase();
  if (network.startsWith("eip155:")) {
    const result = await settleEvm(paymentPayload, reqs, verification);
    res.status(200).json(result);
    return;
  }
  const result = await settleAptos(paymentPayload, reqs, verification);
  res.status(200).json(result);
};

const supportedHandler = (_req: express.Request, res: express.Response): void => {
  const feePayer = getFeePayerAddress();
  res.status(200).json({
    kinds: [
      { x402Version: 2, scheme: "exact", network: "aptos:2", extra: { sponsored: true } },
      { x402Version: 2, scheme: "exact", network: "aptos:1", extra: { sponsored: true } },
      { x402Version: 2, scheme: "exact", network: "eip155:84532", extra: { sponsored: false } },
      { x402Version: 2, scheme: "exact", network: "eip155:8453", extra: { sponsored: false } },
    ],
    signers: {
      "aptos:2": feePayer,
      "aptos:1": feePayer,
      "eip155:84532": process.env.EVM_RELAYER_PRIVATE_KEY ? "relayer" : "",
      "eip155:8453": process.env.EVM_RELAYER_PRIVATE_KEY ? "relayer" : "",
    },
  });
};

const healthHandler = (_req: express.Request, res: express.Response): void => {
  res.status(200).json({ status: "ok" });
};

if (USE_FACILITATOR_PREFIX) {
  app.post("/facilitator/verify", verifyHandler);
  app.post("/facilitator/settle", settleHandler);
  app.get("/facilitator/supported", supportedHandler);
  app.get("/facilitator/health", healthHandler);
}
app.post("/verify", verifyHandler);
app.post("/settle", settleHandler);
app.get("/supported", supportedHandler);
app.get("/health", healthHandler);

app.listen(PORT, () => {
  console.log(`x402-facilitator listening on port ${PORT}`);
});
