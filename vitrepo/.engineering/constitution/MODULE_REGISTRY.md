# VIT Module Registry & Service Discovery

## 1. Overview
The Module Registry is the authoritative catalogue for all runtime components in the VIT ecosystem. It enables the Runtime Kernel to orchestrate the platform without hardcoding module references.

## 2. Standard Module Contract
Every module MUST implement the `ModuleContract` interface:

- `metadata`: Registration details (ID, Version, Owner, Domain).
- `initialize(config)`: Bootstrapping logic.
- `start()`: Activation hook.
- `stop()`: Graceful shutdown hook.
- `check_health()`: Health status reporting.
- `get_diagnostics()`: Runtime telemetry.

## 3. Service Discovery
Modules can locate services dynamically via the `ModuleRegistry` APIs:

- `discover_by_capability(capability)`: Find modules providing specific features (e.g., "inference").
- `discover_by_domain(domain)`: Find modules within a bounding context.
- `get_module(module_id)`: Direct lookup.

## 4. Lifecycle Management
The Registry tracks the following states for every module:
- `REGISTERED`, `INITIALIZING`, `INITIALIZED`, `STARTING`, `STARTED`, `READY`, `DEGRADED`, `FAILED`.

## 5. Dependency Validation
Before the Kernel boots, the Registry performs a mandatory audit of the dependency graph:
- **Missing Dependencies**: Rejects startup if a mandatory requirement is absent.
- **Circular Dependencies**: Rejects startup if a circular loop is detected.

## 6. Architecture Integration
- **Kernel Integration**: The Kernel uses the Registry to determine startup order and supervise health.
- **FastAPI Integration**: System diagnostics are exposed via `/api/system/registry`.
