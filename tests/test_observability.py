import pytest
import asyncio
from app.core.observability.manager import obs_manager
from app.core.observability.models import MetricType, HealthStatus, AlertSeverity

@pytest.mark.asyncio
async def test_metrics_collection():
    obs_manager.metrics.clear()
    obs_manager.record_metric("test_metric", 42.0, MetricType.COUNTER, labels={"env": "test"})

    snapshot = obs_manager.metrics.get_snapshot()
    assert len(snapshot) == 1
    assert snapshot[0].name == "test_metric"
    assert snapshot[0].value == 42.0
    assert snapshot[0].labels["env"] == "test"

@pytest.mark.asyncio
async def test_health_monitoring():
    obs_manager.health.update_status("test_sub", HealthStatus.HEALTHY, "OK")
    assert obs_manager.health.get_overall_status() == HealthStatus.HEALTHY

    obs_manager.health.update_status("test_sub_2", HealthStatus.UNHEALTHY, "FAIL")
    assert obs_manager.health.get_overall_status() == HealthStatus.UNHEALTHY

    obs_manager.health.update_status("test_sub_2", HealthStatus.DEGRADED, "WARNING")
    assert obs_manager.health.get_overall_status() == HealthStatus.DEGRADED

@pytest.mark.asyncio
async def test_tracing_context():
    obs_manager.tracing.clear()
    t_id, c_id = obs_manager.tracing.start_trace()
    assert t_id is not None
    assert c_id == t_id

    context = obs_manager.get_context()
    assert context.trace_id == t_id

    s_id = obs_manager.tracing.start_span("test_span")
    context_2 = obs_manager.get_context()
    assert context_2.span_id == s_id
    assert context_2.trace_id == t_id

@pytest.mark.asyncio
async def test_alerting():
    obs_manager.alerts._alerts = []
    obs_manager.emit_alert(AlertSeverity.ERROR, "Test Alert", "Something went wrong", "test_module")

    alerts = obs_manager.alerts.get_active_alerts()
    assert len(alerts) == 1
    assert alerts[0].title == "Test Alert"
    assert alerts[0].severity == AlertSeverity.ERROR

@pytest.mark.asyncio
async def test_audit_logging():
    obs_manager.audit._history = []
    obs_manager.audit_event("user_1", "login", "auth_service", status="success")

    records = obs_manager.audit.get_records()
    assert len(records) == 1
    assert records[0].actor == "user_1"
    assert records[0].action == "login"

@pytest.mark.asyncio
async def test_diagnostics_report():
    report = obs_manager.get_diagnostics()
    assert report.timestamp is not None
    assert isinstance(report.health_summary, HealthStatus)
    assert isinstance(report.metrics_snapshot, list)
