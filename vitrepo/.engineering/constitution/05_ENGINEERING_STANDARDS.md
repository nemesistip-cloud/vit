# 05 Engineering Standards

## 1. Code Style & Patterns
- **Async First**: Use `async/await` for all I/O bound operations.
- **Naming Conventions**:
  - **Python**: `snake_case` for variables, functions, and files. `PascalCase` for classes.
  - **JS/TS**: `camelCase` for variables and functions. `PascalCase` for components and classes. `kebab-case` for CSS classes.
- **Explicit Imports**: Always use named exports in TypeScript and specific imports in Python.
- **Guard Clauses**: Use `getattr` guards and safe defaults (e.g., 0.0, empty lists) for optional data. Prefere early returns over nested `if` blocks.
- **Idempotency**: All financial and state-changing logic MUST be idempotent. Use `idempotency_key` for critical transactions.

## 2. Technical Debt Management
- **TODOs**: All `TODO` and `FIXME` comments MUST include a link to a Track or Issue (e.g., `TODO(TRACK-015): Refactor logic`).
- **Deprecation**: Deprecated code MUST be marked with the `@deprecated` decorator/comment and scheduled for removal in the next major version.
- **Refactoring**: 20% of every Track's capacity SHOULD be allocated to paying down technical debt within the targeted domain.

## 3. Frontend Standards
- **Institutional OS UI**: Deep charcoal background (#0C0E12), Electric Cyan (#00F5FF) accents.
- **Typography**: JetBrains Mono for all numeric metrics.
- **Spacing**: 8pt grid system.
- **Precision**: 1px borders (white/5), `rounded-sm` corners.
- **Components**: Use standardized UI primitives (Card, Button, Badge) from `InstitutionalUI.tsx`.

## 4. Python Standards
- **Configuration**: Use `app/config.py` as the single source of truth for environment variables.
- **Database**: Use `AsyncSessionLocal` from `app/db/database.py`.
- **Typing**: Use type hints for ALL function signatures.

## 5. Agent Execution Protocol
- All agents MUST follow the rules in this constitution.
- Every modification MUST be verified using read-only tools.
- Before submission, `pre_commit_instructions` MUST be followed.
