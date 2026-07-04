# ARCHITECTURE_CLEANUP_PLAN.md

## 1. Core Platform Review

### A. Subsystem Duplication
- **Wallet Platform**: Significant overlap between `app.modules.wallet` (Legacy) and `app.core.wallet` (v1.1 Authoritative).
    - **Issue**: Two different sets of models, repository patterns, and routes.
    - **Action**: Deprecate `app.modules.wallet` and force all interactions through `WalletSubsystem`.
- **Identity**: Duplicate logic in `app.modules.identity` and `app.plugins.identity`.
    - **Action**: Retire the module version in favor of the plugin-based identity platform.

### B. Circular Dependencies
- **ModuleRegistry -> Kernel -> Subsystems -> ModuleRegistry**:
    - **Issue**: The Kernel registers subsystems which then register themselves in the ModuleRegistry, but the Registry is also used by subsystems for discovery.
    - **Action**: Enforce a strict "Registry-First" initialization where dependencies are validated *before* the Kernel attempts to boot.
- **Tasks -> AI Orchestrator**:
    - **Action**: Already partially resolved, but need to ensure all background tasks use the `ResourcePlatformSubsystem` instead of importing orchestrators directly.

### C. Dead Code / Redundant Abstractions
- **BackgroundTaskSupervisor**: Found in `main.py` but functionally replaced by `ResourcePlatformSubsystem`.
    - **Action**: Remove from `main.py` and update any remaining references.
- **ModuleContract**: Ensure all core modules implement the unified contract to prevent custom initialization logic.

## 2. Cleanup Roadmap

### Step 1: Subsystem Refactoring
- Formalize the `WalletSubsystem` as the sole authoritative wallet engine.
- Migrate any business-critical logic from `app.modules.wallet` to `app.core.wallet`.

### Step 2: Dependency Decoupling
- Introduce an Event Bus for inter-subsystem communication to eliminate direct imports.
- Use `kernel.get_subsystem("name")` instead of direct imports in high-level services.

### Step 3: Dead Code Removal
- Delete the `archive/` directory contents once verified that no production scripts depend on them.
- Purge legacy router files identified in the Router Consolidation Plan.
