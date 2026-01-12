"""Air Quality Service for OpenAQ API integration.

This service retrieves air quality data from OpenAQ API:
- Air Quality Index (AQI)
- PM2.5, PM10, NO2, O3, SO2, CO measurements
- Temporal trends
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class AirQualityService:
    """Service for retrieving air quality data from OpenAQ API."""

    def __init__(self):
        """Initialize air quality service."""
        self.api_url = "https://api.openaq.org/v2"
        self.cache_enabled = settings.AIR_QUALITY_CACHE_ENABLED
        self.cache_ttl_hours = settings.AIR_QUALITY_CACHE_TTL_HOURS
        # Simple in-memory cache (could be replaced with Redis in production)
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)

    def _get_cache_key(self, lat: float, lon: float, radius: float) -> str:
        """Generate cache key for location query."""
        key_str = f"aqi_{lat:.4f}_{lon:.4f}_{radius:.0f}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid."""
        if not self.cache_enabled:
            return False
        age = datetime.utcnow() - timestamp
        return age < timedelta(hours=self.cache_ttl_hours)

    def _calculate_aqi_from_pm25(self, pm25: float) -> float:
        """
        Calculate AQI from PM2.5 concentration (US EPA formula).

        Args:
            pm25: PM2.5 concentration in µg/m³

        Returns:
            AQI value (0-500)
        """
        # US EPA AQI breakpoints for PM2.5
        if pm25 <= 12.0:
            return (50.0 / 12.0) * pm25
        elif pm25 <= 35.4:
            return 50.0 + ((100.0 - 50.0) / (35.4 - 12.0)) * (pm25 - 12.0)
        elif pm25 <= 55.4:
            return 100.0 + ((150.0 - 100.0) / (55.4 - 35.4)) * (pm25 - 35.4)
        elif pm25 <= 150.4:
            return 150.0 + ((200.0 - 150.0) / (150.4 - 55.4)) * (pm25 - 55.4)
        elif pm25 <= 250.4:
            return 200.0 + ((300.0 - 200.0) / (250.4 - 150.4)) * (pm25 - 150.4)
        else:
            return 300.0 + ((500.0 - 300.0) / (500.4 - 250.4)) * (pm25 - 250.4)

    def _generate_synthetic_aqi(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Generate synthetic AQI data for testing/fallback.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Synthetic air quality data
        """
        # Use location to seed for consistency
        import random
        seed = int((lat * 1000 + lon * 1000) % 10000)
        random.seed(seed)

        # Generate realistic synthetic values
        base_aqi = 50 + random.uniform(-20, 40)  # 30-90 range
        pm25 = 10 + random.uniform(-5, 15)  # 5-25 µg/m³
        pm10 = pm25 * 1.5 + random.uniform(-5, 10)
        no2 = 20 + random.uniform(-10, 30)  # 10-50 µg/m³

        return {
            "aqi": max(0, min(500, base_aqi)),
            "pm25": max(0, pm25),
            "pm10": max(0, pm10),
            "no2": max(0, no2),
            "o3": 30 + random.uniform(-10, 20),
            "so2": 5 + random.uniform(-2, 8),
            "co": 0.5 + random.uniform(-0.2, 0.5),
            "data_source": "synthetic",
            "queried_at": datetime.utcnow().isoformat()
        }

    async def get_air_quality(
        self,
        lat: float,
        lon: float,
        radius_km: float = 5.0
    ) -> Dict[str, Any]:
        """
        Get air quality data for location.

        Args:
            lat: Latitude
            lon: Longitude
            radius_km: Search radius in kilometers (default: 5km)

        Returns:
            Dictionary with air quality data:
            - aqi: Air Quality Index (0-500)
            - pm25: PM2.5 concentration (µg/m³)
            - pm10: PM10 concentration (µg/m³)
            - no2: NO2 concentration (µg/m³)
            - o3: O3 concentration (µg/m³)
            - so2: SO2 concentration (µg/m³)
            - co: CO concentration (mg/m³)
            - data_source: "openaq" or "synthetic"
        """
        if not settings.AIR_QUALITY_ENABLED:
            logger.warning("Air quality service is disabled")
            return self._generate_synthetic_aqi(lat, lon)

        # Check cache
        cache_key = self._get_cache_key(lat, lon, radius_km)
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.debug(f"Using cached air quality data for ({lat}, {lon})")
                return data

        try:
            # Query OpenAQ API v2
            radius_m = radius_km * 1000
            url = f"{self.api_url}/locations"
            params = {
                "coordinates": f"{lat},{lon}",
                "radius": int(radius_m),
                "limit": 1,
                "order_by": "distance"
            }

            logger.info(f"Querying OpenAQ API for ({lat}, {lon}) within {radius_km}km")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if results and len(results) > 0:
                    location = results[0]
                    location_id = location.get("id")

                    # Get latest measurements for this location
                    measurements_url = f"{self.api_url}/locations/{location_id}/latest"
                    measurements_response = requests.get(measurements_url, timeout=10)

                    if measurements_response.status_code == 200:
                        measurements_data = measurements_response.json()
                        measurements = measurements_data.get("results", [])

                        # Extract parameters
                        aqi_data = {
                            "pm25": None,
                            "pm10": None,
                            "no2": None,
                            "o3": None,
                            "so2": None,
                            "co": None
                        }

                        for measurement in measurements:
                            parameter = measurement.get("parameter", "").lower()
                            value = measurement.get("value")
                            if parameter in aqi_data:
                                aqi_data[parameter] = value

                        # Calculate AQI from PM2.5 (primary indicator)
                        pm25 = aqi_data["pm25"] or 0.0
                        aqi = self._calculate_aqi_from_pm25(pm25) if pm25 > 0 else 50.0

                        result = {
                            "aqi": aqi,
                            "pm25": aqi_data["pm25"],
                            "pm10": aqi_data["pm10"],
                            "no2": aqi_data["no2"],
                            "o3": aqi_data["o3"],
                            "so2": aqi_data["so2"],
                            "co": aqi_data["co"],
                            "data_source": "openaq",
                            "location_id": location_id,
                            "queried_at": datetime.utcnow().isoformat()
                        }

                        # Cache result
                        if self.cache_enabled:
                            self._cache[cache_key] = (result, datetime.utcnow())

                        logger.info(f"Air quality retrieved: AQI={aqi:.1f}, PM2.5={pm25:.1f} µg/m³")
                        return result

            # Fallback to synthetic data
            logger.warning(f"OpenAQ API returned no data, using synthetic fallback")
            return self._generate_synthetic_aqi(lat, lon)

        except requests.RequestException as e:
            logger.error(f"OpenAQ API request failed: {e}")
            return self._generate_synthetic_aqi(lat, lon)
        except Exception as e:
            logger.error(f"Air quality retrieval failed: {e}", exc_info=True)
            return self._generate_synthetic_aqi(lat, lon)
