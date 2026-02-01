#!/usr/bin/env node
/**
 * Credit agent wallets for demo/testing (Aptos + instructions for EVM).
 * Run from repo root: node demo_mcp/scripts/credit-agent-wallets.mjs
 *
 * Aptos: creates wallet if missing (setup-aptos), then funds on devnet when
 * APTOS_FAUCET_NETWORK=devnet, or prints testnet mint page instructions.
 * Ref: https://canteenapp-aptos-x402.notion.site/ (Canteen – Aptos x402).
 *
 * EVM: prints instructions (no programmatic testnet faucet in this script).
 */

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { homedir } from 'os';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const demoMcpRoot = path.resolve(__dirname, '..');
const projectRoot = path.resolve(demoMcpRoot, '..');
const agentCwd = path.join(projectRoot, 'demo_mcp', 'autonomous');
const isWindows = process.platform === 'win32';

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: opts.cwd || projectRoot,
      stdio: opts.stdio ?? 'pipe',
      shell: opts.shell ?? false,
      env: { ...process.env, ...opts.env },
    });
    let out = '';
    let err = '';
    if (child.stdout) child.stdout.on('data', (d) => { out += d; });
    if (child.stderr) child.stderr.on('data', (d) => { err += d; });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) reject(new Error(`${cmd} ${args.join(' ')} exited ${code}\n${err || out}`));
      else resolve({ out, err });
    });
  });
}

function aptosWalletPath() {
  return path.join(homedir(), '.aptos-agent-wallet.json');
}

async function main() {
  console.log('Credit agent wallets (Aptos + EVM instructions)\n');

  // Aptos: ensure wallet exists
  const aptosWallet = aptosWalletPath();
  if (!fs.existsSync(aptosWallet)) {
    console.log('Creating Aptos agent wallet (setup-aptos)...');
    try {
      await run('node', ['src/setup-aptos.js'], { cwd: agentCwd, shell: isWindows });
    } catch (e) {
      console.error('Aptos setup failed:', e.message);
      process.exit(1);
    }
  }

  // Aptos: credit (devnet programmatic or testnet instructions)
  const faucetNetwork = (process.env.APTOS_FAUCET_NETWORK || 'testnet').toLowerCase();
  if (faucetNetwork === 'devnet') {
    console.log('Funding Aptos agent wallet on devnet...');
    try {
      await run('node', ['src/credit-aptos-agent.js', '--amount', '100000000'], {
        cwd: agentCwd,
        shell: isWindows,
        env: { ...process.env, APTOS_FAUCET_NETWORK: 'devnet' },
      });
      console.log('Aptos (devnet) funded. Demo MCP uses testnet by default; use devnet config for local testing.');
    } catch (e) {
      console.error('Devnet faucet failed:', e.message);
      process.exit(1);
    }
  } else {
    console.log('Aptos testnet: no programmatic faucet. Showing credit script instructions:');
    await run('node', ['src/credit-aptos-agent.js'], {
      cwd: agentCwd,
      shell: isWindows,
      stdio: 'inherit',
    }).catch(() => {});
  }

  console.log('\nEVM (open_bank_account): fund Base Sepolia and whitelist at onboarding flow. No programmatic crediting in this script.');
  console.log('  Ref: https://canteenapp-aptos-x402.notion.site/');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
