/**
 * Aptos wallet state: load/save key file, expose address and private key for signing.
 * Wallet path: ~/.aptos-agent-wallet.json (chmod 600).
 */

import { existsSync, readFileSync, writeFileSync, chmodSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

const WALLET_PATH = join(homedir(), '.aptos-agent-wallet.json');

/**
 * @returns {{ address: string, privateKey: string, createdAt?: string }|null}
 */
export function load() {
  try {
    if (!existsSync(WALLET_PATH)) return null;
    const data = readFileSync(WALLET_PATH, 'utf8');
    const wallet = JSON.parse(data);
    if (!wallet.privateKey || !wallet.address) throw new Error('Invalid wallet file');
    return wallet;
  } catch (e) {
    throw new Error(`Failed to load Aptos wallet: ${e.message}`);
  }
}

/**
 * @param {{ address: string, privateKey: string, createdAt?: string }} wallet
 */
export function save(wallet) {
  try {
    const data = JSON.stringify(
      { ...wallet, createdAt: wallet.createdAt || new Date().toISOString() },
      null,
      2
    );
    writeFileSync(WALLET_PATH, data, 'utf8');
    chmodSync(WALLET_PATH, 0o600);
  } catch (e) {
    throw new Error(`Failed to save Aptos wallet: ${e.message}`);
  }
}

/**
 * @returns {{ address: string, privateKey: string }}
 */
export function getWallet() {
  const w = load();
  if (!w) throw new Error('No Aptos wallet found. Run setup-aptos.js first.');
  return { address: w.address, privateKey: w.privateKey };
}

export function exists() {
  return existsSync(WALLET_PATH);
}

/**
 * @returns {{ address: string, createdAt: string }|null}
 */
export function getWalletInfo() {
  const w = load();
  if (!w) return null;
  return { address: w.address, createdAt: w.createdAt || '' };
}
