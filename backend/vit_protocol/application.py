"""Validated application manifests for the VIT Developer Platform."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ApplicationManifestError(ValueError):
    """Raised when an application manifest violates the platform contract."""


@dataclass(frozen=True)
class ApplicationManifest:
    app_id: str
    developer_id: str
    version: str
    account_id: str
    permissions: tuple[str, ...]
    dependencies: dict[str, str]
    resource_limits: dict[str, int]
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "developer_id": self.developer_id,
            "version": self.version,
            "account_id": self.account_id,
            "permissions": list(self.permissions),
            "dependencies": dict(self.dependencies),
            "resource_limits": dict(self.resource_limits),
            "status": self.status,
        }


def validate_manifest(manifest: ApplicationManifest) -> ApplicationManifest:
    if not manifest.app_id.startswith("app:"):
        raise ApplicationManifestError("app_id must use the app: namespace")
    if not manifest.developer_id.startswith("dev:"):
        raise ApplicationManifestError("developer_id must use the dev: namespace")
    if not manifest.account_id.startswith("acct:"):
        raise ApplicationManifestError("account_id must use the acct: namespace")
    if not manifest.version or any(not part.isdigit() for part in manifest.version.split(".")):
        raise ApplicationManifestError("version must be numeric semver")
    if manifest.status not in {"draft", "active", "suspended", "retired"}:
        raise ApplicationManifestError("invalid application lifecycle status")
    if any(not permission or "." not in permission for permission in manifest.permissions):
        raise ApplicationManifestError("permissions must use a scoped name")
    if any(value < 0 for value in manifest.resource_limits.values()):
        raise ApplicationManifestError("resource limits cannot be negative")
    return manifest


def m24_reference_manifest() -> ApplicationManifest:
    """Reference manifest proving M24 uses shared platform capabilities."""
    return validate_manifest(
        ApplicationManifest(
            app_id="app:m24",
            developer_id="dev:vit-core",
            version="1.0.0",
            account_id="acct:m24",
            permissions=(
                "identity.read",
                "wallet.read",
                "wallet.transfer",
                "chain.read",
                "storage.read",
                "storage.write",
                "ai.infer",
                "events.subscribe",
                "proof.create",
                "proof.verify",
            ),
            dependencies={"chain": "7764", "ai": "1", "storage": "1", "registry": "2"},
            resource_limits={"requests_per_minute": 120, "storage_bytes": 10_000_000_000},
        )
    )
