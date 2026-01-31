/**
 * MCP client with x402 retry: call tool; on 402 pay via facilitator and retry with PAYMENT-SIGNATURE.
 * Expects MCP server at MCP_SERVER_URL (env); tool calls via HTTP POST; 402 in status or body.
 */

import { fetchWithX402Retry } from '../x402/index.js';

const DEFAULT_TOOLS_PATH = '/mcp/tools/call';
const PAYMENT_SIGNATURE_HEADER = 'PAYMENT-SIGNATURE';

/**
 * @param {Object} config
 * @param {string} config.baseUrl - MCP server base URL (e.g. from MCP_SERVER_URL)
 * @param {string} [config.toolsPath] - path for tool call (default /mcp/tools/call)
 * @param {string} config.facilitatorUrl - x402 facilitator base URL
 * @param {(r: import('../x402/types.js').PaymentRequirements) => Promise<Object>} config.getAptosPaymentPayload
 * @param {(r: import('../x402/types.js').PaymentRequirements) => Promise<Object>} config.getEvmPaymentPayload
 * @param {number} [config.maxRetries]
 */
export function createMcpClient(config) {
  const baseUrl = (config.baseUrl || '').replace(/\/+$/, '');
  const toolsPath = config.toolsPath || DEFAULT_TOOLS_PATH;
  const toolCallUrl = `${baseUrl}${toolsPath}`;
  const x402Context = {
    facilitatorUrl: config.facilitatorUrl,
    getAptosPaymentPayload: config.getAptosPaymentPayload,
    getEvmPaymentPayload: config.getEvmPaymentPayload,
    maxRetries: config.maxRetries ?? 2,
  };

  /**
   * Call MCP tool by name with args; on 402 pay and retry with PAYMENT-SIGNATURE.
   * @param {string} name - tool name (run_prediction, run_backtest, open_bank_account)
   * @param {Record<string, unknown>} args - tool arguments
   * @returns {Promise<{ result?: unknown; request_payload?: Object; response_payload?: Object; payment_receipt?: Object }>}
   */
  async function callTool(name, args = {}) {
    const body = JSON.stringify({ tool: name, arguments: args });
    const options = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    };

    const result = await fetchWithX402Retry(toolCallUrl, options, x402Context);

    if (result && typeof result === 'object' && (result.result !== undefined || result.content !== undefined)) {
      return result;
    }
    return { result };
  }

  return { callTool };
}
