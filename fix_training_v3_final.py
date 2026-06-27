import re

with open('app/api/routes/training.py', 'r') as f:
    content = f.read()

# Fix Sequential tachyon upload in _run_training_body
old_sequential_block = r'async def _tachyon_upload_sequential\(key_path_pairs: list\):.*?logger\.error\(f"\[tachyon\] failed to queue upload task: \{_te\}"\)'

new_sequential_block = """        async def _tachyon_upload_sequential(key_path_pairs: list):
            index_path = os.path.join(_MODELS_DIR, "tachyon_index.json")
            try:
                import json as _json
                if os.path.exists(index_path):
                    with open(index_path) as _f:
                        _idx = _json.load(_f)
                else:
                    _idx = {}
            except Exception:
                _idx = {}

            for mkey, p in key_path_pairs:
                try:
                    fid = await tachyon_client.upload_model(p)
                    if fid:
                        if not mkey.endswith("_archive"):
                            _idx[mkey] = fid
                        logger.info("[tachyon] uploaded %s → model_key=%s file_id=%s", os.path.basename(p), mkey, fid)
                    else:
                        logger.warning("[tachyon] upload returned None for %s", os.path.basename(p))
                except Exception as _te:
                    logger.error("[tachyon] upload failed for %s: %s", os.path.basename(p), _te)
                await asyncio.sleep(0.5)

            try:
                import json as _json
                os.makedirs(_MODELS_DIR, exist_ok=True)
                with open(index_path, "w") as _f:
                    _idx_data = {k: v for k, v in _idx.items() if not k.endswith("_archive")}
                    _json.dump(_idx_data, _f)
                logger.info("[tachyon] index updated: %d model(s) mapped", len(_idx_data))
            except Exception as _ie:
                logger.error("[tachyon] failed to write tachyon_index.json: %s", _ie)

        all_pkl_pairs = list(_active_pkl_map.items())
        for mkey, info in saved_pkls.items():
            arc_fname = info.get("archive")
            if arc_fname:
                p = os.path.join(_MODELS_DIR, arc_fname)
                if os.path.exists(p):
                    all_pkl_pairs.append((f"{mkey}_archive", p))

        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_tachyon_upload_sequential(all_pkl_pairs))
            logger.info("[tachyon] queued sequential upload of %d pkl files", len(all_pkl_pairs))
        except Exception as _te:
            logger.error(f"[tachyon] failed to queue upload task: {_te}")"""

content = re.sub(old_sequential_block, new_sequential_block, content, flags=re.DOTALL)

with open('app/api/routes/training.py', 'w') as f:
    f.write(content)
