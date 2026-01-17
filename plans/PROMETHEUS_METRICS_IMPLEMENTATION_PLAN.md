# Prometheus Metrics Implementation Plan: CreditNexus

**Status**: Comprehensive Implementation Plan  
**Priority**: P1 (High)  
**Estimated Timeline**: 2-3 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This document provides a **complete plan** for implementing a Prometheus `/metrics` endpoint in CreditNexus. The implementation will expose comprehensive application metrics, business metrics, and system metrics in Prometheus format for monitoring, alerting, and observability.

**Key Features**:
- Standard HTTP metrics (request count, latency, errors)
- Business metrics (LLM calls, policy decisions, trades, documents)
- Database metrics (connection pool, query performance)
- System metrics (CPU, memory, disk)
- Custom CreditNexus-specific metrics
- Integration with existing audit/logging systems

---

## Current State Assessment

### ✅ Existing Infrastructure

1. **Health Check Endpoint**: `/api/health` (JSON-based, not Prometheus format)
2. **Audit Logging**: Comprehensive audit system with `AuditLog`, `PolicyDecision`, `LLMCallLog` models
3. **OpenTelemetry**: `logfire`, `opentelemetry-sdk` present (but not Prometheus)
4. **FastAPI**: Modern async framework with middleware support
5. **Database**: SQLAlchemy 2.0 with connection pooling

### ❌ Missing Components

1. **Prometheus Client Library**: Not in dependencies
2. **`/metrics` Endpoint**: Does not exist
3. **Metrics Middleware**: No request metrics collection
4. **Custom Metrics**: No business metrics exposed
5. **System Metrics**: No CPU/memory/disk metrics
6. **Database Metrics**: No connection pool metrics

---

## Feasibility Assessment

### ✅ **HIGHLY FEASIBLE**

**Reasons**:
1. **FastAPI Support**: FastAPI has excellent Prometheus integration via `prometheus-fastapi-instrumentator`
2. **Python Ecosystem**: Mature Prometheus client libraries (`prometheus-client`)
3. **Existing Data**: Audit logs and database models provide rich data for metrics
4. **Middleware Support**: FastAPI middleware can collect request metrics easily
5. **Low Overhead**: Prometheus metrics collection has minimal performance impact (<1ms per request)

**Challenges**:
1. **Metric Design**: Need to design meaningful business metrics
2. **Label Cardinality**: Avoid high-cardinality labels (e.g., user_id, deal_id)
3. **Performance**: Ensure metrics collection doesn't impact request latency
4. **Storage**: Prometheus metrics are ephemeral (not persisted to database)

**Solutions**:
1. Use aggregation for high-cardinality data (e.g., `user_id` → `role`, `organization_id`)
2. Use async metrics collection where possible
3. Cache expensive metric calculations
4. Use Prometheus remote write for long-term storage (optional)

---

## Implementation Plan

### Project 1: Prometheus Client Integration

**Objective**: Add Prometheus client library and create base metrics infrastructure.

#### Task 1.1: Add Dependencies

**File**: `pyproject.toml` (UPDATE)

**Lines**: ~21-100 (dependencies section)

**Subtasks**:
1. **Add Prometheus client library**:
   ```toml
   # Metrics & Observability
   "prometheus-client>=0.19.0",  # Prometheus Python client
   "prometheus-fastapi-instrumentator>=6.1.0",  # FastAPI Prometheus integration
   ```

2. **Optional (for advanced features)**:
   ```toml
   "psutil>=5.9.0",  # System metrics (CPU, memory, disk)
   ```

**Code Reference**: See `pyproject.toml` lines 21-100

#### Task 1.2: Create Metrics Registry

**File**: `app/core/metrics.py` (NEW)

**Lines**: 1-200

**Subtasks**:
1. **Create Prometheus registry and metrics**:
   ```python
   from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
   from prometheus_client.openmetrics import generate_latest as generate_latest_openmetrics
   from typing import Dict, Any
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
   except ImportError:
       logger.warning("psutil not available, system metrics will be disabled")
       system_cpu_percent = None
       system_memory_bytes = None
       system_disk_bytes = None
   
   # Application Info
   app_info = Info(
       'creditnexus_app',
       'CreditNexus application information'
   )
   
   # Initialize app info
   app_info.info({
       'version': '1.0.0',
       'environment': 'production'  # Will be set from settings
   })
   
   def get_metrics() -> bytes:
       """Get Prometheus metrics in text format."""
       return generate_latest(REGISTRY)
   
   def get_metrics_openmetrics() -> bytes:
       """Get Prometheus metrics in OpenMetrics format."""
       return generate_latest_openmetrics(REGISTRY)
   ```

