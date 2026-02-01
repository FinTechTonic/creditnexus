/**
 * MCP client with x402 retry: uses official MCP SDK with StreamableHTTP transport.
 * On 402 from tool call, pays via facilitator and retries.
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { verifyPayment, settlePayment } from '../x402/index.js';

/**
 * @param {Object} config
 * @param {string} config.baseUrl - MCP server base URL (e.g. http://localhost:4023)
 * @param {string} config.facilitatorUrl - x402 facilitator base URL
 * @param {(r: import('../x402/types.js').PaymentRequirements) => Promise<Object>} config.getAptosPaymentPayload
 * @param {(r: import('../x402/types.js').PaymentRequirements) => Promise<Object>} config.getEvmPaymentPayload
 * @param {number} [config.maxRetries]
 */
export function createMcpClient(config) {
  const baseUrl = (config.baseUrl || '').replace(/\/+$/, '');
  const mcpUrl = `${baseUrl}/mcp`;
  const facilitatorUrl = config.facilitatorUrl;
  const getAptosPaymentPayload = config.getAptosPaymentPayload;
  const getEvmPaymentPayload = config.getEvmPaymentPayload;
  const maxRetries = config.maxRetries ?? 2;

  let mcpClient = null;
  let isConnected = false;

  /**
   * Connect to MCP server
   */
  async function connect() {
    if (isConnected && mcpClient) {
      console.log('Already connected to MCP server');
      return;
    }

    console.log(`Connecting to MCP server at ${mcpUrl}`);
    try {
      const transport = new StreamableHTTPClientTransport(
        new URL(mcpUrl)
      );

      mcpClient = new Client({
        name: 'creditnexus-agent',
        version: '1.0.0',
      }, {
        capabilities: {},
      });

      await mcpClient.connect(transport);
      isConnected = true;
      console.log('Successfully connected to MCP server');
    } catch (error) {
      console.error('Failed to connect to MCP server:', error);
      throw error;
    }
  }

  /**
   * Disconnect from MCP server
   */
  async function disconnect() {
    if (mcpClient && isConnected) {
      await mcpClient.close();
      isConnected = false;
      mcpClient = null;
    }
  }

  /**
   * Call MCP tool by name with args; on 402 pay and retry.
   * @param {string} name - tool name (run_prediction, run_backtest, open_bank_account)
   * @param {Record<string, unknown>} args - tool arguments
   * @returns {Promise<{ result?: unknown; payment_receipt?: Object }>}
   */
  async function callTool(name, args = {}) {
    console.log(`MCP client calling tool: ${name}`, args);
    await connect();
    console.log('MCP client connected');

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        console.log(`MCP tool call attempt ${attempt + 1}`);
        const result = await mcpClient.callTool({
          name,
          arguments: args,
        });
        console.log('MCP callTool result:', result);

        // Check for 402 in result (can be in structuredContent or text content)
        let errorData = null;

        // Try structuredContent first
        if (result.structuredContent?.status === 402) {
          errorData = result.structuredContent;
        }
        // Try parsing text content
        else if (result.content?.[0]?.text) {
          try {
            const parsed = JSON.parse(result.content[0].text);
            if (parsed.status === 402) {
              errorData = parsed;
            }
          } catch {
            // Not JSON or not 402
          }
        }

        if (errorData?.status === 402 && errorData.paymentRequirements) {
            // Handle payment
            const paymentRequirements = errorData.paymentRequirements;
            console.log(`Payment required for ${name}: ${paymentRequirements.amount} on ${paymentRequirements.network}`);

            // Get payment payload based on network
            let paymentPayload;
            try {
              if (paymentRequirements.network.startsWith('aptos:')) {
                if (!getAptosPaymentPayload) {
                  return { result: { error: 'No Aptos wallet configured' } };
                }
                console.log('Creating Aptos payment payload...');
                paymentPayload = await getAptosPaymentPayload(paymentRequirements);
                console.log('Payment payload created');
              } else if (paymentRequirements.network.startsWith('eip155:')) {
                if (!getEvmPaymentPayload) {
                  return { result: { error: 'No EVM wallet configured' } };
                }
                paymentPayload = await getEvmPaymentPayload(paymentRequirements);
              } else {
                return { result: { error: `Unsupported network: ${paymentRequirements.network}` } };
              }

              // Verify payment with facilitator
              console.log(`Verifying payment with facilitator: ${facilitatorUrl}`);
              const verification = await verifyPayment(facilitatorUrl, paymentPayload, paymentRequirements);
              console.log('Verification result:', verification);

              if (!verification.isValid) {
                return { result: { error: `Payment verification failed: ${verification.invalidReason}` } };
              }

              // Settle payment
              console.log('Settling payment...');
              const settlement = await settlePayment(facilitatorUrl, paymentPayload, paymentRequirements);
              console.log(`Payment settled: ${settlement.transactionHash}`);
            } catch (error) {
              console.error('Payment error:', error);
              return { result: { error: error.message } };
            }

            // Retry with payment proof
            // Note: FastMCP doesn't support custom headers in tool calls yet
            // For now, we just retry - the server should recognize the settled payment
            continue;
        }

        // Success
        const content = result.content?.[0];
        if (content?.type === 'text') {
          try {
            return { result: JSON.parse(content.text) };
          } catch {
            return { result: content.text };
          }
        }
        return { result: content };

      } catch (error) {
        if (attempt === maxRetries) {
          return { result: { error: error.message } };
        }
      }
    }

    return { result: { error: 'Max retries exceeded' } };
  }

  return { callTool, connect, disconnect };
}
