"""LoanAsset SQLModel for Ground Truth Protocol.

This model stores loan assets with both legal (text) and physical (geospatial)
verification data, including vector embeddings for semantic search.
"""

from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text, Float, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB

# Note: pgvector Column type must be defined via sa_column when available
# For now, we store vectors as JSONB arrays (compatible without pgvector extension)


class RiskStatus:
    """Risk status constants for loan assets."""
    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    BREACH = "BREACH"
    PENDING = "PENDING"
    ERROR = "ERROR"


class LoanAsset(SQLModel, table=True):
    """
    Unified model for loan assets combining legal and physical verification.
    
    Stores:
    - Legal reality: Original text + embedding from PDF analysis
    - Physical reality: Geolocation + satellite imagery analysis
    - Verification state: NDVI score and compliance status
    """
    __tablename__ = "loan_assets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    loan_id: str = Field(index=True, description="External loan identifier")
    
    # --- Legal Reality (from PDF) ---
    original_text: Optional[str] = Field(
        default=None, 
        sa_column=Column(Text),
        description="Raw text from loan covenant section"
    )
    # Vector embedding of legal text (OpenAI 1536-dim)
    # Stored as JSON array for compatibility; use pgvector Column(Vector(1536)) if extension is enabled
    legal_vector: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="OpenAI embedding of legal text (1536 dimensions)"
    )
    
    # --- Physical Reality (from Satellite) ---
    geo_lat: Optional[float] = Field(
        default=None,
        description="Latitude of collateral asset"
    )
    geo_lon: Optional[float] = Field(
        default=None,
        description="Longitude of collateral asset"
    )
    collateral_address: Optional[str] = Field(
        default=None,
        description="Original address string from document"
    )
    satellite_snapshot_url: Optional[str] = Field(
        default=None,
        description="URL to stored satellite image snapshot"
    )
    # Geo vector embedding (ResNet/EuroSAT 512-dim)
    geo_vector: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Image embedding from satellite snapshot (512 dimensions)"
    )
    
    # --- SPT Data (FINOS CDM) ---
    spt_data: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="FINOS CDM Sustainability Performance Target JSON"
    )
    
    # --- Verification State ---
    last_verified_score: Optional[float] = Field(
        default=None,
        description="NDVI vegetation index (0.0 to 1.0)"
    )
    spt_threshold: Optional[float] = Field(
        default=0.8,
        description="SPT threshold for compliance (e.g., 0.8 = 80% vegetation)"
    )
    risk_status: str = Field(
        default=RiskStatus.PENDING,
        description="Current compliance status: COMPLIANT, WARNING, BREACH, PENDING, ERROR"
    )
    base_interest_rate: Optional[float] = Field(
        default=5.0,
        description="Base interest rate in percentage"
    )
    current_interest_rate: Optional[float] = Field(
        default=5.0,
        description="Current interest rate (adjusted for penalties)"
    )
    penalty_bps: Optional[float] = Field(
        default=50.0,
        description="Penalty in basis points applied on breach"
    )
    
    # --- Metadata ---
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp"
    )
    last_verified_at: Optional[datetime] = Field(
        default=None,
        description="Last satellite verification timestamp"
    )
    verification_error: Optional[str] = Field(
        default=None,
        description="Error message if verification failed"
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "loan_id": self.loan_id,
            "collateral_address": self.collateral_address,
            "geo_lat": self.geo_lat,
            "geo_lon": self.geo_lon,
            "satellite_snapshot_url": self.satellite_snapshot_url,
            "spt_data": self.spt_data,
            "last_verified_score": self.last_verified_score,
            "spt_threshold": self.spt_threshold,
            "risk_status": self.risk_status,
            "base_interest_rate": self.base_interest_rate,
            "current_interest_rate": self.current_interest_rate,
            "penalty_bps": self.penalty_bps,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "verification_error": self.verification_error,
        }
    
    def update_verification(self, ndvi_score: float) -> None:
        """
        Update verification state based on NDVI score.
        
        Args:
            ndvi_score: Calculated NDVI value (0.0 to 1.0)
        """
        self.last_verified_score = ndvi_score
        self.last_verified_at = datetime.utcnow()
        
        if ndvi_score >= self.spt_threshold:
            self.risk_status = RiskStatus.COMPLIANT
            self.current_interest_rate = self.base_interest_rate
        elif ndvi_score >= self.spt_threshold * 0.9:  # Within 10% of threshold
            self.risk_status = RiskStatus.WARNING
            self.current_interest_rate = self.base_interest_rate
        else:
            self.risk_status = RiskStatus.BREACH
            # Apply penalty: base rate + penalty basis points
            self.current_interest_rate = self.base_interest_rate + (self.penalty_bps / 100)