**Code Reference**: See `app/core/metrics.py` (NEW)

---

### Project 2: Metrics Middleware

**Objective**: Create FastAPI middleware to collect HTTP request metrics automatically.

#### Task 2.1: Create Metrics Middleware

**File**: `app/middleware/metrics_middleware.py` (NEW)

**Lines**: 1-150

**Subtasks**:
1. **Create HTTP metrics middleware**:
   ```python
   from fastapi import Request, Response
   from starlette.middleware.base import BaseHTTPMiddleware
   from starlette.types import ASGIApp
   import time
   import logging
   
   from app.core.metrics import (
       http_requests_total,
       http_request_duration_seconds
   )
   
   logger = logging.getLogger(__name__)
   
   
   class MetricsMiddleware(BaseHTTPMiddleware):
       """Middleware to collect HTTP request metrics."""
       
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
           """Normalize path to reduce cardinality (e.g., /api/deals/123 -> /api/deals/:id)."""
           # Replace UUIDs and numeric IDs with placeholders
           import re
           
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
   ```

**Code Reference**: See `app/middleware/metrics_middleware.py` (NEW)

#### Task 2.2: Register Middleware

**File**: `server.py` (UPDATE)

**Lines**: ~530-550 (after security headers middleware)

**Subtasks**:
1. **Add metrics middleware**:
   ```python
   # Metrics middleware (after security headers)
   from app.middleware.metrics_middleware import MetricsMiddleware
   app.add_middleware(MetricsMiddleware)
   ```

**Code Reference**: See `server.py` lines 530-550

---

### Project 3: Metrics Endpoint

**Objective**: Create `/metrics` endpoint to expose Prometheus metrics.

#### Task 3.1: Create Metrics Endpoint

**File**: `app/api/metrics_routes.py` (NEW)

**Lines**: 1-100

**Subtasks**:
1. **Create metrics router**:
   ```python
   from fastapi import APIRouter, Response
   from fastapi.responses import PlainTextResponse
   from app.core.metrics import get_metrics, get_metrics_openmetrics
   from app.core.config import settings
   import logging
   
   logger = logging.getLogger(__name__)
   
   router = APIRouter(prefix="/metrics", tags=["metrics"])
   
   
   @router.get("")
   async def metrics(
       format: str = "prometheus"  # prometheus or openmetrics
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
   ```

**Code Reference**: See `app/api/metrics_routes.py` (NEW)

#### Task 3.2: Register Metrics Router

**File**: `server.py` (UPDATE)

**Lines**: ~552-575 (with other routers)

**Subtasks**:
1. **Add metrics router**:
   ```python
   from app.api.metrics_routes import router as metrics_router
   app.include_router(metrics_router)
   ```

**Code Reference**: See `server.py` lines 552-575

---

### Project 4: Business Metrics Integration

**Objective**: Integrate metrics collection into existing services.

#### Task 4.1: LLM Call Metrics

**File**: `app/core/llm_client.py` (UPDATE)

**Lines**: Find LLM call locations

