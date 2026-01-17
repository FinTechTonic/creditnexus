"""Prometheus metrics definitions for CreditNexus.

This module defines all Prometheus metrics used throughout the application,
including HTTP request metrics, business metrics (LLM, policy, documents),
database metrics, and system metrics.
"""

import time
from typing import Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.openmetrics.exposition import generate_latest as generate_openmetrics

# Create a custom registry for application metrics
registry = CollectorRegistry()

# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    "creditnexus_http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "creditnexus_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status_code"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

http_request_size_bytes = Histogram(
    "creditnexus_http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "path"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
    registry=registry,
)

http_response_size_bytes = Histogram(
    "creditnexus_http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "path", "status_code"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000],
    registry=registry,
)

# ============================================================================
# LLM Call Metrics
# ============================================================================

llm_calls_total = Counter(
    "creditnexus_llm_calls_total",
    "Total number of LLM API calls",
    ["provider", "model", "status"],
    registry=registry,
)

llm_call_duration_seconds = Histogram(
    "creditnexus_llm_call_duration_seconds",
    "LLM API call duration in seconds",
    ["provider", "model", "status"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0],
    registry=registry,
)

llm_tokens_total = Counter(
    "creditnexus_llm_tokens_total",
    "Total number of LLM tokens processed",
    ["provider", "model", "type"],  # type: prompt, completion, total
    registry=registry,
)

llm_cost_usd = Counter(
    "creditnexus_llm_cost_usd_total",
    "Total LLM API cost in USD",
    ["provider", "model"],
    registry=registry,
)

llm_rate_limited_total = Counter(
    "creditnexus_llm_rate_limited_total",
    "Total number of LLM rate limit errors",
    ["provider", "model"],
    registry=registry,
)

# ============================================================================
# Policy Decision Metrics
# ============================================================================

policy_decisions_total = Counter(
    "creditnexus_policy_decisions_total",
    "Total number of policy decisions",
    ["decision", "rule_applied", "category"],
    registry=registry,
)

policy_decision_duration_seconds = Histogram(
    "creditnexus_policy_decision_duration_seconds",
    "Policy decision evaluation duration in seconds",
    ["decision", "category"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)

# ============================================================================
# Document Processing Metrics
# ============================================================================

documents_processed_total = Counter(
    "creditnexus_documents_processed_total",
    "Total number of documents processed",
    ["status", "type", "operation"],
    registry=registry,
)

document_processing_duration_seconds = Histogram(
    "creditnexus_document_processing_duration_seconds",
    "Document processing duration in seconds",
    ["type", "operation", "status"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0],
    registry=registry,
)

document_size_bytes = Histogram(
    "creditnexus_document_size_bytes",
    "Document size in bytes",
    ["type"],
    buckets=[1000, 10000, 100000, 500000, 1000000, 5000000, 10000000],
    registry=registry,
)

# ============================================================================
# Trade Execution Metrics
# ============================================================================

trades_executed_total = Counter(
    "creditnexus_trades_executed_total",
    "Total number of trades executed",
    ["status", "type"],  # type: buy, sell
    registry=registry,
)

trade_value_usd = Counter(
    "creditnexus_trade_value_usd_total",
    "Total trade value in USD",
    ["status", "type"],
    registry=registry,
)

# ============================================================================
# Verification Metrics
# ============================================================================

verifications_total = Counter(
    "creditnexus_verifications_total",
    "Total number of verifications performed",
    ["status", "type"],  # type: satellite, ground_truth, ssl
    registry=registry,
)

verification_duration_seconds = Histogram(
    "creditnexus_verification_duration_seconds",
    "Verification duration in seconds",
    ["type", "status"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 300.0],
    registry=registry,
)

# ============================================================================
# Stock Prediction Metrics
# ============================================================================

stock_predictions_total = Counter(
    "creditnexus_stock_predictions_total",
    "Total number of stock predictions made",
    ["timeframe", "status"],  # timeframe: daily, hourly, 15min
    registry=registry,
)

stock_prediction_duration_seconds = Histogram(
    "creditnexus_stock_prediction_duration_seconds",
    "Stock prediction duration in seconds",
    ["timeframe", "status"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0],
    registry=registry,
)

stock_prediction_gpu_memory_bytes = Gauge(
    "creditnexus_stock_prediction_gpu_memory_bytes",
    "GPU memory usage for stock predictions in bytes",
    ["device"],
    registry=registry,
)

# ============================================================================
# Database Metrics
# ============================================================================

db_connections_active = Gauge(
    "creditnexus_db_connections_active",
    "Number of active database connections",
    ["state"],  # state: idle, in_use
    registry=registry,
)

db_connections_idle = Gauge(
    "creditnexus_db_connections_idle",
    "Number of idle database connections",
    registry=registry,
)

db_query_duration_seconds = Histogram(
    "creditnexus_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # operation: select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry,
)

db_transactions_total = Counter(
    "creditnexus_db_transactions_total",
    "Total number of database transactions",
    ["status"],  # status: committed, rolled_back
    registry=registry,
)

# ============================================================================
# System Metrics
# ============================================================================

system_cpu_usage_percent = Gauge(
    "creditnexus_system_cpu_usage_percent",
    "CPU usage percentage",
    ["cpu"],  # cpu: total, or cpu0, cpu1, etc.
    registry=registry,
)

system_memory_bytes = Gauge(
    "creditnexus_system_memory_bytes",
    "System memory usage in bytes",
    ["type"],  # type: total, available, used, free
    registry=registry,
)

system_disk_bytes = Gauge(
    "creditnexus_system_disk_bytes",
    "Disk usage in bytes",
    ["mount", "type"],  # type: total, used, free
    registry=registry,
)

# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    "creditnexus_app_info",
    "Application information",
    registry=registry,
)

# Initialize app info (will be set at startup)
app_info.info({"version": "1.0.0", "name": "creditnexus"})


# ============================================================================
# Helper Functions
# ============================================================================


def get_metrics() -> bytes:
    """Get metrics in Prometheus text format.
    
    Returns:
        bytes: Metrics in Prometheus text format
    """
    return generate_latest(registry)


def get_metrics_openmetrics() -> bytes:
    """Get metrics in OpenMetrics format.
    
    Returns:
        bytes: Metrics in OpenMetrics format
    """
    return generate_openmetrics(registry)


def normalize_path(path: str) -> str:
    """Normalize HTTP path to reduce cardinality.
    
    Replaces UUIDs and numeric IDs with placeholders to reduce
    metric cardinality.
    
    Args:
        path: Original HTTP path
        
    Returns:
        Normalized path with IDs replaced
    """
    import re
    
    # Replace UUIDs (8-4-4-4-12 format)
    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        ":id",
        path,
        flags=re.IGNORECASE,
    )
    
    # Replace numeric IDs at end of path segments
    path = re.sub(r"/\d+(?=/|$)", "/:id", path)
    
    # Replace query parameters
    if "?" in path:
        path = path.split("?")[0]
    
    return path
