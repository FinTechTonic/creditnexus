"""Green Finance Data Models (Pydantic).

This module contains Pydantic models for green finance data:
- Environmental metrics (emissions, air quality, pollution)
- Urban activity metrics (vehicle counts, traffic, OSM-based indicators)
- Sustainability scores (composite, SDG-aligned)
- SDG alignment scores
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class EnvironmentalMetrics(BaseModel):
    """Environmental metrics for green finance assessment."""
    
    air_quality_index: Optional[float] = Field(
        default=None,
        description="Air Quality Index (AQI) value (0-500)"
    )
    pm25: Optional[float] = Field(
        default=None,
        description="PM2.5 concentration in µg/m³"
    )
    pm10: Optional[float] = Field(
        default=None,
        description="PM10 concentration in µg/m³"
    )
    no2: Optional[float] = Field(
        default=None,
        description="NO2 concentration in µg/m³"
    )
    o3: Optional[float] = Field(
        default=None,
        description="O3 concentration in µg/m³"
    )
    so2: Optional[float] = Field(
        default=None,
        description="SO2 concentration in µg/m³"
    )
    co: Optional[float] = Field(
        default=None,
        description="CO concentration in mg/m³"
    )
    vehicle_emissions: Optional[float] = Field(
        default=None,
        description="Estimated vehicle emissions in tons CO2/year per km²"
    )
    methane_level: Optional[float] = Field(
        default=None,
        description="Methane concentration in ppb above background"
    )


class UrbanActivityMetrics(BaseModel):
    """Urban activity metrics from OSM and satellite data."""
    
    vehicle_count: Optional[int] = Field(
        default=None,
        description="Number of vehicles detected"
    )
    vehicle_density: Optional[float] = Field(
        default=None,
        description="Vehicle density in vehicles/km²"
    )
    road_density: Optional[float] = Field(
        default=None,
        description="Road network density in km/km²"
    )
    building_density: Optional[float] = Field(
        default=None,
        description="Building density in buildings/km²"
    )
    building_count: Optional[int] = Field(
        default=None,
        description="Number of buildings"
    )
    poi_count: Optional[int] = Field(
        default=None,
        description="Number of Points of Interest"
    )
    traffic_flow: Optional[float] = Field(
        default=None,
        description="Estimated traffic flow (vehicles/hour)"
    )


class SustainabilityComponents(BaseModel):
    """Component scores for composite sustainability calculation."""
    
    vegetation_health: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Vegetation health score (NDVI-based, 0.0-1.0)"
    )
    air_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Air quality score (AQI-based, inverted, 0.0-1.0)"
    )
    urban_activity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Urban activity score (OSM-based, 0.0-1.0)"
    )
    green_infrastructure: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Green infrastructure score (parks, green spaces, 0.0-1.0)"
    )
    pollution_levels: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Pollution levels score (inverted, 0.0-1.0)"
    )


class SustainabilityScore(BaseModel):
    """Composite sustainability score with component breakdown."""
    
    composite_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Composite sustainability score (0.0-1.0)"
    )
    components: SustainabilityComponents = Field(
        description="Individual component scores"
    )
    location_type: str = Field(
        description="Location classification: urban, suburban, or rural"
    )
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when score was calculated"
    )


class SDGAlignment(BaseModel):
    """SDG alignment scores per goal."""
    
    sdg_11: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="SDG 11: Sustainable Cities and Communities (0.0-1.0)"
    )
    sdg_13: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="SDG 13: Climate Action (0.0-1.0)"
    )
    sdg_15: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="SDG 15: Life on Land (0.0-1.0)"
    )
    overall_alignment: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall SDG alignment score (average, 0.0-1.0)"
    )
    aligned_goals: List[str] = Field(
        default_factory=list,
        description="List of SDG goals with score >= 0.7"
    )
    needs_improvement: List[str] = Field(
        default_factory=list,
        description="List of SDG goals with score < 0.5"
    )


class GreenFinanceAssessment(BaseModel):
    """Comprehensive green finance assessment result."""
    
    transaction_id: str = Field(
        description="Transaction/deal identifier"
    )
    location_lat: float = Field(
        description="Location latitude"
    )
    location_lon: float = Field(
        description="Location longitude"
    )
    location_type: str = Field(
        description="Location classification: urban, suburban, or rural"
    )
    location_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in location classification (0.0-1.0)"
    )
    environmental_metrics: EnvironmentalMetrics = Field(
        description="Environmental metrics (emissions, air quality, pollution)"
    )
    urban_activity_metrics: UrbanActivityMetrics = Field(
        description="Urban activity metrics (vehicle counts, traffic, OSM-based indicators)"
    )
    sustainability_score: SustainabilityScore = Field(
        description="Composite sustainability score with component breakdown"
    )
    sdg_alignment: SDGAlignment = Field(
        description="SDG alignment scores per goal"
    )
    policy_decisions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of policy decisions related to this assessment"
    )
    cdm_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="CDM events related to this assessment"
    )
    assessed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Assessment timestamp"
    )