**Subtasks**:
1. **Add metrics to LLM calls**:
   ```python
   from app.core.metrics import (
       llm_calls_total,
       llm_call_duration_seconds,
       llm_tokens_total,
       llm_cost_total
   )
   import time
   
   # In LLM call function:
   start_time = time.time()
   try:
       result = await llm.ainvoke(messages)
       
       # Calculate metrics
       duration = time.time() - start_time
       prompt_tokens = getattr(result, 'prompt_tokens', 0)
       completion_tokens = getattr(result, 'completion_tokens', 0)
       cost = calculate_cost(provider, model, prompt_tokens, completion_tokens)
       
       # Record metrics
       llm_calls_total.labels(
           provider=provider,
           model=model,
           status="success"
       ).inc()
       
       llm_call_duration_seconds.labels(
           provider=provider,
           model=model
       ).observe(duration)
       
       llm_tokens_total.labels(
           provider=provider,
           model=model,
           type="input"
       ).inc(prompt_tokens)
       
       llm_tokens_total.labels(
           provider=provider,
           model=model,
           type="output"
       ).inc(completion_tokens)
       
       llm_cost_total.labels(
           provider=provider,
           model=model
       ).inc(cost)
       
   except Exception as e:
       duration = time.time() - start_time
       
       llm_calls_total.labels(
           provider=provider,
           model=model,
           status="error"
       ).inc()
       
       llm_call_duration_seconds.labels(
           provider=provider,
           model=model
       ).observe(duration)
       
       raise
   ```

**Code Reference**: See `app/core/llm_client.py`

#### Task 4.2: Policy Decision Metrics

**File**: `app/services/policy_service.py` (UPDATE)

**Lines**: Find policy evaluation methods

**Subtasks**:
1. **Add metrics to policy decisions**:
   ```python
   from app.core.metrics import (
       policy_decisions_total,
       policy_decision_duration_seconds
   )
   import time
   
   # In policy evaluation method:
   start_time = time.time()
   try:
       result = self.policy_engine.evaluate(transaction)
       decision = result.get("decision", "ALLOW")
       rule_applied = result.get("rule_applied", "default")
       duration = time.time() - start_time
       
       policy_decisions_total.labels(
           decision=decision,
           rule_applied=rule_applied
       ).inc()
       
       policy_decision_duration_seconds.labels(
           decision=decision
       ).observe(duration)
       
       return result
   except Exception as e:
       duration = time.time() - start_time
       policy_decisions_total.labels(
           decision="ERROR",
           rule_applied="error"
       ).inc()
       raise
   ```

**Code Reference**: See `app/services/policy_service.py`

#### Task 4.3: Document Processing Metrics

**File**: `app/api/routes.py` (UPDATE)

**Lines**: Find document extraction endpoints

**Subtasks**:
1. **Add metrics to document processing**:
   ```python
   from app.core.metrics import (
       documents_processed_total,
       document_processing_duration_seconds
   )
   import time
   
   # In document extraction endpoint:
   start_time = time.time()
   try:
       result = await extract_document(file)
       duration = time.time() - start_time
       file_type = file.content_type or "unknown"
       
       documents_processed_total.labels(
           status="success",
           type=file_type
       ).inc()
       
       document_processing_duration_seconds.labels(
           type=file_type
       ).observe(duration)
       
       return result
   except Exception as e:
       duration = time.time() - start_time
       documents_processed_total.labels(
           status="error",
           type=file_type
       ).inc()
       raise
   ```

**Code Reference**: See `app/api/routes.py`

#### Task 4.4: Trade Execution Metrics

**File**: `app/api/routes.py` or trading service (UPDATE)

**Lines**: Find trade execution endpoints

**Subtasks**:
1. **Add metrics to trade execution**:
   ```python
   from app.core.metrics import (
       trades_executed_total,
       trade_value_total
   )
   
   # In trade execution endpoint:
   try:
       trade = await execute_trade(request)
       
       trades_executed_total.labels(
           status="success",
           type=trade.type  # buy or sell
       ).inc()
       
       trade_value_total.labels(
           type=trade.type
       ).inc(float(trade.amount))
       
       return trade
   except Exception as e:
       trades_executed_total.labels(
           status="failed",
           type=request.type
       ).inc()
       raise
   ```

**Code Reference**: See trading endpoints in `app/api/routes.py`

#### Task 4.5: Verification Metrics

**File**: `app/agents/verifier.py` (UPDATE)

**Lines**: Find verification methods

**Subtasks**:
1. **Add metrics to verification**:
   ```python
   from app.core.metrics import (
       verifications_total,
       verification_duration_seconds
   )
   import time
   
   # In verification method:
   start_time = time.time()
   try:
       result = await verify_location(location)
       duration = time.time() - start_time
       verification_type = "satellite" if use_satellite else "ground_truth"
       
       verifications_total.labels(
           status="success",
           type=verification_type
       ).inc()
       
       verification_duration_seconds.labels(
           type=verification_type
       ).observe(duration)
       
       return result
   except Exception as e:
       duration = time.time() - start_time
       verifications_total.labels(
           status="failed",
           type=verification_type
       ).inc()
       raise
   ```

