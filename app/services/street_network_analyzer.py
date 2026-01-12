"""Street Network Analyzer using OSMnx.

This service analyzes road networks using OSMnx library to calculate:
- Road network density
- Road length per area
- Road type distribution
- Connectivity metrics
"""

import logging
from typing import Dict, Any, Optional
import osmnx as ox

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure OSMnx
ox.settings.use_cache = True
ox.settings.log_console = False


class StreetNetworkAnalyzer:
    """Service for analyzing street networks using OSMnx."""

    def __init__(self):
        """Initialize street network analyzer."""
        self.network_type = 'all'  # 'drive', 'walk', 'bike', 'all'

    def analyze_road_network(
        self,
        lat: float,
        lon: float,
        distance_m: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Analyze road network within distance of location.

        Args:
            lat: Latitude
            lon: Longitude
            distance_m: Distance in meters (default: 1000m = 1km)

        Returns:
            Dictionary with network analysis results:
            - road_length_km: Total road length in kilometers
            - road_density: Road length per area (km/km²)
            - node_count: Number of network nodes
            - edge_count: Number of network edges
            - road_types: Distribution of road types
            - connectivity: Basic connectivity metrics
        """
        try:
            logger.info(f"Analyzing road network for ({lat}, {lon}) within {distance_m}m")

            # Get graph from point
            G = ox.graph_from_point(
                (lat, lon),
                dist=distance_m,
                network_type=self.network_type,
                simplify=True
            )

            if G is None or len(G.nodes()) == 0:
                logger.warning(f"No road network found for ({lat}, {lon})")
                return self._empty_result()

            # Calculate total road length
            road_length_m = sum([
                data.get('length', 0)
                for u, v, data in G.edges(data=True)
            ])
            road_length_km = road_length_m / 1000.0

            # Calculate area (approximate)
            bbox = ox.utils_geo.bbox_from_point((lat, lon), dist=distance_m)
            area_km2 = self._calculate_bbox_area(bbox)

            # Road density
            road_density = road_length_km / area_km2 if area_km2 > 0 else 0.0

            # Road type distribution
            road_types = {}
            for u, v, data in G.edges(data=True):
                highway_type = data.get('highway', 'unknown')
                # Handle both string and list types (OSM can return either)
                if isinstance(highway_type, list):
                    # If it's a list, use the first element or join them
                    highway_type = highway_type[0] if highway_type else 'unknown'
                elif not isinstance(highway_type, str):
                    # Convert other types to string
                    highway_type = str(highway_type) if highway_type else 'unknown'
                road_types[highway_type] = road_types.get(highway_type, 0) + 1

            # Basic connectivity metrics
            node_count = len(G.nodes())
            edge_count = len(G.edges())

            # Calculate average node degree (connectivity indicator)
            degrees = dict(G.degree())
            avg_degree = sum(degrees.values()) / node_count if node_count > 0 else 0.0

            result = {
                "road_length_km": road_length_km,
                "road_density": road_density,  # km/km²
                "node_count": node_count,
                "edge_count": edge_count,
                "road_types": road_types,
                "connectivity": {
                    "average_degree": avg_degree,
                    "max_degree": max(degrees.values()) if degrees else 0,
                    "min_degree": min(degrees.values()) if degrees else 0
                },
                "area_km2": area_km2,
                "distance_m": distance_m
            }

            logger.info(
                f"Road network analysis complete: {road_length_km:.2f} km roads, "
                f"density={road_density:.2f} km/km², {node_count} nodes"
            )

            return result

        except Exception as e:
            logger.error(f"Road network analysis failed: {e}", exc_info=True)
            return self._empty_result()

    @staticmethod
    def _calculate_bbox_area(bbox: tuple) -> float:
        """
        Calculate approximate area of bounding box in km².

        Args:
            bbox: (north, south, east, west) tuple

        Returns:
            Area in square kilometers
        """
        north, south, east, west = bbox

        # Approximate calculation (simplified)
        # 1 degree latitude ≈ 111 km
        lat_diff = abs(north - south)
        lon_diff = abs(east - west)

        # Adjust for longitude (varies by latitude)
        avg_lat = (north + south) / 2.0
        lon_km_per_degree = 111.0 * abs(avg_lat / 90.0) if avg_lat != 0 else 111.0

        area_km2 = (lat_diff * 111.0) * (lon_diff * lon_km_per_degree)

        return area_km2

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "road_length_km": 0.0,
            "road_density": 0.0,
            "node_count": 0,
            "edge_count": 0,
            "road_types": {},
            "connectivity": {
                "average_degree": 0.0,
                "max_degree": 0,
                "min_degree": 0
            },
            "area_km2": 0.0,
            "distance_m": 0.0,
            "error": "No network data available"
        }
