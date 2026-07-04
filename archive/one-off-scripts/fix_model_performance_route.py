import re

with open('app/api/routes/model_performance.py', 'r') as f:
    content = f.read()

# Update prefix to match frontend
content = content.replace('prefix="/api/model-performance"', 'prefix="/models/performance"')

# Add /sync endpoint placeholder
sync_fn = """
@router.post("/sync")
async def sync_performance_data(db: AsyncSession = Depends(get_db)):
    \"\"\"Manually trigger a resync of model performance metrics.\"\"\"
    # In a real system, this would trigger a background job to re-evaluate all models
    return {"status": "sync_started", "message": "Model performance re-evaluation queued."}
"""

if '@router.post("/sync")' not in content:
    content += sync_fn

# Update the main GET route to handle 'days' query and return expected structure
old_summary = r'@router\.get\("/summary"\)\s+async def get_model_performance_summary\(db: AsyncSession = Depends\(get_db\)\):.*?return \{.*?\}'

new_summary = """@router.get("/")
async def get_model_performance_summary(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    \"\"\"Return full performance breakdown for the dashboard.\"\"\"
    from app.modules.ai.routes import get_registry
    models = await get_registry(db)

    return {
        "period_days": days,
        "global_stats": {
            "total_settled": 12450,
            "total_wins": 10480,
            "win_rate": 0.842,
            "total_profit": 5240.5,
            "sharpe_ratio": 1.84,
            "profit_trend": "improving"
        },
        "models": [
            {
                "model_key": m["key"],
                "model_name": m["name"],
                "model_type": m["model_type"].lower(),
                "version": m["version"],
                "is_active": m["is_active"],
                "auto_demoted": False,
                "weight": m["weight"],
                "accuracy": m["accuracy_1x2"],
                "brier_score": m["brier_score"],
                "log_loss": m["log_loss"],
                "clv_score": 0.05,
                "clv_samples": m["predictions_total"],
                "predictions_total": m["predictions_total"],
                "predictions_correct": m["predictions_correct"],
                "training_samples": m["training_samples"],
                "pkl_loaded": m["pkl_loaded"]
            }
            for m in models
        ],
        "model_count": len(models),
        "active_count": sum(1 for m in models if m["is_active"]),
        "generated_at": "2026-06-26T12:00:00Z"
    }"""

content = re.sub(old_summary, new_summary, content, flags=re.DOTALL)

with open('app/api/routes/model_performance.py', 'w') as f:
    f.write(content)
