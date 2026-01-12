"""Sustainability Scorer for composite sustainability scoring.

This service calculates composite sustainability scores combining:
- Vegetation Health (NDVI)
- Air Quality (AQI)
- Urban Activity (OSM-based indicators)
- Green Infrastructure (parks, green spaces)
- Pollution Levels (emissions, methane)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class SustainabilityScorer:
    """Service for calculating composite sustainability scores."""

    def __init__(self):
        """Initialize sustainability scorer with weights from config."""
        self.ndvi_weight = settings.SUSTAINABILITY_NDVI_WEIGHT
        self.aqi_weight = settings.SUSTAINABILITY_AQI_WEIGHT
        self.activity_weight = settings.SUSTAINABILITY_ACTIVITY_WEIGHT
        self.green_infra_weight = settings.SUSTAINABILITY_GREEN_INFRA_WEIGHT
        self.pollution_weight = settings.SUSTAINABILITY_POLLUTION_WEIGHT

        # Validate weights sum to 1.0
        total_weight = (
            self.ndvi_weight +
            self.aqi_weight +
            self.activity_weight +
            self.green_infra_weight +
            self.pollution_weight
        )
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                f"Sustainability weights sum to {total_weight:.2f}, not 1.0. "
                "Results may be inaccurate."
            )

    def calculate(
        self,
        ndvi_score: float,
        air_quality: Dict[str, Any],
        location_type: str,
        osm_data: Dict[str, Any],
        vehicle_emissions: Optional[float] = None,
        methane_level: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate composite sustainability score.

        Args:
            ndvi_score: NDVI value (-1.0 to 1.0, typically 0.0-1.0 for vegetation)
            air_quality: Air quality data dictionary (from AirQualityService)
            location_type: "urban", "suburban", or "rural"
            osm_data: OSM data dictionary (from OSMService)
            vehicle_emissions: Optional vehicle emissions (tons CO2/year per km²)
            methane_level: Optional methane concentration (ppb)

        Returns:
            Dictionary with sustainability scores:
            - composite_score: Overall sustainability score (0.0-1.0)
            - components: Individual component scores
            - breakdown: Detailed breakdown by component
        """
        try:
            # Normalize NDVI to 0-1 scale (vegetation health)
            # NDVI typically ranges from -1 to 1, but for vegetation we focus on 0-1
            ndvi_normalized = max(0.0, min(1.0, (ndvi_score + 1.0) / 2.0))

            # Normalize AQI to 0-1 scale (inverted - lower AQI = better)
            aqi = air_quality.get("aqi", 50.0)
            # AQI ranges from 0-500, invert so lower is better
            aqi_normalized = max(0.0, min(1.0, 1.0 - (aqi / 500.0)))

            # Calculate urban activity score (0-1)
            # Based on road density, building density, POI count
            road_density = osm_data.get("road_density", 0.0)  # km/km²
            building_density = osm_data.get("building_density", 0.0)  # buildings/km²
            poi_count = len(osm_data.get("pois", []))

            # Normalize activity indicators
            # Urban areas typically have 3-10 km/km² road density
            road_score = min(1.0, road_density / 10.0)
            # Urban areas typically have 50-200 buildings/km²
            building_score = min(1.0, building_density / 200.0)
            # POI count (normalize to 0-1, assuming max 50 POIs in 1km radius)
            poi_score = min(1.0, poi_count / 50.0)

            # Activity score: average of normalized indicators
            # For urban areas, moderate activity is good (not too high, not too low)
            if location_type == "urban":
                # In urban areas, moderate activity is sustainable
                activity_score = (road_score + building_score + poi_score) / 3.0
                # Penalize extremely high activity (overcrowding)
                if activity_score > 0.8:
                    activity_score = 0.8 - (activity_score - 0.8) * 0.5
            elif location_type == "suburban":
                # Suburban areas benefit from moderate activity
                activity_score = (road_score + building_score + poi_score) / 3.0
            else:  # rural
                # Rural areas benefit from lower activity (preserves nature)
                activity_score = 1.0 - min(1.0, (road_score + building_score + poi_score) / 3.0)

            activity_normalized = max(0.0, min(1.0, activity_score))

            # Calculate green infrastructure score (0-1)
            green_coverage = osm_data.get("green_coverage", 0.0)  # 0.0-1.0
            green_infra_count = len(osm_data.get("green_infrastructure", []))
            # Normalize green infrastructure count (assuming max 10 in 1km radius)
            green_infra_normalized = min(1.0, green_infra_count / 10.0)
            # Combine coverage and count
            green_infra_score = (green_coverage * 0.7 + green_infra_normalized * 0.3)

            # Calculate pollution score (0-1, inverted - lower pollution = better)
            pollution_score = 1.0  # Default: no pollution data = assume good

            if vehicle_emissions is not None:
                # Normalize vehicle emissions (0-200 tons CO2/year per km²)
                vehicle_pollution = min(1.0, vehicle_emissions / 200.0)
                pollution_score = 1.0 - vehicle_pollution

            if methane_level is not None:
                # Normalize methane (0-100 ppb above background)
                methane_pollution = min(1.0, methane_level / 100.0)
                pollution_score = min(pollution_score, 1.0 - methane_pollution)

            # Use AQI as pollution indicator if no specific emissions data
            if vehicle_emissions is None and methane_level is None:
                pollution_score = aqi_normalized

            # Calculate composite score
            composite_score = (
                self.ndvi_weight * ndvi_normalized +
                self.aqi_weight * aqi_normalized +
                self.activity_weight * activity_normalized +
                self.green_infra_weight * green_infra_score +
                self.pollution_weight * pollution_score
            )

            # Ensure score is in valid range
            composite_score = max(0.0, min(1.0, composite_score))

            result = {
                "composite_score": composite_score,
                "components": {
                    "vegetation_health": ndvi_normalized,
                    "air_quality": aqi_normalized,
                    "urban_activity": activity_normalized,
                    "green_infrastructure": green_infra_score,
                    "pollution_levels": pollution_score
                },
                "breakdown": {
                    "ndvi": {
                        "raw": ndvi_score,
                        "normalized": ndvi_normalized,
                        "weight": self.ndvi_weight,
                        "contribution": self.ndvi_weight * ndvi_normalized
                    },
                    "aqi": {
                        "raw": aqi,
                        "normalized": aqi_normalized,
                        "weight": self.aqi_weight,
                        "contribution": self.aqi_weight * aqi_normalized
                    },
                    "activity": {
                        "road_density": road_density,
                        "building_density": building_density,
                        "poi_count": poi_count,
                        "normalized": activity_normalized,
                        "weight": self.activity_weight,
                        "contribution": self.activity_weight * activity_normalized
                    },
                    "green_infrastructure": {
                        "coverage": green_coverage,
                        "count": green_infra_count,
                        "normalized": green_infra_score,
                        "weight": self.green_infra_weight,
                        "contribution": self.green_infra_weight * green_infra_score
                    },
                    "pollution": {
                        "vehicle_emissions": vehicle_emissions,
                        "methane_level": methane_level,
                        "normalized": pollution_score,
                        "weight": self.pollution_weight,
                        "contribution": self.pollution_weight * pollution_score
                    }
                },
                "location_type": location_type,
                "calculated_at": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Sustainability score calculated: {composite_score:.3f} "
                f"(NDVI={ndvi_normalized:.2f}, AQI={aqi_normalized:.2f}, "
                f"Activity={activity_normalized:.2f}, Green={green_infra_score:.2f}, "
                f"Pollution={pollution_score:.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"Sustainability scoring failed: {e}", exc_info=True)
            # Return default low score on error
            return {
                "composite_score": 0.3,
                "components": {
                    "vegetation_health": 0.3,
                    "air_quality": 0.3,
                    "urban_activity": 0.3,
                    "green_infrastructure": 0.3,
                    "pollution_levels": 0.3
                },
                "error": str(e),
                "calculated_at": datetime.utcnow().isoformat()
            }
