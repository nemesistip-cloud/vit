"""
VIT Persistence & Data Platform
Authoritative data access layer for the VIT Ecosystem.
"""
from app.core.persistence.manager import PersistenceManager
from app.core.persistence.repository import BaseRepository, RepositoryRegistry, RepositoryFactory
from app.core.persistence.transaction import TransactionManager, UnitOfWork
from app.core.persistence.query import QueryBuilder, QueryService
from app.core.persistence.cache import CacheManager
from app.core.persistence.audit import AuditRepository, AuditLog
from app.core.persistence.migration import MigrationManager
from app.core.persistence.schema import SchemaRegistry
from app.core.persistence.backup import BackupManager, RecoveryManager
from app.core.persistence.diagnostics import PersistenceDiagnostics
