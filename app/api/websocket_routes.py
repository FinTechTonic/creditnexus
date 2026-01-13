"""WebSocket routes for real-time satellite layer verification updates.

Provides WebSocket endpoints for:
- Real-time verification progress
- Layer processing updates
- Verification completion notifications
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User
from app.models.loan_asset import LoanAsset
from app.agents.audit_workflow import run_full_audit
from app.services.layer_processing_service import LayerProcessingService
from app.services.layer_storage_service import LayerStorageService
from app.auth.jwt_auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

# Store active WebSocket connections
active_connections: Dict[int, Set[WebSocket]] = {}  # asset_id -> set of websockets

# Initialize services
layer_processing_service = LayerProcessingService()
layer_storage_service = LayerStorageService()


async def get_current_user_from_token(
    token: str,
    db: Session
) -> Optional[User]:
    """Get user from JWT token."""
    try:
        payload = verify_token(token)
        if payload is None:
            return None
        
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user
    except Exception as e:
        logger.error(f"Failed to verify token: {e}")
        return None


async def send_message(websocket: WebSocket, message: dict):
    """Send JSON message to WebSocket client."""
    try:
        await websocket.send_json(message)
    except Exception as e:
        logger.error(f"Failed to send WebSocket message: {e}")


async def broadcast_to_asset(asset_id: int, message: dict):
    """Broadcast message to all WebSocket connections for an asset."""
    if asset_id not in active_connections:
        return
    
    disconnected = set()
    for websocket in active_connections[asset_id]:
        try:
            await send_message(websocket, message)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            disconnected.add(websocket)
    
    # Remove disconnected connections
    active_connections[asset_id] -= disconnected
    if not active_connections[asset_id]:
        del active_connections[asset_id]


@router.websocket("/verification/{asset_id}")
async def websocket_verification(
    websocket: WebSocket,
    asset_id: int,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time verification updates.
    
    Args:
        websocket: WebSocket connection
        asset_id: ID of the loan asset being verified
        token: Optional JWT token for authentication (passed as query param)
    """
    await websocket.accept()
    
    # Authenticate (optional - can be made required)
    user = None
    if token:
        from app.db import SessionLocal
        db = SessionLocal()
        try:
            user = await get_current_user_from_token(token, db)
        finally:
            db.close()
    
    # Add connection to active connections
    if asset_id not in active_connections:
        active_connections[asset_id] = set()
    active_connections[asset_id].add(websocket)
    
    logger.info(f"WebSocket connected for asset {asset_id} (user: {user.id if user else 'anonymous'})")
    
    try:
        # Send initial connection message
        await send_message(websocket, {
            "type": "connected",
            "asset_id": asset_id,
            "message": "Connected to verification stream"
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages (ping/pong or commands)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await send_message(websocket, {"type": "pong"})
                    elif message.get("type") == "start_verification":
                        # Trigger verification if requested
                        await handle_start_verification(asset_id, websocket)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {data}")
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                await send_message(websocket, {"type": "ping"})
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for asset {asset_id}")
    except Exception as e:
        logger.error(f"WebSocket error for asset {asset_id}: {e}", exc_info=True)
    finally:
        # Remove connection
        if asset_id in active_connections:
            active_connections[asset_id].discard(websocket)
            if not active_connections[asset_id]:
                del active_connections[asset_id]


async def handle_start_verification(asset_id: int, websocket: WebSocket):
    """Handle verification start request."""
    from app.db import SessionLocal
    db = SessionLocal()
    
    try:
        # Get asset
        asset = db.query(LoanAsset).filter(LoanAsset.id == asset_id).first()
        if not asset:
            await send_message(websocket, {
                "type": "error",
                "message": f"Asset {asset_id} not found",
                "retryable": False
            })
            return
        
        # Start verification in background
        asyncio.create_task(run_verification_with_updates(asset_id, asset, websocket, db))
        
    except Exception as e:
        logger.error(f"Failed to start verification: {e}", exc_info=True)
        await send_message(websocket, {
            "type": "error",
            "message": str(e),
            "retryable": True
        })


async def run_verification_with_updates(
    asset_id: int,
    asset: LoanAsset,
    websocket: WebSocket,
    db: Session
):
    """
    Run verification workflow with real-time WebSocket updates.
    
    This function processes the verification and sends progress updates
    via WebSocket as layers are processed.
    """
    try:
        # Stage 1: Geocoding
        await send_message(websocket, {
            "type": "progress",
            "stage": "geocoding",
            "current": 1,
            "total": 5,
            "percentage": 20,
            "message": "Geocoding address..."
        })
        
        from app.agents.verifier import geocode_address
        if asset.collateral_address:
            coords = await geocode_address(asset.collateral_address)
            if coords:
                asset.geo_lat, asset.geo_lon = coords
                db.commit()
        
        if not asset.geo_lat or not asset.geo_lon:
            await send_message(websocket, {
                "type": "error",
                "message": "Failed to geocode address",
                "stage": "geocoding",
                "retryable": True
            })
            return
        
        # Stage 2: Fetching bands
        await send_message(websocket, {
            "type": "progress",
            "stage": "fetching_bands",
            "current": 0,
            "total": 13,
            "percentage": 40,
            "message": "Fetching satellite data..."
        })
        
        def progress_callback(update: dict):
            """Callback for band fetching progress."""
            asyncio.create_task(send_message(websocket, {
                "type": "progress",
                "stage": "fetching_bands",
                "current": update.get("current", 0),
                "total": update.get("total", 13),
                "band": update.get("band", ""),
                "percentage": 40 + (update.get("current", 0) / update.get("total", 13)) * 20,
                "message": f"Fetching band {update.get('band', '')}..."
            }))
        
        # Fetch all bands
        bands = await layer_processing_service.fetch_all_bands(
            lat=asset.geo_lat,
            lon=asset.geo_lon,
            size_km=1.0,
            progress_callback=progress_callback
        )
        
        # Stage 3: Calculate NDVI
        await send_message(websocket, {
            "type": "progress",
            "stage": "calculating_ndvi",
            "current": 1,
            "total": 1,
            "percentage": 65,
            "message": "Calculating NDVI..."
        })
        
        nir = bands.get('B08')
        red = bands.get('B04')
        if nir is not None and red is not None:
            ndvi_data, ndvi_metadata = await layer_processing_service.generate_ndvi_layer(nir, red)
            
            # Store NDVI layer
            ndvi_layer = layer_storage_service.store_layer(
                db=db,
                loan_asset_id=asset_id,
                layer_type='ndvi',
                layer_data=ndvi_data,
                metadata=ndvi_metadata
            )
            
            await send_message(websocket, {
                "type": "layer_update",
                "layer_id": str(ndvi_layer.id),
                "layer_type": "ndvi",
                "status": "complete",
                "progress": 1.0,
                "metadata": ndvi_metadata,
                "thumbnail_url": f"/api/layers/{asset_id}/{ndvi_layer.id}/thumbnail"
            })
        
        # Stage 4: Classification
        await send_message(websocket, {
            "type": "progress",
            "stage": "classifying",
            "current": 1,
            "total": 1,
            "percentage": 80,
            "message": "Classifying land use..."
        })
        
        classification_data, classification_metadata = await layer_processing_service.generate_classification_overlay(
            asset.geo_lat, asset.geo_lon, bands
        )
        
        # Store classification layer
        classification_layer = layer_storage_service.store_layer(
            db=db,
            loan_asset_id=asset_id,
            layer_type='classification',
            layer_data=classification_data,
            metadata=classification_metadata
        )
        
        await send_message(websocket, {
            "type": "layer_update",
            "layer_id": str(classification_layer.id),
            "layer_type": "classification",
            "status": "complete",
            "progress": 1.0,
            "metadata": classification_metadata,
            "thumbnail_url": f"/api/layers/{asset_id}/{classification_layer.id}/thumbnail"
        })
        
        # Stage 5: False color composite
        if nir is not None and red is not None:
            false_color_data, false_color_metadata = await layer_processing_service.generate_false_color_composite(
                nir, red
            )
            
            false_color_layer = layer_storage_service.store_layer(
                db=db,
                loan_asset_id=asset_id,
                layer_type='false_color',
                layer_data=false_color_data,
                metadata=false_color_metadata
            )
            
            await send_message(websocket, {
                "type": "layer_update",
                "layer_id": str(false_color_layer.id),
                "layer_type": "false_color",
                "status": "complete",
                "progress": 1.0,
                "metadata": false_color_metadata,
                "thumbnail_url": f"/api/layers/{asset_id}/{false_color_layer.id}/thumbnail"
            })
        
        # Calculate NDVI score for asset
        from app.agents.verifier import calculate_ndvi
        if nir is not None and red is not None:
            ndvi_score = calculate_ndvi(nir, red)
            asset.last_verified_score = ndvi_score
            asset.last_verified_at = datetime.utcnow()
            
            # Determine risk status
            from app.agents.verifier import determine_risk_status
            threshold = asset.spt_threshold or 0.8
            asset.risk_status = determine_risk_status(ndvi_score, threshold)
            
            db.commit()
        
        # Send completion message
        await send_message(websocket, {
            "type": "verification_complete",
            "asset_id": asset_id,
            "layers_generated": [
                str(ndvi_layer.id) if nir is not None and red is not None else None,
                str(classification_layer.id),
                str(false_color_layer.id) if nir is not None and red is not None else None
            ],
            "ndvi_score": asset.last_verified_score,
            "risk_status": asset.risk_status
        })
        
    except Exception as e:
        logger.error(f"Verification failed for asset {asset_id}: {e}", exc_info=True)
        await send_message(websocket, {
            "type": "error",
            "message": str(e),
            "stage": "verification",
            "retryable": True
        })
    finally:
        db.close()
