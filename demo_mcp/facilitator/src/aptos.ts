/**
 * Aptos verify and settle for x402 facilitator.
 * Verify: deserialize BCS payload, validate 0x1::primary_fungible_store::transfer, simulate.
 * Settle: attach fee payer, sign as fee payer, submit, wait.
 */

import {
  Account,
  Aptos,
  AptosConfig,
  Deserializer,
  Network,
  RawTransaction,
  SimpleTransaction,
  TransactionPayloadEntryFunction,
  AccountAuthenticator,
  AccountAddress,
  Ed25519PrivateKey,
  U64,
} from "@aptos-labs/ts-sdk";
import type {
  PaymentPayload,
  PaymentRequirements,
  VerifyResponse,
  SettleResponse,
} from "./types.js";

const APTOS_NETWORK = process.env.APTOS_NETWORK || "testnet";
const APTOS_FULLNODE_URL =
  process.env.APTOS_FULLNODE_URL ||
  "https://fullnode.testnet.aptoslabs.com/v1";
const APTOS_PRIVATE_KEY = process.env.APTOS_PRIVATE_KEY || "";
const ENABLE_WALLET_CHECK = process.env.ENABLE_WALLET_CHECK === "true";
const ONRAMP_URL = process.env.ONRAMP_URL || "";

const TRANSFER_FUNCTION = "0x1::primary_fungible_store::transfer";
const SUPPORTED_NETWORKS = ["aptos:2", "aptos:1"];

function getAptosClient(): Aptos {
  const network =
    APTOS_NETWORK === "mainnet" ? Network.MAINNET : Network.TESTNET;
  const config = new AptosConfig({
    network,
    fullnode: APTOS_FULLNODE_URL,
  });
  return new Aptos(config);
}

function normalizePayTo(addr: string): string {
  return (addr || "").replace(/^0x/, "").toLowerCase();
}

function parsePayload(paymentPayload: PaymentPayload): {
  transaction: Uint8Array;
  senderAuthenticator: Uint8Array;
} {
  const raw = paymentPayload.payload;
  let txBytes: number[];
  let authBytes: number[];
  if (typeof raw === "string") {
    try {
      const decoded = Buffer.from(raw, "base64").toString("utf8");
      const parsed = JSON.parse(decoded) as {
        transaction: number[];
        senderAuthenticator: number[];
      };
      txBytes = parsed.transaction;
      authBytes = parsed.senderAuthenticator;
    } catch {
      const parsed = JSON.parse(raw) as {
        transaction: number[];
        senderAuthenticator: number[];
      };
      txBytes = parsed.transaction;
      authBytes = parsed.senderAuthenticator;
    }
  } else {
    const obj = raw as { transaction: number[]; senderAuthenticator: number[] };
    txBytes = obj.transaction;
    authBytes = obj.senderAuthenticator;
  }
  return {
    transaction: new Uint8Array(txBytes),
    senderAuthenticator: new Uint8Array(authBytes),
  };
}

function getEntryFunctionFullName(entry: {
  module_name: { address: { toString(): string }; name: { identifier: string } };
  function_name: { identifier: string };
}): string {
  const mod = entry.module_name;
  const modStr = `${mod.address.toString()}::${mod.name.identifier}`;
  return `${modStr}::${entry.function_name.identifier}`;
}

function getRecipientAndAmount(entry: {
  args: Array<{ value: { value: Uint8Array } }>;
}): { recipient: string; amount: bigint } | null {
  if (entry.args.length < 3) return null;
  try {
    const addrBytes = entry.args[0].value.value;
    const amountBytes = entry.args[2].value.value;
    const recipient = AccountAddress.deserialize(new Deserializer(addrBytes));
    const amount = U64.deserialize(new Deserializer(amountBytes));
    return { recipient: recipient.toString(), amount: amount.value };
  } catch {
    return null;
  }
}

/**
 * Verify Aptos payment payload against payment requirements.
 * Deserializes BCS, validates primary_fungible_store::transfer, simulates.
 */