**Code Reference**: See `app/agents/verifier.py`

#### Task 4.6: Stock Prediction Metrics

**File**: `app/services/stock_prediction_service.py` (UPDATE - when implemented)

**Lines**: Find prediction methods

**Subtasks**:
1. **Add metrics to stock predictions**:
   ```python
   from app.core.metrics import (
       stock_predictions_total,
       stock_prediction_duration_seconds,
       stock_prediction_gpu_memory_bytes
   )
   import time
   
   # In prediction method:
   start_time = time.time()
   try:
       result = await generate_prediction(symbol, timeframe)
       duration = time.time() - start_time
       gpu_memory = get_gpu_memory_usage()  # If available
       
       stock_predictions_total.labels(
           timeframe=timeframe,
           status="success"
       ).inc()
       
       stock_prediction_duration_seconds.labels(
           timeframe=timeframe
       ).observe(duration)
       
       if gpu_memory:
           stock_prediction_gpu_memory_bytes.labels(
               timeframe=timeframe
           ).observe(gpu_memory)
       
       return result
   except Exception as e:
       duration = time.time() - start_time
       stock_predictions_total.labels(
           timeframe=timeframe,
           status="error"
       ).inc()
       raise
   ```

**Code Reference**: See `STOCK_PREDICTION_VENDORING_PLAN.md`

---

### Project 5: Database Metrics

**Objective**: Collect database connection pool and query performance metrics.

#### Task 5.1: Database Connection Metrics

**File**: `app/db/__init__.py` or new `app/db/metrics.py` (NEW)

**Lines**: 1-100

**Subtasks**:
1. **Add database connection metrics**:
   ```python
   from app.core.metrics import (
       db_connections_active,
       db_connections_total
   )
   from sqlalchemy import event
   from sqlalchemy.pool import Pool
   import logging
   
   logger = logging.getLogger(__name__)
   
   
   def setup_db_metrics(engine):
       """Setup database connection pool metrics."""
       
       @event.listens_for(Pool, "connect")
       def on_connect(dbapi_conn, connection_record):
           """Track connection creation."""
           db_connections_total.labels(action="created").inc()
           db_connections_active.labels(state="idle").inc()
       
       @event.listens_for(Pool, "checkout")
       def on_checkout(dbapi_conn, connection_record, connection_proxy):
           """Track connection checkout."""
           db_connections_active.labels(state="idle").dec()
           db_connections_active.labels(state="in_use").inc()
       
       @event.listens_for(Pool, "checkin")
       def on_checkin(dbapi_conn, connection_record):
           """Track connection checkin."""
           db_connections_active.labels(state="in_use").dec()
           db_connections_active.labels(state="idle").inc()
       
       @event.listens_for(Pool, "invalidate")
       def on_invalidate(dbapi_conn, connection_record, exception):
           """Track connection invalidation."""
           db_connections_total.labels(action="closed").inc()
           db_connections_active.labels(state="in_use").dec()
   ```

**Code Reference**: See `app/db/__init__.py` or `app/db/metrics.py` (NEW)

#### Task 5.2: Query Performance Metrics

**File**: `app/db/metrics.py` (UPDATE)

**Lines**: 100-200

**Subtasks**:
1. **Add query performance metrics**:
   ```python
   from app.core.metrics import db_query_duration_seconds
   from sqlalchemy import event
   from sqlalchemy.engine import Engine
   import time
   import logging
   
   logger = logging.getLogger(__name__)
   
   
   def setup_query_metrics(engine):
       """Setup database query performance metrics."""
       
       @event.listens_for(Engine, "before_cursor_execute")
       def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
           """Record query start time."""
           context._query_start_time = time.time()
       
       @event.listens_for(Engine, "after_cursor_execute")
       def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
           """Record query duration."""
           if hasattr(context, '_query_start_time'):
               duration = time.time() - context._query_start_time
               
               # Determine operation type
               statement_upper = statement.upper().strip()
               if statement_upper.startswith('SELECT'):
                   operation = "select"
               elif statement_upper.startswith('INSERT'):
                   operation = "insert"
               elif statement_upper.startswith('UPDATE'):
                   operation = "update"
               elif statement_upper.startswith('DELETE'):
                   operation = "delete"
               else:
                   operation = "other"
               
               db_query_duration_seconds.labels(
                   operation=operation
               ).observe(duration)
   ```

