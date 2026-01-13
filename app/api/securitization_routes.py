"""Securitization API routes for structured finance products."""

import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db import get_db
from app.db.models import (
    SecuritizationPool, SecuritizationTranche, SecuritizationPoolAsset,
    RegulatoryFiling, Deal, LoanAsset, User, NotarizationRecord, PaymentEvent as PaymentEventModel
)
from app.auth.jwt_auth import get_current_user, require_auth
from app.services.securitization_service import SecuritizationService
from app.services.wallet_service import WalletService
from app.services.blockchain_service import BlockchainService
from app.services.x402_payment_service import X402PaymentService, get_x402_payment_service
from app.services.notarization_service import NotarizationService
from app.models.cdm import Money, Currency, Party
from app.models.cdm_payment import PaymentEvent, PaymentType, PaymentMethod
from app.core.config import settings
from app.utils.audit import log_audit_action, AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/securitization", tags=["securitization"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateSecuritizationPoolRequest(BaseModel):
    """Request model for creating a securitization pool."""
    pool_name: str = Field(..., description="Pool name")
    pool_type: str = Field(..., description="Pool type: ABS, CLO, MBS, etc.")
    originator_user_id: int = Field(..., description="User ID of the originator")
    trustee_user_id: int = Field(..., description="User ID of the trustee")
    servicer_user_id: Optional[int] = Field(None, description="User ID of the servicer (optional)")
    underlying_asset_ids: List[Dict[str, Any]] = Field(
        ...,
        description="List of underlying assets with asset_id, asset_type, value, currency"
    )
    tranche_data: List[Dict[str, Any]] = Field(
        ...,
        description="List of tranches with name, class, size, interest_rate, priority, risk_rating"
    )
    payment_waterfall_rules: List[Dict[str, Any]] = Field(
        ...,
        description="List of payment waterfall rules with priority, tranche_id, payment_type, percentage"
    )


class AddTranchesRequest(BaseModel):
    """Request model for adding tranches to a pool."""
    tranche_data: List[Dict[str, Any]] = Field(
        ...,
        description="List of tranches with name, class, size, interest_rate, priority, risk_rating"
    )


class AddAssetsRequest(BaseModel):
    """Request model for adding assets to a pool."""
    underlying_asset_ids: List[Dict[str, Any]] = Field(
        ...,
        description="List of underlying assets with asset_id, asset_type, value, currency"
    )


class PurchaseTrancheRequest(BaseModel):
    """Request model for purchasing a tranche."""
    tranche_id: int = Field(..., description="Tranche ID to purchase")
    buyer_user_id: int = Field(..., description="User ID of the buyer")
    payment_payload: Optional[Dict[str, Any]] = Field(None, description="x402 payment payload (required for non-admin)")


class DistributePaymentsRequest(BaseModel):
    """Request model for distributing payments to tranche holders."""
    payment_amount: Decimal = Field(..., description="Total payment amount to distribute")
    payment_type: str = Field(..., description="Payment type: 'interest' or 'principal'")
    payment_payloads: Optional[List[Dict[str, Any]]] = Field(None, description="x402 payment payloads (one per tranche)")


class NotarizeSecuritizationRequest(BaseModel):
    """Request model for notarizing a securitization pool."""
    signer_user_ids: List[int] = Field(..., description="List of user IDs who must sign")
    payment_payload: Optional[Dict[str, Any]] = Field(None, description="x402 payment payload (required for non-admin)")
    skip_payment: Optional[bool] = Field(False, description="Skip payment (admin only)")


# ============================================================================
# Pool Management Endpoints
# ============================================================================

