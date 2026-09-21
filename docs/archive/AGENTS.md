## Storage System Coordination
The Tachyon coordination service requires `PYTHONPATH=.` to find the `tachyon` package.
Missing dependencies (`fastapi`, `uvicorn`, `python-multipart`) must be installed if not present.

## Quality Engineering Guidance
This repository should be treated as production infrastructure. The default mode for agents is verification-first engineering:

- inspect the current system before adding features
- prove behavior with tests, runtime checks, or deployment validation
- prioritize reliability, security, observability, and API contract integrity
- avoid speculative feature work unless it is justified by a verified gap

For the full playbook, see [docs/QUALITY_ASSURANCE_AGENT_PROMPT.md](docs/QUALITY_ASSURANCE_AGENT_PROMPT.md). For repository-level agent expectations, see [COPILOT_INSTRUCTIONS.md](COPILOT_INSTRUCTIONS.md).
