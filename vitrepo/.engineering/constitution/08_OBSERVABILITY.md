# 08 Observability

## 1. Logging
- **Structured Logging**: All logs MUST be emitted in JSON format for ingestion by Cloud Logging.
- **Mandatory Fields**:
  - `trace_id` (OpenTelemetry compatible)
  - `span_id`
  - `service_name`
  - `environment` (production/staging/dev)
- **Severity Levels**: Use appropriate levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- **Context**: Include `user_id`, `match_id`, or `request_id` where applicable.

## 2. Monitoring & Metrics
- **Health Checks**: Every service MUST expose a `/health` endpoint returning 200 OK.
- **Critical Metrics**:
  - `http_request_duration_seconds` (Histogram)
  - `http_requests_total` (Counter by status code)
  - `ai_inference_duration_seconds`
  - `database_connection_pool_usage`
  - `tachyon_shard_availability_ratio`

## 3. Error Reporting & Alerts
- Use Cloud Error Reporting to track unhandled exceptions.
- **Alert Thresholds**:
  - API Error Rate > 1% over 5 minutes.
  - p99 Latency > 1s over 10 minutes.
  - Database Connection Usage > 80%.
