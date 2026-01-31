/**
 * LangChain.js ReAct agent: MCP tools + local tools, Hugging Face LLM.
 */

import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { createLLM } from './llm.js';
import { createMcpTools } from './tools/mcpTools.js';
import { createLocalTools } from './tools/localTools.js';

const SYSTEM_MESSAGE = `You are an autonomous agent that can run stock predictions, backtests, and open bank accounts via paid MCP tools.
Use run_prediction for stock predictions (symbol, horizon in days). Use run_backtest for backtesting a strategy.
Use open_bank_account to start the bank account flow (costs ~$3.65 on Ethereum/Base).
Use balance_aptos and balance_evm to check wallet balances before calling paid tools. Use get_wallet_addresses to see configured wallets.
When you need to pay for a tool (402), the payment is handled automatically; just call the tool.`;

/**
 * Create agent graph: llm + tools (MCP + local).
 * @param {{ llm?: import('@langchain/core/language_models/chat_models').BaseChatModel; tools?: import('@langchain/core/tools').StructuredToolInterface[] }} options - llm and tools (if omitted, created from env and mcpClient)
 * @param {{ callTool: (name: string, args: Object) => Promise<Object> }} [options.mcpClient] - required if tools not provided
 * @returns {Promise<{ agent: import('@langchain/langgraph').CompiledStateGraph; runAgent: (message: string) => Promise<Object> }>}
 */
export async function createAgent(options = {}) {
  const llm = options.llm || createLLM();
  let tools = options.tools;
  if (!tools && options.mcpClient) {
    tools = [...createMcpTools(options.mcpClient), ...createLocalTools()];
  }
  if (!tools) {
    throw new Error('Provide options.tools or options.mcpClient to createAgent.');
  }

  const agent = createReactAgent({
    llm,
    tools,
    stateModifier: (state) => [{ role: 'system', content: SYSTEM_MESSAGE }, ...(state.messages || [])],
  });

  async function runAgent(userMessage) {
    const result = await agent.invoke({
      messages: [{ role: 'user', content: userMessage }],
    });
    return result;
  }

  return { agent, runAgent };
}
