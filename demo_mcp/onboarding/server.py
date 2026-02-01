"""
Standalone onboarding site: serves static HTML/CSS/JS and exposes allowlist API.
Optional Plaid KYC: proxy GET /plaid/link-token and POST /plaid/exchange from MCP server.
No auth (demo); in production protect with admin auth.
"""

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Union

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
ALLOWLIST_FILE = Path(os.getenv("ONBOARDING_ALLOWLIST_FILE", str(APP_DIR / "allowlist.json")))
SUBMISSIONS_FILE = Path(os.getenv("ONBOARDING_SUBMISSIONS_FILE", str(APP_DIR / "submissions.json")))


def _print_startup_message() -> None:
    """Print orientation to stdout. Uses buffer+UTF-8 so PM2/Windows cp1252 never raises."""
    if os.getenv("ONBOARDING_SILENT_STARTUP"):
        return
    port = int(os.getenv("PORT", "4024"))
    app_url = os.getenv("CREDITNEXUS_APP_URL", "http://localhost:8000")
    msg = (
        f"\n  Onboarding server: http://0.0.0.0:{port}  ->  / (landing)  /flow.html (onboarding)\n"
        f"  Host app URL: {app_url}\n"
    )
    buf = msg.encode("utf-8", errors="replace") + b"\n"
    try:
        sys.stdout.buffer.write(buf)
        sys.stdout.buffer.flush()
    except (AttributeError, OSError):
        try:
            print(msg, flush=True)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    _print_startup_message()
    yield


