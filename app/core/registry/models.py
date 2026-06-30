from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ModuleStatus(Enum):
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    VALIDATED = "VALIDATED"
    INITIALIZING = "INITIALIZING"
    INITIALIZED = "INITIALIZED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    SHUTDOWN = "SHUTDOWN"

class HealthStatus(Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"

class ModuleMetadata(BaseModel):
    module_id: str = Field(..., description="Unique identifier for the module")
    name: str = Field(..., description="Human-readable name")
    version: str = Field("1.0.0", description="Semantic version")
    description: str = ""
    owner: str = Field(..., description="Entity/Team responsible for the module")
    domain: str = Field(..., description="The bounding context domain")
    dependencies: List[str] = Field(default_factory=list, description="Mandatory module dependencies")
    optional_dependencies: List[str] = Field(default_factory=list, description="Optional module dependencies")
    capabilities: List[str] = Field(default_factory=list, description="Services/Features provided by this module")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema for module configuration")
    published_events: List[str] = Field(default_factory=list, description="Events emitted by this module")
    consumed_events: List[str] = Field(default_factory=list, description="Events listened to by this module")

class ModuleRuntimeInfo(BaseModel):
    metadata: ModuleMetadata
    status: ModuleStatus = ModuleStatus.REGISTERED
    health: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: float = 0.0
    error_count: int = 0
    uptime_start: float = 0.0
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

class LifecycleEvent(BaseModel):
    module_id: str
    previous_state: ModuleStatus
    current_state: ModuleStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class LifecycleDiagnostic(BaseModel):
    module_id: str
    state_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    failure_reports: List[Dict[str, Any]] = Field(default_factory=list)
    recovery_attempts: int = 0
    last_error: Optional[str] = None
    boot_time_ms: float = 0.0
