import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.models import User
from app.modules.ai.models import ModelMetadata
from app.api.dependencies.admin import require_admin
from app.db.database import get_db

@pytest.fixture
async def override_admin_auth():
    admin_user = User(id=1, email="admin@vit.network", role="admin")
    app.dependency_overrides[require_admin] = lambda: admin_user

    async for db in get_db():
        m = ModelMetadata(key="xgb_match", name="XGBoost Match Predictor", model_type="xgb", is_active=True)
        db.add(m)
        await db.commit()
        break

    yield admin_user
    app.dependency_overrides.pop(require_admin, None)

@pytest.mark.asyncio
async def test_admin_training_jobs_lifecycle(override_admin_auth):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Trigger via POST /api/admin/training-jobs/trigger
        r0 = await client.post("/api/admin/training-jobs/trigger", json={})
        assert r0.status_code == 200, r0.text
        data0 = r0.json()
        assert data0["ok"] is True
        job_id0 = data0["job_id"]

        # 2. Trigger retrain all models
        r2 = await client.post("/api/admin/models/retrain-all")
        assert r2.status_code == 200, r2.text
        data2 = r2.json()
        assert data2["ok"] is True
        job_id2 = data2["job_id"]
        assert job_id2 is not None

        # 3. List training jobs
        r3 = await client.get("/api/admin/training-jobs")
        assert r3.status_code == 200, r3.text
        jobs_list = r3.json()["jobs"]
        job_ids = [j["job_id"] for j in jobs_list]
        assert job_id0 in job_ids
        assert job_id2 in job_ids

        # 4. Get job by string job_id
        r4 = await client.get(f"/api/admin/training-jobs/{job_id0}")
        assert r4.status_code == 200, r4.text
        detail0 = r4.json()
        assert detail0["job_id"] == job_id0
        assert "events" in detail0
        assert "config" in detail0

        # 5. Cancel running/queued job
        r5 = await client.post(f"/api/admin/training-jobs/{job_id2}/cancel")
        assert r5.status_code == 200, r5.text
        assert r5.json()["status"] == "cancelled"

        # 6. Verify job state changed to cancelled
        r6 = await client.get(f"/api/admin/training-jobs/{job_id2}")
        assert r6.status_code == 200, r6.text
        assert r6.json()["status"] == "cancelled"

        # 7. Delete cancelled job
        r7 = await client.delete(f"/api/admin/training-jobs/{job_id2}")
        assert r7.status_code == 200, r7.text
        assert r7.json()["ok"] is True

        # 8. Verify deletion
        r8 = await client.get(f"/api/admin/training-jobs/{job_id2}")
        assert r8.status_code == 404
