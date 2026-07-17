# VIT Runtime Kernel Specification

## 1. Overview
The VIT Runtime Kernel is the foundational execution layer of the ecosystem. It provides a deterministic environment for bootstrapping, orchestrating, and supervising all platform subsystems.

## 2. Lifecycle States
Every subsystem and the Kernel itself follows a strict state machine:

- **INITIALIZING**: Kernel is setting up internal structures and loading core configuration.
- **STARTING**: Subsystems are being initialized in topological order.
- **RUNNING**: All critical subsystems are operational.
- **DEGRADED**: One or more non-critical subsystems have failed or are experiencing issues.
- **SHUTTING_DOWN**: Kernel is gracefully stopping subsystems in reverse order.
- **STOPPED**: All subsystems have ceased operation and resources are released.

## 3. Dependency Resolution
The Kernel uses a **Topological Sort** algorithm to determine the correct startup sequence.
- Subsystems declare their dependencies explicitly via the `dependencies` attribute.
- The Kernel ensures that foundational services (Database, Redis, Secrets) are started before high-level domain modules.

## 4. Kernel Components

### Configuration Loader
- Centralized loading of environment variables and platform-specific configs.
- Validates mandatory secrets before proceeding to boot.

### Module Registry
- Registry of all active subsystems.
- Prevents duplicate registration and manages subsystem instances.

### Supervision Loop
- Periodic health checks across all registered subsystems.
- Automatic transition to `DEGRADED` state upon failure.

## 5. Integration with FastAPI
The Kernel is integrated via the FastAPI `lifespan` event.
- `await kernel.boot()` is called on startup.
- `await kernel.shutdown()` is called on shutdown.
- All legacy bootstrap and worker initialization logic has been migrated into Kernel Subsystems.
