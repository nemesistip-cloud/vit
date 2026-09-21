# Copilot Instructions for VIT Network

This repository is a production-grade monorepo. Prioritize correctness, reliability, and verification over feature generation.

## Working Style

- Treat the codebase as production infrastructure.
- Verify before changing behavior.
- Prefer root-cause analysis over speculative fixes.
- Add or improve tests whenever behavior changes.
- Preserve backward compatibility and avoid breaking API contracts.
- Prefer small, targeted fixes that improve reliability or safety.

## Quality Engineering Priorities

When working in this repository:
- inspect existing tests and health checks before adding new features
- validate API contracts between frontend and backend
- check runtime and deployment configuration before claiming readiness
- look for security, observability, and resilience gaps
- prefer fixing issues that improve system confidence and production readiness

## Repository-Specific Notes

- The Tachyon coordination service requires PYTHONPATH=. so the tachyon package can be imported correctly.
- Missing dependencies such as fastapi, uvicorn, and python-multipart may need to be installed before running local services.
- Review the QA workflow document in docs/QUALITY_ASSURANCE_AGENT_PROMPT.md for the full quality-audit playbook.

## Default Expectations

For this repository, the agent should:
1. investigate the current state before making changes
2. verify existing behavior with tests or runtime checks
3. document important gaps and risks
4. implement minimal fixes that increase reliability or coverage
5. avoid introducing unnecessary new features
