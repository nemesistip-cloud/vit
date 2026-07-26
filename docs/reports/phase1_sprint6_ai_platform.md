# Phase 1 Sprint 6 — Global AI Platform Engineering Report

## Scope

Sprint 6 turns the existing assistant layer into a shared platform service. It reuses current AI services, gateway routes, command palette, event bus, identity service, search service, notification framework, and platform integration singleton. No duplicate AI service was introduced.

## Discovery and architecture audit

Existing capabilities found in the codebase:

- `app/api/routes/ai_assistant.py` exposes the authenticated gateway-mounted VIT Bot API under `/api/ai/assistant/*`.
- `app/modules/assistant/service.py` provides the `GlobalAssistantService` abstraction and workflow handlers.
- `app/modules/ai`, `app/modules/ai_core`, `app/api/routes/ai.py`, `app/api/routes/ai_intelligence.py`, and `app/services/ai_client.py` provide existing AI model, orchestration, and native provider capabilities.
- `app/modules/command_palette` exposes shared command registration and execution.
- `app/core/event_bus.py` provides event publication, metadata, replay, and diagnostics.
- `app/modules/search/foundation.py` provides shared resource indexing and search.
- `app/modules/notifications` provides notification channels and platform delivery.
- `app/modules/identity` and `app/api/routes/identity_management.py` provide identity/workspace primitives.
- `app/modules/platform/integration.py` already owns the shared platform service instances.

## Completed functionality

- Gateway auth and `/api/ai/assistant/chat` remain intact for the existing VIT Bot flow.
- Platform service instances already exist for identity, events, search, notifications, assistant, and commands.
- Search, notifications, event bus, and command palette have unit/integration coverage.

## Remaining gaps addressed in this sprint

- The global assistant service was not reachable through the existing gateway-mounted AI assistant API.
- Assistant service wiring existed in the platform singleton but was not verified through an HTTP route.
- Conversation memory and command orchestration needed route-level regression coverage.
- The previous auth side-effect helper needed lazy coroutine creation to make best-effort handling safer.

## Implementation plan executed

1. Keep the existing VIT Bot route intact.
2. Add platform assistant endpoints to the existing `/api/ai/assistant/*` router instead of creating a new AI service.
3. Wire authenticated users into `AssistantConversationContext` with user, session, workspace, role, and metadata.
4. Execute shared assistant orchestration through the platform integration singleton.
5. Expose status and history endpoints for operational visibility.
6. Add regression tests for service-level and route-level behavior.
7. Verify syntax, tests, and production frontend build.

## API documentation

The shared platform assistant is exposed through the existing FastAPI/OpenAPI gateway route group:

- `POST /api/ai/assistant/platform/chat`
  - Runs the global assistant over the existing command palette, event bus, search platform, notification platform, and identity service.
  - Request fields: `message`, `session_id`, `workspace_id`, `metadata`, `execute`.
  - Use `execute=true` for structured orchestration output; otherwise the route returns the assistant string response.
- `GET /api/ai/assistant/platform/history`
  - Returns in-process conversation memory for the authenticated user/session/workspace scope.
- `GET /api/ai/assistant/platform/status`
  - Reports which required platform services are wired into the assistant.

## Implemented changes

- Added workspace-aware assistant context fields for `workspace_id` and roles.
- Added an in-memory conversation memory abstraction keyed by user, workspace, and session.
- Added command execution support so natural-language prompts such as `open wallet` and command prompts such as `/open_ai` route through the existing command registry.
- Added assistant event publication for completed messages and command executions through the existing event bus.
- Preserved existing search, notification, and workspace workflow behavior while making it more tolerant of async service handlers.
- Wired the platform integration singleton so the global assistant is registered with Identity, Event Bus, Search, Notifications, and Commands by default.
- Added gateway-mounted platform assistant API endpoints to the existing AI assistant router.
- Refined the auth side-effect helper to create side-effect coroutines lazily, avoiding pre-created coroutine objects during best-effort error handling.

## Verification

- Added regression coverage for command execution, conversation memory, event publication, shared search, default platform wiring, and gateway route behavior.
- Re-ran auth tests to ensure login/register hardening remains intact.
- Ran syntax compilation, whitespace checks, and production frontend build.

## Deployment readiness

- Changes are additive to existing routes and services.
- No database migration is required.
- No new external service dependency is required.
- The existing authenticated `/api/ai/assistant/chat` route remains intact.
- New APIs are gateway-mounted and included in FastAPI generated OpenAPI documentation.
