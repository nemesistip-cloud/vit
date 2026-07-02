import logging
from typing import Dict, Any, List, Type, Optional
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

class SchemaRegistry:
    """Central metadata registry for database schemas and entities."""

    _entities: Dict[str, Type[DeclarativeBase]] = {}
    _metadata_info: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register_entity(cls, name: str, entity_class: Type[DeclarativeBase]):
        """Register a database entity and extract its metadata."""
        cls._entities[name] = entity_class

        # Extract metadata
        columns = []
        for col in entity_class.__table__.columns:
            columns.append({
                "name": col.name,
                "type": str(col.type),
                "nullable": col.nullable,
                "primary_key": col.primary_key
            })

        cls._metadata_info[name] = {
            "table_name": entity_class.__tablename__,
            "columns": columns,
            "indexes": [idx.name for idx in entity_class.__table__.indexes],
            "constraints": [cons.name for cons in entity_class.__table__.constraints if cons.name]
        }
        logger.debug(f"[persistence] Registered entity schema: {name} (table: {entity_class.__tablename__})")

    @classmethod
    def get_entity(cls, name: str) -> Optional[Type[DeclarativeBase]]:
        """Get an entity class by name."""
        return cls._entities.get(name)

    @classmethod
    def get_metadata(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific entity."""
        return cls._metadata_info.get(name)

    @classmethod
    def list_entities(cls) -> List[str]:
        """List all registered entities."""
        return list(cls._entities.keys())

    @classmethod
    def get_full_registry(self) -> Dict[str, Any]:
        """Return the complete schema registry."""
        return self._metadata_info
