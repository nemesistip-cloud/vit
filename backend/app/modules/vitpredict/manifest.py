"""VITPredict's application identity and least-privilege service contract."""

from vit_protocol.application import ApplicationManifest, validate_manifest


def vitpredict_manifest() -> ApplicationManifest:
    return validate_manifest(
        ApplicationManifest(
            app_id="app:vitpredict",
            developer_id="dev:vit-core",
            version="1.0.0",
            account_id="acct:vitpredict",
            permissions=(
                "identity.read",
                "sports.read",
                "odds.read",
                "prediction.read",
                "prediction.generate",
                "prediction.history.read",
                "prediction.attest",
                "models.evaluate",
            ),
            dependencies={"identity": "1", "gateway": "1", "ai": "1"},
            resource_limits={"requests_per_minute": 120, "predictions_per_day": 20},
            status="active",
        )
    )