@router.post("/pools")
async def create_securitization_pool(
    request: CreateSecuritizationPoolRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create a new securitization pool.
    
    Creates a CDM-compliant securitization pool with underlying assets and tranches.
    """
    try:
        service = SecuritizationService(db)
        
        # Convert request format to service format
        underlying_assets = []
        for asset in request.underlying_asset_ids:
            asset_dict = {
                "asset_type": asset.get("asset_type"),
                "asset_id": asset.get("asset_id"),
                "value": asset.get("value", "0"),
                "currency": asset.get("currency", "USD")
            }
            # Extract deal_id or loan_asset_id from asset_id if needed
            if asset.get("asset_type") == "deal":
                asset_dict["deal_id"] = asset.get("deal_id") or asset.get("asset_id")
            elif asset.get("asset_type") == "loan_asset":
                asset_dict["loan_asset_id"] = asset.get("loan_asset_id") or asset.get("asset_id")
            underlying_assets.append(asset_dict)
        
        # Convert tranche data format
        tranches = []
        for tranche in request.tranche_data:
            tranche_dict = {
                "tranche_name": tranche.get("name") or tranche.get("tranche_name"),
                "tranche_class": tranche.get("class") or tranche.get("tranche_class"),
                "size": {
                    "amount": tranche.get("size") if isinstance(tranche.get("size"), (int, float, str)) else tranche.get("size", {}).get("amount", 0),
                    "currency": tranche.get("currency") or tranche.get("size", {}).get("currency", "USD")
                },
                "interest_rate": tranche.get("interest_rate"),
                "risk_rating": tranche.get("risk_rating"),
                "payment_priority": tranche.get("priority") or tranche.get("payment_priority", 999)
            }
            tranches.append(tranche_dict)
        
        # Convert payment waterfall rules
        payment_waterfall = None
        if request.payment_waterfall_rules:
            payment_waterfall = {
                "rules": request.payment_waterfall_rules
            }
        
        pool = service.create_securitization_pool(
            pool_name=request.pool_name,
            pool_type=request.pool_type,
            originator_id=request.originator_user_id,
            trustee_id=request.trustee_user_id,
            underlying_assets=underlying_assets,
            tranches=tranches,
            payment_waterfall=payment_waterfall
        )
        
        return {
            "status": "success",
            "pool_id": pool.pool_id,
            "pool_name": pool.pool_name,
            "total_pool_value": str(pool.total_pool_value),
            "currency": pool.currency,
            "status": pool.status,
            "created_at": pool.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create securitization pool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create pool: {str(e)}")


@router.get("/pools")
async def list_securitization_pools(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    pool_type: Optional[str] = Query(None, description="Filter by pool type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List securitization pools with pagination and filtering."""
    try:
        query = db.query(SecuritizationPool)
        
        if pool_type:
            query = query.filter(SecuritizationPool.pool_type == pool_type)
        if status:
            query = query.filter(SecuritizationPool.status == status)
        
        total = query.count()
        pools = query.order_by(SecuritizationPool.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        return {
            "status": "success",
            "pools": [
                {
                    "id": pool.id,
                    "pool_id": pool.pool_id,
                    "pool_name": pool.pool_name,
                    "pool_type": pool.pool_type,
                    "total_pool_value": str(pool.total_pool_value),
                    "currency": pool.currency,
                    "status": pool.status,
                    "created_at": pool.created_at.isoformat()
                }
                for pool in pools
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Failed to list securitization pools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list pools: {str(e)}")


@router.get("/pools/{pool_id}")
async def get_securitization_pool(
    pool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get securitization pool details in CDM-compliant format."""
    try:
        service = SecuritizationService(db)
        pool_details = await service.get_pool_details(str(pool_id))
        
        if not pool_details:
            raise HTTPException(status_code=404, detail="Securitization pool not found")
        
        return {
            "status": "success",
            "pool": pool_details  # Service returns dict directly
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get securitization pool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get pool: {str(e)}")


# ============================================================================
# Asset Selection Endpoints
# ============================================================================

@router.get("/available-deals")
async def get_available_deals(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query("active", description="Filter by deal status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available deals for securitization."""
    try:
        query = db.query(Deal)
        
        if status:
            query = query.filter(Deal.status == status)
        
        total = query.count()
        deals = query.order_by(Deal.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        return {
            "status": "success",
            "deals": [
                {
                    "id": deal.id,
                    "deal_id": deal.deal_id,
                    "borrower_name": deal.borrower_name,
                    "total_commitment": str(deal.total_commitment) if deal.total_commitment else None,
                    "currency": deal.currency,
                    "status": deal.status,
                    "created_at": deal.created_at.isoformat() if deal.created_at else None
                }
                for deal in deals
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Failed to get available deals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get deals: {str(e)}")


@router.get("/available-loans")
async def get_available_loans(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by loan status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available loan assets for securitization."""
    try:
        query = db.query(LoanAsset)
        
        if status:
            query = query.filter(LoanAsset.risk_status == status)
        
        total = query.count()
        loans = query.order_by(LoanAsset.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        return {
            "status": "success",
            "loans": [
                {
                    "id": loan.id,
                    "loan_id": loan.loan_id,
                    "collateral_address": loan.collateral_address,
                    "risk_status": loan.risk_status,
                    "last_verified_score": float(loan.last_verified_score) if loan.last_verified_score else None,
                    "created_at": loan.created_at.isoformat() if loan.created_at else None
                }
                for loan in loans
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Failed to get available loans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get loans: {str(e)}")


@router.get("/available-assets")
async def get_available_assets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    asset_type: Optional[str] = Query(None, description="Filter by asset type: 'deal' or 'loan_asset'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get combined list of available deals and loans for securitization."""
    try:
        deals_query = db.query(Deal).filter(Deal.status == "active")
        loans_query = db.query(LoanAsset)
        
        deals = deals_query.order_by(Deal.created_at.desc()).limit(limit // 2).all()
        loans = loans_query.order_by(LoanAsset.created_at.desc()).limit(limit // 2).all()
        
        assets = []
        
        if not asset_type or asset_type == "deal":
            assets.extend([
                {
                    "asset_id": str(deal.id),
                    "asset_type": "deal",
                    "deal_id": deal.deal_id,
                    "name": deal.borrower_name,
                    "value": str(deal.total_commitment) if deal.total_commitment else "0",
                    "currency": deal.currency or "USD",
                    "status": deal.status
                }
                for deal in deals
            ])
        
        if not asset_type or asset_type == "loan_asset":
            assets.extend([
                {
                    "asset_id": str(loan.id),
                    "asset_type": "loan_asset",
                    "loan_id": loan.loan_id,
                    "name": loan.collateral_address or loan.loan_id,
                    "value": "0",  # Loan assets may not have explicit value
                    "currency": "USD",
                    "status": loan.risk_status
                }
                for loan in loans
            ])
        
        return {
            "status": "success",
            "assets": assets,
            "total": len(assets)
        }
    except Exception as e:
        logger.error(f"Failed to get available assets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get assets: {str(e)}")


# ============================================================================
# Auto-Generation Endpoints
# ============================================================================

@router.get("/contract-addresses")
async def get_contract_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get securitization contract addresses (auto-deploy if missing)."""
    try:
        blockchain_service = BlockchainService()
        contracts = blockchain_service.ensure_contracts_deployed(db)
        
        return {
            "status": "success",
            "contracts": {
                "notarization": contracts.get('notarization', settings.SECURITIZATION_NOTARIZATION_CONTRACT),
                "token": contracts.get('token', settings.SECURITIZATION_TOKEN_CONTRACT),
                "payment_router": contracts.get('router', settings.SECURITIZATION_PAYMENT_ROUTER_CONTRACT),
                "usdc": settings.USDC_TOKEN_ADDRESS
            }
        }
    except Exception as e:
        logger.error(f"Failed to get contract addresses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get contract addresses: {str(e)}")


@router.get("/pools/{pool_id}/auto-signers")
async def get_auto_signers(
    pool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get auto-suggested signer addresses for pool notarization."""
    try:
        pool = db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Securitization pool not found")
        
        wallet_service = WalletService()
        signers = []
        
        # Get originator wallet
        originator = db.query(User).filter(User.id == pool.originator_id).first()
        if originator:
            originator_wallet = wallet_service.ensure_user_has_wallet(originator, db)
            if originator_wallet:
                signers.append({
                    "user_id": originator.id,
                    "wallet_address": originator_wallet,
                    "role": "originator",
                    "name": originator.display_name
                })
        
        # Get trustee wallet
        trustee = db.query(User).filter(User.id == pool.trustee_id).first()
        if trustee:
            trustee_wallet = wallet_service.ensure_user_has_wallet(trustee, db)
            if trustee_wallet:
                signers.append({
                    "user_id": trustee.id,
                    "wallet_address": trustee_wallet,
                    "role": "trustee",
                    "name": trustee.display_name
                })
        
        # Get servicer wallet if exists
        if pool.servicer_id:
            servicer = db.query(User).filter(User.id == pool.servicer_id).first()
            if servicer:
                servicer_wallet = wallet_service.ensure_user_has_wallet(servicer, db)
                if servicer_wallet:
                    signers.append({
                        "user_id": servicer.id,
                        "wallet_address": servicer_wallet,
                        "role": "servicer",
                        "name": servicer.display_name
                    })
        
        return {
            "status": "success",
            "signers": signers
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get auto-signers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get auto-signers: {str(e)}")


# ============================================================================
# Tranche Management Endpoints
# ============================================================================

@router.post("/pools/{pool_id}/tranches")
async def add_tranches(
    pool_id: int,
    request: AddTranchesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Add tranches to an existing securitization pool."""
    try:
        pool = db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Securitization pool not found")
        
        service = SecuritizationService(db)
        # Note: This would require a separate create_tranches method
        # For now, tranches are created as part of pool creation
        raise HTTPException(status_code=501, detail="Separate tranche creation not yet implemented")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add tranches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add tranches: {str(e)}")


@router.get("/pools/{pool_id}/tranches")
async def list_tranches(
    pool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tranches for a securitization pool."""
    try:
        pool = db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Securitization pool not found")
        
        tranches = db.query(SecuritizationTranche).filter(
            SecuritizationTranche.pool_id == pool_id
        ).all()
        
        return {
            "status": "success",
            "tranches": [
                {
                    "id": tranche.id,
                    "tranche_id": tranche.tranche_id,
                    "tranche_name": tranche.tranche_name,
                    "tranche_class": tranche.tranche_class,
                    "size": str(tranche.size),
                    "currency": tranche.currency,
                    "interest_rate": float(tranche.interest_rate),
                    "risk_rating": tranche.risk_rating,
                    "payment_priority": tranche.payment_priority,
                    "token_id": tranche.token_id,
                    "owner_wallet_address": tranche.owner_wallet_address
                }
                for tranche in tranches
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tranches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tranches: {str(e)}")


# ============================================================================
# Payment Endpoints (x402 Integration)
# ============================================================================

@router.post("/pools/{pool_id}/purchase-tranche")
async def purchase_tranche(
    pool_id: int,
    request: PurchaseTrancheRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    payment_service: Optional[X402PaymentService] = Depends(get_x402_payment_service)
):
    """Purchase a securitization tranche via x402 payment.
    
    Returns 402 Payment Required if payment_payload not provided.
    """
    try:
        service = SecuritizationService(db)
        
        # Get pool to find pool_id string
        pool = db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Securitization pool not found")
        
        # Get tranche to find tranche_id string
        tranche_db = db.query(SecuritizationTranche).filter(
            SecuritizationTranche.id == request.tranche_id
        ).first()
        if not tranche_db:
            raise HTTPException(status_code=404, detail="Tranche not found")
        
        # Call service method
        result = service.purchase_tranche_with_payment(
            pool_id=pool.pool_id,
            tranche_id=tranche_db.tranche_name,  # Use tranche_name as identifier
            buyer_id=request.buyer_user_id,
            payment_payload=request.payment_payload,
            payment_service=payment_service
        )
        
        # Check if payment is required (402 response)
        if result.get("status") == "payment_required":
            return JSONResponse(
                status_code=402,
                content=result
            )
        
        return {
            "status": "success",
            "tranche_id": tranche_db.tranche_id,
            "pool_id": pool.pool_id,
            "transaction_hash": result.get("transaction_hash")
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        if e.status_code == 402:
            # Return 402 Payment Required response
            tranche = db.query(SecuritizationTranche).filter(
                SecuritizationTranche.id == request.tranche_id
            ).first()
            if not tranche:
                raise HTTPException(status_code=404, detail="Tranche not found")
            
            return JSONResponse(
                status_code=402,
                content={
                    "status": "Payment Required",
                    "tranche_id": tranche.tranche_id,
                    "amount": str(tranche.size),
                    "currency": tranche.currency,
                    "payment_type": "tranche_purchase",
                    "facilitator_url": payment_service.facilitator_url if payment_service else None
                }
            )
        raise
    except Exception as e:
        logger.error(f"Failed to purchase tranche: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to purchase tranche: {str(e)}")


@router.post("/pools/{pool_id}/distribute-payments")
async def distribute_payments(
    pool_id: int,
    request: DistributePaymentsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    payment_service: Optional[X402PaymentService] = Depends(get_x402_payment_service)
):
    """Distribute payments to tranche holders via x402.
    
    Returns 402 Payment Required if payment_payloads not provided.
    """
    try:
        service = SecuritizationService(db)
        
        pool = db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Securitization pool not found")
        
        distributions = service.distribute_payments(
            pool_id=pool.pool_id,
            total_payment_amount=request.payment_amount,
            payment_type=request.payment_type,
            payment_service=payment_service
        )
        
        return {
            "status": "success",
            "distributions": distributions
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        if e.status_code == 402:
            return JSONResponse(
                status_code=402,
                content={
                    "status": "Payment Required",
                    "message": "Payment payloads required for distribution",
                    "facilitator_url": payment_service.facilitator_url if payment_service else None
                }
            )
        raise
    except Exception as e:
        logger.error(f"Failed to distribute payments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to distribute payments: {str(e)}")


# ============================================================================
# Notarization Endpoints
# ============================================================================

@router.post("/pools/{pool_id}/notarize")
async def notarize_securitization_pool(
    pool_id: int,
    request: NotarizeSecuritizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create notarization request for a securitization pool.
    
    Returns 402 Payment Required if payment_payload not provided (unless admin).
    """
    try:
        service = SecuritizationService(db)
        
        pool = db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Securitization pool not found")
        
        # Use regular notarization service for securitization pools
        notarization_service = NotarizationService(db)
        
        # Get wallet addresses for signers
        wallet_service = WalletService()
        signer_addresses = []
        for user_id in request.signer_user_ids:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=400, detail=f"Signer user {user_id} not found")
            wallet = wallet_service.ensure_user_has_wallet(user, db)
            if wallet:
                signer_addresses.append(wallet)
        
        # For securitization, we need to create a notarization with securitization_pool_id
        # The NotarizationService expects deal_id, but we can work around this
        # by creating the notarization record directly for securitization pools
        
        # Generate notarization hash from pool CDM data
        import hashlib
        import json
        pool_cdm_data = pool.cdm_data or {}
        notarization_hash = hashlib.sha256(
            json.dumps(pool_cdm_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Create notarization record directly (bypassing service for securitization)
        # Note: deal_id is NOT NULL in schema, so we use a placeholder
        # In production, we should make deal_id nullable for securitization notarizations
        placeholder_deal = db.query(Deal).first()
        if not placeholder_deal:
            raise HTTPException(status_code=400, detail="No deals exist - cannot create securitization notarization")
        
        notarization = NotarizationRecord(
            deal_id=placeholder_deal.id,  # Placeholder - securitization_pool_id is the real link
            securitization_pool_id=pool_id,
            notarization_hash=notarization_hash,
            required_signers=signer_addresses,
            signatures=[],
            status="pending"
        )
        db.add(notarization)
        db.flush()
        
        # Handle payment if enabled
        if settings.NOTARIZATION_FEE_ENABLED and not request.skip_payment:
            from app.services.notarization_payment_service import NotarizationPaymentService
            payment_service_wrapper = NotarizationPaymentService(db, None)
            
            # Check if admin can skip
            if current_user.role == "admin" and payment_service_wrapper.can_skip_payment(current_user):
                notarization.payment_status = "skipped"
                db.commit()
            elif request.payment_payload:
                # Process payment (simplified - would need full payment flow)
                notarization.payment_status = "pending"
                db.commit()
            else:
                # Return 402 Payment Required
                fee = payment_service_wrapper.get_notarization_fee()
                return JSONResponse(
                    status_code=402,
                    content={
                        "status": "Payment Required",
                        "notarization_id": notarization.id,
                        "amount": str(fee.amount),
                        "currency": fee.currency.value,
                        "payment_type": "notarization_fee"
                    }
                )
        
        return {
            "status": "success",
            "notarization_id": notarization.id,
            "notarization_hash": notarization.notarization_hash,
            "required_signers": notarization.required_signers,
            "status": notarization.status,
            "payment_status": notarization.payment_status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        if e.status_code == 402:
            # Return 402 Payment Required response
            pool = db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
            if not pool:
                raise HTTPException(status_code=404, detail="Pool not found")
            
            from app.services.notarization_payment_service import NotarizationPaymentService
            payment_service_wrapper = NotarizationPaymentService(db, None)
            fee = payment_service_wrapper.get_notarization_fee()
            
            return JSONResponse(
                status_code=402,
                content={
                    "status": "Payment Required",
                    "notarization_id": None,  # Not yet created
                    "amount": str(fee.amount),
                    "currency": fee.currency.value,
                    "payment_type": "notarization_fee"
                }
            )
        raise
    except Exception as e:
        logger.error(f"Failed to notarize securitization pool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to notarize pool: {str(e)}")


# ============================================================================
# Token Endpoints
# ============================================================================

@router.get("/pools/{pool_id}/tranches/{tranche_id}/token")
async def get_tranche_token(
    pool_id: int,
    tranche_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get NFT token ID for a tranche."""
    try:
        tranche = db.query(SecuritizationTranche).filter(
            and_(
                SecuritizationTranche.id == tranche_id,
                SecuritizationTranche.pool_id == pool_id
            )
        ).first()
        
        if not tranche:
            raise HTTPException(status_code=404, detail="Tranche not found")
        
        return {
            "status": "success",
            "tranche_id": tranche.tranche_id,
            "token_id": tranche.token_id,
            "owner_wallet_address": tranche.owner_wallet_address,
            "nft_contract": settings.SECURITIZATION_TOKEN_CONTRACT
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tranche token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")


@router.get("/tokens/{token_id}")
async def get_token_details(
    token_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details for a tranche token (NFT)."""
    try:
        tranche = db.query(SecuritizationTranche).filter(
            SecuritizationTranche.token_id == token_id
        ).first()
        
        if not tranche:
            raise HTTPException(status_code=404, detail="Token not found")
        
        pool = db.query(SecuritizationPool).filter(
            SecuritizationPool.id == tranche.pool_id
        ).first()
        
        return {
            "status": "success",
            "token_id": token_id,
            "tranche": {
                "tranche_id": tranche.tranche_id,
                "tranche_name": tranche.tranche_name,
                "tranche_class": tranche.tranche_class,
                "size": str(tranche.size),
                "currency": tranche.currency,
                "interest_rate": float(tranche.interest_rate),
                "risk_rating": tranche.risk_rating
            },
            "pool": {
                "pool_id": pool.pool_id if pool else None,
                "pool_name": pool.pool_name if pool else None
            },
            "owner_wallet_address": tranche.owner_wallet_address,
            "nft_contract": settings.SECURITIZATION_TOKEN_CONTRACT
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get token details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get token details: {str(e)}")
