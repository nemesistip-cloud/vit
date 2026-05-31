from pathlib import Path


def test_env_example_includes_required_runtime_variables():
    required = {
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "ADMIN_EMAIL",
        "ADMIN_PASSWORD",
        "ADMIN_USERNAME",
        "API_KEY",
        "AUTH_ENABLED",
        "BACKGROUND_TASK_CHECK_INTERVAL_SECONDS",
        "BACKGROUND_TASK_MAX_RESTARTS",
        "CORS_ALLOWED_ORIGINS",
        "JWT_SECRET_KEY",
        "SECRET_KEY",
        "VIT_DATABASE_URL",
        "FOOTBALL_DATA_API_KEY",
        "THE_ODDS_API_KEY",
        "PAYSTACK_SECRET_KEY",
        "STRIPE_SECRET_KEY",
        "VITE_API_URL",
    }

    entries = {
        line.split("=", 1)[0]
        for line in Path(".env.example").read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    }

    assert required.issubset(entries)