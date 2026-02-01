/**
 * EVM (EIP-3009) verify and settle for x402 facilitator.
 * Verify: recover signer from TransferWithAuthorization signature, validate amount/payTo/validBefore.
 * Settle: call receiveWithAuthorization on token contract (relayer pays gas).
 */

import {
  createPublicClient,
  createWalletClient,
  http,
  type Chain,
  recoverTypedDataAddress,
  encodeFunctionData,
} from "viem";
import { privateKeyToAccount } from "viem/accounts";
import type {
  PaymentPayload,
  PaymentRequirements,
  VerifyResponse,
  SettleResponse,
} from "./types.js";

const baseSepolia = {
  id: 84532,
  name: "Base Sepolia",
  nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 },
  rpcUrls: {
    default: { http: ["https://sepolia.base.org"] },
  },
  blockExplorers: {
    default: { name: "BaseScan", url: "https://sepolia.basescan.org" },
  },
} as const satisfies Chain;

const base = {
  id: 8453,
  name: "Base",
  nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 },
  rpcUrls: {
    default: { http: ["https://mainnet.base.org"] },
  },
  blockExplorers: {
    default: { name: "BaseScan", url: "https://basescan.org" },
  },
} as const satisfies Chain;

const EIP3009_DOMAIN = {
  name: "USD Coin",
  version: "2",
} as const;

const EIP3009_TYPES = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" },
  ],
} as const;

const EVM_RELAYER_PRIVATE_KEY = process.env.EVM_RELAYER_PRIVATE_KEY || "";
const BASE_SEPOLIA_RPC = process.env.BASE_SEPOLIA_RPC || "https://sepolia.base.org";
const BASE_RPC = process.env.BASE_RPC || "https://mainnet.base.org";
const ENABLE_WALLET_CHECK = process.env.ENABLE_WALLET_CHECK === "true";
const ONRAMP_URL = process.env.ONRAMP_URL || "";

const SUPPORTED_EVM_NETWORKS = ["eip155:84532", "eip155:8453"];

function getEvmPayload(paymentPayload: PaymentPayload): {
  from: string;
  to: string;
  value: string;
  validAfter: number;
  validBefore: number;
  nonce: string;
  signature: string;
  contract: string;
} {
  const raw = paymentPayload.payload;
  if (typeof raw === "string") {
    const parsed = JSON.parse(
      raw.startsWith("{") ? raw : Buffer.from(raw, "base64").toString("utf8")
    ) as {
      from: string;
      to: string;
      value: string;
      validAfter: number;
      validBefore: number;
      nonce: string;
      signature: string;
      contract: string;
    };
    return parsed;
  }
  return raw as {
    from: string;
    to: string;
    value: string;
    validAfter: number;
    validBefore: number;
    nonce: string;
    signature: string;
    contract: string;
  };
}

function getChainAndRpc(network: string): { chain: Chain; rpc: string } {
  if (network === "eip155:8453") {
    return { chain: base, rpc: BASE_RPC };
  }
  return { chain: baseSepolia, rpc: BASE_SEPOLIA_RPC };
}

function normalizeEvmAddress(addr: string): string {
  return (addr || "").replace(/^0x/, "").toLowerCase();
}

/**
 * Verify EVM (EIP-3009) payment payload.
 */
export async function verifyEvm(
  paymentPayload: PaymentPayload,
  paymentRequirements: PaymentRequirements
): Promise<VerifyResponse> {
  const network = (paymentPayload.network || paymentRequirements.network || "").toLowerCase();
  if (!SUPPORTED_EVM_NETWORKS.includes(network)) {
    return { isValid: false, payer: "", invalidReason: "invalid_network" };
  }

  try {
    const p = getEvmPayload(paymentPayload);
    const { chain, rpc } = getChainAndRpc(network);

    const domain = {
      ...EIP3009_DOMAIN,
      chainId: chain.id,
      verifyingContract: p.contract as `0x${string}`,
    };

    const recovered = await recoverTypedDataAddress({
      domain,
      types: EIP3009_TYPES,
      primaryType: "TransferWithAuthorization",
      message: {
        from: p.from as `0x${string}`,
        to: p.to as `0x${string}`,
        value: BigInt(p.value),
        validAfter: BigInt(p.validAfter),
        validBefore: BigInt(p.validBefore),
        nonce: p.nonce as `0x${string}`,
      },
      signature: p.signature as `0x${string}`,
    });

    const fromNorm = normalizeEvmAddress(p.from);
    const recoveredNorm = normalizeEvmAddress(recovered);
    if (recoveredNorm !== fromNorm) {
      return { isValid: false, payer: "", invalidReason: "invalid_signature" };
    }

    const payToNorm = normalizeEvmAddress(paymentRequirements.payTo);
    const toNorm = normalizeEvmAddress(p.to);
    if (toNorm !== payToNorm) {
      return { isValid: false, payer: "", invalidReason: "pay_to_mismatch" };
    }

    const amountVal = BigInt(p.value);
    const requiredAmount = BigInt(
      typeof paymentRequirements.amount === "number"
        ? paymentRequirements.amount
        : String(paymentRequirements.amount)
    );
    if (amountVal < requiredAmount) {
      return { isValid: false, payer: "", invalidReason: "amount_insufficient" };
    }

    const assetNorm = normalizeEvmAddress(paymentRequirements.asset || "");
    const contractNorm = normalizeEvmAddress(p.contract);
    if (assetNorm && contractNorm !== assetNorm) {
      return { isValid: false, payer: "", invalidReason: "asset_mismatch" };
    }

    const now = Math.floor(Date.now() / 1000);
    if (p.validBefore <= now) {
      return { isValid: false, payer: "", invalidReason: "authorization_expired" };
    }

    if (ENABLE_WALLET_CHECK) {
      const client = createPublicClient({
        chain,
        transport: http(rpc),
      });
      const balance = await client.readContract({
        address: p.contract as `0x${string}`,
        abi: [{ name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ name: "account", type: "address" }], outputs: [{ type: "uint256" }] }],
        functionName: "balanceOf",
        args: [p.from as `0x${string}`],
      });
      if (balance < BigInt(p.value)) {
        return {
          isValid: false,
          payer: p.from,
          invalidReason: "insufficient_funds",
          onramp_url: ONRAMP_URL || undefined,
        };
      }
    }

    return { isValid: true, payer: p.from };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { isValid: false, payer: "", invalidReason: `verify_error: ${msg}` };
  }
}

