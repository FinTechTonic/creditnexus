"""Layer Storage Service for Satellite Layer Visualization.

This service handles:
1. Storing layer data (PNG/GeoTIFF)
2. Retrieving layer data
3. Layer metadata management
4. Cache management
5. Cleanup of old layers
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import numpy as np
from PIL import Image
import io

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.config import settings
from app.db.models import SatelliteLayer

logger = logging.getLogger(__name__)


class LayerStorageService:
    """Service for storing and retrieving layer data."""
    
    def __init__(self, storage_base_path: Optional[str] = None):
        """
        Initialize layer storage service.
        
        Args:
            storage_base_path: Base path for layer storage (defaults to settings.STORAGE_DIR)
        """
        self.logger = logging.getLogger(__name__)
        self.storage_base_path = Path(
            storage_base_path or getattr(settings, 'STORAGE_DIR', 'storage')
        )
        self.layers_dir = self.storage_base_path / 'layers'
        self.layers_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Layer storage initialized at: {self.layers_dir}")
    
    def store_layer(
        self,
        db: Session,
        loan_asset_id: int,
        layer_type: str,
        layer_data: np.ndarray,
        metadata: Dict[str, Any],
        band_number: Optional[str] = None,
        format: str = 'png'
    ) -> SatelliteLayer:
        """
        Store layer data to disk and database.
        
        Args:
            db: Database session
            loan_asset_id: ID of the loan asset
            layer_type: Type of layer (ndvi, false_color, classification, sentinel_band)
            layer_data: Layer data as numpy array
            metadata: Layer metadata dictionary
            band_number: Band number if this is a Sentinel-2 band (e.g., 'B04')
            format: Storage format ('png' or 'geotiff')
            
        Returns:
            SatelliteLayer database record
        """
        # Generate file path
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{loan_asset_id}_{layer_type}_{band_number or ''}_{timestamp}.{format}"
        file_path = self.layers_dir / filename
        
        # Save layer data to file
        if format == 'png':
            self._save_as_png(layer_data, file_path, metadata)
        elif format == 'geotiff':
            # TODO: Implement GeoTIFF saving with rasterio
            self.logger.warning("GeoTIFF format not yet implemented, saving as PNG")
            self._save_as_png(layer_data, file_path, metadata)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Calculate bounds from metadata or use defaults
        bounds = metadata.get('bounds', {
            'north': 0.0,
            'south': 0.0,
            'east': 0.0,
            'west': 0.0
        })
        
        # Create database record
        layer_record = SatelliteLayer(
            loan_asset_id=loan_asset_id,
            layer_type=layer_type,
            band_number=band_number,
            file_path=str(file_path.relative_to(self.storage_base_path)),
            metadata=metadata,
            resolution=metadata.get('resolution', 10),
            bounds_north=bounds.get('north', 0.0),
            bounds_south=bounds.get('south', 0.0),
            bounds_east=bounds.get('east', 0.0),
            bounds_west=bounds.get('west', 0.0),
            crs=metadata.get('crs', 'EPSG:4326')
        )
        
        db.add(layer_record)
        db.commit()
        db.refresh(layer_record)
        
        self.logger.info(
            f"Stored layer: {layer_type} for asset {loan_asset_id} "
            f"at {file_path} (ID: {layer_record.id})"
        )
        
        return layer_record
    
    def _save_as_png(
        self,
        layer_data: np.ndarray,
        file_path: Path,
        metadata: Dict[str, Any]
    ) -> None:
        """Save layer data as PNG image."""
        # Handle different data types
        if layer_data.dtype == np.float32 or layer_data.dtype == np.float64:
            # Normalize float data to 0-255
            data_min = np.min(layer_data)
            data_max = np.max(layer_data)
            if data_max > data_min:
                normalized = ((layer_data - data_min) / (data_max - data_min) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(layer_data, dtype=np.uint8)
        else:
            normalized = np.clip(layer_data, 0, 255).astype(np.uint8)
        
        # Handle different array shapes
        if len(normalized.shape) == 2:
            # Grayscale - convert to RGB
            image = Image.fromarray(normalized, mode='L').convert('RGB')
        elif len(normalized.shape) == 3:
            # RGB/RGBA
            if normalized.shape[2] == 3:
                image = Image.fromarray(normalized, mode='RGB')
            elif normalized.shape[2] == 4:
                image = Image.fromarray(normalized, mode='RGBA')
            else:
                # Take first 3 channels
                image = Image.fromarray(normalized[:, :, :3], mode='RGB')
        else:
            raise ValueError(f"Unsupported array shape: {normalized.shape}")
        
        # Save image
        image.save(file_path, 'PNG')
        self.logger.debug(f"Saved PNG image to {file_path}")
    
    def retrieve_layer(
        self,
        db: Session,
        layer_id: int,
        format: str = 'array'
    ) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
        """
        Retrieve layer data from storage.
        
        Args:
            db: Database session
            layer_id: ID of the layer record
            format: Return format ('array', 'png', 'geotiff')
            
        Returns:
            Tuple of (layer_data, metadata) or (None, None) if not found
        """
        layer_record = db.query(SatelliteLayer).filter(SatelliteLayer.id == layer_id).first()
        
        if not layer_record:
            self.logger.warning(f"Layer {layer_id} not found")
            return None, None
        
        # Load from file
        file_path = self.storage_base_path / layer_record.file_path
        
        if not file_path.exists():
            self.logger.error(f"Layer file not found: {file_path}")
            return None, None
        
        try:
            if format == 'array':
                # Load as numpy array
                image = Image.open(file_path)
                layer_data = np.array(image)
                
                # Convert RGB to grayscale if needed (for NDVI)
                if layer_record.layer_type == 'ndvi' and len(layer_data.shape) == 3:
                    # Convert back from normalized 0-255 to -1 to 1 range
                    # This is approximate - in production, store raw data
                    layer_data = layer_data[:, :, 0].astype(float) / 255.0 * 2.0 - 1.0
                
                return layer_data, layer_record.layer_metadata
            elif format == 'png':
                # Return file path
                return file_path, layer_record.layer_metadata
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve layer {layer_id}: {e}", exc_info=True)
            return None, None
    
    def get_layer_metadata(
        self,
        db: Session,
        layer_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get layer metadata only (without loading full data).
        
        Args:
            db: Database session
            layer_id: ID of the layer record
            
        Returns:
            Layer metadata dictionary or None
        """
        layer_record = db.query(SatelliteLayer).filter(SatelliteLayer.id == layer_id).first()
        
        if not layer_record:
            return None
        
        return {
            'id': layer_record.id,
            'loan_asset_id': layer_record.loan_asset_id,
            'layer_type': layer_record.layer_type,
            'band_number': layer_record.band_number,
            'metadata': layer_record.layer_metadata,
            'resolution': layer_record.resolution,
            'bounds': {
                'north': layer_record.bounds_north,
                'south': layer_record.bounds_south,
                'east': layer_record.bounds_east,
                'west': layer_record.bounds_west
            },
            'crs': layer_record.crs,
            'created_at': layer_record.created_at.isoformat() if layer_record.created_at else None,
            'file_size': (self.storage_base_path / layer_record.file_path).stat().st_size if (self.storage_base_path / layer_record.file_path).exists() else 0
        }
    
    def list_layers_for_asset(
        self,
        db: Session,
        loan_asset_id: int
    ) -> list[SatelliteLayer]:
        """
        List all layers for a loan asset.
        
        Args:
            db: Database session
            loan_asset_id: ID of the loan asset
            
        Returns:
            List of SatelliteLayer records
        """
        layers = db.query(SatelliteLayer).filter(
            SatelliteLayer.loan_asset_id == loan_asset_id
        ).order_by(SatelliteLayer.created_at.desc()).all()
        
        return layers
    
    def cleanup_old_layers(
        self,
        db: Session,
        days_old: int = 90
    ) -> int:
        """
        Clean up layers older than specified days.
        
        Args:
            db: Database session
            days_old: Delete layers older than this many days
            
        Returns:
            Number of layers deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        old_layers = db.query(SatelliteLayer).filter(
            SatelliteLayer.created_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for layer in old_layers:
            try:
                # Delete file
                file_path = self.storage_base_path / layer.file_path
                if file_path.exists():
                    file_path.unlink()
                
                # Delete database record
                db.delete(layer)
                deleted_count += 1
            except Exception as e:
                self.logger.error(f"Failed to delete layer {layer.id}: {e}")
        
        db.commit()
        
        self.logger.info(f"Cleaned up {deleted_count} old layers (older than {days_old} days)")
        return deleted_count
