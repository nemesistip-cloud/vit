import os


def test_load_runtime_env_reads_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("REDIS_URL=redis://example:6379/0\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REDIS_URL", raising=False)

    from app.config import load_runtime_env

    load_runtime_env()

    assert os.getenv("REDIS_URL") == "redis://example:6379/0"
