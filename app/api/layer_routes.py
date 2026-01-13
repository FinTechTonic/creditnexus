"""API routes for satellite layer data.

Provides endpoints for:
- Listing layers for a loan asset
- Retrieving specific layer data
- Generating missing layers
- Getting layer metadata
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from pathlib import Path
import io
import numpy as np

from app.db import get_db
from app.db.models import SatelliteLayer, User
from app.auth.jwt_auth import get_current_user
from app.services.layer_storage_service import LayerStorageService
from app.services.layer_processing_service import LayerProcessingService
from app.models.loan_asset import LoanAsset
from app.utils.audit import log_audit_action
from app.db.models import AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/layers", tags=["layers"])


# Pydantic models for request/response
class LayerListItem(BaseModel):
    """Layer list item response."""
    id: int
    layer_type: str
    band_number: Optional[str] = None
    metadata: dict
    thumbnail_url: Optional[str] = None
    bounds: dict
    created_at: str


class LayerListResponse(BaseModel):
    """Response for layer list endpoint."""
    layers: List[LayerListItem]
    total: int


class GenerateLayersRequest(BaseModel):
    """Request to generate layers."""
    layer_types: List[str] = Field(default=["ndvi", "false_color", "classification"])
    force_regenerate: bool = Field(default=False)


class GenerateLayersResponse(BaseModel):
    """Response for layer generation."""
    generated: List[int]
    existing: List[int]
    failed: List[str]


# Initialize services
layer_storage_service = LayerStorageService()
layer_processing_service = LayerProcessingService()


@router.get("/{asset_id}", response_model=LayerListResponse)
async def list_layers(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all available layers for a loan asset.
    
    Args:
        asset_id: ID of the loan asset
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of layers with metadata
    """
    # Verify asset exists
    asset = db.query(LoanAsset).filter(LoanAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Loan asset {asset_id} not found")
    
    # Get layers
    layers = layer_storage_service.list_layers_for_asset(db, asset_id)
    
    # Build response
    layer_items = []
    for layer in layers:
        bounds = {
            "north": float(layer.bounds_north) if layer.bounds_north else None,
            "south": float(layer.bounds_south) if layer.bounds_south else None,
            "east": float(layer.bounds_east) if layer.bounds_east else None,
            "west": float(layer.bounds_west) if layer.bounds_west else None,
        }
        
        layer_items.append(LayerListItem(
            id=layer.id,
            layer_type=layer.layer_type,
            band_number=layer.band_number,
            metadata=layer.layer_metadata or {},
            thumbnail_url=f"/api/layers/{asset_id}/{layer.id}/thumbnail",
            bounds=bounds,
            created_at=layer.created_at.isoformat() if layer.created_at else ""
        ))
    
    return LayerListResponse(layers=layer_items, total=len(layer_items))


@router.get("/{asset_id}/{layer_id}")
async def get_layer(
    asset_id: int,
    layer_id: int,
    format: str = Query("png", description="Format: png, geotiff, or json"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific layer data.
    
    Args:
        asset_id: ID of the loan asset
        layer_id: ID of the layer
        format: Output format (png, geotiff, json)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Layer data in requested format
    """
    # Verify layer belongs to asset
    layer = db.query(SatelliteLayer).filter(
        SatelliteLayer.id == layer_id,
        SatelliteLayer.loan_asset_id == asset_id
    ).first()
    
    if not layer:
        raise HTTPException(status_code=404, detail=f"Layer {layer_id} not found for asset {asset_id}")
    
    if format == "png":
        # Return PNG file
        file_path = layer_storage_service.storage_base_path / layer.file_path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Layer file not found")
        
        return FileResponse(
            path=str(file_path),
            media_type="image/png",
            filename=f"layer_{layer_id}.png"
        )
    
    elif format == "json":
        # Return JSON with array data
        layer_data, metadata = layer_storage_service.retrieve_layer(db, layer_id, format='array')
        
        if layer_data is None:
            raise HTTPException(status_code=404, detail="Layer data not found")
        
        # Convert to list for JSON serialization
        if isinstance(layer_data, np.ndarray):
            data_list = layer_data.tolist()
        else:
            data_list = layer_data
        
        return {
            "id": layer.id,
            "type": layer.layer_type,
            "data": {
                "format": "array",
                "values": data_list,
                "shape": list(layer_data.shape) if hasattr(layer_data, 'shape') else None
            },
            "metadata": metadata or {},
            "bounds": {
                "north": float(layer.bounds_north) if layer.bounds_north else None,
                "south": float(layer.bounds_south) if layer.bounds_south else None,
                "east": float(layer.bounds_east) if layer.bounds_east else None,
                "west": float(layer.bounds_west) if layer.bounds_west else None,
            }
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


@router.get("/{asset_id}/{layer_id}/metadata")
async def get_layer_metadata(
    asset_id: int,
    layer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get layer metadata only (without full data).
    
    Args:
        asset_id: ID of the loan asset
        layer_id: ID of the layer
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Layer metadata
    """
    # Verify layer belongs to asset
    layer = db.query(SatelliteLayer).filter(
        SatelliteLayer.id == layer_id,
        SatelliteLayer.loan_asset_id == asset_id
    ).first()
    
    if not layer:
        raise HTTPException(status_code=404, detail=f"Layer {layer_id} not found for asset {asset_id}")
    
    metadata = layer_storage_service.get_layer_metadata(db, layer_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Layer metadata not found")
    
    return metadata


@router.get("/{asset_id}/{layer_id}/thumbnail")
async def get_layer_thumbnail(
    asset_id: int,
    layer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get layer thumbnail (small preview image).
    
    Args:
        asset_id: ID of the loan asset
        layer_id: ID of the layer
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Thumbnail image
    """
    # Verify layer belongs to asset
    layer = db.query(SatelliteLayer).filter(
        SatelliteLayer.id == layer_id,
        SatelliteLayer.loan_asset_id == asset_id
    ).first()
    
    if not layer:
        raise HTTPException(status_code=404, detail=f"Layer {layer_id} not found for asset {asset_id}")
    
    # For now, return the full image (in production, generate thumbnails)
    file_path = layer_storage_service.storage_base_path / layer.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Layer file not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        filename=f"thumbnail_{layer_id}.png"
    )


@router.post("/{asset_id}/generate", response_model=GenerateLayersResponse)
async def generate_layers(
    asset_id: int,
    request: GenerateLayersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate missing layers for a loan asset.
    
    Args:
        asset_id: ID of the loan asset
        request: Generation request with layer types
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of generated and existing layer IDs
    """
    # Verify asset exists and has coordinates
    asset = db.query(LoanAsset).filter(LoanAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Loan asset {asset_id} not found")
    
    if not asset.geo_lat or not asset.geo_lon:
        raise HTTPException(
            status_code=400,
            detail="Loan asset must have geographic coordinates (geo_lat, geo_lon)"
        )
    
    generated = []
    existing = []
    failed = []
    
    # Fetch all bands
    logger.info(f"Fetching bands for asset {asset_id} at ({asset.geo_lat}, {asset.geo_lon})")
    bands = await layer_processing_service.fetch_all_bands(
        lat=asset.geo_lat,
        lon=asset.geo_lon,
        size_km=1.0
    )
    
    # Generate requested layer types
    for layer_type in request.layer_types:
        try:
            # Check if layer already exists
            existing_layer = db.query(SatelliteLayer).filter(
                SatelliteLayer.loan_asset_id == asset_id,
                SatelliteLayer.layer_type == layer_type
            ).first()
            
            if existing_layer and not request.force_regenerate:
                existing.append(existing_layer.id)
                continue
            
            # Generate layer
            if layer_type == "ndvi":
                nir = bands.get('B08')
                red = bands.get('B04')
                if nir is None or red is None:
                    failed.append(f"{layer_type}: Missing required bands")
                    continue
                
                layer_data, metadata = await layer_processing_service.generate_ndvi_layer(nir, red)
            
            elif layer_type == "false_color":
                nir = bands.get('B08')
                red = bands.get('B04')
                green = bands.get('B03')
                if nir is None or red is None:
                    failed.append(f"{layer_type}: Missing required bands")
                    continue
                
                layer_data, metadata = await layer_processing_service.generate_false_color_composite(
                    nir, red, green
                )
            
            elif layer_type == "classification":
                layer_data, metadata = await layer_processing_service.generate_classification_overlay(
                    asset.geo_lat, asset.geo_lon, bands
                )
            
            else:
                failed.append(f"{layer_type}: Unknown layer type")
                continue
            
            # Add bounds to metadata
            delta = 0.005  # Approximate 0.5km
            metadata['bounds'] = {
                'north': asset.geo_lat + delta,
                'south': asset.geo_lat - delta,
                'east': asset.geo_lon + delta,
                'west': asset.geo_lon - delta
            }
            
            # Store layer
            layer_record = layer_storage_service.store_layer(
                db=db,
                loan_asset_id=asset_id,
                layer_type=layer_type,
                layer_data=layer_data,
                metadata=metadata
            )
            
            generated.append(layer_record.id)
            
            # Audit log
            log_audit_action(
                db,
                AuditAction.CREATE,
                "satellite_layer",
                layer_record.id,
                current_user.id,
                metadata={"layer_type": layer_type, "asset_id": asset_id}
            )
            
        except Exception as e:
            logger.error(f"Failed to generate layer {layer_type} for asset {asset_id}: {e}", exc_info=True)
            failed.append(f"{layer_type}: {str(e)}")
    
    return GenerateLayersResponse(
        generated=generated,
        existing=existing,
        failed=failed
    )
