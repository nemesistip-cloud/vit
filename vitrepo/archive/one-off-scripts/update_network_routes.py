import re

with open('app/modules/network/routes.py', 'r') as f:
    content = f.read()

# Add JoinValidatorRequest schema
schema_block = """
class JoinValidatorRequest(BaseModel):
    wallet_address: str
    node_name: str
    provider: str = "custom"
    gb_contributed: float = 100.0
"""

content = content.replace('class NodeActivityRequest(BaseModel):', schema_block + '\nclass NodeActivityRequest(BaseModel):')

# Add POST /join endpoint
join_endpoint = """
@router.post("/join")
async def join_validator_network(
    body: JoinValidatorRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    \"\"\"Allow a user to join the validator network and register a storage node.\"\"\"
    from app.modules.storage_verification.models import UserStorageNode
    import uuid

    # Update user's wallet address and role
    current_user.wallet_address = body.wallet_address
    if current_user.role == "user":
        current_user.role = "validator"

    # Register the storage node
    config_key = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}"
    node = UserStorageNode(
        user_id=current_user.id,
        provider=body.provider,
        alias=body.node_name,
        config_key=config_key,
        status="active",
        gb_contributed=Decimal(str(body.gb_contributed)),
    )
    db.add(node)

    # Record initial activity
    activity = NodeActivity(
        node_id=config_key,
        node_name=body.node_name,
        node_type="storage",
        activity_type="validator_joined",
        contribution_score=10.0,
        activity_meta={"wallet": body.wallet_address}
    )
    db.add(activity)

    await db.commit()
    return {
        "status": "success",
        "message": f"Welcome to the VIT Validator network, {current_user.username}!",
        "node_id": config_key,
        "role": current_user.role
    }
"""

content = content.replace('@router.post("/activity")', join_endpoint + '\n@router.post("/activity")')

# Add missing imports if needed
if 'from app.auth.dependencies import get_current_user, get_current_admin' not in content:
    content = content.replace('from app.db.database import get_db', 'from app.db.database import get_db\nfrom app.auth.dependencies import get_current_user, get_current_admin')

with open('app/modules/network/routes.py', 'w') as f:
    f.write(content)
