"""Prometheus metrics API routes."""

from fastapi import APIRouter, Response, Query
from fastapi.responses import PlainTextResponse
from app.core.metrics import get_metrics, get_metrics_openmetrics
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics(
    format: str = Query("prometheus", description="Output format: 'prometheus' or 'openmetrics'")
):
    """Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format or OpenMetrics format.
    
    Query Parameters:
    - format: "prometheus" (default) or "openmetrics"
    
    Returns:
    - 200: Metrics in requested format
    """
    try:
        if format == "openmetrics":
            metrics_data = get_metrics_openmetrics()
            content_type = "application/openmetrics-text; version=1.0.0; charset=utf-8"
        else:
            metrics_data = get_metrics()
            content_type = "text/plain; version=0.0.4; charset=utf-8"
        
        return Response(
            content=metrics_data,
            media_type=content_type
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            status_code=500,
            media_type="text/plain"
        )


@router.get("/health")
async def metrics_health():
    """Health check for metrics endpoint."""
    return {"status": "healthy", "service": "metrics"}
