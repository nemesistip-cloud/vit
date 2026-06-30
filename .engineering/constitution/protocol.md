# VIT Parallel Execution Protocol

## Rules for all Jules Agents

1. **No Cross-Domain File Editing**: Agents must only modify files within their assigned domain ownership.
2. **No Modification Outside Owned Domain**: Any changes required in another domain must be requested via contract updates or coordinated with the owner of that domain.
3. **No Changes to Contracts**: Interface contracts in `.engineering/contracts.json` cannot be modified without integration approval.
4. **Async Workflow Standard**: All asynchronous workflows must use the existing `app/tasks` system.
5. **Database Access Standard**: All database changes and access must go through the `app/db` module only.
6. **Financial Idempotency**: All financial logic must remain idempotent.
7. **Stateless APIs**: All APIs must be stateless.
8. **Integration Engine Exclusive**: Only the "INTEGRATION ENGINE" agent is allowed to modify `main.py`, cross-domain routing, and system wiring.

## Integration Rules
- Only ONE future agent is allowed to modify:
  - `main.py`
  - cross-domain routing
  - system wiring
- That agent is called: **INTEGRATION ENGINE**
