"""
x402 Payment Verifier/Facilitator
Handles payment verification and settlement for Aptos and Ethereum/Base
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="x402 Verifier", version="0.1.0")


# Request/Response Models
class PaymentRequirements(BaseModel):
    amount: str  # USD amount
    currency: str = "USD"
    network: str  # "aptos:2" or "eip155:84532"
    asset: str  # USDC contract/asset address
    payTo: str  # Receiver address
    resource: str  # Resource being paid for
    description: Optional[str] = None


class PaymentPayload(BaseModel):
    """Payment payload from user (signed transaction)"""
    signature: str
    transaction: dict  # For MVP, accept as dict instead of BCS-encoded string
    network: str


class VerifyRequest(BaseModel):
    payment_payload: PaymentPayload
    payment_requirements: PaymentRequirements


class VerifyResponse(BaseModel):
    isValid: bool
    payer: Optional[str] = None
    invalidReason: Optional[str] = None


class SettleRequest(BaseModel):
    payment_payload: PaymentPayload
    payment_requirements: PaymentRequirements
    verification: dict  # Result from /verify


class SettleResponse(BaseModel):
    success: bool
    transaction: Optional[str] = None  # Transaction hash
    network: Optional[str] = None
    payer: Optional[str] = None
    errorReason: Optional[str] = None


class AllowlistAddRequest(BaseModel):
    address: str
    admin_key: str


# In-memory allowlist (will be env vars initially)
AGENT_ALLOWLIST = set(os.getenv("AGENT_ALLOWLIST", "").split(","))
PAY_TO_ALLOWLIST = set(os.getenv("PAY_TO_ALLOWLIST", "").split(","))
ADMIN_KEY = os.getenv("ADMIN_KEY", "hackathon_admin_key")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "x402-verifier",
        "networks": ["aptos:2", "eip155:84532"]
    }


@app.post("/verify", response_model=VerifyResponse)
async def verify_payment(request: VerifyRequest):
    """
    Verify a payment payload against payment requirements.

    Steps:
    1. Decode transaction based on network (Aptos BCS or EVM)
    2. Extract payer, amount, receiver, asset
    3. Verify signature
    4. Check against payment requirements
    5. Check allowlists (agent or payTo)
    6. Optional: Check wallet balance
    """
    network = request.payment_payload.network

    # Route to network-specific verifier
    if network.startswith("aptos"):
        return await verify_aptos_payment(request)
    elif network.startswith("eip155"):
        return await verify_evm_payment(request)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported network: {network}")


@app.post("/settle", response_model=SettleResponse)
async def settle_payment(request: SettleRequest):
    """
    Settle a verified payment on-chain.

    Steps:
    1. Submit transaction to network RPC
    2. Wait for confirmation
    3. Return transaction hash
    """
    if not request.verification.get("isValid"):
        raise HTTPException(status_code=400, detail="Cannot settle invalid payment")

    network = request.payment_payload.network

    # Route to network-specific settler
    if network.startswith("aptos"):
        return await settle_aptos_payment(request)
    elif network.startswith("eip155"):
        return await settle_evm_payment(request)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported network: {network}")


@app.post("/allowlist/agent/add")
async def add_to_agent_allowlist(request: AllowlistAddRequest):
    """Add an agent address to the allowlist (admin only)"""
    if request.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    AGENT_ALLOWLIST.add(request.address)
    return {
        "success": True,
        "address": request.address,
        "allowlist_size": len(AGENT_ALLOWLIST)
    }


@app.get("/allowlist/check/{address}")
async def check_allowlist(address: str):
    """Check if an address is in any allowlist"""
    return {
        "address": address,
        "in_agent_allowlist": address in AGENT_ALLOWLIST,
        "in_payto_allowlist": address in PAY_TO_ALLOWLIST
    }


# Import Aptos verifier
from aptos_verifier import AptosVerifier

# Initialize Aptos verifier
aptos_verifier = AptosVerifier(
    agent_allowlist=AGENT_ALLOWLIST,
    payto_allowlist=PAY_TO_ALLOWLIST
)

# Network-specific implementations

async def verify_aptos_payment(request: VerifyRequest) -> VerifyResponse:
    """Verify Aptos payment using AptosVerifier"""
    result = await aptos_verifier.verify(
        payment_payload=request.payment_payload.dict(),
        payment_requirements=request.payment_requirements.dict()
    )

    return VerifyResponse(
        isValid=result["isValid"],
        payer=result.get("payer"),
        invalidReason=result.get("invalidReason")
    )


async def verify_evm_payment(request: VerifyRequest) -> VerifyResponse:
    """Verify EVM payment (EIP-3009 or raw transaction)"""
    # TODO: Implement EVM verification
    # 1. Decode EVM transaction
    # 2. Extract sender, receiver, amount
    # 3. Verify signature
    # 4. Check against requirements

    return VerifyResponse(
        isValid=False,
        invalidReason="EVM verification not implemented yet"
    )


async def settle_aptos_payment(request: SettleRequest) -> SettleResponse:
    """Submit Aptos transaction to network using AptosVerifier"""
    result = await aptos_verifier.settle(
        payment_payload=request.payment_payload.dict(),
        verification=request.verification
    )

    return SettleResponse(
        success=result["success"],
        transaction=result.get("transaction"),
        network=result.get("network"),
        payer=result.get("payer"),
        errorReason=result.get("errorReason")
    )


async def settle_evm_payment(request: SettleRequest) -> SettleResponse:
    """Submit EVM transaction to network"""
    # TODO: Implement EVM settlement
    # 1. Submit to EVM RPC
    # 2. Wait for confirmation
    # 3. Return transaction hash

    return SettleResponse(
        success=False,
        errorReason="EVM settlement not implemented yet"
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 4022))
    uvicorn.run(app, host="0.0.0.0", port=port)
