import sys
import os

path = 'tachyon/api/router.py'
with open(path, 'r') as f:
    content = f.read()

# Add necessary import
if 'from app.modules.storage_verification.service import register_content, submit_storage_proof' not in content:
    content = content.replace(
        'from app.modules.storage_verification.service import register_content',
        'from app.modules.storage_verification.service import register_content, submit_storage_proof'
    )

# Patch upload_file route
search_text = """    try:
        fragments = TachyonShredder.shred(content)
        qsh = TachyonShredder.get_fragment_hash(fragments[0]) if fragments else None
        await register_content(
            db=db,
            content_hash=file_hash,
            content_type=file.content_type or "application/octet-stream",
            description=f"Tachyon upload: {file.filename}",
            size_bytes=len(content),
            owner_user_id=user.id if user else None,
            is_tachyon=True,
            tachyon_shards=num_frags,
            tachyon_parity_shards=parity_shards,
            quantum_state_hash=qsh,
        )
    except Exception as exc:
        logger.error("[tachyon] content registry failed: %s", exc)"""

replace_text = """    try:
        fragments = TachyonShredder.shred(content)
        qsh = TachyonShredder.get_fragment_hash(fragments[0]) if fragments else None
        registry_entry = await register_content(
            db=db,
            content_hash=file_hash,
            content_type=file.content_type or "application/octet-stream",
            description=f"Tachyon upload: {file.filename}",
            size_bytes=len(content),
            owner_user_id=user.id if user else None,
            is_tachyon=True,
            tachyon_shards=num_frags,
            tachyon_parity_shards=parity_shards,
            quantum_state_hash=qsh,
        )

        # VESS Core: Auto-anchor every shard for verification
        if registry_entry and fragments:
            for i, frag in enumerate(fragments):
                try:
                    p_idx = i % len(_providers)
                    provider = _providers[p_idx]
                    frag_hash = TachyonShredder.get_fragment_hash(frag)
                    await submit_storage_proof(
                        db=db,
                        content_hash=file_hash,
                        node_address=f"{type(provider).__name__}:{provider.name}",
                        proof_data=frag_hash,
                        proof_type="tachyon_shard_qsh",
                        prover_user_id=user.id if user else None
                    )
                except Exception as e:
                    logger.warning("[tachyon] shard anchoring failed for index %d: %s", i, e)

    except Exception as exc:
        logger.error("[tachyon] content registry / anchoring failed: %s", exc)"""

if search_text in content:
    content = content.replace(search_text, replace_text)
    with open(path, 'w') as f:
        f.write(content)
    print("Patch applied successfully")
else:
    print("Search text not found")
