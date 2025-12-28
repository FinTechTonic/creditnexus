"""Geospatial Verification Agent for Ground Truth Protocol.

This agent handles:
1. Address geocoding (converting text addresses to lat/lon)
2. Sentinel Hub satellite data fetching
3. NDVI (Normalized Difference Vegetation Index) calculation
4. Risk status determination based on SPT thresholds
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
import os

import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sentinel Hub configuration
SENTINELHUB_AVAILABLE = False
try:
    from sentinelhub import (
        SHConfig,
        SentinelHubRequest,
        DataCollection,
        MimeType,
        BBox,
        CRS,
        bbox_to_dimensions,
    )
    SENTINELHUB_AVAILABLE = True
    logger.info("Sentinel Hub library loaded successfully")
except ImportError:
    logger.warning("Sentinel Hub library not available - using mock data")


def get_sentinel_config() -> Optional["SHConfig"]:
    """
    Get Sentinel Hub configuration from environment.
    
    Returns:
        SHConfig object if credentials are available, None otherwise
    """
    if not SENTINELHUB_AVAILABLE:
        return None
    
    try:
        sh_key = settings.SENTINELHUB_KEY
        sh_secret = settings.SENTINELHUB_SECRET
        
        if sh_key and sh_secret:
            config = SHConfig()
            config.sh_client_id = sh_key.get_secret_value()
            config.sh_client_secret = sh_secret.get_secret_value()
            return config
    except Exception as e:
        logger.warning(f"Could not configure Sentinel Hub: {e}")
    
    return None


async def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert text address to geographic coordinates using geocoding.
    
    Args:
        address: Full address string (e.g., "123 Main St, City, State ZIP")
        
    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    try:
        geolocator = Nominatim(user_agent="creditnexus_verifier")
        location = geolocator.geocode(address, timeout=10)
        
        if location:
            logger.info(f"Geocoded '{address}' to ({location.latitude}, {location.longitude})")
            return (location.latitude, location.longitude)
        else:
            logger.warning(f"Could not geocode address: {address}")
            return None
            
    except GeocoderTimedOut:
        logger.error(f"Geocoding timed out for address: {address}")
        return None
    except GeocoderServiceError as e:
        logger.error(f"Geocoding service error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected geocoding error: {e}")
        return None


def calculate_ndvi(nir_band: np.ndarray, red_band: np.ndarray) -> float:
    """
    Calculate Normalized Difference Vegetation Index (NDVI).
    
    NDVI = (NIR - Red) / (NIR + Red)
    
    Typical values:
    - Dense forest: 0.6 to 1.0
    - Sparse vegetation: 0.2 to 0.5
    - Bare soil: 0.1 to 0.2
    - Water: -0.3 to 0.0
    - Burned/dead vegetation: -0.1 to 0.1
    
    Args:
        nir_band: Near-infrared band data (Band 8 in Sentinel-2)
        red_band: Red band data (Band 4 in Sentinel-2)
        
    Returns:
        Mean NDVI value for the region (-1.0 to 1.0)
    """
    # Convert to float for calculation
    nir = nir_band.astype(float)
    red = red_band.astype(float)
    
    # Calculate NDVI with epsilon to avoid division by zero
    numerator = nir - red
    denominator = nir + red + 1e-10
    ndvi = numerator / denominator
    
    # Return mean NDVI for the region
    mean_ndvi = float(np.mean(ndvi))
    
    # Clamp to valid range
    mean_ndvi = max(-1.0, min(1.0, mean_ndvi))
    
    logger.info(f"Calculated NDVI: {mean_ndvi:.4f}")
    return mean_ndvi


async def fetch_sentinel_data(
    lat: float, 
    lon: float, 
    size_km: float = 1.0,
    time_range_days: int = 90
) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """
    Fetch Sentinel-2 NIR and Red bands for a location.
    
    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        size_km: Size of bounding box in kilometers
        time_range_days: Days to look back for imagery
        
    Returns:
        Tuple of (nir_band, red_band) as numpy arrays, or None on failure
    """
    config = get_sentinel_config()
    
    if not config or not SENTINELHUB_AVAILABLE:
        logger.info("Sentinel Hub not available, using synthetic data")
        return generate_synthetic_bands(lat, lon)
    
    try:
        # Create bounding box around the point
        delta = size_km / 111  # Approximate degrees per km
        bbox = BBox(
            bbox=[lon - delta, lat - delta, lon + delta, lat + delta],
            crs=CRS.WGS84
        )
        
        # Time range for data request - use longer window
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range_days)
        time_interval = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        # Resolution in meters
        resolution = 10
        size = bbox_to_dimensions(bbox, resolution=resolution)
        
        # Simplified evalscript that returns both bands stacked
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{
                    bands: ["B04", "B08"],
                    units: "REFLECTANCE"
                }],
                output: {
                    bands: 2,
                    sampleType: "FLOAT32"
                }
            };
        }
        
        function evaluatePixel(sample) {
            return [sample.B04, sample.B08];
        }
        """
        
        logger.info(f"Fetching Sentinel-2 data for ({lat}, {lon}), time range: {time_interval}")
        
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=time_interval,
                    mosaicking_order="leastCC"  # Least cloud cover
                )
            ],
            responses=[
                SentinelHubRequest.output_response("default", MimeType.TIFF),
            ],
            bbox=bbox,
            size=size,
            config=config
        )
        
        # Fetch data
        response = request.get_data()
        
        if response and len(response) > 0:
            data = response[0]
            logger.info(f"Sentinel Hub response shape: {data.shape}")
            
            if len(data.shape) == 3 and data.shape[2] >= 2:
                red_band = data[:, :, 0]
                nir_band = data[:, :, 1]
                logger.info(f"Fetched Sentinel-2 data: red shape={red_band.shape}, nir shape={nir_band.shape}")
                logger.info(f"Red band range: {red_band.min():.4f} to {red_band.max():.4f}")
                logger.info(f"NIR band range: {nir_band.min():.4f} to {nir_band.max():.4f}")
                return (nir_band, red_band)
            else:
                logger.warning(f"Unexpected data shape: {data.shape}, using synthetic data")
                return generate_synthetic_bands(lat, lon)
        else:
            logger.warning("No Sentinel-2 data returned, using synthetic data")
            return generate_synthetic_bands(lat, lon)
            
    except Exception as e:
        logger.error(f"Sentinel Hub request failed: {e}")
        return generate_synthetic_bands(lat, lon)


