"""Metrics middleware for automatic HTTP request metrics collection."""

import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_request_size_bytes,
    http_response_size_bytes,
    normalize_path,
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics automatically.
    
    This middleware tracks:
    - Request count by method, path, and status code
    - Request duration
    - Request and response sizes
    """

    def __init__(self, app: ASGIApp, exclude_paths: list[str] | None = None):
        """Initialize metrics middleware.
        
        Args:
            app: ASGI application
            exclude_paths: List of path patterns to exclude from metrics
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health", "/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response
        """
        # Skip metrics collection for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Normalize path to reduce cardinality
        normalized_path = normalize_path(request.url.path)
        method = request.method

        # Track request start time
        start_time = time.time()

        # Get request size (if available)
        request_size = 0
        if hasattr(request, "_body") and request._body:
            request_size = len(request._body)
        elif hasattr(request, "body") and await request.body():
            body = await request.body()
            request_size = len(body)
            # Recreate request with body for downstream handlers
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            request._receive = receive

        # Track request size
        if request_size > 0:
            http_request_size_bytes.labels(method=method, path=normalized_path).observe(request_size)

        # Process request
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Track metrics
            http_requests_total.labels(
                method=method,
                path=normalized_path,
                status_code=str(status_code),
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                path=normalized_path,
                status_code=str(status_code),
            ).observe(duration)

            # Track response size (if available)
            # Note: Response size tracking is limited as we don't have access
            # to the full response body in middleware. This would require
            # a custom response wrapper.
            http_response_size_bytes.labels(
                method=method,
                path=normalized_path,
                status_code=str(status_code),
            ).observe(0)  # Placeholder - actual size tracking would need response wrapper
