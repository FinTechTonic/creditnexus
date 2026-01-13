"""
x402 Payment Service for Credit Nexus.

Handles payment processing using x402 standard, integrated with CDM domain model.
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException, status, Request
import httpx

from app.models.cdm import CreditAgreement, Money, Currency, Party

logger = logging.getLogger(__name__)


class X402PaymentService:
    """
    Service layer for x402 payment processing.
    
    Provides CDM-compliant interfaces to x402 payment protocol,
    handling payment requests, verification, and settlement.
    """
    
    def __init__(
        self,
        facilitator_url: str,
        network: str = "base",
        token: str = "USDC"
    ):
        """
        Initialize x402 payment service.
        
        Args:
            facilitator_url: URL of x402 facilitator service
            network: Blockchain network (base, ethereum, etc.)
            token: Token symbol (USDC, USDT, etc.)
        """
        self.facilitator_url = facilitator_url.rstrip('/')
        self.network = network
        self.token = token
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def request_payment(
        self,
        amount: Decimal,
        currency: Currency,
        payer: Party,
        receiver: Party,
        payment_type: str,
        cdm_reference: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request payment using x402 protocol.
        
        Returns HTTP 402 response structure with payment instructions.
        
        Args:
            amount: Payment amount
            currency: Payment currency (CDM Currency enum)
            payer: Payer party (CDM Party)
            receiver: Receiver party (CDM Party)
            payment_type: Type of payment (loan_disbursement, trade_settlement, interest, penalty)
            cdm_reference: Optional CDM event reference
            
        Returns:
            x402 payment request structure
        """
        # Convert CDM currency to token if needed
        token_address = self._get_token_address(currency)
        
        # Build x402 payment request
        payment_request = {
            "amount": str(amount),
            "currency": currency.value,
            "network": self.network,
            "token": token_address,
            "payer": {
                "id": payer.id,
                "name": payer.name,
                "lei": payer.lei,
                "wallet_address": getattr(payer, 'wallet_address', None)
            },
            "receiver": {
                "id": receiver.id,
                "name": receiver.name,
                "lei": receiver.lei,
                "wallet_address": getattr(receiver, 'wallet_address', None)
            },
            "payment_type": payment_type,
            "cdm_reference": cdm_reference or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "status_code": 402,
            "status": "Payment Required",
            "payment_request": payment_request,
            "facilitator_url": self.facilitator_url
        }
    
    async def verify_payment(
        self,
        payment_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify payment via x402 facilitator.
        
        Args:
            payment_payload: Payment payload from client
            
        Returns:
            Verification result
        """
        try:
            response = await self.client.post(
                f"{self.facilitator_url}/verify",
                json=payment_payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Payment verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Payment verification failed: {str(e)}"
            )
    
    async def settle_payment(
        self,
        payment_payload: Dict[str, Any],
        verification_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Settle payment via x402 facilitator.
        
        Args:
            payment_payload: Payment payload from client
            verification_result: Result from verify_payment
            
        Returns:
            Settlement result
        """
        if not verification_result.get("valid"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment verification failed, cannot settle"
            )
        
        try:
            response = await self.client.post(
                f"{self.facilitator_url}/settle",
                json={
                    "payment_payload": payment_payload,
                    "verification": verification_result
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Payment settlement failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Payment settlement failed: {str(e)}"
            )
    
    async def process_payment_flow(
        self,
        amount: Decimal,
        currency: Currency,
        payer: Party,
        receiver: Party,
        payment_type: str,
        payment_payload: Optional[Dict[str, Any]] = None,
        cdm_reference: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete payment flow: request → verify → settle.
        
        Args:
            amount: Payment amount
            currency: Payment currency
            payer: Payer party
            receiver: Receiver party
            payment_type: Type of payment
            payment_payload: Optional payment payload (if already received)
            cdm_reference: Optional CDM event reference
            
        Returns:
            Complete payment result
        """
        # Step 1: Request payment (if payload not provided)
        if payment_payload is None:
            payment_request = await self.request_payment(
                amount=amount,
                currency=currency,
                payer=payer,
                receiver=receiver,
                payment_type=payment_type,
                cdm_reference=cdm_reference
            )
            return payment_request
        
        # Step 2: Verify payment
        verification = await self.verify_payment(payment_payload)
        
        if not verification.get("valid"):
            return {
                "status": "verification_failed",
                "verification": verification
            }
        
        # Step 3: Settle payment
        settlement = await self.settle_payment(payment_payload, verification)
        
        return {
            "status": "settled",
            "verification": verification,
            "settlement": settlement,
            "payment_id": settlement.get("payment_id"),
            "transaction_hash": settlement.get("transaction_hash")
        }
    
    def _get_token_address(self, currency: Currency) -> str:
        """Get token address for currency on network."""
        # Map CDM currencies to token addresses
        # These are example addresses - should be configured per network
        token_map = {
            Currency.USD: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
            Currency.EUR: "0x..."  # EUR stablecoin address (placeholder)
        }
        return token_map.get(currency, token_map[Currency.USD])
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


def get_x402_payment_service(request: Request) -> Optional[X402PaymentService]:
    """
    FastAPI dependency to get x402 payment service instance from application state.
    
    This dependency function provides access to the X402PaymentService instance
    that was initialized at application startup. Returns None if x402
    payment service is disabled.
    
    Args:
        request: FastAPI request object (to access app.state)
        
    Returns:
        X402PaymentService instance or None if disabled
    """
    if hasattr(request.app.state, 'x402_payment_service'):
        return request.app.state.x402_payment_service
    return None
















