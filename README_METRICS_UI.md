# CreditNexus Metrics UI Setup

This guide explains how to visualize your Prometheus metrics using Grafana.

## What You're Seeing

The output you copied is **Prometheus metrics** in OpenMetrics format. It includes:
- **HTTP metrics**: Request counts, durations, response sizes
- **Database metrics**: Connection pool, query performance, transactions
- **Business metrics**: LLM calls, policy decisions, document processing (when used)
- **System metrics**: CPU, memory, disk (when enabled)

## Quick Start: Grafana UI

### 1. Start Prometheus & Grafana

```powershell
docker-compose up -d prometheus grafana
```

This starts:
- **Prometheus** on `http://localhost:9090` (scrapes your metrics)
- **Grafana** on `http://localhost:3000` (visualizes metrics)

### 2. Access Grafana

1. Open `http://localhost:3000` in your browser
2. Login:
   - **Username**: `admin`
   - **Password**: `admin`
3. Change the password when prompted (or skip)

### 3. View Dashboards

Grafana will automatically:
- Connect to Prometheus (pre-configured)
- Load the "CreditNexus Overview" dashboard

**Navigate**: Dashboards → Browse → CreditNexus → CreditNexus Overview

## Manual Dashboard Creation

If the auto-loaded dashboard doesn't appear, create one manually:

### Step 1: Add Prometheus Data Source

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL: `http://prometheus:9090` (or `http://localhost:9090` from host)
5. Click **Save & Test**

### Step 2: Create a Dashboard

1. Go to **Dashboards** → **New Dashboard**
2. Click **Add visualization**
3. Select **Prometheus** as data source
4. Try these queries:

#### HTTP Request Rate
```
rate(creditnexus_http_requests_total[5m])
```

#### HTTP Request Duration (p95)
```
histogram_quantile(0.95, rate(creditnexus_http_request_duration_seconds_bucket[5m]))
```

#### Database Connections
```
creditnexus_db_connections_active
creditnexus_db_connections_idle
```

#### Database Query Duration (p95)
```
histogram_quantile(0.95, rate(creditnexus_db_query_duration_seconds_bucket[5m]))
```

#### HTTP Status Codes
```
sum(rate(creditnexus_http_requests_total[5m])) by (status_code)
```

## Troubleshooting

### Prometheus Can't Scrape Metrics

**Problem**: Prometheus shows "connection refused" for `host.docker.internal:8000`

**Solution**: 
1. Make sure your CreditNexus server is running on `http://127.0.0.1:8000`
2. On Windows, `host.docker.internal` should work. If not, try:
   - Update `prometheus.yml` to use your actual IP address
   - Or use `host.docker.internal:8000` explicitly

### Grafana Can't Connect to Prometheus

**Problem**: Grafana shows "Data source is not working"

**Solution**:
1. Check Prometheus is running: `http://localhost:9090`
2. In Grafana, set Prometheus URL to `http://prometheus:9090` (from inside Docker) or `http://localhost:9090` (from host)

### No Metrics Showing

**Problem**: Dashboard shows "No data"

**Solution**:
1. Check Prometheus targets: `http://localhost:9090/targets`
2. Verify your server is running: `http://localhost:8000/metrics`
3. Make some API requests to generate metrics
4. Check time range in Grafana (top right)

## Useful Prometheus Queries

### Request Rate by Endpoint
```
sum(rate(creditnexus_http_requests_total[5m])) by (path)
```

### Error Rate
```
sum(rate(creditnexus_http_requests_total{status_code=~"5.."}[5m]))
```

### Average Request Duration
```
rate(creditnexus_http_request_duration_seconds_sum[5m]) / rate(creditnexus_http_request_duration_seconds_count[5m])
```

### Database Query Rate
```
rate(creditnexus_db_query_duration_seconds_count[5m])
```

### Active Database Connections
```
creditnexus_db_connections_active
```

## Next Steps

1. **Create custom dashboards** for your specific use cases
2. **Set up alerts** in Grafana for thresholds (e.g., error rate > 1%)
3. **Export dashboards** as JSON to share with your team
4. **Add more metrics** as you instrument more parts of your application

## Access URLs

- **Grafana UI**: http://localhost:3000
- **Prometheus UI**: http://localhost:9090
- **Your Metrics Endpoint**: http://localhost:8000/metrics
- **Prometheus Targets**: http://localhost:9090/targets
