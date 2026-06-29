# 05 Engineering Standards

## 1. Code Style & Patterns
- **Async First**: Use `async/await` for all I/O bound operations.
- **Explicit Imports**: Always use named exports in TypeScript and specific imports in Python.
- **Guard Clauses**: Use `getattr` guards and safe defaults (e.g., 0.0, empty lists) for optional data.
- **Idempotency**: All financial and state-changing logic must be idempotent.

## 2. Frontend Standards
- **Institutional OS UI**: Deep charcoal background (#0C0E12), Electric Cyan (#00F5FF) accents.
- **Typography**: JetBrains Mono for all numeric metrics.
- **Spacing**: 8pt grid system.
- **Precision**: 1px borders (white/5), `rounded-sm` corners.
- **Components**: Use standardized UI primitives (Card, Button, Badge) from `InstitutionalUI.tsx`.

## 3. Python Standards
- **Configuration**: Use `app/config.py` as the single source of truth for environment variables.
- **Database**: Use `AsyncSessionLocal` from `app/db/database.py`.
- **Typing**: Use type hints for all function signatures.

## 4. Agent Execution Protocol
- All agents must follow the rules in this constitution.
- Every modification must be verified using read-only tools.
- Before submission, `pre_commit_instructions` must be followed.
