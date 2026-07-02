# ADR-011: VIT Resource Platform & Distributed Execution Framework

- **Date**: 2026-07-02
- **Status**: Accepted
- **Context**: The VIT ecosystem requires a unified, robust, and observable infrastructure for background tasks, scheduled jobs, and resource-aware execution. Currently, background tasks are handled in a fragmented manner. A centralized Resource Platform is needed to manage CPU/Memory quotas, provide distributed coordination, and ensure reliable execution across the ecosystem.
- **Decision**:
    - Implement a `ResourcePlatformSubsystem` integrated into the VIT Runtime Kernel.
    - Use Redis as the primary backend for distributed locking, task queuing, and rate limiting.
    - Provide a `ResourceManager` for tracking and enforcing resource utilization.
    - Implement a `Scheduler` supporting Cron and delayed execution.
    - Use a `WorkerPool` architecture for isolated and scalable task execution.
    - Standardize on an `ExecutionContext` for trace propagation and cancellation.
- **Consequences**:
    - All future background tasks must migrate to this framework.
    - Increased dependency on Redis for coordination.
    - Improved observability and reliability of background operations.
    - Clear separation between infrastructure (this platform) and business logic (tasks).
