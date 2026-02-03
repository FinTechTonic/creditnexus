#!/usr/bin/env node
/**
 * Launch CreditNexus demo MCP flow:
 * 1. Start CreditNexus backend (PM2 backend-dev), logs → demo_mcp/logs/
 * 2. Wait 1 minute
 * 3. Log in as administrator (POST /api/auth/login)
 * 4. Create API key (POST /api/admin/generate-api-key), save to demo_mcp/server/.env
 * 5. Start MCP server (PM2 mcp-server), logs → demo_mcp/logs/
 * 6. Start onboarding site (PM2 onboarding), http://localhost:4024 for whitelisting
 * 7. Run demo agent in foreground with human input (stdio inherit)
 *
 * Requires: ADMIN_EMAIL, ADMIN_PASSWORD in env or in project root .env / demo_mcp/.env
 * Optional: CREDITNEXUS_URL (default http://localhost:8000)
 *
 * Usage: from repo root: npm run demo-mcp:launch
 *        or: node demo_mcp/scripts/launch-demo-mcp.mjs
 */

import { spawn } from "child_process";
import { createInterface } from "readline";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const demoMcpRoot = path.resolve(__dirname, "..");
const projectRoot = path.resolve(demoMcpRoot, "..");
const isWindows = process.platform === "win32";

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const content = fs.readFileSync(filePath, "utf8");
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const raw = trimmed.slice(eq + 1).trim();
    const value = raw.startsWith('"') && raw.endsWith('"')
      ? raw.slice(1, -1).replace(/\\"/g, '"')
      : raw.startsWith("'") && raw.endsWith("'")
        ? raw.slice(1, -1).replace(/\\'/g, "'")
        : raw;
    if (!process.env[key]) process.env[key] = value;
  }
}

function loadEnv() {
  loadEnvFile(path.join(projectRoot, ".env"));
  loadEnvFile(path.join(demoMcpRoot, ".env"));
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: opts.cwd || projectRoot,
      stdio: opts.stdio ?? "pipe",
      shell: opts.shell ?? false,
      env: { ...process.env, ...opts.env },
    });
    let out = "";
    let err = "";
    if (child.stdout) child.stdout.on("data", (d) => { out += d; if (opts.stdio === "inherit") process.stdout.write(d); });
    if (child.stderr) child.stderr.on("data", (d) => { err += d; if (opts.stdio === "inherit") process.stderr.write(d); });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) reject(new Error(`${cmd} ${args.join(" ")} exited ${code}\n${err || out}`));
      else resolve({ out, err });
    });
  });
}

function runInherit(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: opts.cwd || projectRoot,
      stdio: "inherit",
      shell: opts.shell ?? false,
      env: { ...process.env, ...opts.env },
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) reject(new Error(`${cmd} exited ${code}`));
      else resolve();
    });
  });
}

/** Run agent subprocess without touching stdin so parent readline keeps working for next Message> */
function runAgentProcess(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: opts.cwd || projectRoot,
      stdio: ["ignore", process.stdout, process.stderr],
      shell: opts.shell ?? false,
      env: { ...process.env, ...opts.env },
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) reject(new Error(`${cmd} exited ${code}`));
      else resolve();
    });
  });
}

