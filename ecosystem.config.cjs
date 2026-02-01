/**
 * PM2 ecosystem file for CreditNexus development.
 * Runs backend (FastAPI) and frontend (Vite) with logs under logs/pm2/.
 *
 * Usage:
 *   pm2 start ecosystem.config.cjs
 *   pm2 start ecosystem.config.cjs --only backend-dev
 *   npm run dev:pm2
 *
 * @see docs/guides/pm2-dev-setup.md
 */
const fs = require('fs');
const path = require('path');

const projectRoot = __dirname;
const logsDir = path.join(projectRoot, 'logs', 'pm2');
const isWindows = process.platform === 'win32';

const venvPython = isWindows
  ? path.join(projectRoot, '.venv', 'Scripts', 'python.exe')
  : path.join(projectRoot, '.venv', 'bin', 'python');
const useVenv = fs.existsSync(venvPython);

module.exports = {
  apps: [
    {
      name: 'backend-dev',
      // Prefer project .venv so icalendar and other deps are available. If no .venv,
      // on Windows use cmd /c to avoid "SyntaxError in ...\PYTHON.EXE".
      script: useVenv ? venvPython : (isWindows ? 'cmd' : 'python'),
      args: useVenv ? ['scripts/run_dev.py'] : (isWindows ? ['/c', 'python', 'scripts/run_dev.py'] : ['scripts/run_dev.py']),
      cwd: projectRoot,
      interpreter: 'none',
      env: {
        NODE_ENV: 'development',
        PYTHONUNBUFFERED: '1',
        PM2: '1',
        // Ensure Python can import the top-level `app` package and `server` module
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
      name: 'frontend-dev',
      script: isWindows ? 'cmd' : 'sh',
      args: isWindows ? ['/c', 'npm', 'run', 'dev'] : ['-c', 'npm run dev'],
      cwd: path.join(projectRoot, 'client'),
      interpreter: 'none',
      env: { NODE_ENV: 'development' },
      out_file: path.join(logsDir, 'frontend-dev-out.log'),
      error_file: path.join(logsDir, 'frontend-dev-error.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss.SSS',
      merge_logs: false,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '2s',
    },
    // Wraps the Vite dev client (and backend) in OpenFin via app-dev.json (view at :5000). Logs to logs/pm2/openfin-dev-*.log.
    {
      name: 'openfin-dev',
      script: 'node',
      args: ['scripts/pm2-openfin-launcher.js'],
      cwd: projectRoot,
      interpreter: 'none',
      env: {
        NODE_ENV: 'development',
        OPENFIN_ENABLED: process.env.OPENFIN_ENABLED || '1',
        OPENFIN_MANIFEST_URL: process.env.OPENFIN_MANIFEST_URL || 'http://localhost:8000/openfin/app-dev.json',
        BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
        FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:5000',
      },
      out_file: path.join(logsDir, 'openfin-dev-out.log'),
      error_file: path.join(logsDir, 'openfin-dev-error.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss.SSS',
      merge_logs: false,
      watch: false,
      autorestart: false,
    },
    // Autonomous agent (x402 MCP + LangChain.js). Run from repo root: pm2 start ecosystem.config.cjs --only agent-autonomous
    {
      name: 'agent-autonomous',
      script: 'node',
      args: ['src/run-agent.js'],
      cwd: path.join(projectRoot, 'demo_mcp', 'autonomous'),
      interpreter: 'none',
      env: { NODE_ENV: 'development' },
      out_file: path.join(logsDir, 'agent-autonomous-out.log'),
      error_file: path.join(logsDir, 'agent-autonomous-error.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss.SSS',
      merge_logs: false,
      watch: false,
      autorestart: false,
      max_restarts: 0,
    },
    // Standalone Aptos x402 facilitator (verify/settle). Run: pm2 start ecosystem.config.cjs --only x402-facilitator
    {
      name: 'x402-facilitator',
      script: 'node',
      args: ['dist/index.js'],
      cwd: path.join(projectRoot, 'x402-facilitator'),
      interpreter: 'none',
      env: { NODE_ENV: 'development' },
      out_file: path.join(logsDir, 'x402-facilitator-out.log'),
      error_file: path.join(logsDir, 'x402-facilitator-error.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss.SSS',
      merge_logs: false,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '2s',
    },
  ],
};
