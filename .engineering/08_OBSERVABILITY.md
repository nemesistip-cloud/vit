# 08 Observability

## 1. Logging
- **Structured Logging**: All logs must be emitted in JSON format for ingestion by Cloud Logging.
- **Severity Levels**: Use appropriate levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- **Context**: Include `user_id`, `match_id`, or `request_id` where applicable.

## 2. Monitoring
- **Health Checks**: Every service must expose a `/health` endpoint.
- **Metrics**: Track critical metrics including API latency, inference success rate, and database connection pool usage.

## 3. Error Reporting
- Use Cloud Error Reporting to track unhandled exceptions.
- Ensure all background task failures are logged with a full stack trace.
