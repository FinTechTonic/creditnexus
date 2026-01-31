/**
 * Local tools for the agent: balance_aptos, balance_evm, get_wallet_addresses.
 */

import { tool } from '@langchain/core/tools';
import { z } from 'zod';
import { getAptosBalance } from '../../lib/aptos/balance.js';
import { getWalletInfo as getAptosWalletInfo } from '../../lib/aptos/wallet.js';
import { getWalletInfo as getEvmWalletInfo } from '../../lib/wallet.js';
import { createPublicClientWithRetry } from '../../lib/rpc.js';
import { getChain, getSupportedChains } from '../../lib/chains.js';
import { formatEther } from 'viem';
import { getAddress, exists as evmWalletExists } from '../../lib/wallet.js';

export function createLocalTools() {
  const balance_aptos = tool(
    async () => {
      try {
        const info = getAptosWalletInfo();
        if (!info?.address) return JSON.stringify({ error: 'No Aptos wallet. Run setup-aptos.js.' });
        const bal = await getAptosBalance(info.address);
        return JSON.stringify(bal ?? { error: 'Could not fetch balance' });
      } catch (e) {
        return JSON.stringify({ error: e.message });
      }
    },
    {
      name: 'balance_aptos',
      description: 'Get Aptos USDC balance for the agent wallet. Use before calling paid Aptos tools (run_prediction, run_backtest).',
      schema: z.object({}),
    }
  );

  const balance_evm = tool(
    async ({ chain }) => {
      try {
        if (!evmWalletExists()) return JSON.stringify({ error: 'No EVM wallet. Run setup.js.' });
        const addr = getAddress();
        const chainName = (chain || 'base').toLowerCase();
        if (!getSupportedChains().includes(chainName)) {
          return JSON.stringify({ error: `Unsupported chain. Use one of: ${getSupportedChains().join(', ')}` });
        }
        const chainConfig = getChain(chainName);
        const client = createPublicClientWithRetry(chainName);
        const balance = await client.getBalance({ address: addr });
        return JSON.stringify({
          address: addr,
          chain: chainName,
          balance: formatEther(balance),
          symbol: chainConfig.nativeToken?.symbol || 'ETH',
        });
      } catch (e) {
        return JSON.stringify({ error: e.message });
      }
    },
    {
      name: 'balance_evm',
      description: 'Get EVM native token balance for the agent wallet on a chain (base, baseSepolia, ethereum, etc.).',
      schema: z.object({
        chain: z.string().optional().describe('Chain name: base, baseSepolia, ethereum, polygon, arbitrum, optimism'),
      }),
    }
  );

  const get_wallet_addresses = tool(
    async () => {
      const aptos = getAptosWalletInfo();
      const evm = evmWalletExists() ? getEvmWalletInfo() : null;
      return JSON.stringify({
        aptos: aptos?.address ?? null,
        evm: evm?.address ?? null,
      });
    },
    {
      name: 'get_wallet_addresses',
      description: 'Get agent wallet addresses (Aptos and EVM). Use to check which wallets are configured.',
      schema: z.object({}),
    }
  );

  return [balance_aptos, balance_evm, get_wallet_addresses];
}
