# ADR-001: Transition to GCP Native

- **Date**: 2025-06-25
- **Status**: Accepted
- **Context**: Legacy providers had resource constraints. GCP offers better scalability and integration.
- **Decision**: Move compute to Cloud Run and data to Cloud SQL/Memorystore.
- **Consequences**:
  - Improved scalability and observability.
  - Dependency on GCP services.
  - Requirement for GCP-specific configuration.