app = FastAPI(
    title="CornerStone Agentic Score – Onboarding",
    description="Standalone onboarding site: register agent allowlist and get MCP + env snippet (Arnstein Banking Systems)",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _normalize(addr: str) -> str:
    return (addr or "").strip().lower().replace("0x", "") or ""


def _with_0x(addr: str) -> str:
    a = (addr or "").strip()
    return a if a.startswith("0x") else f"0x{a}"


def load_allowlist() -> dict:
    if not ALLOWLIST_FILE.exists():
        return {"agents": [], "pay_to": [], "agent_wallets": {"evm": [], "aptos": []}}
    try:
        with open(ALLOWLIST_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if "agent_wallets" not in data:
            data["agent_wallets"] = {"evm": [], "aptos": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"agents": [], "pay_to": [], "agent_wallets": {"evm": [], "aptos": []}}


def save_allowlist(data: dict) -> None:
    ALLOWLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALLOWLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ----- Static site -----


@app.get("/")
def index():
    """Serve landing page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/flow.html")
def flow():
    """Serve onboarding flow page."""
    return FileResponse(STATIC_DIR / "flow.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Avoid 404 when browser requests favicon."""
    return Response(status_code=204)


@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
def chrome_devtools():
    """Avoid 404 when Chrome DevTools probes this path."""
    return Response(content=b"{}", media_type="application/json")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ----- API (same as previous app.py) -----


class BankingApplication(BaseModel):
    full_name: str | None = None
    email: str | None = None
    address: str | None = None


class AgentWalletEntry(BaseModel):
    """Single agent wallet with optional network (testnet/mainnet)."""
    address: str = Field(..., description="Wallet address")
    network: str | None = Field(None, description="testnet or mainnet; optional")


class RegisterBody(BaseModel):
    agent_address: str | None = Field(None, description="EVM wallet address to allow as agent (payer) for open_bank_account")
    aptos_agent_address: str | None = Field(None, description="Aptos wallet address to allow as agent for run_prediction/run_backtest")
    agent_addresses: list[Union[str, AgentWalletEntry]] | None = Field(None, description="Multiple EVM addresses; entries may be strings or { address, network? }")
    aptos_agent_addresses: list[Union[str, AgentWalletEntry]] | None = Field(None, description="Multiple Aptos addresses; entries may be strings or { address, network? }")
    pay_to_address: str | None = Field(None, description="Wallet address to allow as payTo (recipient); not required for demo")
    banking_application: BankingApplication | None = Field(None, description="Optional banking application info for submission")


def _load_submissions() -> list:
    if not SUBMISSIONS_FILE.exists():
        return []
    try:
        with open(SUBMISSIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_submissions(entries: list) -> None:
    SUBMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def _mcp_base() -> str | None:
    """MCP server base URL for Plaid proxy (e.g. http://localhost:4023). None if not set."""
    url = (os.getenv("MCP_SERVER_URL") or "").strip().rstrip("/")
    return url or None


def _hydro_env_file() -> Path | None:
    """Path to write env snippet for terminal hydration (source this file). None if not set."""
    raw = (os.getenv("ONBOARDING_HYDRO_ENV_FILE") or "").strip()
    return Path(raw).resolve() if raw else None


@app.get("/config")
def get_config():
    """Return client config (e.g. CreditNexus app URL, Plaid via MCP)."""
    mcp_base = _mcp_base()
    hydro = _hydro_env_file()
    return {
        "creditnexus_app_url": os.getenv("CREDITNEXUS_APP_URL", ""),
        "api_base": "",
        "plaid_enabled": bool(mcp_base),
        "plaid_via_mcp": bool(mcp_base),
        "mcp_server_url": mcp_base or "",
        "hydro_env_file": str(hydro) if hydro else "",
        "env_export_url": "/env-export",
    }


@app.get("/plaid/link-token")
async def plaid_link_token():
    """Proxy Plaid link token from MCP server (serves Plaid KYC from MCP)."""
    mcp_base = _mcp_base()
    if not mcp_base:
        raise HTTPException(status_code=503, detail="Plaid not configured (set MCP_SERVER_URL)")
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{mcp_base}/plaid/link-token", timeout=30.0)
            if r.status_code >= 400:
                detail = r.json() if "application/json" in (r.headers.get("content-type") or "") else r.text
                raise HTTPException(status_code=min(r.status_code, 502), detail=detail)
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/plaid/exchange")
async def plaid_exchange(body: dict):
    """Proxy Plaid public_token exchange to MCP server. Pass optional wallet for borrower score association."""
    mcp_base = _mcp_base()
    if not mcp_base:
        raise HTTPException(status_code=503, detail="Plaid not configured (set MCP_SERVER_URL)")
    body = body or {}
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")
    public_token = body.get("public_token")
    if not public_token:
        raise HTTPException(status_code=400, detail="public_token required")
    payload: dict = {"public_token": public_token}
    if body.get("wallet"):
        payload["wallet"] = body["wallet"]
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{mcp_base}/plaid/exchange",
                json=payload,
                timeout=30.0,
            )
            if r.status_code >= 400:
                detail = r.json() if "application/json" in (r.headers.get("content-type") or "") else r.text
                raise HTTPException(status_code=min(r.status_code, 502), detail=detail)
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


def _collect_addresses(
    single: str | None,
    many: list[Union[str, AgentWalletEntry, dict]] | None,
) -> list[tuple[str, str | None]]:
    """Return list of (normalized_address, network)."""
    out: list[tuple[str, str | None]] = []
    if single and (n := _normalize(single)):
        out.append((n, None))
    if many:
        for item in many:
            if isinstance(item, str) and (n := _normalize(item)):
                out.append((n, None))
            else:
                addr = (getattr(item, "address", None) or (item.get("address") if isinstance(item, dict) else "") or "").strip()
                net_raw = getattr(item, "network", None) or (item.get("network") if isinstance(item, dict) else None)
                net = (net_raw or "").strip().lower() or None
                if net and net not in ("testnet", "mainnet"):
                    net = None
                if addr and (n := _normalize(addr)):
                    out.append((n, net))
    return out


@app.post("/register")
def register(body: RegisterBody):
    """Add agent address(es) to allowlist. At least one EVM or Aptos required. Supports multiple per type with optional testnet/mainnet."""
    evm_entries = _collect_addresses(body.agent_address, body.agent_addresses)
    aptos_entries = _collect_addresses(body.aptos_agent_address, body.aptos_agent_addresses)
    if not evm_entries and not aptos_entries:
        raise HTTPException(
            status_code=400,
            detail="At least one of agent_address (EVM) or aptos_agent_address (Aptos) or agent_addresses/aptos_agent_addresses is required for whitelisting",
        )
    data = load_allowlist()
    agents = set(_normalize(a) for a in data.get("agents") or [])
    pay_to = set(_normalize(p) for p in data.get("pay_to") or [])
    agent_wallets = data.get("agent_wallets") or {"evm": [], "aptos": []}
    evm_wallets: list[dict] = list(agent_wallets.get("evm") or [])
    aptos_wallets: list[dict] = list(agent_wallets.get("aptos") or [])

    seen_evm = {_normalize(e.get("address", "")) for e in evm_wallets}
    for addr, network in evm_entries:
        agents.add(addr)
        if addr not in seen_evm:
            evm_wallets.append({"address": _with_0x(addr), "network": network})
            seen_evm.add(addr)
    seen_aptos = {_normalize(a.get("address", "")) for a in aptos_wallets}
    for addr, network in aptos_entries:
        agents.add(addr)
        if addr not in seen_aptos:
            aptos_wallets.append({"address": _with_0x(addr), "network": network})
            seen_aptos.add(addr)
    if body.pay_to_address:
        pay_to.add(_normalize(body.pay_to_address))

    data["agents"] = [_with_0x(a) for a in sorted(agents)]
    data["pay_to"] = [_with_0x(p) for p in sorted(pay_to)]
    data["agent_wallets"] = {"evm": evm_wallets, "aptos": aptos_wallets}
    save_allowlist(data)

    agent_list = data["agents"]
    pay_to_list = data["pay_to"]
    env_snippet = (
        f"AGENT_ALLOWLIST={','.join(agent_list)}\n"
        f"PAY_TO_ALLOWLIST={','.join(pay_to_list)}"
    )
    hydro_path = _hydro_env_file()
    if hydro_path:
        try:
            hydro_path.parent.mkdir(parents=True, exist_ok=True)
            hydro_path.write_text(env_snippet + "\n", encoding="utf-8")
        except OSError:
            pass
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:4023")
    mcp_snippet = {
        "mcpServers": {
            "creditnexus-demo": {
                "url": mcp_server_url.rstrip("/") + "/mcp",
            }
        }
    }
    if body.banking_application and any([body.banking_application.full_name, body.banking_application.email, body.banking_application.address]):
        entries = _load_submissions()
        entries.append({
            "agent_address": body.agent_address or (evm_entries[0][0] if evm_entries else None),
            "agent_wallets": {"evm": evm_wallets, "aptos": aptos_wallets},
            "banking_application": body.banking_application.model_dump(exclude_none=True),
        })
        _save_submissions(entries[-100:])  # keep last 100

    agent_list = data["agents"]
    pay_to_list = data["pay_to"]
    return {
        "agent_allowlist": agent_list,
        "pay_to_allowlist": pay_to_list,
        "agent_wallets": data["agent_wallets"],
        "env_snippet": env_snippet,
        "mcp_snippet": mcp_snippet,
    }


@app.get("/allowlist")
def get_allowlist():
    """Return current agent and pay_to allowlists and optional agent_wallets (evm/aptos with network)."""
    data = load_allowlist()
    return {
        "agent_allowlist": data.get("agents", []),
        "pay_to_allowlist": data.get("pay_to", []),
        "agent_wallets": data.get("agent_wallets", {"evm": [], "aptos": []}),
    }


@app.get("/snippet")
def get_snippet(mcp_server_url: str | None = None):
    """Return env_snippet and mcp_snippet for current allowlist."""
    data = load_allowlist()
    agent_list = data.get("agents") or []
    pay_to_list = data.get("pay_to") or []
    base = (mcp_server_url or os.getenv("MCP_SERVER_URL", "http://localhost:4023")).rstrip("/")
    env_snippet = (
        f"AGENT_ALLOWLIST={','.join(agent_list)}\n"
        f"PAY_TO_ALLOWLIST={','.join(pay_to_list)}"
    )
    mcp_snippet = {
        "mcpServers": {
            "creditnexus-demo": {
                "url": base + "/mcp",
            }
        }
    }
    return {
        "env_snippet": env_snippet,
        "mcp_snippet": mcp_snippet,
    }


@app.get("/env-export")
def env_export():
    """Return current allowlist as shell export lines for terminal hydration (eval $(curl -s .../env-export))."""
    data = load_allowlist()
    agent_list = data.get("agents") or []
    pay_to_list = data.get("pay_to") or []
    agent_val = ",".join(agent_list)
    pay_to_val = ",".join(pay_to_list)
    lines = [
        f"export AGENT_ALLOWLIST={_sh_escape(agent_val)}",
        f"export PAY_TO_ALLOWLIST={_sh_escape(pay_to_val)}",
    ]
    return Response(
        "\n".join(lines) + "\n",
        media_type="text/plain; charset=utf-8",
    )


def _sh_escape(s: str) -> str:
    """Escape for double-quoted shell (no newlines)."""
    if not s:
        return '""'
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`").replace("\n", " ") + '"'


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "4024"))
    uvicorn.run(app, host="0.0.0.0", port=port)
