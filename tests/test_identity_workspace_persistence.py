import pytest


@pytest.mark.asyncio
async def test_identity_organization_and_workspace_persistence(client, auth_headers):
    headers = auth_headers

    create_org = await client.post(
        "/api/identity/organizations",
        headers=headers,
        json={"name": "Research Lab", "slug": "research-lab"},
    )
    assert create_org.status_code == 201, create_org.text
    org = create_org.json()
    assert org["name"] == "Research Lab"
    assert org["slug"] == "research-lab"

    list_orgs = await client.get("/api/identity/organizations", headers=headers)
    assert list_orgs.status_code == 200, list_orgs.text
    orgs_payload = list_orgs.json()
    assert any(item["slug"] == "research-lab" for item in orgs_payload["items"])

    workspace_save = await client.post(
        "/api/identity/me/workspace",
        headers=headers,
        json={
            "key": "dashboard.layout",
            "value": {"widgets": ["overview", "recommendations"], "theme": "dark"},
        },
    )
    assert workspace_save.status_code == 200, workspace_save.text
    saved = workspace_save.json()
    assert saved["key"] == "dashboard.layout"

    workspace_get = await client.get("/api/identity/me/workspace", headers=headers)
    assert workspace_get.status_code == 200, workspace_get.text
    workspace_payload = workspace_get.json()
    assert any(item["key"] == "dashboard.layout" for item in workspace_payload["items"])


@pytest.mark.asyncio
async def test_rbac_assignment_flow(db_session):
    from app.db.models import User
    from app.modules.authz.models import Permission, Role
    from app.modules.authz.service import AuthorizationService

    user = User(email="rbac@example.com", username="rbac_user", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    role = await AuthorizationService.create_custom_role(db_session, "editor", "Editor")
    permission = Permission(slug="workspace.write", description="Write workspace state")
    db_session.add(permission)
    await db_session.flush()

    await AuthorizationService.grant_permission_to_role(db_session, role.slug, permission.slug)
    await AuthorizationService.assign_role_to_user(db_session, user.id, role.slug)

    await db_session.refresh(user)
    assert user.id is not None
