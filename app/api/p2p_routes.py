"""P2P routes for CreditNexus-to-CreditNexus file sharing."""

import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth.jwt_auth import get_current_user
from app.db.models import User
from app.services.p2p_connection_service import P2PConnectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/p2p", tags=["p2p"])

# Global P2P service instance
p2p_service = P2PConnectionService()


@router.websocket("/{connection_id}")
async def p2p_websocket(
    websocket: WebSocket,
    connection_id: str,
    token: Optional[str] = None
):
    """WebSocket endpoint for P2P file sharing.

    Args:
        websocket: WebSocket connection
        connection_id: Unique connection identifier
        token: Optional JWT token for authentication (passed as query param)
    """
    await websocket.accept()

    # Authenticate (optional - can be made required)
    user = None
    if token:
        from app.db import SessionLocal
        db = SessionLocal()
        try:
            from app.auth.jwt_auth import verify_token
            payload = verify_token(token)
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    user = db.query(User).filter(User.id == int(user_id)).first()
        except Exception as e:
            logger.warning(f"Failed to authenticate WebSocket connection: {e}")
        finally:
            db.close()

    # Register connection
    p2p_service.register_connection(connection_id, websocket)

    logger.info(
        f"P2P WebSocket connected: {connection_id} "
        f"(user: {user.id if user else 'anonymous'})"
    )

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "message": "Connected to P2P file sharing"
        })

        # Handle messages
        file_metadata = None
        file_chunks = []

        while True:
            try:
                # Receive message (text or bytes)
                message = await websocket.receive()

                if "text" in message:
                    # JSON message
                    try:
                        data = json.loads(message["text"])
                        msg_type = data.get("type")

                        if msg_type == "file_metadata":
                            # Store metadata for file reception
                            file_metadata = data.get("metadata", {})
                            file_chunks = []
                            logger.info(
                                f"Receiving file via P2P: {file_metadata.get('filename', 'unknown')} "
                                f"({file_metadata.get('size', 0)} bytes)"
                            )

                            # Acknowledge metadata receipt
                            await websocket.send_json({
                                "type": "file_metadata_ack",
                                "connection_id": connection_id
                            })

                        elif msg_type == "file_progress":
                            # Progress update (log only)
                            logger.debug(
                                f"File transfer progress: "
                                f"{data.get('chunk', 0)}/{data.get('total_chunks', 0)} "
                                f"({data.get('bytes_sent', 0)}/{data.get('total_bytes', 0)} bytes)"
                            )

                        elif msg_type == "file_complete":
                            # File transfer complete
                            if file_metadata and file_chunks:
                                file_data = b"".join(file_chunks)
                                logger.info(
                                    f"Received file via P2P: {file_metadata.get('filename', 'unknown')} "
                                    f"({len(file_data)} bytes)"
                                )

                                # Store file receiver info for callback
                                p2p_service.file_receivers[connection_id] = {
                                    "file_data": file_data,
                                    "metadata": file_metadata
                                }

                                # Acknowledge completion
                                await websocket.send_json({
                                    "type": "file_complete_ack",
                                    "connection_id": connection_id,
                                    "size": len(file_data)
                                })
                            else:
                                logger.warning("File complete but no data received")

                            # Reset for next file
                            file_metadata = None
                            file_chunks = []

                        elif msg_type == "ping":
                            # Keepalive ping
                            await websocket.send_json({"type": "pong"})

                        else:
                            logger.warning(f"Unknown message type: {msg_type}")

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON from client: {e}")

                elif "bytes" in message:
                    # Binary chunk
                    chunk = message["bytes"]
                    file_chunks.append(chunk)
                    logger.debug(f"Received chunk: {len(chunk)} bytes (total: {sum(len(c) for c in file_chunks)} bytes)")

            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)

    except WebSocketDisconnect:
        logger.info(f"P2P WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"P2P WebSocket error for {connection_id}: {e}", exc_info=True)
    finally:
        # Unregister connection
        p2p_service.unregister_connection(connection_id)


@router.post("/create-connection")
async def create_p2p_connection(
    target_url: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new P2P connection.

    Args:
        target_url: Optional target URL for direct connection
        db: Database session
        current_user: Current authenticated user

    Returns:
        Connection info with WebRTC offer or WebSocket URL
    """
    import uuid
    connection_id = str(uuid.uuid4())

    connection_info = await p2p_service.create_connection(
        connection_id=connection_id,
        target_url=target_url
    )

    logger.info(f"Created P2P connection {connection_id} for user {current_user.id}")

    return {
        "status": "success",
        "connection_id": connection_id,
        "connection_info": connection_info
    }


@router.get("/connection/{connection_id}")
async def get_connection_status(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of a P2P connection.

    Args:
        connection_id: Connection ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Connection status
    """
    websocket = p2p_service.get_connection(connection_id)

    return {
        "connection_id": connection_id,
        "active": websocket is not None,
        "has_file": connection_id in p2p_service.file_receivers
    }


@router.get("/connection/{connection_id}/file")
async def get_received_file(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get file received via P2P connection.

    Args:
        connection_id: Connection ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        File data and metadata
    """
    if connection_id not in p2p_service.file_receivers:
        raise HTTPException(status_code=404, detail="No file received for this connection")

    file_info = p2p_service.file_receivers[connection_id]

    return {
        "connection_id": connection_id,
        "metadata": file_info["metadata"],
        "size": len(file_info["file_data"]),
        # Note: Actual file data should be returned via streaming or download endpoint
    }