/** Fetch onboarding /env-export and parse into env object so agent gets latest allowlist. */
async function fetchEnvExport(baseUrl) {
  try {
    const opts = typeof AbortSignal !== "undefined" && AbortSignal.timeout
      ? { signal: AbortSignal.timeout(5000) }
      : {};
    const res = await fetch(`${baseUrl}/env-export`, opts);
    if (!res.ok) return {};
    const text = await res.text();
    const env = {};
    for (const line of text.split(/\r?\n/)) {
      const m = line.match(/^export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
      if (!m) continue;
      let val = m[2].trim();
      if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1).replace(/\\"/g, '"');
      else if (val.startsWith("'") && val.endsWith("'")) val = val.slice(1, -1).replace(/\\'/g, "'");
      env[m[1]] = val;
    }
    return env;
  } catch {
    return {};
  }
}

async function login(baseUrl) {
  const email = process.env.ADMIN_EMAIL;
  const password = process.env.ADMIN_PASSWORD;
  if (!email || !password) {
    throw new Error("Set ADMIN_EMAIL and ADMIN_PASSWORD in .env or environment (project root .env or demo_mcp/.env)");
  }
  const res = await fetch(`${baseUrl}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`Login failed (${res.status}): ${t}`);
  }
  const data = await res.json();
  const token = data.access_token;
  if (!token) throw new Error("Login response missing access_token");
  return token;
}

async function generateApiKey(accessToken, baseUrl, profileName = "mcp-service") {
  const res = await fetch(`${baseUrl}/api/admin/generate-api-key`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ profile_name: profileName }),
  });
  if (!res.ok) {
    const t = await res.text();
    const err = new Error(`Generate API key failed (${res.status}): ${t}`);
    err.status = res.status;
    err.body = t;
    throw err;
  }
  const data = await res.json();
  const key = data.api_key;
  if (!key) throw new Error("Generate API key response missing api_key");
  return key;
}

function getEnvKey(envPath, keyName) {
  if (!fs.existsSync(envPath)) return null;
  const content = fs.readFileSync(envPath, "utf8");
  const regex = new RegExp(`^${keyName}=(.+)$`, "m");
  const m = content.match(regex);
  if (!m) return null;
  const raw = m[1].trim();
  if (raw.startsWith('"') && raw.endsWith('"')) return raw.slice(1, -1).replace(/\\"/g, '"');
  if (raw.startsWith("'") && raw.endsWith("'")) return raw.slice(1, -1).replace(/\\'/g, "'");
  return raw;
}

function setEnvKey(envPath, keyName, value) {
  let content = "";
  if (fs.existsSync(envPath)) {
    content = fs.readFileSync(envPath, "utf8");
  }
  const line = `${keyName}=${value}`;
  const regex = new RegExp(`^${keyName}=.*$`, "m");
  if (regex.test(content)) {
    content = content.replace(regex, line);
  } else {
    content = content.trimEnd();
    if (content) content += "\n";
    content += line + "\n";
  }
  fs.writeFileSync(envPath, content, "utf8");
}

async function main() {
  loadEnv();
  const isStandalone = process.env.STANDALONE === "1";
  const creditNexusUrl = isStandalone
    ? "http://127.0.0.1:4023"
    : (process.env.CREDITNEXUS_URL || "http://localhost:8000");
  const onboardingUrl = process.env.ONBOARDING_URL || "http://localhost:4024";

  console.log("CreditNexus demo MCP launcher" + (isStandalone ? " (STANDALONE=1)" : ""));
  console.log("Project root:", projectRoot);
  console.log("CreditNexus URL:", creditNexusUrl);
  console.log("");
  console.log("  After startup you can:");
  console.log("  • Whitelist your agent → " + onboardingUrl + " (or " + onboardingUrl + "/flow.html)");
  console.log("  • Chat with the demo agent → this terminal (Message> prompt)");
  if (!isStandalone) console.log("  • Use the full app → " + creditNexusUrl);
  console.log("");

  if (isStandalone) {
    // STANDALONE=1: skip backend and API key; start MCP + onboarding from demo_mcp root with vendored APIs
    const serverEnvPath = path.join(demoMcpRoot, "server", ".env");
    setEnvKey(serverEnvPath, "CREDITNEXUS_API_URL", "http://127.0.0.1:4023");
    setEnvKey(serverEnvPath, "STANDALONE", "1");
    console.log("\n[STANDALONE] Skipping backend and API key; using vendored stubs/Plaid.");
    console.log("[STANDALONE] Starting MCP server (port 4023) and onboarding (port 4024) from demo_mcp root...");
    const mcpProc = spawn(
      "python",
      [path.join(demoMcpRoot, "server", "server.py")],
      {
        cwd: demoMcpRoot,
        stdio: "pipe",
        shell: false,
        env: {
          ...process.env,
          PYTHONPATH: demoMcpRoot,
          STANDALONE: "1",
          CREDITNEXUS_API_URL: "http://127.0.0.1:4023",
          PORT: "4023",
        },
      }
    );
    mcpProc.stdout?.on("data", (d) => process.stdout.write(d));
    mcpProc.stderr?.on("data", (d) => process.stderr.write(d));
    mcpProc.on("error", (e) => {
      console.error("MCP server failed:", e);
      process.exit(1);
    });
    await sleep(3000);
    const onboardingProc = spawn(
      "python",
      [path.join(demoMcpRoot, "onboarding", "server.py")],
      {
        cwd: demoMcpRoot,
        stdio: "pipe",
        shell: false,
        env: {
          ...process.env,
          PORT: "4024",
          MCP_SERVER_URL: "http://127.0.0.1:4023",
        },
      }
    );
    onboardingProc.stdout?.on("data", (d) => process.stdout.write(d));
    onboardingProc.stderr?.on("data", (d) => process.stderr.write(d));
    onboardingProc.on("error", (e) => {
      console.error("Onboarding server failed:", e);
      process.exit(1);
    });
    await sleep(2000);
    console.log("  → MCP: http://127.0.0.1:4023  Onboarding: " + onboardingUrl);
  } else {
    // Ensure demo_mcp log dir exists (PM2 writes backend + MCP server logs here)
    const logsDir = path.join(demoMcpRoot, "logs");
    if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });

    // Sync Python deps with uv (required for PM2 apps; includes fastmcp for MCP server)
    const ecosystemPath = path.join(demoMcpRoot, "ecosystem.config.cjs");
    console.log("\n[0/7] Syncing Python deps (uv sync)...");
    try {
      await run("uv", ["sync"], { cwd: projectRoot, shell: isWindows });
    } catch (e) {
      console.error("uv sync failed. Install uv: https://docs.astral.sh/uv/");
      throw e;
    }

    // 1. Start backend (using demo_mcp ecosystem; uv run, logs → demo_mcp/logs/)
    console.log("\n[1/7] Starting CreditNexus backend (PM2 backend-dev, logs → demo_mcp/logs/)...");
    await run("npx", ["pm2", "start", ecosystemPath, "--only", "backend-dev"], { cwd: projectRoot, shell: isWindows });
    console.log("Backend started. Waiting 1 minute for startup...");
    console.log("  → When ready, CreditNexus app: " + creditNexusUrl);

    // 2. Wait 1 minute
    await sleep(60 * 1000);

    // 3. Login as admin
    console.log("\n[3/7] Logging in as administrator...");
    const accessToken = await login(creditNexusUrl);
    console.log("Login OK.");

    // 4. Create API key and save to demo_mcp/server/.env (skip if already set)
    const serverEnvPath = path.join(demoMcpRoot, "server", ".env");
    let apiKey = getEnvKey(serverEnvPath, "CREDITNEXUS_SERVICE_KEY");
    if (apiKey) {
      console.log("\n[4/7] CREDITNEXUS_SERVICE_KEY already set in demo_mcp/server/.env, skipping API key creation.");
    } else {
      console.log("\n[4/7] Creating API key and saving to demo_mcp/server/.env...");
      try {
        apiKey = await generateApiKey(accessToken, creditNexusUrl, "mcp-service");
      } catch (e) {
        if (e.status === 400 && e.body && e.body.includes("already exists")) {
          const uniqueName = `mcp-service-${Date.now()}`;
          console.log(`Profile 'mcp-service' already exists, creating '${uniqueName}'...`);
          apiKey = await generateApiKey(accessToken, creditNexusUrl, uniqueName);
        } else {
          throw e;
        }
      }
      setEnvKey(serverEnvPath, "CREDITNEXUS_SERVICE_KEY", apiKey);
      console.log("CREDITNEXUS_SERVICE_KEY saved to demo_mcp/server/.env");
    }

    // 5. Start MCP server (same ecosystem → logs in demo_mcp/logs/)
    console.log("\n[5/7] Starting MCP server (PM2 mcp-server, logs → demo_mcp/logs/)...");
    await run("npx", ["pm2", "start", ecosystemPath, "--only", "mcp-server"], { cwd: projectRoot, shell: isWindows });
    console.log("MCP server started. Giving it a few seconds...");
    console.log("  → Whitelist agents at " + onboardingUrl + "/flow.html so they can call MCP tools.");
    await sleep(5000);

    // 6. Start onboarding site (whitelisting flow)
    console.log("\n[6/7] Starting onboarding site (PM2 onboarding, logs → demo_mcp/logs/)...");
    await run("npx", ["pm2", "start", ecosystemPath, "--only", "onboarding"], { cwd: projectRoot, shell: isWindows });
    console.log("Onboarding site started.");
    console.log("  → Open in browser to whitelist your agent:", onboardingUrl);
    console.log("  → Full flow (wallet, KYC, allowlist, env snippet):", `${onboardingUrl}/flow.html`);
    await sleep(2000);
  }

  // 7. Ensure agent dependencies are installed, then run demo agent with human input
  const agentCwd = path.join(projectRoot, "demo_mcp", "autonomous");
  const agentNodeModules = path.join(agentCwd, "node_modules", "@modelcontextprotocol");
  if (!fs.existsSync(agentNodeModules)) {
    console.log("\n[7/7] Installing agent dependencies (npm install in demo_mcp/autonomous)...");
    await run("npm", ["install"], { cwd: agentCwd, shell: isWindows });
  }

  const creditNexusAppUrl = creditNexusUrl;
  console.log("\n" + "─".repeat(60));
  console.log("  WHAT YOU CAN DO NOW");
  console.log("─".repeat(60));
  console.log("");
  console.log("  1. WHITELIST YOUR AGENT (do this first so the agent is allowed)");
  console.log("     Open in browser:", onboardingUrl);
  console.log("     Flow:", `${onboardingUrl}/flow.html`);
  console.log("     → Connect wallet, complete banking/KYC step, register allowlist, copy env snippet.");
  console.log("     Hydrate this terminal: eval $(curl -s " + onboardingUrl + "/env-export)  (or set ONBOARDING_HYDRO_ENV_FILE and source that file after registering).");
  console.log("");
  console.log("  CREDIT APTOS AGENT (for run_prediction / run_backtest):");
  console.log("     Testnet (demo default): Open https://aptos.dev/network/faucet, sign in, enter agent address, request APT. USDC for x402 from Circle/testnet if needed.");
  console.log("     Devnet (programmatic): In demo_mcp/autonomous run APTOS_FAUCET_NETWORK=devnet node src/credit-aptos-agent.js (or npm run credit:aptos with that env).");
  console.log("     Ref: https://canteenapp-aptos-x402.notion.site/ (Canteen – Aptos x402 hydration).");
  console.log("");
  console.log("  OPEN BANK ACCOUNT: agent needs an EVM wallet and that address whitelisted.");
  console.log("     Option A: In demo_mcp/autonomous run 'node src/setup.js', then whitelist the printed address at flow.html.");
  console.log("     Option B: Set EVM_PRIVATE_KEY to your wallet private key (e.g. export from MetaMask), then whitelist that address at flow.html.");
  console.log("");
  console.log("  2. USE THE DEMO AGENT (this terminal)");
  console.log("     Type a message below and press Enter. Examples:");
  console.log("     • \"Check my Aptos balance\"");
  console.log("     • \"Run a 30-day prediction for AAPL\"");
  console.log("     • \"I would like to open a bank account\"");
  console.log("     Type 'exit' to leave the agent (other apps keep running).");
  console.log("");
  console.log("  3. CREDITNEXUS APP (full web app)");
  console.log("     Open in browser:", creditNexusAppUrl);
  console.log("     → Sign in, link bank (Plaid), use full features.");
  console.log("");
  console.log("─".repeat(60));
  console.log("\n[7/7] Demo agent ready. Type your message and press Enter (or 'exit' to quit).");
  console.log("  Tip: If the agent returns 403, whitelist your agent at " + onboardingUrl + "/flow.html first.\n");

  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const runAgentWithMessage = async (msg) => {
    const hydratedEnv = await fetchEnvExport(onboardingUrl);
    const env = { ...process.env, ...hydratedEnv };
    if (Object.keys(hydratedEnv).length) {
      console.log("  (refreshed allowlist from onboarding for this run)");
    }
    return runAgentProcess("node", ["src/run-agent.js", msg], { cwd: agentCwd, shell: isWindows, env });
  };

  for (;;) {
    const line = await new Promise((resolve) => rl.question("Message> ", resolve));
    const msg = line.trim();
    if (!msg) continue;
    if (msg.toLowerCase() === "exit") break;
    try {
      await runAgentWithMessage(msg);
    } catch (e) {
      console.error("Agent run failed:", e.message);
    }
  }
  rl.close();
  console.log("\nExiting. Backend, MCP server, and onboarding site remain running under PM2.");
  console.log("  → Stop all: npx pm2 stop backend-dev mcp-server onboarding");
  console.log("  → Logs: npx pm2 logs (or see demo_mcp/logs/)");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
