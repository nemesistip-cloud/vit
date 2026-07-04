import re

with open('app/modules/notifications/routes.py', 'r') as f:
    content = f.read()

# Add PushSubscription schema
schema_block = """
class PushSubscriptionRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
"""

content = content.replace('class ManualChatIdBody(BaseModel):', schema_block + '\nclass ManualChatIdBody(BaseModel):')

# Add POST /push/subscribe endpoint
push_route = """
@router.post("/push/subscribe", summary="Register for Web Push notifications")
async def subscribe_push(
    body: PushSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    \"\"\"Save a Web Push subscription for the current user.\"\"\"
    from app.modules.notifications.models import PushSubscription
    from sqlalchemy import delete

    # Remove any existing subscription with the same endpoint
    await db.execute(delete(PushSubscription).where(PushSubscription.endpoint == body.endpoint))

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=body.endpoint,
        p256dh=body.p256dh,
        auth=body.auth
    )
    db.add(sub)
    await db.commit()

    return {"status": "success", "message": "Push subscription registered"}

@router.post("/push/unsubscribe", summary="Unsubscribe from Web Push")
async def unsubscribe_push(
    endpoint: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    \"\"\"Remove a Web Push subscription.\"\"\"
    from app.modules.notifications.models import PushSubscription
    from sqlalchemy import delete

    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == current_user.id
        )
    )
    await db.commit()
    return {"status": "success"}
"""

content = content.replace('@router.get("", summary="List notifications")', push_route + '\n@router.get("", summary="List notifications")')

with open('app/modules/notifications/routes.py', 'w') as f:
    f.write(content)
