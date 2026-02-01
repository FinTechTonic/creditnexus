/**
 * PM2 ecosystem for demo_mcp launcher.
 * Uses uv run for Python so project deps (including fastmcp) are used.
 * Backend, MCP server, and onboarding logs under demo_mcp/logs/.
 * Used by: npm run demo-mcp:launch (launch-demo-mcp.mjs)
 */
const path = require('path');

const demoMcpRoot = __dirname;
const projectRoot = path.join(demoMcpRoot, '..');
const logsDir = path.join(demoMcpRoot, 'logs');

module.exports = {
  apps: [
    {
      name: 'backend-dev',
      script: 'uv',
      args: ['run', 'scripts/run_dev.py'],
      cwd: projectRoot,
      interpreter: 'none',
      env: {
        NODE_ENV: 'development',
        PYTHONUNBUFFERED: '1',
        PM2: '1',
        PYTHONPATH: projectRoot,
      },
      out_file: path.join(logsDir, 'backend-dev-out.log'),
      error_file: path.join(logsDir, 'backend-dev-error.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss.SSS',
      merge_logs: false,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '2s',
    },
    {
      name: 'mcp-server',
      script: 'uv',
      args: ['run', 'demo_mcp/server/server.py'],
      cwd: projectRoot,
      interpreter: 'none',
      env: {
        NODE_ENV: 'development',
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: projectRoot,
        FASTMCP_NO_BANNER: '1',
        FASTMCP_LOG_LEVEL: 'WARNING',
        ONBOARDING_ALLOWLIST_FILE: path.join(projectRoot, 'demo_mcp', 'onboarding', 'allowlist.json'),
        CREDITNEXUS_API_URL: 'http://localhost:8000',
      },
      out_file: path.join(logsDir, 'mcp-server-out.log'),
      error_file: path.join(logsDir, 'mcp-server-error.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss.SSS',
      merge_logs: false,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '2s',
    },
    {
      name: 'onboarding',
      script: 'uv',
      args: ['run', 'demo_mcp/onboarding/server.py'],
      cwd: projectRoot,
      interpreter: 'none',
      env: {
        NODE_ENV: 'development',
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
        PORT: '4024',
        MCP_SERVER_URL: 'http://localhost:4023',
        CREDITNEXUS_APP_URL: 'http://localhost:8000',
      },
      out_file: path.join(logsDir, 'onboarding-out.log'),
      error_file: path.join(logsDir, 'onboarding-error.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss.SSS',
      merge_logs: false,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '2s',
    },
  ],
};
