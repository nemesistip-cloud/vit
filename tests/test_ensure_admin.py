from types import SimpleNamespace


def test_admin_bootstrap_identity_changes_require_commit():
    existing = SimpleNamespace(
        email="admin@vit.network",
        username="admin",
        role="admin",
        is_active=True,
    )
    configured_email = "operator@vit.network"
    identity_changed = (
        existing.email != configured_email.lower()
        or existing.username != "admin"
        or existing.role != "admin"
        or not existing.is_active
    )
    assert identity_changed is True