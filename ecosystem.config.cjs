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
const path = require('path');

const projectRoot = __dirname;
const logsDir = path.join(projectRoot, 'logs', 'pm2');

module.exports = {
  apps: [
    {
      name: 'backend-dev',
      script: 'python',
      args: 'scripts/run_dev.py',
      cwd: projectRoot,
      interpreter: 'none',
      env: { NODE_ENV: 'development' },
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
      script: 'npm',
      args: 'run dev',
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
  ],
};