**Code Reference**: See `app/db/metrics.py`

#### Task 5.3: Initialize Database Metrics

**File**: `app/db/__init__.py` (UPDATE)

**Lines**: Find engine initialization

**Subtasks**:
1. **Initialize database metrics**:
   ```python
   from app.db.metrics import setup_db_metrics, setup_query_metrics
   
   # After engine creation:
   if engine:
       setup_db_metrics(engine)
       setup_query_metrics(engine)
   ```

**Code Reference**: See `app/db/__init__.py`

---

### Project 6: System Metrics (Optional)

**Objective**: Collect system-level metrics (CPU, memory, disk).

#### Task 6.1: System Metrics Collector

**File**: `app/core/system_metrics.py` (NEW)

**Lines**: 1-150

**Subtasks**:
1. **Create system metrics collector**:
   ```python
   from app.core.metrics import (
       system_cpu_percent,
       system_memory_bytes,
       system_disk_bytes
   )
   import psutil
   import asyncio
   import logging
   
   logger = logging.getLogger(__name__)
   
   
   async def collect_system_metrics():
       """Collect system metrics periodically."""
       if not system_cpu_percent:
           logger.warning("System metrics not available (psutil not installed)")
           return
       
       try:
           # CPU metrics
           cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
           system_cpu_percent.labels(cpu="total").set(psutil.cpu_percent(interval=0))
           
           for i, percent in enumerate(cpu_percent):
               system_cpu_percent.labels(cpu=f"core_{i}").set(percent)
           
           # Memory metrics
           memory = psutil.virtual_memory()
           system_memory_bytes.labels(type="total").set(memory.total)
           system_memory_bytes.labels(type="available").set(memory.available)
           system_memory_bytes.labels(type="used").set(memory.used)
           system_memory_bytes.labels(type="free").set(memory.free)
           
           # Disk metrics
           disk = psutil.disk_usage('/')
           system_disk_bytes.labels(type="total", mount="/").set(disk.total)
           system_disk_bytes.labels(type="used", mount="/").set(disk.used)
           system_disk_bytes.labels(type="free", mount="/").set(disk.free)
           
       except Exception as e:
           logger.error(f"Error collecting system metrics: {e}", exc_info=True)
   
   
   async def start_system_metrics_collector(interval: int = 60):
       """Start system metrics collection in background."""
       while True:
           await collect_system_metrics()
           await asyncio.sleep(interval)
   ```

**Code Reference**: See `app/core/system_metrics.py` (NEW)

#### Task 6.2: Start System Metrics Collector

**File**: `server.py` (UPDATE)

**Lines**: ~42-130 (in lifespan startup)

**Subtasks**:
1. **Start system metrics collector**:
   ```python
   from app.core.system_metrics import start_system_metrics_collector
   import asyncio
   
   # In lifespan startup:
   # Start system metrics collector (optional)
   if settings.SYSTEM_METRICS_ENABLED:
       metrics_task = asyncio.create_task(
           start_system_metrics_collector(interval=60)  # Collect every 60 seconds
       )
   ```

**Code Reference**: See `server.py` lifespan function

---

## Configuration

### Environment Variables

**File**: `app/core/config.py` (UPDATE)

**Lines**: Find Settings class

**Subtasks**:
1. **Add metrics configuration**:
   ```python
   class Settings(BaseSettings):
       # ... existing settings ...
       
       # Prometheus Metrics
       METRICS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
       METRICS_PATH: str = Field(default="/metrics", description="Metrics endpoint path")
       SYSTEM_METRICS_ENABLED: bool = Field(default=False, description="Enable system metrics (requires psutil)")
       METRICS_COLLECT_INTERVAL: int = Field(default=60, description="System metrics collection interval (seconds)")
   ```

**Code Reference**: See `app/core/config.py`

---

## Testing

### Unit Tests

