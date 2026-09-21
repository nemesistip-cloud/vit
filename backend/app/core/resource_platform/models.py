from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class TaskStatus(Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"
    DEAD_LETTER = "DEAD_LETTER"

class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

class ScheduleType(Enum):
    ONCE = "ONCE"
    INTERVAL = "INTERVAL"
    CRON = "CRON"

class ResourceQuota(BaseModel):
    cpu_cores: float = 0.1
    memory_mb: int = 128
    timeout_seconds: int = 300

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    scheduled_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    correlation_id: Optional[str] = None
    quota: ResourceQuota = Field(default_factory=ResourceQuota)

class LockInfo(BaseModel):
    lock_id: str
    owner: str
    expires_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkerStatus(Enum):
    STARTING = "STARTING"
    IDLE = "IDLE"
    BUSY = "BUSY"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    UNHEALTHY = "UNHEALTHY"

class WorkerInfo(BaseModel):
    worker_id: str
    status: WorkerStatus
    current_task_id: Optional[str] = None
    tasks_processed: int = 0
    uptime_seconds: float
    resource_usage: Dict[str, Any] = Field(default_factory=dict)

class RateLimitInfo(BaseModel):
    key: str
    limit: int
    window_seconds: int
    current_count: int
    reset_at: datetime
