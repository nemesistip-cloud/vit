# app/core/roles.py — VIT Network RBAC Role & Permission Definitions
from enum import Enum
from typing import List


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    AUDITOR = "auditor"
    SUPPORT = "support"


class SubscriptionTier(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    PRO = "pro"
    ELITE = "elite"


class Permission(str, Enum):
    # User management
    VIEW_USERS = "users:view"
    CREATE_USERS = "users:create"
    EDIT_USERS = "users:edit"
    DELETE_USERS = "users:delete"
    BAN_USERS = "users:ban"
    CHANGE_ROLES = "users:roles"
    RESET_PASSWORDS = "users:passwords"
    VIEW_USER_PNL = "users:pnl"

    # Financial
    VIEW_TRANSACTIONS = "finance:view"
    PROCESS_WITHDRAWALS = "finance:withdraw"
    ADJUST_BALANCES = "finance:adjust"
    CONFIGURE_RATES = "finance:rates"
    VIEW_PLATFORM_PNL = "finance:platform_pnl"

    # Subscriptions
    VIEW_PLANS = "subscriptions:view"
    EDIT_PLANS = "subscriptions:edit"
    DELETE_PLANS = "subscriptions:delete"
    MANUAL_OVERRIDE = "subscriptions:override"
    CANCEL_SUBSCRIPTIONS = "subscriptions:cancel"

    # Leagues & Markets
    VIEW_CONFIG = "config:view"
    EDIT_CONFIG = "config:edit"
    IMPORT_DATA = "config:import"

    # ML & Training
    VIEW_MODELS = "ml:view"
    TRAIN_MODELS = "ml:train"
    UPLOAD_WEIGHTS = "ml:upload"
    CONFIGURE_TRAINING = "ml:configure"

    # System
    MANAGE_FEATURE_FLAGS = "system:flags"
    MANAGE_API_KEYS = "system:apikeys"
    VIEW_AUDIT_LOGS = "system:audit"
    EXPORT_AUDIT_LOGS = "system:audit_export"
    MAINTENANCE_MODE = "system:maintenance"
    DB_BACKUP = "system:backup"
    CLEAR_CACHE = "system:cache"

    # Dashboard
    VIEW_DASHBOARD = "dashboard:view"
    VIEW_REVENUE = "dashboard:revenue"
    VIEW_SYSTEM_HEALTH = "dashboard:health"


# ── Permission matrices per admin role ────────────────────────────────

SUPER_ADMIN_PERMISSIONS: List[Permission] = list(Permission)

ADMIN_PERMISSIONS: List[Permission] = [
    Permission.VIEW_DASHBOARD, Permission.VIEW_REVENUE, Permission.VIEW_SYSTEM_HEALTH,
    Permission.VIEW_USERS, Permission.CREATE_USERS, Permission.EDIT_USERS,
    Permission.BAN_USERS, Permission.CHANGE_ROLES, Permission.RESET_PASSWORDS,
    Permission.VIEW_USER_PNL,
    Permission.VIEW_TRANSACTIONS, Permission.PROCESS_WITHDRAWALS,
    Permission.CONFIGURE_RATES, Permission.VIEW_PLATFORM_PNL,
    Permission.VIEW_PLANS, Permission.EDIT_PLANS, Permission.MANUAL_OVERRIDE,
    Permission.CANCEL_SUBSCRIPTIONS,
    Permission.VIEW_CONFIG, Permission.EDIT_CONFIG, Permission.IMPORT_DATA,
    Permission.VIEW_MODELS, Permission.TRAIN_MODELS, Permission.UPLOAD_WEIGHTS,
    Permission.CONFIGURE_TRAINING,
    Permission.MANAGE_FEATURE_FLAGS, Permission.MANAGE_API_KEYS,
    Permission.VIEW_AUDIT_LOGS, Permission.EXPORT_AUDIT_LOGS,
    Permission.CLEAR_CACHE,
]

AUDITOR_PERMISSIONS: List[Permission] = [
    Permission.VIEW_DASHBOARD, Permission.VIEW_REVENUE, Permission.VIEW_SYSTEM_HEALTH,
    Permission.VIEW_USERS, Permission.VIEW_USER_PNL,
    Permission.VIEW_TRANSACTIONS, Permission.VIEW_PLATFORM_PNL,
    Permission.VIEW_PLANS,
    Permission.VIEW_CONFIG,
    Permission.VIEW_MODELS,
    Permission.VIEW_AUDIT_LOGS, Permission.EXPORT_AUDIT_LOGS,
]

SUPPORT_PERMISSIONS: List[Permission] = [
    Permission.VIEW_DASHBOARD, Permission.VIEW_SYSTEM_HEALTH,
    Permission.VIEW_USERS, Permission.RESET_PASSWORDS, Permission.VIEW_USER_PNL,
    Permission.VIEW_TRANSACTIONS,
    Permission.VIEW_PLANS, Permission.MANUAL_OVERRIDE,
    Permission.CANCEL_SUBSCRIPTIONS,
]

ROLE_PERMISSIONS: dict[AdminRole, List[Permission]] = {
    AdminRole.SUPER_ADMIN: SUPER_ADMIN_PERMISSIONS,
    AdminRole.ADMIN: ADMIN_PERMISSIONS,
    AdminRole.AUDITOR: AUDITOR_PERMISSIONS,
    AdminRole.SUPPORT: SUPPORT_PERMISSIONS,
}


# ── Subscription tier limits ──────────────────────────────────────────

TIER_LIMITS: dict[SubscriptionTier, dict] = {
    SubscriptionTier.VIEWER: {
        "daily_predictions": 5,
        "min_stake": 5,
        "max_stake": 100,
        "markets": ["1x2", "over_under", "btts"],
        "leagues": "top5",
        "live_odds": False,
        "ai_insights": False,
        "analytics": False,
        "api_access": False,
        "validator_status": False,
        "revenue_share": False,
    },
    SubscriptionTier.ANALYST: {
        "daily_predictions": 25,
        "min_stake": 5,
        "max_stake": 250,
        "markets": ["1x2", "over_under", "btts", "double_chance"],
        "leagues": "top10",
        "live_odds": True,
        "ai_insights": False,
        "analytics": True,
        "api_access": False,
        "validator_status": False,
        "revenue_share": False,
    },
    SubscriptionTier.PRO: {
        "daily_predictions": None,
        "min_stake": 1,
        "max_stake": 1000,
        "markets": ["1x2", "over_under", "btts", "double_chance", "draw_no_bet"],
        "leagues": "all",
        "live_odds": True,
        "ai_insights": True,
        "analytics": True,
        "api_access": True,
        "validator_status": False,
        "revenue_share": False,
    },
    SubscriptionTier.ELITE: {
        "daily_predictions": None,
        "min_stake": 1,
        "max_stake": 5000,
        "markets": ["1x2", "over_under", "btts", "double_chance", "draw_no_bet",
                    "asian_handicap", "correct_score", "half_time_full_time", "first_goal_scorer"],
        "leagues": "all",
        "live_odds": True,
        "ai_insights": True,
        "analytics": True,
        "api_access": True,
        "validator_status": True,
        "revenue_share": True,
    },
}


def get_permissions_for_admin_role(admin_role: str) -> List[str]:
    """Return permission strings for the given admin role name."""
    try:
        role = AdminRole(admin_role)
        return [p.value for p in ROLE_PERMISSIONS.get(role, [])]
    except ValueError:
        return []


def has_permission(admin_role: str, permission: Permission) -> bool:
    """Check if an admin role has a specific permission."""
    perms = get_permissions_for_admin_role(admin_role)
    return permission.value in perms
