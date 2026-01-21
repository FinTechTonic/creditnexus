/**
 * Block explorer URLs for tx hashes by chain ID.
 * Used for MarketDashboard transaction_hash and CrossChainTimeline dest_tx_hash.
 */

const EXPLORER_BY_CHAIN: Record<number, string> = {
  1: "https://etherscan.io/tx",
  137: "https://polygonscan.com/tx",
  8453: "https://basescan.org/tx",
  84532: "https://sepolia.basescan.org/tx",
  80002: "https://amoy.polygonscan.com/tx",
};

const DEFAULT_CHAIN = 8453; // Base

export function getBlockExplorerTxUrl(txHash: string, chainId?: number): string {
  if (!txHash || typeof txHash !== "string") return "#";
  const base = EXPLORER_BY_CHAIN[chainId ?? DEFAULT_CHAIN] ?? EXPLORER_BY_CHAIN[DEFAULT_CHAIN];
  return `${base}/${txHash.startsWith("0x") ? txHash : "0x" + txHash}`;
}
