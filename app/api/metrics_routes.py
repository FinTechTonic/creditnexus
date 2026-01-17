"""Metrics API routes for Prometheus metrics endpoint."""

import logging
from fastapi import APIRouter, Response, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.core.metrics import get_metrics, get_metrics_openmetrics
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus Metrics",
    description="Expose Prometheus metrics in text format. Use ?format=openmetrics for OpenMetrics format.",
    tags=["Metrics"],
    responses={
        200: {
            "description": "Metrics in Prometheus or OpenMetrics format",
            "content": {
                "text/plain": {"example": "# HELP creditnexus_http_requests_total Total number of HTTP requests\n# TYPE creditnexus_http_requests_total counter\ncreditnexus_http_requests_total{method=\"GET\",path=\"/api/health\",status_code=\"200\"} 1.0"}
            }
        },
        404: {"description": "Metrics are disabled"},
        500: {"description": "Failed to generate metrics"}
    }
)
async def metrics(
    format: str | None = Query(None, description="Output format: 'prometheus' (default) or 'openmetrics'")
) -> Response:
    """Expose Prometheus metrics.
    
    Args:
        format: Output format ('prometheus' or 'openmetrics')
        
    Returns:
        Metrics in Prometheus or OpenMetrics format
    """
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics are disabled")

    try:
        if format == "openmetrics":
            metrics_data = get_metrics_openmetrics()
            return Response(
                content=metrics_data,
                media_type="application/openmetrics-text; version=1.0.0; charset=utf-8",
            )
        else:
            # Default to Prometheus format
            metrics_data = get_metrics()
            return Response(
                content=metrics_data,
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get(
    "/metrics/health",
    summary="Metrics Health Check",
    description="Health check endpoint for metrics service",
    tags=["Metrics"],
    responses={
        200: {
            "description": "Metrics service health status",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "metrics_enabled": True,
                        "system_metrics_enabled": False
                    }
                }
            }
        }
    }
)
async def metrics_health() -> dict:
    """Health check endpoint for metrics service.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "metrics_enabled": settings.METRICS_ENABLED,
        "system_metrics_enabled": settings.SYSTEM_METRICS_ENABLED,
    }
