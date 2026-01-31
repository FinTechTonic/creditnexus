/**
 * MCP tools as LangChain tools: run_prediction, run_backtest, open_bank_account.
 * Each invokes mcpClient.callTool(name, args) with x402 retry inside the client.
 */

import { tool } from '@langchain/core/tools';
import { z } from 'zod';

/**
 * @param {{ callTool: (name: string, args: Object) => Promise<Object> }} mcpClient - from createMcpClient()
 * @returns {import('@langchain/core/tools').StructuredToolInterface[]}
 */
export function createMcpTools(mcpClient) {
  const run_prediction = tool(
    async ({ symbol, horizon, strategy }) => {
      const out = await mcpClient.callTool('run_prediction', {
        symbol: symbol || 'AAPL',
        horizon: horizon ?? 30,
        strategy: strategy || 'chronos',
      });
      return typeof out?.result === 'object' ? JSON.stringify(out.result) : JSON.stringify(out);
    },
    {
      name: 'run_prediction',
      description: 'Run stock prediction for a ticker. Returns prediction result. Costs ~6¢ (Aptos). Use for daily/hourly/15m predictions.',
      schema: z.object({
        symbol: z.string().describe('Stock symbol (e.g. AAPL)'),
        horizon: z.number().optional().describe('Prediction horizon in days'),
        strategy: z.string().optional().describe('Strategy e.g. chronos, technical'),
      }),
    }
  );

  const run_backtest = tool(
    async ({ symbol, startDate, endDate, strategy }) => {
      const out = await mcpClient.callTool('run_backtest', {
        symbol: symbol || 'AAPL',
        startDate: startDate || '',
        endDate: endDate || '',
        strategy: strategy || 'chronos',
      });
      return typeof out?.result === 'object' ? JSON.stringify(out.result) : JSON.stringify(out);
    },
    {
      name: 'run_backtest',
      description: 'Run backtest for a trading strategy on a symbol. Costs ~6¢ (Aptos).',
      schema: z.object({
        symbol: z.string().describe('Stock symbol'),
        startDate: z.string().optional().describe('Start date YYYY-MM-DD'),
        endDate: z.string().optional().describe('End date YYYY-MM-DD'),
        strategy: z.string().optional().describe('Strategy name'),
      }),
    }
  );

  const open_bank_account = tool(
    async () => {
      const out = await mcpClient.callTool('open_bank_account', {});
      return typeof out?.result === 'object' ? JSON.stringify(out.result) : JSON.stringify(out);
    },
    {
      name: 'open_bank_account',
      description: 'Start open bank account flow (Plaid link). Costs ~$3.65 (Ethereum/Base). Returns link_token or account id.',
      schema: z.object({}),
    }
  );

  return [run_prediction, run_backtest, open_bank_account];
}
