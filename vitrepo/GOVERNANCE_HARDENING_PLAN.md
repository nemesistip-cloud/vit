# GOVERNANCE_HARDENING_PLAN.md

## 1. GitHub Configuration Audit

### A. Branch Protection (REQUIRED)
- **Rule**: `main` branch must require PRs with at least 1 approval.
- **Rule**: Require status checks (Test Pipeline) to pass before merging.
- **Rule**: Restrict deletions and force-pushes.

### B. CODEOWNERS
- **Status**: MISSING.
- **Action**: Create `.github/CODEOWNERS` to enforce domain ownership.
    - `/app/core/` -> @nemesistip-cloud (Platform Lead)
    - `/app/modules/blockchain/` -> @nemesistip-cloud (Consensus)
    - `/frontend/` -> @nemesistip-cloud (Frontend/UX)

### C. Security Policy (SECURITY.md)
- **Status**: MISSING.
- **Action**: Create `SECURITY.md` outlining disclosure processes and support versions.

### D. Templates
- **Status**: MISSING.
- **Action**:
    - Create `.github/ISSUE_TEMPLATE/bug_report.md`
    - Create `.github/ISSUE_TEMPLATE/feature_request.md`
    - Create `.github/PULL_REQUEST_TEMPLATE.md`

## 2. Dependency & Release Management

### A. Dependabot
- **Status**: MISSING.
- **Action**: Create `.github/dependabot.yml` to automate security updates for pip, pnpm, and docker.

### B. Semantic Versioning
- **Status**: MANUAL.
- **Action**: Implement `standard-version` or similar tool to automate CHANGELOG generation and git tagging based on Conventional Commits.

### C. Secret Management
- **Audit**: Verify that no secrets are committed to the repo.
- **Action**: Enforce use of `ENV_VARS.md` for documentation and Cloud Secret Manager for production runtime.

## 3. Governance Implementation Roadmap
1.  **Repository Setup**: Commit the missing templates and policy files.
2.  **Workflow Automation**: Configure Dependabot and Semantic Versioning.
3.  **Enforcement**: Apply branch protection rules in GitHub Settings (User action required).
