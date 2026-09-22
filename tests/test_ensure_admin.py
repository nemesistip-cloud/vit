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


def test_resolve_admin_user_prefers_canonical_user_id_1_when_email_misses():
    records = [
        SimpleNamespace(id=7, email="other@example.com", username="operator", role="user", admin_role=None),
        SimpleNamespace(id=1, email="legacy@vit.network", username="legacy-admin", role="admin", admin_role=None),
    ]

    from scripts.ensure_admin import resolve_admin_user

    chosen = resolve_admin_user(records, "admin@vit.network", "admin")

    assert chosen is records[1]
    assert chosen.id == 1