**File**: `tests/test_metrics.py` (NEW)

**Subtasks**:
1. **Test metrics collection**:
   ```python
   import pytest
   from fastapi.testclient import TestClient
   from app.core.metrics import http_requests_total, get_metrics
   
   def test_metrics_endpoint(client: TestClient):
       """Test /metrics endpoint returns Prometheus format."""
       response = client.get("/metrics")
       assert response.status_code == 200
       assert "creditnexus_http_requests_total" in response.text
   
   def test_http_metrics_collection(client: TestClient):
       """Test HTTP metrics are collected."""
       initial_count = http_requests_total.labels(
           method="GET",
           endpoint="/test",
           status_code="200"
       )._value.get()
       
       client.get("/api/health")
       
       # Metrics should be updated (check via /metrics endpoint)
       response = client.get("/metrics")
       assert "creditnexus_http_requests_total" in response.text
   ```

**Code Reference**: See `tests/test_metrics.py` (NEW)

---

## Documentation

### API Documentation

**File**: `docs/api-reference/metrics.mdx` (NEW)

**Subtasks**:
1. **Document metrics endpoint**:
   ```markdown
   # Metrics API
   
   ## Prometheus Metrics Endpoint
   
   **GET** `/metrics`
   
   Returns Prometheus metrics in text format.
   
   **Query Parameters**:
   - `format`: "prometheus" (default) or "openmetrics"
   
   **Response**: Prometheus text format
   
   **Example**:
   ```bash
   curl http://localhost:8000/metrics
   ```
   ```

**Code Reference**: See `docs/api-reference/metrics.mdx` (NEW)

---

## Implementation Checklist

### Phase 1: Core Infrastructure (Week 1)
- [ ] Add Prometheus client dependencies
- [ ] Create `app/core/metrics.py` with metric definitions
- [ ] Create `app/middleware/metrics_middleware.py`
- [ ] Register metrics middleware in `server.py`
- [ ] Create `app/api/metrics_routes.py` with `/metrics` endpoint
- [ ] Register metrics router in `server.py`
- [ ] Test `/metrics` endpoint returns Prometheus format

### Phase 2: Business Metrics (Week 2)
- [ ] Add LLM call metrics to `app/core/llm_client.py`
- [ ] Add policy decision metrics to `app/services/policy_service.py`
- [ ] Add document processing metrics to `app/api/routes.py`
- [ ] Add trade execution metrics to trading endpoints
- [ ] Add verification metrics to `app/agents/verifier.py`
- [ ] Add stock prediction metrics (when service is implemented)

### Phase 3: Database & System Metrics (Week 3)
- [ ] Create `app/db/metrics.py` for database metrics
- [ ] Setup database connection pool metrics
- [ ] Setup query performance metrics
- [ ] Create `app/core/system_metrics.py` (optional)
- [ ] Start system metrics collector (if enabled)
- [ ] Add configuration options

### Phase 4: Testing & Documentation (Week 3)
- [ ] Write unit tests for metrics collection
- [ ] Write integration tests for `/metrics` endpoint
- [ ] Document metrics endpoint in API docs
- [ ] Create metrics dashboard guide (Grafana)
- [ ] Performance testing (ensure <1ms overhead)

---

## Success Criteria

1. ✅ `/metrics` endpoint returns Prometheus format
2. ✅ HTTP request metrics are collected automatically
3. ✅ Business metrics (LLM, policy, documents, trades) are collected
4. ✅ Database metrics (connections, queries) are collected
5. ✅ System metrics are collected (if enabled)
6. ✅ Metrics collection has <1ms overhead per request
7. ✅ All metrics follow Prometheus naming conventions
8. ✅ Metrics are properly labeled (low cardinality)
9. ✅ Documentation is complete
10. ✅ Tests pass

---

## Related Plans

- **`AUDIT_TRACEABILITY_PLAN.md`** - Audit logging provides data for metrics
- **`STOCK_PREDICTION_VENDORING_PLAN.md`** - Stock prediction metrics integration
- **`BILLING_DASHBOARD_PLAN.md`** - Billing metrics can be exposed via Prometheus

---

**Last Updated**: 2024-12-XX  
**Status**: Planning  
**Version**: 1.0
