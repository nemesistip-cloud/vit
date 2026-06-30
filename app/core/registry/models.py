from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ModuleStatus(Enum):
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    INITIALIZING = "INITIALIZING"
    INITIALIZED = "INITIALIZED"
    STARTING = "STARTING"
    STARTED = "STARTED"
    READY = "READY"
    DEGRADED = "DEGRADED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
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