const RECEIVE_WITH_AUTHORIZATION_ABI = [
  {
    name: "receiveWithAuthorization",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "from", type: "address" },
      { name: "to", type: "address" },
      { name: "value", type: "uint256" },
      { name: "validAfter", type: "uint256" },
      { name: "validBefore", type: "uint256" },
      { name: "nonce", type: "bytes32" },
      { name: "v", type: "uint8" },
      { name: "r", type: "bytes32" },
      { name: "s", type: "bytes32" },
    ],
    outputs: [],
  },
] as const;

function signatureToVrs(signature: string): { v: number; r: `0x${string}`; s: `0x${string}` } {
  const hex = signature.startsWith("0x") ? signature.slice(2) : signature;
  if (hex.length !== 130) {
    throw new Error("Invalid signature length");
  }
  const r = (`0x${hex.slice(0, 64)}`) as `0x${string}`;
  const s = (`0x${hex.slice(64, 128)}`) as `0x${string}`;
  const v = parseInt(hex.slice(128, 130), 16);
  const vNorm = v < 27 ? v + 27 : v;
  return { v: vNorm, r, s };
}

/**
 * Settle EVM payment: call receiveWithAuthorization (relayer pays gas).
 */
export async function settleEvm(
  paymentPayload: PaymentPayload,
  paymentRequirements: PaymentRequirements,
  _verifyResponse: VerifyResponse
): Promise<SettleResponse> {
  if (!EVM_RELAYER_PRIVATE_KEY) {
    return { success: false, errorReason: "missing_evm_relayer_private_key" };
  }

  const verifyAgain = await verifyEvm(paymentPayload, paymentRequirements);
  if (!verifyAgain.isValid) {
    return {
      success: false,
      errorReason: verifyAgain.invalidReason || "reverify_failed",
    };
  }

  try {
    const p = getEvmPayload(paymentPayload);
    const { chain, rpc } = getChainAndRpc(
      paymentPayload.network || paymentRequirements.network || "eip155:84532"
    );

    const account = privateKeyToAccount(
      (EVM_RELAYER_PRIVATE_KEY.startsWith("0x")
        ? EVM_RELAYER_PRIVATE_KEY
        : `0x${EVM_RELAYER_PRIVATE_KEY}`) as `0x${string}`
    );

    const walletClient = createWalletClient({
      account,
      chain,
      transport: http(rpc),
    });

    const publicClient = createPublicClient({
      chain,
      transport: http(rpc),
    });

    const { v, r, s } = signatureToVrs(p.signature);

    const data = encodeFunctionData({
      abi: RECEIVE_WITH_AUTHORIZATION_ABI,
      functionName: "receiveWithAuthorization",
      args: [
        p.from as `0x${string}`,
        p.to as `0x${string}`,
        BigInt(p.value),
        BigInt(p.validAfter),
        BigInt(p.validBefore),
        p.nonce as `0x${string}`,
        v,
        r,
        s,
      ],
    });

    const hash = await walletClient.sendTransaction({
      to: p.contract as `0x${string}`,
      data,
      gas: BigInt(150000),
    });

    await publicClient.waitForTransactionReceipt({ hash });
    return {
      success: true,
      transaction: hash,
      network: paymentRequirements.network,
      payer: p.from,
    };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { success: false, errorReason: `settle_error: ${msg}` };
  }
}
