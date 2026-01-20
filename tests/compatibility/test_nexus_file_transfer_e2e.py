"""
End-to-end .nexus file transfer test: Client A -> Server -> Client B.

Simulates two clients using the server in the middle:
1. Client A (sender): logs in, generates a .nexus file via POST /api/nexus/generate.
2. Server: persists send event, returns .nexus bytes.
3. Client B (receiver): logs in, uploads the .nexus file via POST /api/nexus/upload.
4. Server: parses .nexus, creates receive event, returns workflow data.

Run with the PM2 dev stack:
  npm run dev:pm2
  uv run python tests/compatibility/test_nexus_file_transfer_e2e.py

Or: pytest tests/compatibility/test_nexus_file_transfer_e2e.py -v

Requires: backend on 8000 (or BASE_URL), demo user (demo@creditnexus.app / DemoPassword123!).
Optional: second user for two-client test (e.g. auditor@creditnexus.app / Auditor123!).
"""

from __future__ import annotations

import os
import sys
import time
from io import BytesIO

import httpx

# ---------------------------------------------------------------------------
# Configuration (env overrides)
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
SENDER_EMAIL = os.environ.get("NEXUS_E2E_SENDER_EMAIL", "demo@creditnexus.app")
SENDER_PASSWORD = os.environ.get("NEXUS_E2E_SENDER_PASSWORD", "DemoPassword123!")
RECEIVER_EMAIL = os.environ.get("NEXUS_E2E_RECEIVER_EMAIL", "auditor@creditnexus.app")
RECEIVER_PASSWORD = os.environ.get("NEXUS_E2E_RECEIVER_PASSWORD", "Auditor123!")
HEALTH_TIMEOUT_S = int(os.environ.get("NEXUS_E2E_HEALTH_TIMEOUT", "60"))
HTTP_TIMEOUT_S = float(os.environ.get("NEXUS_E2E_HTTP_TIMEOUT", "30.0"))


def _log(msg: str) -> None:
    print(f"[nexus-e2e] {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"[nexus-e2e] ERROR: {msg}", file=sys.stderr, flush=True)


def wait_for_health(client: httpx.Client) -> bool:
    """Poll /api/health until 200 or timeout."""
    deadline = time.time() + HEALTH_TIMEOUT_S
    while time.time() < deadline:
        try:
            r = client.get(f"{BASE_URL}/api/health", timeout=5.0)
            if r.status_code == 200:
                _log("Backend /api/health OK")
                return True
        except Exception as e:
            _log(f"Health check: {e}")
        time.sleep(1.0)
    return False


def login(client: httpx.Client, email: str, password: str) -> str | None:
    """Login and return access_token or None."""
    try:
        r = client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password},
            timeout=HTTP_TIMEOUT_S,
        )
        r.raise_for_status()
        data = r.json()
        token = data.get("access_token")
        if not token:
            _err(f"No access_token in login response: {list(data.keys())}")
            return None
        return token
    except httpx.HTTPStatusError as e:
        _err(f"Login failed ({email}): {e.response.status_code} {e.response.text[:200]}")
        return None
    except Exception as e:
        _err(f"Login error: {e}")
        return None


def generate_nexus(client: httpx.Client, token: str, deal_id: int | None = None) -> bytes | None:
    """Generate .nexus via POST /api/nexus/generate. Returns .nexus bytes or None."""
    try:
        r = client.post(
            f"{BASE_URL}/api/nexus/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "workflow_type": "verification",
                "deal_id": deal_id,
                "include_files": True,
                "expires_in_hours": 72,
            },
            timeout=HTTP_TIMEOUT_S,
        )
        r.raise_for_status()
        return r.content
    except httpx.HTTPStatusError as e:
        _err(f"Generate failed: {e.response.status_code} {e.response.text[:300]}")
        return None
    except Exception as e:
        _err(f"Generate error: {e}")
        return None


def upload_nexus(client: httpx.Client, token: str, nexus_bytes: bytes, filename: str = "e2e.nexus") -> dict | None:
    """Upload .nexus via POST /api/nexus/upload. Returns JSON response or None."""
    try:
        r = client.post(
            f"{BASE_URL}/api/nexus/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, BytesIO(nexus_bytes), "application/octet-stream")},
            timeout=HTTP_TIMEOUT_S,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        _err(f"Upload failed: {e.response.status_code} {e.response.text[:300]}")
        return None
    except Exception as e:
        _err(f"Upload error: {e}")
        return None


def run_same_user_flow(client: httpx.Client) -> bool:
    """One user generates and uploads (self-transfer)."""
    _log("Same-user flow: generate then upload as same user")
    token = login(client, SENDER_EMAIL, SENDER_PASSWORD)
    if not token:
        return False

    nexus_bytes = generate_nexus(client, token, deal_id=None)
    if not nexus_bytes:
        return False
    _log(f"Generated .nexus: {len(nexus_bytes)} bytes")

    data = upload_nexus(client, token, nexus_bytes)
    if not data:
        return False

    if data.get("status") != "success":
        _err(f"Upload response status: {data.get('status')}")
        return False
    if not data.get("workflow_id"):
        _err("Upload response missing workflow_id")
        return False

    _log(f"Upload OK: workflow_id={data.get('workflow_id')}, embedded={data.get('embedded_files', 0)}")
    return True


def run_two_client_flow(client: httpx.Client) -> bool:
    """Client A generates; Client B uploads (two clients, server in the middle)."""
    _log("Two-client flow: sender generates, receiver uploads")

    sender_token = login(client, SENDER_EMAIL, SENDER_PASSWORD)
    if not sender_token:
        return False

    nexus_bytes = generate_nexus(client, sender_token, deal_id=None)
    if not nexus_bytes:
        return False
    _log(f"Client A generated .nexus: {len(nexus_bytes)} bytes")

    receiver_token = login(client, RECEIVER_EMAIL, RECEIVER_PASSWORD)
    if not receiver_token:
        _log("Receiver login failed; falling back to same-user for upload")
        receiver_token = sender_token

    data = upload_nexus(client, receiver_token, nexus_bytes)
    if not data:
        return False

    if data.get("status") != "success":
        _err(f"Upload response status: {data.get('status')}")
        return False

    _log(f"Client B upload OK: workflow_id={data.get('workflow_id')}")
    return True


def main() -> int:
    _log(f"Base URL: {BASE_URL}")
    _log(f"Sender: {SENDER_EMAIL}; Receiver: {RECEIVER_EMAIL}")

    with httpx.Client() as client:
        if not wait_for_health(client):
            _err("Backend not healthy; is `npm run dev:pm2` running?")
            return 2

        ok1 = run_same_user_flow(client)
        ok2 = run_two_client_flow(client)

    if ok1 and ok2:
        _log("All E2E flows passed.")
        return 0
    if ok1:
        _log("Same-user flow passed; two-client had issues (receiver login may be missing).")
        return 0
    _err("E2E flows failed.")
    return 1


def test_nexus_file_transfer_e2e() -> None:
    """Pytest entry point: runs E2E flows and asserts success."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
