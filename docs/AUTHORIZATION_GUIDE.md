# VIT Authorization & Policy Engine (v4.0)

## 1. Overview
The VIT Authorization & Policy Engine is the centralized authority for access control across the ecosystem. It provides a hybrid RBAC (Role-Based Access Control) and ABAC (Attribute-Based Access Control) framework.

## 2. Architecture
- **AuthorizationManager**: Primary entry point for permission checks.
- **PolicyEngine**: Orchestrates decision making.
- **PolicyEvaluator**: Handles pattern matching and attribute evaluation.
- **Registries**: Centralized discovery of Roles, Permissions, and Resources.

## 3. RBAC Guide
Roles are hierarchical and grant sets of permissions.
Built-in roles:
- `super_admin`: Full platform control.
- `institution_admin`: Management of institutional resources.
- `moderator`: Content and user moderation.
- `validator`: Network node validator.
- `standard_user`: Regular platform user.

## 4. ABAC Guide
Policies allow for fine-grained, conditional access control based on attributes.
Example Policy (JSON):
```json
{
  "name": "Elite Access Only",
  "effect": "allow",
  "action_pattern": "ai.model.train",
  "resource_pattern": "*",
  "conditions": {
    "attr": "user.tier",
    "op": "eq",
    "value": "elite"
  }
}
```

## 5. Permission Catalogue
- `wallet.read`: View balance.
- `wallet.transfer`: Move funds.
- `ai.model.train`: Trigger training.
- `governance.vote`: Participate in voting.
- `admin.users.manage`: User administration.

## 6. Integration Guide
Use the `require_permission` dependency in FastAPI:
```python
@router.post("/train")
async def train_model(user = Depends(require_permission("ai.model.train"))):
    ...
```
