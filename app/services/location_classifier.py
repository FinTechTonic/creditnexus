"""Location Classifier for urban/rural/suburban classification.

This service classifies locations based on OSM data:
- Building density
- Road network density
- Land use patterns
"""

import logging
from typing import Tuple, Dict, Any, Optional

from app.services.osm_service import OSMService
from app.services.street_network_analyzer import StreetNetworkAnalyzer

logger = logging.getLogger(__name__)


class LocationClassifier:
    """Service for classifying locations as urban, suburban, or rural."""

    def __init__(self):
        """Initialize location classifier."""
        self.osm_service = OSMService()
        self.street_analyzer = StreetNetworkAnalyzer()

    async def classify(
        self,
        lat: float,
        lon: float,
        osm_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        """
        Classify location as urban, suburban, or rural.

        Args:
            lat: Latitude
            lon: Longitude
            osm_data: Optional pre-fetched OSM data (if None, will fetch)

        Returns:
            Tuple of (classification, confidence_score)
            - classification: "urban", "suburban", or "rural"
            - confidence_score: 0.0-1.0 confidence in classification
        """
        try:
            # Get OSM data if not provided
            if osm_data is None:
                osm_data = await self.osm_service.get_osm_features(lat, lon, radius_m=1000.0)

            # Get road network analysis
            network_data = self.street_analyzer.analyze_road_network(lat, lon, distance_m=1000.0)

            # Extract metrics
            building_count = osm_data.get("building_count", 0)
            road_density = network_data.get("road_density", 0.0)  # km/km²
            building_density = osm_data.get("building_density", 0.0)  # buildings/km²

            # Extract land use tags
            land_use_tags = []
            for land_use in osm_data.get("land_use", []):
                land_type = land_use.get("type")
                if land_type:
                    land_use_tags.append(land_type)

            # Classification algorithm
            urban_score = 0.0

            # Building density indicators
            if building_count > 100:
                urban_score += 1.0
            elif building_count > 50:
                urban_score += 0.5

            if building_density > 50.0:  # buildings/km²
                urban_score += 1.0
            elif building_density > 20.0:
                urban_score += 0.5

            # Road density indicators
            if road_density > 5.0:  # km/km²
                urban_score += 1.0
            elif road_density > 2.0:
                urban_score += 0.5

            # Land use indicators
            if "residential" in land_use_tags:
                urban_score += 0.5
            if "commercial" in land_use_tags:
                urban_score += 1.0
            if "industrial" in land_use_tags:
                urban_score += 0.5

            # Network connectivity (from street analyzer)
            connectivity = network_data.get("connectivity", {})
            avg_degree = connectivity.get("average_degree", 0.0)
            if avg_degree > 3.0:
                urban_score += 0.5
            elif avg_degree > 2.0:
                urban_score += 0.25

            # Classify based on score
            if urban_score >= 2.5:
                classification = "urban"
                confidence = min(0.9, 0.5 + (urban_score - 2.5) * 0.1)
            elif urban_score >= 1.0:
                classification = "suburban"
                confidence = 0.7
            else:
                classification = "rural"
                confidence = min(0.9, 0.6 + (1.0 - urban_score) * 0.1)

            logger.info(
                f"Location classified as {classification} (confidence={confidence:.2f}, "
                f"score={urban_score:.2f}) for ({lat}, {lon})"
            )

            return classification, confidence

        except Exception as e:
            logger.error(f"Location classification failed: {e}", exc_info=True)
            # Default to rural with low confidence
            return "rural", 0.3
