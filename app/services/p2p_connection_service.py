"""P2P connection service for CreditNexus-to-CreditNexus file sharing."""

import asyncio
import json
from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime
import logging

try:
    from fastapi import WebSocket
except ImportError:
    # For type hints only
    WebSocket = Any

logger = logging.getLogger(__name__)


class P2PConnectionService:
    """Service for P2P connections between CreditNexus instances."""

    def __init__(self):
        """Initialize P2P connection service."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_callbacks: Dict[str, Callable] = {}
        self.file_receivers: Dict[str, Dict[str, Any]] = {}  # connection_id -> file metadata

    async def create_connection(
        self,
        connection_id: str,
        target_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create P2P connection (WebRTC preferred, WebSocket fallback).

        Args:
            connection_id: Unique connection ID
            target_url: Optional target URL for direct connection

        Returns:
            Connection info with WebRTC offer or WebSocket URL
        """
        # Try WebRTC first (if aiortc available)
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

            # Create WebRTC offer
            pc = RTCPeerConnection()
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)

            logger.info(f"Created WebRTC connection {connection_id}")

            return {
                "connection_id": connection_id,
                "type": "webrtc",
                "offer": {
                    "sdp": offer.sdp,
                    "type": offer.type
                },
                "ice_servers": [
                    {"urls": "stun:stun.l.google.com:19302"},
                    # Add TURN servers if configured
                ],
                "created_at": datetime.utcnow().isoformat(),
            }
        except ImportError:
            logger.warning("aiortc not available, using WebSocket fallback")

            # Fallback to WebSocket
            if target_url:
                return {
                    "connection_id": connection_id,
                    "type": "websocket",
                    "url": target_url,
                    "created_at": datetime.utcnow().isoformat(),
                }
            else:
                # Return WebSocket server URL
                return {
                    "connection_id": connection_id,
                    "type": "websocket",
                    "url": f"wss://creditnexus.ai/p2p/{connection_id}",
                    "created_at": datetime.utcnow().isoformat(),
                }

    async def send_file_via_p2p(
        self,
        connection_id: str,
        file_data: bytes,
        metadata: Dict[str, Any],
    ) -> bool:
        """Send file via P2P connection.

        Args:
            connection_id: Connection ID
            file_data: File bytes
            metadata: File metadata

        Returns:
            True if sent successfully
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Connection {connection_id} not found")
            return False

        websocket = self.active_connections[connection_id]
        try:
            # Send metadata first
            await websocket.send_json({
                "type": "file_metadata",
                "metadata": metadata
            })

            # Send file in chunks
            chunk_size = 64 * 1024  # 64KB chunks
            total_chunks = (len(file_data) + chunk_size - 1) // chunk_size

            for i in range(0, len(file_data), chunk_size):
                chunk = file_data[i:i + chunk_size]
                chunk_num = i // chunk_size + 1

                # Send chunk with progress info
                await websocket.send_bytes(chunk)

                # Send progress update every 10 chunks
                if chunk_num % 10 == 0 or chunk_num == total_chunks:
                    await websocket.send_json({
                        "type": "file_progress",
                        "chunk": chunk_num,
                        "total_chunks": total_chunks,
                        "bytes_sent": min(i + chunk_size, len(file_data)),
                        "total_bytes": len(file_data)
                    })

            # Send completion
            await websocket.send_json({
                "type": "file_complete",
                "size": len(file_data),
                "metadata": metadata
            })

            logger.info(f"Sent file via P2P connection {connection_id} ({len(file_data)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to send file via P2P: {e}")
            return False

    async def receive_file_via_p2p(
        self,
        connection_id: str,
        on_file_received: Callable[[bytes, Dict[str, Any]], None],
    ):
        """Receive file via P2P connection.

        Args:
            connection_id: Connection ID
            on_file_received: Callback when file is received
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Connection {connection_id} not found")
            return

        websocket = self.active_connections[connection_id]
        file_metadata = None
        file_chunks = []

        try:
            while True:
                # Wait for message
                message = await websocket.receive()

                if "text" in message:
                    # JSON message
                    data = json.loads(message["text"])
                    msg_type = data.get("type")

                    if msg_type == "file_metadata":
                        file_metadata = data.get("metadata", {})
                        file_chunks = []
                        logger.info(f"Receiving file via P2P: {file_metadata.get('filename', 'unknown')}")

                    elif msg_type == "file_progress":
                        # Progress update
                        logger.debug(
                            f"File transfer progress: {data.get('chunk', 0)}/{data.get('total_chunks', 0)}"
                        )

                    elif msg_type == "file_complete":
                        # File transfer complete
                        if file_metadata and file_chunks:
                            file_data = b"".join(file_chunks)
                            on_file_received(file_data, file_metadata)
                            logger.info(f"Received file via P2P: {file_metadata.get('filename', 'unknown')}")
                        file_metadata = None
                        file_chunks = []

                elif "bytes" in message:
                    # Binary chunk
                    chunk = message["bytes"]
                    file_chunks.append(chunk)

        except Exception as e:
            logger.error(f"Error receiving file via P2P: {e}")

    def register_connection(self, connection_id: str, websocket: WebSocket):
        """Register a WebSocket connection.

        Args:
            connection_id: Connection ID
            websocket: WebSocket connection
        """
        self.active_connections[connection_id] = websocket
        logger.info(f"Registered P2P connection {connection_id}")

    def unregister_connection(self, connection_id: str):
        """Unregister a WebSocket connection.

        Args:
            connection_id: Connection ID
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.file_receivers:
            del self.file_receivers[connection_id]
        logger.info(f"Unregistered P2P connection {connection_id}")

    def get_connection(self, connection_id: str) -> Optional[WebSocket]:
        """Get active connection by ID.

        Args:
            connection_id: Connection ID

        Returns:
            WebSocket connection or None
        """
        return self.active_connections.get(connection_id)
