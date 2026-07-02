# ADR-004: Configuration & Secrets Framework

- **Date**: 2026-07-02
- **Status**: Accepted
- **Context**: The VIT Ecosystem lacks a unified, validated, and secure configuration framework. Subsystems currently read environment variables directly, leading to fragmented configuration, lack of validation, and security risks regarding secret exposure.
- **Decision**: Implement a centralized Configuration & Secrets Framework.
    - **Single Source of Truth**: All configuration must be accessed via the `ConfigurationManager`.
    - **Provider-Based Resolution**: Deterministic precedence: Overrides > Secrets > Environment > Configuration Files > Defaults.
    - **Validation**: Use Pydantic models for strict type and constraint validation at startup.
    - **Security**: Implement a `SecretsManager` that redacts sensitive values from logs and diagnostics.
    - **Feature Flags**: Centralized management of runtime flags with support for environment-specific defaults.
    - **Kernel Integration**: The framework is initialized as the first step in the Kernel boot sequence.
- **Consequences**:
    - Modules no longer read `os.environ` or `.env` files directly.
    - Startup will fail if mandatory configuration is missing or invalid.
    - Improved security through secret redaction and centralized management.
    - Simplified testing through configuration injection and overrides.
