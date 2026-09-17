from pathlib import Path


def test_frontend_bundle_uses_manual_chunks():
    config_text = Path("frontend/vite.config.ts").read_text()
    assert "manualChunks" in config_text
    assert "react-vendor" in config_text
    assert "ui-vendor" in config_text
