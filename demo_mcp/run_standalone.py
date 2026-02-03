"""
Standalone entrypoint: start facilitator (x402), then onboarding (web), then MCP.
Replit default web URL should point at onboarding port so users see the onboarding site.
MCP and agents depend on the facilitator for 402 verify/settle.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# demo_mcp root (parent of this file)
ROOT = Path(__file__).resolve().parent
FACILITATOR_DIR = ROOT / "facilitator"

# Env defaults for standalone
os.environ.setdefault("STANDALONE", "1")
os.environ.setdefault("CREDITNEXUS_API_URL", "http://127.0.0.1:4023")
FACILITATOR_PORT = os.environ.get("FACILITATOR_PORT", "4022")
ONBOARDING_PORT = os.environ.get("ONBOARDING_PORT", "8080")
MCP_PORT = os.environ.get("MCP_PORT", "4023")
os.environ.setdefault("MCP_SERVER_URL", f"http://127.0.0.1:{MCP_PORT}")
os.environ.setdefault("X402_FACILITATOR_URL", f"http://127.0.0.1:{FACILITATOR_PORT}")


def _ensure_facilitator_built():
    """Run npm install and npm run build in facilitator/ if dist/ is missing."""
    dist_js = FACILITATOR_DIR / "dist" / "index.js"
    if dist_js.exists():
        return
    for args in [["npm", "install"], ["npm", "run", "build"]]:
        rc = subprocess.call(args, cwd=str(FACILITATOR_DIR), shell=(os.name == "nt"))
        if rc != 0:
            sys.stderr.write(f"Facilitator build failed: {' '.join(args)}\n")
            sys.exit(rc)


def _pay_to_from_allowlist():
    """Read pay_to from ONBOARDING_ALLOWLIST_FILE if set; return comma-separated or empty."""
    path = os.environ.get("ONBOARDING_ALLOWLIST_FILE")
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        pay_to = data.get("pay_to") or []
        return ",".join((p or "").strip() for p in pay_to if (p or "").strip())
    except (OSError, json.JSONDecodeError):
        return ""


def main():
    # 1. Start x402 facilitator first (MCP and agents depend on it for verify/settle)
    _ensure_facilitator_built()
    facilitator_env = os.environ.copy()
    facilitator_env["PORT"] = str(FACILITATOR_PORT)
    pay_to = _pay_to_from_allowlist()
    if pay_to and not facilitator_env.get("PAY_TO_ALLOWLIST"):
        facilitator_env["PAY_TO_ALLOWLIST"] = pay_to
    if os.environ.get("FACILITATOR_MODE"):
        facilitator_env["FACILITATOR_MODE"] = os.environ["FACILITATOR_MODE"]
    elif pay_to:
        facilitator_env.setdefault("FACILITATOR_MODE", "creditnexus")
    facilitator_proc = subprocess.Popen(
        ["node", str(FACILITATOR_DIR / "dist" / "index.js")],
        cwd=str(FACILITATOR_DIR),
        env=facilitator_env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    time.sleep(0.5)

    # 2. Start onboarding (primary port = web) so Replit binds default URL to it
    onboarding_env = os.environ.copy()
    onboarding_env["PORT"] = str(ONBOARDING_PORT)
    onboarding_env["MCP_SERVER_URL"] = f"http://127.0.0.1:{MCP_PORT}"
    onboarding_proc = subprocess.Popen(
        [sys.executable, str(ROOT / "onboarding" / "server.py")],
        cwd=str(ROOT),
        env=onboarding_env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    # 3. Start MCP server on secondary port
    mcp_env = os.environ.copy()
    mcp_env["PORT"] = MCP_PORT
    mcp_env["PYTHONPATH"] = str(ROOT)
    mcp_env["X402_FACILITATOR_URL"] = f"http://127.0.0.1:{FACILITATOR_PORT}"
    mcp_proc = subprocess.Popen(
        [sys.executable, str(ROOT / "server" / "server.py")],
        cwd=str(ROOT),
        env=mcp_env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    procs = (facilitator_proc, onboarding_proc, mcp_proc)

    def shutdown(sig=None, _frame=None):
        for p in procs:
            if p.poll() is None:
                p.terminate()
        sys.exit(0 if sig is None else 128 + (sig or 0))

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        while True:
            for i, p in enumerate(procs):
                if p.poll() is not None:
                    for q in procs:
                        if q.poll() is None:
                            q.terminate()
                    sys.exit(p.returncode if p.returncode != 0 else 0)
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown(signal.SIGINT)


if __name__ == "__main__":
    main()
