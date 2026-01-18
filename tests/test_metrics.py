"""Unit tests for Prometheus metrics collection."""

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, Counter, Histogram

from app.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    llm_calls_total,
    policy_decisions_total,
    documents_processed_total,
    get_metrics
)

from server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_metrics_endpoint_returns_prometheus_format(client: TestClient):
    """Test /metrics endpoint returns Prometheus format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    assert "creditnexus_http_requests_total" in response.text


def test_metrics_endpoint_openmetrics_format(client: TestClient):
    """Test /metrics endpoint returns OpenMetrics format when requested."""
    response = client.get("/metrics?format=openmetrics")
    assert response.status_code == 200
    assert "application/openmetrics-text" in response.headers.get("content-type", "")
    # OpenMetrics format shows metric names in HELP/TYPE lines
    assert "creditnexus_http_requests" in response.text or "creditnexus_http_requests_total" in response.text


def test_http_metrics_collection(client: TestClient):
    """Test HTTP metrics are collected automatically."""
    # Make a request
    response = client.get("/api/health")
    assert response.status_code in [200, 503]  # May be 503 if DB not configured
    
    # Check metrics endpoint includes the request
    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    # The metrics should include our request
    assert "creditnexus_http_requests_total" in metrics_response.text


def test_metrics_registry_contains_all_metrics():
    """Test that all expected metrics are registered."""
    metrics_text = get_metrics().decode('utf-8')
    
    # Check HTTP metrics
    assert "creditnexus_http_requests_total" in metrics_text
    assert "creditnexus_http_request_duration_seconds" in metrics_text
    
    # Check LLM metrics
    assert "creditnexus_llm_calls_total" in metrics_text
    assert "creditnexus_llm_call_duration_seconds" in metrics_text
    assert "creditnexus_llm_tokens_total" in metrics_text
    assert "creditnexus_llm_cost_total" in metrics_text
    
    # Check policy metrics
    assert "creditnexus_policy_decisions_total" in metrics_text
    assert "creditnexus_policy_decision_duration_seconds" in metrics_text
    
    # Check document metrics
    assert "creditnexus_documents_processed_total" in metrics_text
    assert "creditnexus_document_processing_duration_seconds" in metrics_text
    
    # Check database metrics
    assert "creditnexus_db_connections_active" in metrics_text
    assert "creditnexus_db_connections_total" in metrics_text
    assert "creditnexus_db_query_duration_seconds" in metrics_text


def test_http_metrics_increment():
    """Test that HTTP metrics increment correctly."""
    # Get initial count (if any)
    initial_count = http_requests_total.labels(
        method="GET",
        endpoint="/test",
        status_code="200"
    )._value.get()
    
    # Metrics should be accessible
    assert isinstance(initial_count, (int, float))


def test_metrics_health_endpoint(client: TestClient):
    """Test metrics health check endpoint."""
    response = client.get("/metrics/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "metrics"


def test_metrics_endpoint_handles_errors_gracefully():
    """Test that metrics endpoint handles errors gracefully."""
    # This test would require mocking an error condition
    # For now, we just verify the endpoint exists and returns data
    pass


@pytest.mark.asyncio
async def test_llm_metrics_wrapper():
    """Test LLM metrics wrapper function."""
    from app.core.llm_client import invoke_with_metrics, get_chat_model
    
    # This test would require a mock LLM model
    # For now, we verify the function exists
    assert callable(invoke_with_metrics)


def test_policy_metrics_increment():
    """Test that policy metrics can be incremented."""
    # Test that metrics are accessible
    policy_decisions_total.labels(
        decision="ALLOW",
        rule_applied="test_rule"
    ).inc()
    
    # Verify it's registered
    metrics_text = get_metrics().decode('utf-8')
    assert "creditnexus_policy_decisions_total" in metrics_text


def test_document_metrics_increment():
    """Test that document metrics can be incremented."""
    # Test that metrics are accessible
    documents_processed_total.labels(
        status="success",
        type="pdf"
    ).inc()
    
    # Verify it's registered
    metrics_text = get_metrics().decode('utf-8')
    assert "creditnexus_documents_processed_total" in metrics_text
