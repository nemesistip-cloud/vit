# 12 API Standards

## 1. Design
- Follow RESTful principles.
- Use plural nouns for resources (e.g., `/api/matches`, `/api/users`).
- Use appropriate HTTP methods (GET, POST, PUT, DELETE).

## 2. Request/Response
- Use Pydantic schemas for request validation and response serialization.
- Return consistent error structures: `{"detail": "error message"}`.

## 3. Documentation
- All endpoints must be documented using FastAPI's automatic Swagger/OpenAPI support.
- Provide descriptive docstrings for all route handlers.

## 4. Versioning
- Major API versions should be included in the path (e.g., `/api/v1/...`).
