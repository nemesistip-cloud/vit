import logging
from typing import Dict, Any
from app.core.persistence.manager import PersistenceManager
from app.core.kernel import kernel

logger = logging.getLogger(__name__)

# This file facilitates the registration of the persistence subsystem
# It's kept separate to avoid circular imports during kernel registration

def get_persistence_subsystem(kernel_instance):
    return PersistenceManager(kernel_instance)

def register_persistence_subsystem():
    kernel.register_subsystem(PersistenceManager)
    logger.info("[persistence] Persistence subsystem registered with VIT Kernel.")
