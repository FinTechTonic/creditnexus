"""FastAPI middleware for collecting HTTP request metrics."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import re
import logging

from app.core.metrics import (
    http_requests_total,
    http_request_duration_seconds
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Extract endpoint (normalize path)
        endpoint = self._normalize_path(request.url.path)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            status_code = response.status_code
            method = request.method
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record error
            duration = time.time() - start_time
            status_code = 500
            
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status_code="500"
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
            
            # Re-raise exception
            raise
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality (e.g., /api/deals/123 -> /api/deals/:id).
        
        Args:
            path: Original request path
            
        Returns:
            Normalized path with IDs replaced by placeholders
        """
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            ':id',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+/', '/:id/', path)
        path = re.sub(r'/\d+$', '/:id', path)
        
        return path
