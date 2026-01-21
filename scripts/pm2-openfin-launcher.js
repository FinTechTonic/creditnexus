/**
 * PM2 OpenFin launcher: waits for backend and frontend, then runs
 * scripts/launch_openfin.ps1 (Windows) or scripts/launch_openfin.sh (Unix).
 * Logs to stdout/stderr so PM2 captures to logs/pm2/openfin-dev-*.log.
 *
 * Env (from ecosystem or shell):
 *   OPENFIN_ENABLED - if "0", exit 0 without launching (default "1")
 *   OPENFIN_MANIFEST_URL - default http://localhost:8000/openfin/app-dev.json
 *   BACKEND_URL - default http://localhost:8000
 *   FRONTEND_URL - default http://localhost:5000
 */

const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const https = require('https');

const P = '[pm2-openfin]';
const projectRoot = path.resolve(__dirname, '..');

function log(msg) {
  const ts = new Date().toISOString();
  process.stdout.write(`${ts} ${P} ${msg}\n`);
}

function logErr(msg) {
  const ts = new Date().toISOString();
  process.stderr.write(`${ts} ${P} ${msg}\n`);
}

function getClient(url) {
  return url.startsWith('https:') ? https : http;
}

function check(url, timeout = 4000) {
  return new Promise((resolve) => {
    const req = getClient(url).get(url, { timeout }, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 500);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

async function waitFor(url, label, maxWaitMs = 90000, intervalMs = 2000) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    const ok = await check(url);
    if (ok) {
      log(`${label} ready (${url})`);
      return true;
    }
    log(`waiting for ${label} (${url})...`);
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}

function run() {
  if (process.env.OPENFIN_ENABLED === '0') {
    log('OPENFIN_ENABLED=0, skipping OpenFin launch');
    process.exit(0);
  }

  const backend = process.env.BACKEND_URL || 'http://localhost:8000';
  const frontend = process.env.FRONTEND_URL || 'http://localhost:5000';
  const manifest = process.env.OPENFIN_MANIFEST_URL || `${backend}/openfin/app-dev.json`;

  log(`OpenFin wrapper config: BACKEND_URL=${backend} FRONTEND_URL=${frontend} OPENFIN_MANIFEST_URL=${manifest}`);

  const backendHealth = `${backend}/api/health`;
  const isWin = process.platform === 'win32';
  const launchScript = isWin
    ? path.join(projectRoot, 'scripts', 'launch_openfin.ps1')
    : path.join(projectRoot, 'scripts', 'launch_openfin.sh');
  const runner = isWin ? 'powershell' : 'bash';
  const args = isWin
    ? ['-ExecutionPolicy', 'Bypass', '-File', launchScript]
    : [launchScript];

  (async () => {
    log('waiting for backend and frontend before launching OpenFin...');
    const backendOk = await waitFor(backendHealth, 'backend');
    if (!backendOk) {
      logErr('backend did not become ready; aborting OpenFin launch');
      process.exit(1);
    }
    const frontendOk = await waitFor(frontend, 'frontend');
    if (!frontendOk) {
      logErr('frontend did not become ready; aborting OpenFin launch');
      process.exit(1);
    }

    const manifestOk = await check(manifest);
    if (!manifestOk) {
      logErr(`manifest not reachable: ${manifest}; aborting`);
      process.exit(1);
    }
    log(`manifest OK: ${manifest}`);
    log(`Wrapping client at ${frontend} (and backend at ${backend}) in OpenFin via ${manifest}`);

    log(`launching OpenFin via ${runner} ${args.slice(-1)[0]}`);
    const env = {
      ...process.env,
      OPENFIN_MANIFEST_URL: manifest,
      BACKEND_URL: backend,
      FRONTEND_URL: frontend,
    };
    const child = spawn(runner, args, { cwd: projectRoot, env, stdio: 'inherit' });
    child.on('error', (e) => {
      logErr(`spawn error: ${e.message}`);
      process.exit(1);
    });
    child.on('exit', (code, sig) => {
      if (code === 0) {
        log('OpenFin launcher script finished successfully');
      } else {
        logErr(`launcher script exited code=${code} signal=${sig || 'none'}`);
      }
      process.exit(code != null ? code : 1);
    });
  })().catch((e) => {
    logErr(String(e));
    process.exit(1);
  });
}

run();
