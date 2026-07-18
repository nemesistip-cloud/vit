import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class PermissionDefinition:
    slug: str
    description: str
    category: str

@dataclass
class RoleDefinition:
    slug: str
    name: str
    description: str
    default_permissions: List[str] = field(default_factory=list)
    parent_role: Optional[str] = None

class PermissionRegistry:
    """Central registry for all discoverable system permissions."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PermissionRegistry, cls).__new__(cls)
            cls._instance._permissions: Dict[str, PermissionDefinition] = {}
        return cls._instance

    def register(self, slug: str, description: str, category: str):
        if slug in self._permissions:
            # Idempotent: skip silent re-registration (modules may import this
            # multiple times during startup). No warning needed.
            return
        self._permissions[slug] = PermissionDefinition(slug, description, category)
        logger.debug(f"[authz] Registered permission: {slug}")

    def get_all(self) -> List[PermissionDefinition]:
        return list(self._permissions.values())

    def exists(self, slug: str) -> bool:
        return slug in self._permissions

class RoleRegistry:
    """Registry for built-in system roles and their hierarchies."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoleRegistry, cls).__new__(cls)
            cls._instance._roles: Dict[str, RoleDefinition] = {}
        return cls._instance

    def register_role(self, slug: str, name: str, description: str,
                      default_permissions: List[str] = None,
                      parent_role: str = None):
        self._roles[slug] = RoleDefinition(
            slug=slug,
            name=name,
            description=description,
            default_permissions=default_permissions or [],
            parent_role=parent_role
        )
        logger.debug(f"[authz] Registered role definition: {slug}")

    def get_role(self, slug: str) -> Optional[RoleDefinition]:
        return self._roles.get(slug)

    def get_all_builtins(self) -> List[RoleDefinition]:
        return list(self._roles.values())

@dataclass
class ResourceDefinition:
    slug: str
    type: str
    description: str

class ResourceRegistry:
    """Registry for securable system resources."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceRegistry, cls).__new__(cls)
            cls._instance._resources: Dict[str, ResourceDefinition] = {}
        return cls._instance

    def register(self, slug: str, type: str, description: str):
        self._resources[slug] = ResourceDefinition(slug, type, description)
        logger.debug(f"[authz] Registered resource: {slug}")

    def get_all(self) -> List[ResourceDefinition]:
        return list(self._resources.values())

# Global Instances
permission_registry = PermissionRegistry()
role_registry = RoleRegistry()
resource_registry = ResourceRegistry()

def initialize_registries():
    """Seed the registries with built-in VIT roles and permissions."""

    # 1. Register Permissions
    perms = [
        # Wallet
        ("wallet.read", "View wallet balance and history", "wallet"),
        ("wallet.transfer", "Perform transfers", "wallet"),
        ("wallet.freeze", "Freeze wallet assets", "wallet"),
        ("wallet.audit", "Audit wallet transactions", "wallet"),

        # Governance
        ("governance.vote", "Vote on proposals", "governance"),
        ("governance.proposal.create", "Create new proposals", "governance"),
        ("governance.proposal.approve", "Approve proposals", "governance"),
        ("governance.proposal.execute", "Execute approved proposals", "governance"),

        # AI
        ("ai.model.deploy", "Deploy AI models", "ai"),
        ("ai.model.train", "Trigger model training", "ai"),
        ("ai.model.delete", "Remove AI models", "ai"),
        ("ai.analytics.view", "View AI performance analytics", "ai"),

        # Marketplace
        ("marketplace.product.create", "Create products", "marketplace"),
        ("marketplace.product.publish", "Publish products to store", "marketplace"),
        ("marketplace.product.manage", "Manage existing products", "marketplace"),

        # Admin
        ("admin.users.manage", "Full user management", "admin"),
        ("admin.system.config", "Manage platform configuration", "admin"),
        ("admin.access", "General admin panel access", "admin"),
        ("admin.super", "Full super admin access", "admin"),

        # Research & Education
        ("research.report.create", "Create research reports", "research"),
        ("research.data.access", "Access raw research data", "research"),
        ("student.campus.access", "Access campus resources", "education"),
    ]
    for slug, desc, cat in perms:
        permission_registry.register(slug, desc, cat)

    # 2. Register Resources
    resources = [
        ("wallet", "service", "VIT Wallet Service"),
        ("governance", "service", "VIT Governance Protocol"),
        ("ai_model", "entity", "AI Intelligence Model"),
        ("marketplace", "service", "Institutional Marketplace"),
        ("user", "entity", "System User Profile"),
        ("system_config", "entity", "Platform Configuration"),
    ]
    for slug, type, desc in resources:
        resource_registry.register(slug, type, desc)

    # 3. Register Roles
    role_registry.register_role(
        "super_admin", "Super Administrator", "Full platform control",
        default_permissions=[p[0] for p in perms]
    )

    role_registry.register_role(
        "institution_admin", "Institution Administrator", "Manage institutional resources",
        default_permissions=["admin.users.manage", "wallet.read", "ai.analytics.view"]
    )

    role_registry.register_role(
        "moderator", "Moderator", "Content and user moderation",
        default_permissions=["admin.users.manage", "admin.access"]
    )

    role_registry.register_role(
        "validator", "Validator", "Network node validator",
        default_permissions=["governance.vote", "wallet.read"]
    )

    role_registry.register_role(
        "treasury_operator", "Treasury Operator", "Manage platform treasury",
        default_permissions=["wallet.read", "wallet.transfer", "wallet.audit"]
    )

    role_registry.register_role(
        "ai_operator", "AI Operator", "Manage AI models and training",
        default_permissions=["ai.model.deploy", "ai.model.train", "ai.analytics.view"]
    )

    role_registry.register_role(
        "marketplace_manager", "Marketplace Manager", "Manage marketplace listings",
        default_permissions=["marketplace.product.manage", "marketplace.product.publish"]
    )

    role_registry.register_role(
        "merchant", "Merchant", "Sell products on marketplace",
        default_permissions=["marketplace.product.create", "wallet.read"]
    )

    role_registry.register_role(
        "researcher", "Researcher", "Access research data and create reports",
        default_permissions=["research.report.create", "research.data.access", "wallet.read"]
    )

    role_registry.register_role(
        "student", "Student", "Access educational resources",
        default_permissions=["student.campus.access", "wallet.read"]
    )

    role_registry.register_role(
        "standard_user", "Standard User", "Regular user",
        default_permissions=["wallet.read", "wallet.transfer"]
    )

    role_registry.register_role(
        "service_account", "Service Account", "System level access",
        default_permissions=["wallet.read", "ai.model.train", "admin.system.config"]
    )

initialize_registries()
