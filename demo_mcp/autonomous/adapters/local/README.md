# Local / OSS agents

Use the CreditNexus x402 capability from local or OSS agents (e.g. LM Studio, AutoGen, CrewAI).

1. **Source:** GitHub repo (CreditNexus `demo_mcp/autonomous`).
2. **Install:** `npm install` in `autonomous/`.
3. **Config:** Set `MCP_SERVER_URL` to your MCP server (e.g. `http://localhost:4023` or deployed Replit MCP URL). Set x402 facilitator URL and LLM/env as needed.
4. **Run:** `node src/run-agent.js "your message"` or wire MCP client to your agent framework.
5. **x402:** On 402 responses, call facilitator verify → settle, then retry the request with `PAYMENT-SIGNATURE` header.

See parent `autonomous/README.md` for full config and tool list.