export async function verifyAptos(
  paymentPayload: PaymentPayload,
  paymentRequirements: PaymentRequirements
): Promise<VerifyResponse> {
  const scheme = (
    paymentPayload.scheme || paymentRequirements.scheme || ""
  ).toLowerCase();
  const network = (
    paymentPayload.network || paymentRequirements.network || ""
  ).toLowerCase();
  if (scheme !== "aptos" && scheme !== "exact") {
    return { isValid: false, payer: "", invalidReason: "invalid_scheme" };
  }
  if (!SUPPORTED_NETWORKS.includes(network)) {
    return { isValid: false, payer: "", invalidReason: "invalid_network" };
  }

  try {
    const { transaction: txBytes, senderAuthenticator: authBytes } =
      parsePayload(paymentPayload);
    const deserializerTx = new Deserializer(txBytes);
    const rawTxn = RawTransaction.deserialize(deserializerTx);
    const deserializerAuth = new Deserializer(authBytes);
    const authenticator = AccountAuthenticator.deserialize(deserializerAuth);

    const sender = rawTxn.sender;
    const payer = sender.toString();

    const payload = rawTxn.payload;
    if (!(payload instanceof TransactionPayloadEntryFunction)) {
      return { isValid: false, payer: "", invalidReason: "invalid_payload_type" };
    }
    const entry = payload.entryFunction;
    const fnName = getEntryFunctionFullName(entry);
    if (fnName !== TRANSFER_FUNCTION) {
      return {
        isValid: false,
        payer: "",
        invalidReason: "invalid_function",
      };
    }
    if (entry.type_args.length < 1 || entry.args.length < 3) {
      return {
        isValid: false,
        payer: "",
        invalidReason: "invalid_args",
      };
    }
    const recipientAmount = getRecipientAndAmount(
      entry as unknown as { args: Array<{ value: { value: Uint8Array } }> }
    );
    if (!recipientAmount) {
      return {
        isValid: false,
        payer: "",
        invalidReason: "invalid_args",
      };
    }
    const { recipient, amount } = recipientAmount;
    const requiredAmount = BigInt(
      typeof paymentRequirements.amount === "number"
        ? paymentRequirements.amount
        : String(paymentRequirements.amount)
    );
    const payToNorm = normalizePayTo(paymentRequirements.payTo);
    const recipientNorm = normalizePayTo(recipient);
    if (recipientNorm !== payToNorm) {
      return {
        isValid: false,
        payer: "",
        invalidReason: "pay_to_mismatch",
      };
    }
    if (amount < requiredAmount) {
      return {
        isValid: false,
        payer: "",
        invalidReason: "amount_insufficient",
      };
    }

    const aptos = getAptosClient();
    const simpleTxn = new SimpleTransaction(rawTxn);
    const signerPublicKey = authenticator.isEd25519()
      ? authenticator.public_key
      : (authenticator as unknown as { public_key: Parameters<typeof aptos.transaction.simulate.simple>[0]["signerPublicKey"] }).public_key;
    try {
      await aptos.transaction.simulate.simple({
        signerPublicKey,
        transaction: simpleTxn,
      });
    } catch {
      if (ENABLE_WALLET_CHECK) {
        return {
          isValid: false,
          payer,
          invalidReason: "insufficient_funds",
          onramp_url: ONRAMP_URL || undefined,
        };
      }
      return {
        isValid: false,
        payer: "",
        invalidReason: "simulation_failed",
      };
    }

    return { isValid: true, payer };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return {
      isValid: false,
      payer: "",
      invalidReason: `verify_error: ${msg}`,
    };
  }
}

/**
 * Settle Aptos payment: re-verify, attach fee payer, sign, submit, wait.
 */
export async function settleAptos(
  paymentPayload: PaymentPayload,
  paymentRequirements: PaymentRequirements,
  verifyResponse: VerifyResponse
): Promise<SettleResponse> {
  if (!verifyResponse.isValid) {
    return {
      success: false,
      errorReason: verifyResponse.invalidReason || "invalid_verification",
    };
  }
  if (!APTOS_PRIVATE_KEY) {
    return { success: false, errorReason: "missing_aptos_private_key" };
  }

  const verifyAgain = await verifyAptos(paymentPayload, paymentRequirements);
  if (!verifyAgain.isValid) {
    return {
      success: false,
      errorReason: verifyAgain.invalidReason || "reverify_failed",
    };
  }

  try {
    const { transaction: txBytes, senderAuthenticator: authBytes } =
      parsePayload(paymentPayload);
    const deserializerTx = new Deserializer(txBytes);
    const rawTxn = RawTransaction.deserialize(deserializerTx);
    const deserializerAuth = new Deserializer(authBytes);
    const senderAuthenticator =
      AccountAuthenticator.deserialize(deserializerAuth);

    const privateKey = new Ed25519PrivateKey(APTOS_PRIVATE_KEY, false);
    const feePayerAccount = Account.fromPrivateKey({ privateKey });
    const aptos = getAptosClient();

    const simpleTxn = new SimpleTransaction(
      rawTxn,
      feePayerAccount.accountAddress
    );
    const feePayerAuthenticator = aptos.transaction.signAsFeePayer({
      signer: feePayerAccount,
      transaction: simpleTxn,
    });

    const pending = await aptos.transaction.submit.simple({
      transaction: simpleTxn,
      senderAuthenticator,
      feePayerAuthenticator,
    });
    await aptos.waitForTransaction({ transactionHash: pending.hash });
    return {
      success: true,
      transaction: pending.hash,
      network: paymentRequirements.network,
      payer: verifyResponse.payer,
    };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return {
      success: false,
      errorReason: `settle_error: ${msg}`,
    };
  }
}

export function getFeePayerAddress(): string {
  if (!APTOS_PRIVATE_KEY) return "";
  try {
    const privateKey = new Ed25519PrivateKey(APTOS_PRIVATE_KEY, false);
    const acc = Account.fromPrivateKey({ privateKey });
    return acc.accountAddress.toString();
  } catch {
    return "";
  }
}
