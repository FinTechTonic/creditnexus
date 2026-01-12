"""OpenStreetMap Service for geospatial data retrieval.

This service integrates with OpenStreetMap's Overpass API to retrieve:
- Road networks
- Building footprints
- Land use polygons
- Points of Interest (POIs)
- Green infrastructure (parks, green spaces)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib

import overpy
from app.core.config import settings

logger = logging.getLogger(__name__)


class OSMService:
    """Service for querying OpenStreetMap data via Overpass API."""

    def __init__(self):
        """Initialize OSM service with configuration."""
        self.api_url = settings.OSM_OVERPASS_API_URL
        self.cache_enabled = settings.OSM_CACHE_ENABLED
        self.cache_ttl_hours = settings.OSM_CACHE_TTL_HOURS
        self.api = overpy.Overpass(url=self.api_url)
        # Simple in-memory cache (could be replaced with Redis in production)
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)

    def _get_cache_key(self, lat: float, lon: float, radius: float) -> str:
        """Generate cache key for location query."""
        key_str = f"osm_{lat:.4f}_{lon:.4f}_{radius:.0f}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid."""
        if not self.cache_enabled:
            return False
        age = datetime.utcnow() - timestamp
        return age < timedelta(hours=self.cache_ttl_hours)

    async def get_osm_features(
        self,
        lat: float,
        lon: float,
        radius_m: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Get OSM features within radius of location.

        Args:
            lat: Latitude
            lon: Longitude
            radius_m: Radius in meters (default: 1000m = 1km)

        Returns:
            Dictionary with OSM features:
            - building_count: Number of buildings
            - buildings: List of building data
            - roads: List of road data
            - land_use: List of land use polygons
            - pois: List of Points of Interest
            - green_infrastructure: List of green spaces
            - road_density: Road length per area (km/km²)
            - building_density: Building count per area
            - green_coverage: Percentage of green infrastructure
        """
        # Check cache
        cache_key = self._get_cache_key(lat, lon, radius_m)
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.debug(f"Using cached OSM data for ({lat}, {lon})")
                return data

        try:
            # Calculate bounding box
            # Approximate: 1 degree latitude ≈ 111 km
            delta_lat = radius_m / 111000.0
            delta_lon = radius_m / (111000.0 * abs(lat / 90.0)) if lat != 0 else radius_m / 111000.0

            south = lat - delta_lat
            north = lat + delta_lat
            west = lon - delta_lon
            east = lon + delta_lon

            # Build Overpass QL query
            query = f"""
            [out:json][timeout:25];
            (
              way["building"]({south},{west},{north},{east});
              way["highway"]({south},{west},{north},{east});
              way["landuse"]({south},{west},{north},{east});
              way["leisure"]({south},{west},{north},{east});
              node["amenity"]({south},{west},{north},{east});
              node["shop"]({south},{west},{north},{east});
            );
            out body;
            >;
            out skel qt;
            """

            logger.info(f"Querying OSM data for ({lat}, {lon}) with radius {radius_m}m")
            result = self.api.query(query)

            # Process results
            buildings = []
            roads = []
            land_use = []
            pois = []
            green_infrastructure = []

            # Process ways (buildings, roads, land use)
            for way in result.ways:
                tags = way.tags
                if "building" in tags:
                    buildings.append({
                        "id": way.id,
                        "tags": tags,
                        "nodes": len(way.nodes)
                    })
                elif "highway" in tags:
                    # Calculate approximate length (simplified)
                    road_length = self._estimate_way_length(way.nodes)
                    roads.append({
                        "id": way.id,
                        "type": tags.get("highway", "unknown"),
                        "length_m": road_length,
                        "tags": tags
                    })
                elif "landuse" in tags:
                    land_use.append({
                        "id": way.id,
                        "type": tags.get("landuse"),
                        "tags": tags
                    })
                elif "leisure" in tags:
                    leisure_type = tags.get("leisure")
                    if leisure_type in ["park", "garden", "nature_reserve"]:
                        green_infrastructure.append({
                            "id": way.id,
                            "type": leisure_type,
                            "tags": tags
                        })

            # Process nodes (POIs)
            for node in result.nodes:
                tags = node.tags
                if "amenity" in tags or "shop" in tags:
                    pois.append({
                        "id": node.id,
                        "lat": node.lat,
                        "lon": node.lon,
                        "tags": tags
                    })

            # Calculate metrics
            total_road_length_km = sum(r["length_m"] for r in roads) / 1000.0
            area_km2 = (2 * delta_lat * 111) * (2 * delta_lon * 111 * abs(lat / 90.0) if lat != 0 else 2 * delta_lon * 111)
            road_density = total_road_length_km / area_km2 if area_km2 > 0 else 0.0

            building_count = len(buildings)
            building_density = building_count / area_km2 if area_km2 > 0 else 0.0

            # Estimate green coverage (simplified - count green infrastructure)
            green_coverage = len(green_infrastructure) / max(building_count, 1) if building_count > 0 else 0.0
            green_coverage = min(green_coverage, 1.0)  # Cap at 100%

            result_data = {
                "building_count": building_count,
                "buildings": buildings[:100],  # Limit to first 100 for response size
                "roads": roads[:100],
                "land_use": land_use,
                "pois": pois[:50],
                "green_infrastructure": green_infrastructure,
                "road_density": road_density,  # km/km²
                "building_density": building_density,  # buildings/km²
                "green_coverage": green_coverage,  # 0.0-1.0
                "total_road_length_km": total_road_length_km,
                "area_km2": area_km2,
                "queried_at": datetime.utcnow().isoformat()
            }

            # Cache result
            if self.cache_enabled:
                self._cache[cache_key] = (result_data, datetime.utcnow())

            logger.info(
                f"OSM query complete: {building_count} buildings, "
                f"{len(roads)} roads, road_density={road_density:.2f} km/km²"
            )

            return result_data

        except Exception as e:
            logger.error(f"OSM query failed: {e}", exc_info=True)
            # Return empty result on error
            return {
                "building_count": 0,
                "buildings": [],
                "roads": [],
                "land_use": [],
                "pois": [],
                "green_infrastructure": [],
                "road_density": 0.0,
                "building_density": 0.0,
                "green_coverage": 0.0,
                "total_road_length_km": 0.0,
                "area_km2": 0.0,
                "error": str(e),
                "queried_at": datetime.utcnow().isoformat()
            }

    def _estimate_way_length(self, nodes: List) -> float:
        """
        Estimate way length from nodes (simplified calculation).

        Args:
            nodes: List of node objects with lat/lon

        Returns:
            Estimated length in meters
        """
        if len(nodes) < 2:
            return 0.0

        total_length = 0.0
        for i in range(len(nodes) - 1):
            node1 = nodes[i]
            node2 = nodes[i + 1]
            # Haversine distance (simplified)
            lat1, lon1 = node1.lat, node1.lon
            lat2, lon2 = node2.lat, node2.lon
            distance = self._haversine_distance(lat1, lon1, lat2, lon2)
            total_length += distance

        return total_length

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Returns:
            Distance in meters
        """
        from math import radians, sin, cos, sqrt, atan2

        R = 6371000  # Earth radius in meters

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c
