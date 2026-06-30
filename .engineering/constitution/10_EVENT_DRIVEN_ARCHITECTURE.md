# 10 Event-Driven Architecture

## 1. Async Task Queue
- Use Celery/Redis for all long-running background tasks.
- Task definitions live in `app/tasks/` and `app/worker.py`.

## 2. WebSocket Bus
- Use the WebSocket event bus (`admin_ws`) for real-time system notifications and live data updates.

## 3. Idempotency Keys
- All event consumers must be idempotent to handle potential double-delivery of events.
