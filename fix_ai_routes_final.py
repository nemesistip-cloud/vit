import re
import os

with open('app/modules/ai/routes.py', 'r') as f:
    content = f.read()

# 1. Fix upload_pkl redundant joblib load and len(content) -> len(data)
# Also fix the check for existing version
upload_pattern = r'(data = await file\.read\(\)\s+try:\s+import joblib\s+import io\s+payload = joblib\.load\(io\.BytesIO\(data\)\)\s+)payload = joblib\.load\(staged_path\)'
content = re.sub(upload_pattern, r'\1', content)
content = content.replace('len(content)', 'len(data)')

# 2. Fix the dest_path local exists check to check version_history instead
content = content.replace('if os.path.exists(dest_path):', 'if any(h.get("version") == version for h in (row.version_history or [])):')

# 3. Fix promote_version artifact check
old_promote_check = r'pkl_path = target\.get\("pkl_path"\)\s+if not pkl_path or not os\.path\.exists\(pkl_path\):\s+raise HTTPException\(\s+status_code=410,\s+detail=f"Artifact for version \'{version}\' is missing on disk: \{pkl_path\}"\s+\)'

new_promote_check = """    pkl_path = target.get("pkl_path")
    if not pkl_path:
        raise HTTPException(status_code=410, detail="Artifact path is missing")
    if pkl_path.startswith("/") and not os.path.exists(pkl_path):
        raise HTTPException(status_code=410, detail=f"Local artifact missing: {pkl_path}")"""

content = re.sub(old_promote_check, new_promote_check, content)

# 4. Add index update logic after db.commit() in promote_version
# We need to find the specific await db.commit() inside promote_version
promote_start = content.find('async def promote_version')
commit_pos = content.find('await db.commit()', promote_start)

if promote_start != -1 and commit_pos != -1:
    index_logic = """
    # Update tachyon_index.json for the model loader
    if pkl_path.startswith("tachyon://"):
        try:
            fid = pkl_path.replace("tachyon://", "")
            index_path = os.path.join(MODELS_DIR, "tachyon_index.json")
            import json
            idx = {}
            if os.path.exists(index_path):
                with open(index_path) as f:
                    idx = json.load(f)
            idx[key] = fid
            os.makedirs(MODELS_DIR, exist_ok=True)
            with open(index_path, "w") as f:
                json.dump(idx, f)
            logger.info(f"[tachyon] Updated index for {key} -> {fid}")
        except Exception as e:
            logger.error(f"Failed to update tachyon_index.json: {e}")
"""
    # Insert after the commit
    content = content[:commit_pos + 17] + index_logic + content[commit_pos + 17:]

with open('app/modules/ai/routes.py', 'w') as f:
    f.write(content)
