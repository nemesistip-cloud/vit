# 18 Decision Records (ADR)

## ADR-001: Transition to GCP Native
- **Date**: 2025-06-25
- **Status**: Accepted
- **Context**: Legacy providers had resource constraints. GCP offers better scalability and integration.
- **Decision**: Move compute to Cloud Run and data to Cloud SQL/Memorystore.

## ADR-002: Modular Domain Ownership
- **Date**: 2025-06-26
- **Status**: Accepted
- **Context**: Parallel development by multiple agents required clear boundaries.
- **Decision**: Implement strict domain ownership mapping in `state.json`.
