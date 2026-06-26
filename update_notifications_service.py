import re

with open('app/modules/notifications/service.py', 'r') as f:
    content = f.read()

# Add push notification dispatch to _dispatch_external
push_dispatch = """
            # ── Web Push ───────────────────────────────────────────────────
            try:
                from app.services.push_service import PushService
                await PushService.notify_user(
                    db=db,
                    user_id=user_id,
                    title=title,
                    body=body,
                    data={"type": ntype_str}
                )
            except Exception as exc:
                logger.warning(f"Web Push dispatch failed for user {user_id}: {exc}")
"""

content = content.replace('# ── Telegram ───────────────────────────────────────────────────',
                          push_dispatch + '\n            # ── Telegram ───────────────────────────────────────────────────')

with open('app/modules/notifications/service.py', 'w') as f:
    f.write(content)
