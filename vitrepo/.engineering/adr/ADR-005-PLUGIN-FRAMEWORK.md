# ADR-005: Plugin & Extension Framework

- **Date**: 2024-05-20
- **Status**: Accepted
- **Context**:
    VIT needs to transition from a monolithic-style module system to a fully modular ecosystem. While the existing `ModuleRegistry` and `LifecycleManager` provide basic orchestration, they are designed for internal core subsystems. There is no mechanism for dynamic discovery, isolation, version compatibility, or capability-based service discovery for third-party or optional extensions.

- **Decision**:
    Implement a dedicated `Plugin & Extension Framework` as a first-class subsystem. Key architectural decisions include:
    1.  **Manifest-First Discovery**: Every plugin must provide a `manifest.json` (or Pydantic-validated equivalent) defining identity, dependencies, and capabilities.
    2.  **Topological Dependency Resolution**: Plugins are loaded based on a dependency graph, ensuring parents start before children.
    3.  **Capability-Based Discovery**: Plugins interact via registered capabilities (e.g., `IdentityProvider`) rather than direct module imports, promoting loose coupling.
    4.  **Sandbox Isolation**: Plugins are loaded into restricted namespaces with limited access to the Kernel's internal APIs.
    5.  **Deterministic Lifecycle**: Plugins follow a lifecycle that extends the standard VIT module lifecycle, adding `SUSPEND`, `RESUME`, and `UPGRADE` states.

- **Consequences**:
    - **Pros**: Enables rapid ecosystem expansion without core modification; improves system stability through isolation; simplifies testing of individual features.
    - **Cons**: Introduces slight runtime overhead for dynamic loading and capability resolution; increases complexity of the boot sequence.
    - **Security**: Plugins must be signed and validated against a manifest before execution.
