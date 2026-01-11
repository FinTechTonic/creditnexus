"""
Deal Event Handler for Satellite Verification Results.

This service handles processing satellite verification results, storing
satellite images, updating deal metadata, and creating CDM events.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
import json

import numpy as np
from PIL import Image

from app.services.deal_service import DealService
from app.services.file_storage_service import FileStorageService
from app.db.models import Deal, DealNote
from app.models.cdm_events import generate_cdm_observation, generate_cdm_terms_change

logger = logging.getLogger(__name__)


class DealEventHandler:
    """
    Event handler for satellite verification results.
    
    Handles:
    - Storing satellite images
    - Updating deal metadata
    - Creating CDM events
    - Creating deal notes
    """
    
    def __init__(self, db_session, deal_service: Optional[DealService] = None):
        """
        Initialize deal event handler.
        
        Args:
            db_session: Database session
            deal_service: Optional DealService instance (will create if not provided)
        """
        self.db = db_session
        self.deal_service = deal_service or DealService(db_session)
        self.file_storage = FileStorageService()
    
    def handle_satellite_verification(
        self,
        deal_id: int,
        verification_result: Dict[str, Any],
        satellite_bands: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        loan_asset_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle satellite verification results for a deal.
        
        This method:
        1. Stores satellite images (if provided)
        2. Updates deal with verification results
        3. Creates CDM Observation and TermsChange events (if breach detected)
        4. Creates deal note with verification summary
        
        Args:
            deal_id: ID of the deal
            verification_result: Dictionary with verification results
            satellite_bands: Optional tuple of (nir_band, red_band) numpy arrays
            loan_asset_id: Optional loan asset ID associated with verification
            user_id: Optional user ID performing verification
            
        Returns:
            Dictionary with processing results
        """
        deal = self.deal_service.get_deal(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        result = {
            "success": False,
            "deal_id": deal_id,
            "satellite_image_stored": False,
            "deal_updated": False,
            "cdm_events_created": [],
            "deal_note_created": False
        }
        
        try:
            # 1. Store satellite images if provided
            satellite_image_path = None
            if satellite_bands:
                nir_band, red_band = satellite_bands
                satellite_image_path = self._store_satellite_image(
                    user_id=deal.applicant_id,
                    deal_id=deal.deal_id,
                    nir_band=nir_band,
                    red_band=red_band,
                    verification_result=verification_result
                )
                result["satellite_image_stored"] = True
                result["satellite_image_path"] = satellite_image_path
                logger.info(f"Stored satellite image for deal {deal.deal_id} at {satellite_image_path}")
            
            # 2. Update deal with verification results
            updated_deal = self.deal_service.update_deal_on_verification(
                deal_id=deal_id,
                verification_result=verification_result,
                loan_asset_id=loan_asset_id,
                user_id=user_id
            )
            result["deal_updated"] = True
            
            # 3. Create CDM events if breach detected
            ndvi_score = verification_result.get("ndvi_score")
            risk_status = verification_result.get("risk_status", verification_result.get("status"))
            
            if risk_status == "BREACH":
                # Create CDM Observation event
                observation_event = generate_cdm_observation(
                    trade_id=deal.deal_id,
                    satellite_hash=verification_result.get("hash", ""),
                    ndvi_score=ndvi_score or 0.0,
                    status=risk_status
                )
                
                # Create TermsChange event for breach
                previous_rate = verification_result.get("previous_rate", 5.0)
                current_rate = verification_result.get("current_rate", previous_rate + 0.5)
                
                terms_change_event = generate_cdm_terms_change(
                    trade_id=deal.deal_id,
                    current_rate=previous_rate,
                    status=risk_status,
                    policy_service=None  # Can be provided if needed
                )
                
                if terms_change_event:
                    # Link TermsChange to Observation
                    observation_event_id = observation_event.get("meta", {}).get("globalKey", "")
                    terms_change_event["relatedEventIdentifier"] = [{
                        "eventIdentifier": {
                            "issuer": "CreditNexus",
                            "assignedIdentifier": [{
                                "identifier": {"value": observation_event_id}
                            }]
                        }
                    }]
                
                # Store CDM events
                self.file_storage.store_cdm_event(
                    user_id=deal.applicant_id,
                    deal_id=deal.deal_id,
                    event_id=f"OBSERVATION_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    event_data=observation_event
                )
                result["cdm_events_created"].append("Observation")
                
                if terms_change_event:
                    self.file_storage.store_cdm_event(
                        user_id=deal.applicant_id,
                        deal_id=deal.deal_id,
                        event_id=f"TERMS_CHANGE_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                        event_data=terms_change_event
                    )
                    result["cdm_events_created"].append("TermsChange")
                
                logger.info(f"Created CDM events for breach on deal {deal.deal_id}")
            
            # 4. Update verification result with satellite image path if stored
            if satellite_image_path:
                if updated_deal.deal_data and "latest_verification" in updated_deal.deal_data:
                    updated_deal.deal_data["latest_verification"]["satellite_image_path"] = satellite_image_path
                if updated_deal.deal_data and "verification_history":
                    if len(updated_deal.deal_data["verification_history"]) > 0:
                        updated_deal.deal_data["verification_history"][-1]["satellite_image_path"] = satellite_image_path
            
            result["success"] = True
            logger.info(f"Successfully handled satellite verification for deal {deal.deal_id}")
            
        except Exception as e:
            logger.error(f"Error handling satellite verification for deal {deal_id}: {e}", exc_info=True)
            result["error"] = str(e)
            raise
        
        return result
    
    def _store_satellite_image(
        self,
        user_id: int,
        deal_id: str,
        nir_band: np.ndarray,
        red_band: np.ndarray,
        verification_result: Dict[str, Any]
    ) -> str:
        """
        Store satellite image as PNG file.
        
        Creates a false-color composite image from NIR and Red bands.
        Uses NIR for red channel, Red for green channel, and NIR-Red difference for blue.
        
        Args:
            user_id: ID of the user/applicant
            deal_id: Unique deal identifier
            nir_band: Near-infrared band data
            red_band: Red band data
            verification_result: Verification result dictionary for metadata
            
        Returns:
            Path to the stored image file
        """
        try:
            # Normalize bands to 0-255 range for image display
            def normalize_band(band: np.ndarray) -> np.ndarray:
                """Normalize band to 0-255 uint8 range."""
                band_min = band.min()
                band_max = band.max()
                if band_max > band_min:
                    normalized = ((band - band_min) / (band_max - band_min) * 255).astype(np.uint8)
                else:
                    normalized = np.zeros_like(band, dtype=np.uint8)
                return normalized
            
            nir_normalized = normalize_band(nir_band)
            red_normalized = normalize_band(red_band)
            
            # Create false-color composite: NIR=Red, Red=Green, (NIR-Red)=Blue
            # This creates a vegetation visualization where healthy vegetation appears red
            blue_band = np.clip(nir_normalized.astype(int) - red_normalized.astype(int), 0, 255).astype(np.uint8)
            
            # Stack bands: R=NIR, G=Red, B=(NIR-Red)
            rgb_image = np.dstack([nir_normalized, red_normalized, blue_band])
            
            # Ensure deal folder exists
            deal_folder = self.file_storage.base_storage_path / str(user_id) / deal_id
            if not deal_folder.exists():
                self.file_storage.create_deal_folder(user_id, deal_id)
            
            # Create satellite_images subdirectory
            images_dir = deal_folder / "satellite_images"
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Convert to PIL Image
            image = Image.fromarray(rgb_image, mode='RGB')
            
            # Resize if too large (max 2048x2048 for storage efficiency)
            max_size = 2048
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            filename = f"satellite_{timestamp}.png"
            image_path = images_dir / filename
            
            # Save image
            image.save(image_path, format='PNG', optimize=True)
            
            # Save metadata JSON alongside image
            metadata = {
                "timestamp": timestamp,
                "ndvi_score": verification_result.get("ndvi_score"),
                "risk_status": verification_result.get("risk_status", verification_result.get("status")),
                "threshold": verification_result.get("threshold", 0.8),
                "data_source": verification_result.get("data_source", "unknown"),
                "image_size": {
                    "width": image.width,
                    "height": image.height
                },
                "bands_info": {
                    "nir_range": [float(nir_band.min()), float(nir_band.max())],
                    "red_range": [float(red_band.min()), float(red_band.max())]
                },
                "image_format": "PNG"
            }
            
            metadata_path = images_dir / f"satellite_{timestamp}_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Stored satellite image for deal {deal_id} at {image_path}")
            
            return str(image_path.absolute())
            
        except Exception as e:
            logger.error(f"Error storing satellite image: {e}", exc_info=True)
            raise
    
    def get_verification_history(
        self,
        deal_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get verification history for a deal.
        
        Args:
            deal_id: ID of the deal
            
        Returns:
            List of verification entries from deal_data
        """
        deal = self.deal_service.get_deal(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        if deal.deal_data and "verification_history" in deal.deal_data:
            return deal.deal_data["verification_history"]
        
        return []
    
    def get_latest_verification(
        self,
        deal_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest verification result for a deal.
        
        Args:
            deal_id: ID of the deal
            
        Returns:
            Latest verification entry or None
        """
        deal = self.deal_service.get_deal(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        if deal.deal_data and "latest_verification" in deal.deal_data:
            return deal.deal_data["latest_verification"]
        
        return None
