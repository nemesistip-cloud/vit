## 2026-06-24 - Optimizing Render Free Tier Deployment

**Learning:** Render's Free Tier has strict RAM limits (512MB) and health check timeouts. Heavy ML libraries (sentence-transformers) and blocking bootstrap operations (migrations, seeding) frequently cause deployment failures if not managed. Background agents should be strictly offloaded to worker services in production, and bootstrap tasks should be delayed until the API is responsive.

**Action:** Always implement lazy loading for heavy ML models. Use `ENVIRONMENT=production` checks to disable non-essential background agents in the main API process. Move blocking bootstrap tasks to a delayed `asyncio.create_task` loop to ensure health checks pass.
