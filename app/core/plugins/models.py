from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
import semver

class PluginStatus(Enum):
    DISCOVERED = "DISCOVERED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    REGISTERED = "REGISTERED"
    RESOLVING = "RESOLVING"
    INITIALIZING = "INITIALIZING"
    INITIALIZED = "INITIALIZED"
    ACTIVATING = "ACTIVATING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    UPGRADING = "UPGRADING"
    DEGRADED = "DEGRADED"
    FAILING = "FAILING"
    FAILED = "FAILED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"
    REMOVED = "REMOVED"

class SecurityClassification(Enum):
    CORE = "CORE"
    TRUSTED = "TRUSTED"
    COMMUNITY = "COMMUNITY"
    EXPERIMENTAL = "EXPERIMENTAL"
    UNTRUSTED = "UNTRUSTED"

class Capability(BaseModel):
    name: str = Field(..., description="Unique name of the capability")
    version: str = Field("1.0.0", description="Version of the capability interface")
    description: Optional[str] = None
    provider_id: str = Field(..., description="ID of the plugin providing this capability")

class PluginManifest(BaseModel):
    plugin_id: str = Field(..., description="Unique identifier for the plugin (e.g., com.vit.sports)")
    name: str = Field(..., description="Human-readable name")
    version: str = Field(..., description="Semantic version of the plugin")
    description: str = ""
    author: str = ""
    organization: Optional[str] = None
    platform_version: str = Field(..., description="Target platform version")
    min_runtime_version: str = Field("1.0.0", description="Minimum VIT Runtime version required")

    dependencies: Dict[str, str] = Field(default_factory=dict, description="Required plugins and their version constraints")
    optional_dependencies: Dict[str, str] = Field(default_factory=dict, description="Optional plugins and their version constraints")

    config_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for plugin configuration")
    permissions: List[str] = Field(default_factory=list, description="Requested platform permissions")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities provided by this plugin")

    published_events: List[str] = Field(default_factory=list, description="Events emitted by this plugin")
    consumed_events: List[str] = Field(default_factory=list, description="Events listened to by this plugin")

    health_check_endpoint: Optional[str] = None
    lifecycle_hooks: List[str] = Field(default_factory=list, description="Custom lifecycle hook names supported")
    security_classification: SecurityClassification = SecurityClassification.COMMUNITY

    @field_validator('version', 'platform_version', 'min_runtime_version')
    @classmethod
    def validate_semver(cls, v: str) -> str:
        if not semver.VersionInfo.is_valid(v):
            raise ValueError(f"Invalid semantic version: {v}")
        return v

class PluginRuntimeInfo(BaseModel):
    manifest: PluginManifest
    status: PluginStatus = PluginStatus.DISCOVERED
    load_time: float = 0.0
    error_count: int = 0
    capabilities: List[Capability] = Field(default_factory=list)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    sandbox_id: Optional[str] = None
