"""FastAPI routes and API initialization."""

from fastapi import APIRouter

from app.api.gdpr_routes import gdpr_router
from app.api.deal_signature_routes import router as deal_signature_router
from app.api.signature_routes import signature_router
from app.api.kyc_routes import kyc_router
from app.api.structured_products_routes import router as structured_products_router


api_router = APIRouter(prefix="/api")

# Include routers
api_router.include_router(gdpr_router)
api_router.include_router(deal_signature_router)
api_router.include_router(signature_router)
api_router.include_router(kyc_router)
api_router.include_router(structured_products_router)
