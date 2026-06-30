# 12 API Standards

## 1. Design & RESTfulness
- Follow RESTful principles.
- Use plural nouns for resources (e.g., `/api/matches`, `/api/users`).
- Use appropriate HTTP methods (GET, POST, PUT, DELETE).
- **Statelessness**: No session-based state on the server. Use JWT for authentication.

## 2. Request/Response
- Use Pydantic schemas for request validation and response serialization.
- **Consistency**: Return consistent error structures:
  ```json
  {
    "detail": "error message",
    "code": "ERROR_CODE",
    "meta": {}
  }
  ```
- **Success Responses**: Wrap list results in a `data` key with pagination metadata.

## 3. Versioning
- **Path Versioning**: Major versions MUST be in the path (e.g., `/api/v1/...`).
- **Header Versioning**: Minor versioning or experimental features SHOULD use `X-API-Version` header.

## 4. Documentation
- All endpoints MUST be documented using FastAPI's automatic Swagger/OpenAPI support.
- Provide descriptive docstrings and `summary` fields for all route handlers.

## 5. Status Codes
- `200 OK`: Success with body.
- `201 Created`: Success after creation.
- `204 No Content`: Success with no body (e.g., DELETE).
- `400 Bad Request`: Validation or logic error.
- `401 Unauthorized`: Missing or invalid auth.
- `403 Forbidden`: Auth valid but insufficient permissions.
- `404 Not Found`: Resource missing.
- `429 Too Many Requests`: Rate limit exceeded.
