from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class MetricType(str, Enum):
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"

class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"

class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class TelemetryContext(BaseModel):
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    module_id: Optional[str] = None

class MetricEntry(BaseModel):
    name: str
    value: float
    type: MetricType
    unit: str = ""
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class LogEntry(BaseModel):
    ts: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel
    module: str
    msg: str
    context: TelemetryContext
    extra: Dict[str, Any] = Field(default_factory=dict)
    runtime_version: str = "1.1.0"
    env: str = "development"

class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    context: TelemetryContext
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AuditRecord(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str  # user_id or system
    action: str
    resource: str
    status: str
    context: TelemetryContext
    details: Dict[str, Any] = Field(default_factory=dict)

class Alert(BaseModel):
    id: str
    severity: AlertSeverity
    title: str
    description: str
    module_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: TelemetryContext
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SubsystemHealth(BaseModel):
    name: str
    status: HealthStatus
    last_check: datetime
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

class SystemDiagnostics(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    kernel_state: str
    uptime_seconds: float
    health_summary: HealthStatus
    subsystems: List[SubsystemHealth]
    metrics_snapshot: List[MetricEntry]
