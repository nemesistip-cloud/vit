# 04 Module Contracts

## 1. Interface Standards
All cross-domain interactions MUST use formalized interfaces. These are defined in `contracts.json`.

## 2. Core Contracts

### DatabaseSession
- **Interface**: `AsyncSessionLocal`
- **Output**: `AsyncSession`
- **Owner**: Database System
- **Description**: Primary database session factory for all async operations.

### GetDBDependency
- **Interface**: `get_db`
- **Output**: `AsyncGenerator[AsyncSession, None]`
- **Owner**: Database System
- **Description**: FastAPI dependency for injecting database sessions.

### AIInference
- **Interface**: `call_ai`
- **Inputs**: `prompt: str`, `**kwargs`
- **Output**: `str`
- **Owner**: AI System
- **Description**: Main entry point for AI text generation.

### BackgroundTaskQueue
- **Interface**: `app.worker.tasks`
- **Owner**: Task System
- **Description**: Entry points for scheduling asynchronous background tasks.

## 3. Modification Rule
Interface contracts cannot be modified without Integration Approval.
