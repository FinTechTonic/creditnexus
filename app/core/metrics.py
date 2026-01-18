"""Prometheus metrics registry for CreditNexus.

This module defines all Prometheus metrics used throughout the application,
including HTTP request metrics, business metrics, database metrics, and system metrics.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
try:
    from prometheus_client.openmetrics.exposition import generate_latest as generate_latest_openmetrics
except ImportError:
    # Fallback if openmetrics not available - use standard generate_latest
    generate_latest_openmetrics = generate_latest
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# HTTP Request Metrics
http_requests_total = Counter(
    'creditnexus_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'creditnexus_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Business Metrics - LLM Calls
llm_calls_total = Counter(
    'creditnexus_llm_calls_total',
    'Total LLM API calls',
    ['provider', 'model', 'status']  # status: success, error, rate_limited
)

llm_call_duration_seconds = Histogram(
    'creditnexus_llm_call_duration_seconds',
    'LLM call duration in seconds',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

llm_tokens_total = Counter(
    'creditnexus_llm_tokens_total',
    'Total LLM tokens (input + output)',
    ['provider', 'model', 'type']  # type: input, output
)

llm_cost_total = Counter(
    'creditnexus_llm_cost_total',
    'Total LLM cost in USD',
    ['provider', 'model']
)

# Business Metrics - Policy Decisions
policy_decisions_total = Counter(
    'creditnexus_policy_decisions_total',
    'Total policy decisions',
    ['decision', 'rule_applied']  # decision: ALLOW, BLOCK, FLAG
)

policy_decision_duration_seconds = Histogram(
    'creditnexus_policy_decision_duration_seconds',
    'Policy decision duration in seconds',
    ['decision'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

# Business Metrics - Documents
documents_processed_total = Counter(
    'creditnexus_documents_processed_total',
    'Total documents processed',
    ['status', 'type']  # status: success, error; type: pdf, docx, image
)

document_processing_duration_seconds = Histogram(
    'creditnexus_document_processing_duration_seconds',
    'Document processing duration in seconds',
    ['type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Business Metrics - Trades
trades_executed_total = Counter(
    'creditnexus_trades_executed_total',
    'Total trades executed',
    ['status', 'type']  # status: success, failed; type: buy, sell
)

trade_value_total = Counter(
    'creditnexus_trade_value_total',
    'Total trade value in USD',
    ['type']
)

# Business Metrics - Verifications
verifications_total = Counter(
    'creditnexus_verifications_total',
    'Total verifications performed',
    ['status', 'type']  # status: success, failed; type: satellite, ground_truth
)

verification_duration_seconds = Histogram(
    'creditnexus_verification_duration_seconds',
    'Verification duration in seconds',
    ['type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Business Metrics - Stock Predictions
stock_predictions_total = Counter(
    'creditnexus_stock_predictions_total',
    'Total stock predictions generated',
    ['timeframe', 'status']  # timeframe: daily, hourly, 15min; status: success, error
)

stock_prediction_duration_seconds = Histogram(
    'creditnexus_stock_prediction_duration_seconds',
    'Stock prediction duration in seconds',
    ['timeframe'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

stock_prediction_gpu_memory_bytes = Histogram(
    'creditnexus_stock_prediction_gpu_memory_bytes',
    'GPU memory used for stock predictions',
    ['timeframe'],
    buckets=[100_000_000, 500_000_000, 1_000_000_000, 2_000_000_000, 5_000_000_000]
)

# Database Metrics
db_connections_active = Gauge(
    'creditnexus_db_connections_active',
    'Active database connections',
    ['state']  # state: idle, in_use
)

db_connections_total = Counter(
    'creditnexus_db_connections_total',
    'Total database connections',
    ['action']  # action: created, closed
)

db_query_duration_seconds = Histogram(
    'creditnexus_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],  # operation: select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# System Metrics (if psutil available)
try:
    import psutil
    system_cpu_percent = Gauge(
        'creditnexus_system_cpu_percent',
        'System CPU usage percentage',
        ['cpu']  # cpu: total, per_core
    )
    
    system_memory_bytes = Gauge(
        'creditnexus_system_memory_bytes',
        'System memory usage in bytes',
        ['type']  # type: total, available, used, free
    )
    
    system_disk_bytes = Gauge(
        'creditnexus_system_disk_bytes',
        'System disk usage in bytes',
        ['type', 'mount']  # type: total, used, free
    )
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil not available, system metrics will be disabled")
    system_cpu_percent = None
    system_memory_bytes = None
    system_disk_bytes = None
    PSUTIL_AVAILABLE = False

# Application Info
app_info = Info(
    'creditnexus_app',
    'CreditNexus application information'
)


def initialize_app_info(version: str = "1.0.0", environment: str = "development"):
    """Initialize application info metrics.
    
    Args:
        version: Application version
        environment: Environment name (development, staging, production)
    """
    app_info.info({
        'version': version,
        'environment': environment
    })


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format.
    
    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(REGISTRY)


def get_metrics_openmetrics() -> bytes:
    """Get Prometheus metrics in OpenMetrics format.
    
    Returns:
        Metrics in OpenMetrics format
    """
    return generate_latest_openmetrics(REGISTRY)