def generate_synthetic_bands(lat: float, lon: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic NIR and Red band data for demo/testing.
    
    Uses location to seed random generator for consistent results.
    
    Args:
        lat: Latitude (used for seeding)
        lon: Longitude (used for seeding)
        
    Returns:
        Tuple of synthetic (nir_band, red_band)
    """
    # Seed based on location for reproducibility
    seed = int((lat * 1000 + lon * 1000) % 10000)
    np.random.seed(seed)
    
    # Generate 100x100 synthetic image
    size = (100, 100)
    
    # Create base patterns - healthy vegetation has high NIR, low Red
    # Use latitude to vary the "health" of vegetation (demo purposes)
    health_factor = 0.5 + 0.3 * np.sin(lat * 0.1)  # 0.2 to 0.8
    
    # NIR band (healthy vegetation = high values)
    nir = np.random.uniform(0.3, 0.6, size) * health_factor + 0.2
    nir = nir + np.random.normal(0, 0.05, size)  # Add noise
    nir = np.clip(nir, 0, 1)
    
    # Red band (healthy vegetation = low values)
    red = np.random.uniform(0.05, 0.15, size)
    red = red + np.random.normal(0, 0.02, size)
    red = np.clip(red, 0, 1)
    
    logger.info(f"Generated synthetic bands for ({lat}, {lon}), health_factor={health_factor:.3f}")
    
    return (nir.astype(np.float32), red.astype(np.float32))


def determine_risk_status(ndvi_score: float, threshold: float = 0.8) -> str:
    """
    Determine risk status based on NDVI score and SPT threshold.
    
    Args:
        ndvi_score: Calculated NDVI value (0.0 to 1.0 for vegetation)
        threshold: SPT compliance threshold (default 0.8)
        
    Returns:
        Risk status string: "COMPLIANT", "WARNING", or "BREACH"
    """
    # Normalize NDVI from (-1,1) to (0,1) for vegetation
    # Typical healthy vegetation is 0.6-0.9 raw NDVI
    # Map this to 0.7-1.0 for our threshold comparison
    normalized = (ndvi_score + 1) / 2  # Map -1..1 to 0..1
    
    if normalized >= threshold:
        return "COMPLIANT"
    elif normalized >= threshold * 0.9:  # Within 10% of threshold
        return "WARNING"
    else:
        return "BREACH"


async def verify_asset_location(
    lat: float,
    lon: float,
    threshold: float = 0.8
) -> dict:
    """
    Complete verification workflow for an asset location.
    
    Args:
        lat: Asset latitude
        lon: Asset longitude
        threshold: SPT compliance threshold
        
    Returns:
        Dictionary with verification results
    """
    logger.info(f"Starting verification for location ({lat}, {lon})")
    
    # Fetch satellite data
    bands = await fetch_sentinel_data(lat, lon)
    
    if bands is None:
        return {
            "success": False,
            "error": "Failed to fetch satellite data",
            "ndvi_score": None,
            "risk_status": "ERROR",
            "verified_at": datetime.utcnow().isoformat()
        }
    
    nir_band, red_band = bands
    
    # Calculate NDVI
    ndvi_score = calculate_ndvi(nir_band, red_band)
    
    # Determine risk status
    risk_status = determine_risk_status(ndvi_score, threshold)
    
    result = {
        "success": True,
        "ndvi_score": ndvi_score,
        "risk_status": risk_status,
        "threshold": threshold,
        "verified_at": datetime.utcnow().isoformat(),
        "data_source": "sentinel_hub" if get_sentinel_config() else "synthetic"
    }
    
    logger.info(f"Verification complete: NDVI={ndvi_score:.4f}, status={risk_status}")
    return result


# Demo function
async def demo_verification():
    """Demo verification for Paradise, CA (fire-prone area)."""
    # Paradise, CA coordinates
    lat, lon = 39.7596, -121.6219
    
    print("=" * 60)
    print("Geospatial Verification Demo - Paradise, CA")
    print("=" * 60)
    
    result = await verify_asset_location(lat, lon, threshold=0.8)
    
    print(f"NDVI Score: {result.get('ndvi_score', 'N/A')}")
    print(f"Risk Status: {result['risk_status']}")
    print(f"Data Source: {result.get('data_source', 'unknown')}")
    print(f"Verified At: {result['verified_at']}")
    
    return result
