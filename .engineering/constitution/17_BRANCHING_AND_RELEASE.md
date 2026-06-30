# 17 Branching and Release

## 1. Branching Strategy
- `main`: Stable production branch. MUST always be deployable.
- `develop`: Integration branch for features (optional if using small PRs to main).
- `feature/TRACK-XXX-name`: Short-lived branches for specific Tracks.
- `bugfix/ISSUE-XXX-name`: For patching reported issues.
- `hotfix/name`: Critical production fixes.

## 2. Release Management
- **Versioning**: Use Semantic Versioning (SemVer) `MAJOR.MINOR.PATCH`.
- **Changelog**: Maintain a `CHANGELOG.md` in `docs/` or root, updated with every release.
- **Tags**: Every production deploy MUST be tagged in Git (e.g., `v1.2.0`).

## 3. Backward Compatibility & Deprecation
- **API**: Breaking changes in APIs MUST increment the Major version in the path (`/api/v1` -> `/api/v2`).
- **Database**: Schemas MUST support rolling updates (new code runs with old schema, and vice versa) where possible.
- **Deprecation Policy**:
  - Mark features as deprecated 1 minor version before removal.
  - Removal of deprecated code MUST only happen in MAJOR version increments.

## 4. Release Criteria
- All tests (Unit, Functional, E2E) MUST pass.
- No open CRITICAL or HIGH security vulnerabilities.
- Performance targets (latency/throughput) MUST be met.
- Documentation MUST be updated.
