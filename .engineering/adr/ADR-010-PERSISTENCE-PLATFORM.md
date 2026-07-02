# ADR-010: Persistence & Data Platform Architecture

- **Date**: 2024-05-24
- **Status**: Accepted
- **Context**:
    The VIT ecosystem requires a standardized, authoritative data access layer. Currently, database access is fragmented, and modules often interact with SQLAlchemy sessions directly. To ensure security, observability, and maintainability, all persistence operations must be centralized through a dedicated Persistence Platform. This platform must provide standardized repositories, transaction management, schema evolution, caching, and auditing.

- **Decision**:
    We will implement a centralized Persistence & Data Platform as a core subsystem of the VIT Runtime Kernel.
    Key architectural decisions include:
    1. **PersistenceManager**: The singleton entry point that manages the lifecycle of the persistence layer and exposes capabilities to the Kernel.
    2. **Repository Framework**: A standardized base class for all data access objects (DAOs), supporting CRUD, pagination, filtering, and soft deletes. All domain-specific repositories must inherit from this framework.
    3. **Unit of Work & Transaction Manager**: Decoupling transaction boundaries from business logic. Transactions will be managed centrally, supporting nested transactions and automatic rollbacks.
    4. **Capability-Based Discovery**: Repositories will be registered with the Module Registry, allowing other modules to discover and use them without direct coupling.
    5. **Automated Auditing**: A middleware/hook-based system to automatically record data changes (Create, Update, Delete) with user identity and correlation IDs.
    6. **Integrated Caching**: A transparent caching layer (using Redis) that repositories can utilize to improve performance without adding complexity to business logic.
    7. **Migration & Schema Registry**: Centralized management of database schema evolution, ensuring that all modules register their schemas and migrations are applied safely at startup.

- **Consequences**:
    - **Pros**: Improved security (no direct SQL), better observability (centralized metrics), consistent transaction handling, and easier testing through repository mocking.
    - **Cons**: Slightly increased boilerplate for new modules (must define repositories and schemas), and a dependency on the Persistence Platform for all data-related tasks.
    - **Constraint**: Direct database access (e.g., raw SQL in services) is strictly prohibited.
