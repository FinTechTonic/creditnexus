"""API routes for verified implementations management."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import VerifiedImplementation, UserImplementationConnection, User
from app.auth.jwt_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/implementations", tags=["implementations"])


@router.get("/available")
async def list_available_implementations(
    db: Session = Depends(get_db)
):
    """List all available verified implementations."""
    implementations = db.query(VerifiedImplementation).filter(
        VerifiedImplementation.is_active == True
    ).all()
    
    return {
        "implementations": [
            {
                "id": impl.id,
                "name": impl.name,
                "display_name": impl.display_name,
                "category": impl.category
            }
            for impl in implementations
        ]
    }


@router.get("/signup-choices")
async def signup_implementation_choices(
    db: Session = Depends(get_db)
):
    """List implementation id, name, display_name, and category for signup selection. No auth required."""
    implementations = db.query(VerifiedImplementation).filter(
        VerifiedImplementation.is_active == True
    ).all()
    
    return [
        {
            "id": impl.id,
            "name": impl.name,
            "display_name": impl.display_name,
            "category": impl.category
        }
        for impl in implementations
    ]


@router.post("/{impl_id}/connect")
async def connect_implementation(
    impl_id: int,
    connection_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Connect user to a verified implementation."""
    implementation = db.query(VerifiedImplementation).filter(
        VerifiedImplementation.id == impl_id
    ).first()
    
    if not implementation:
        raise HTTPException(status_code=404, detail="Implementation not found")
    
    if not implementation.is_active:
        raise HTTPException(status_code=400, detail="Implementation is not active")
    
    # Create or update connection
    connection = db.query(UserImplementationConnection).filter(
        UserImplementationConnection.user_id == current_user.id,
        UserImplementationConnection.implementation_id == impl_id
    ).first()
    
    if connection:
        connection.connection_data = connection_data
        connection.is_active = True
    else:
        connection = UserImplementationConnection(
            user_id=current_user.id,
            implementation_id=impl_id,
            connection_data=connection_data,
            is_active=True
        )
        db.add(connection)
    
    db.commit()
    return {"status": "connected", "connection_id": connection.id}


@router.get("/connections")
async def list_user_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's connected implementations."""
    connections = db.query(UserImplementationConnection).filter(
        UserImplementationConnection.user_id == current_user.id,
        UserImplementationConnection.is_active == True
    ).all()
    
    return {
        "connections": [
            {
                "id": conn.id,
                "implementation_id": conn.implementation_id,
                "implementation_name": conn.implementation.name if conn.implementation else None,
                "implementation_display_name": conn.implementation.display_name if conn.implementation else None,
                "category": conn.implementation.category if conn.implementation else None,
                "last_synced_at": conn.last_synced_at.isoformat() if conn.last_synced_at else None,
                "created_at": conn.created_at.isoformat() if conn.created_at else None,
            }
            for conn in connections
        ]
    }


@router.delete("/connections/{connection_id}")
async def disconnect_implementation(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect user from a verified implementation."""
    connection = db.query(UserImplementationConnection).filter(
        UserImplementationConnection.id == connection_id,
        UserImplementationConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connection.is_active = False
    db.commit()
    
    return {"status": "disconnected", "connection_id": connection_id}
