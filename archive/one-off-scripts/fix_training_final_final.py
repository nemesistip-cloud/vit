import re

with open('app/api/routes/training.py', 'r') as f:
    content = f.read()

# Fix clear_training_dataset
content = re.sub(
    r'async def clear_training_dataset\(api_key: Optional\[str\] = Query\(default=None\)\):.*?return \{"success": True, "message": "historical_matches\.json cleared"\}',
    'async def clear_training_dataset(api_key: Optional[str] = Query(default=None)):\n    """Clear the historical_matches.json dataset (admin only)."""\n    _verify_key(api_key)\n    await set_config_value("training_dataset_file_id", None)\n    return {"success": True, "message": "historical_matches.json cleared from Tachyon"}',
    content,
    flags=re.DOTALL
)

# Fix compare_models
content = re.sub(
    r'async def compare_models\(api_key: Optional\[str\] = Query\(default=None\)\):.*?metrics = json\.load\(f\).*?except Exception as e:.*?raise HTTPException\(status_code=500, detail=f"Failed to read metrics: \{e\}"\)',
    'async def compare_models(api_key: Optional[str] = Query(default=None)):\n    """Compare model performance metrics from training metrics file."""\n    _verify_key(api_key)\n\n    metrics = await _get_tachyon_json("training_metrics_file_id")\n    if metrics is None:\n        return {"models": [], "message": "No training metrics available yet"}',
    content,
    flags=re.DOTALL
)

with open('app/api/routes/training.py', 'w') as f:
    f.write(content)
