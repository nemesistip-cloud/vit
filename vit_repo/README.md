# VIT Sports Intelligence Network

FastAPI + React football prediction platform with admin-managed API keys, model upload, CLV tracking, bankroll reporting, and Colab training assets.

## Local setup

1. Copy `.env.example` to `.env`.
2. Set `AUTH_ENABLED=true`, `API_KEY`, and `SESSION_SECRET`.
3. Install backend packages with `pip install -r requirements.txt`.
4. Run `./scripts/start_backend.sh`.
5. Run frontend separately with `./scripts/start_frontend.sh`.

Enter the admin key in the top bar. Use Admin > API Key Management to update Football Data, Odds API, Telegram, and AI provider keys.

## Colab training

Upload `colab/train_real_match_models.py` to Colab, provide `/content/historical_matches.csv` with columns `home_team`, `away_team`, `home_goals`, `away_goals`, run it, then download `/content/vit_training_output/vit_models.zip`. Upload that zip in Admin > Model Weights Upload.

## GitHub readiness

Generated files, local secrets, databases, Python caches, model weights, and frontend build outputs are ignored. Commit source files, `requirements.txt`, `.env.example`, scripts, and the Colab trainer.
