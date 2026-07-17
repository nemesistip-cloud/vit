# 06 Security Standards

## 1. Authentication & Authorization
- **Dependency Injection**: Use `Depends(get_current_admin)` for all admin routes.
- **Least Privilege**: Only the required permissions should be granted to service accounts and users.
- **Secrets**: Never hardcode secrets. Use GCP Secret Manager or `app/core/secrets_loader.py`.
- **JWT Policy**:
  - Access Token TTL: 1 hour.
  - Refresh Token TTL: 7 days.
  - Algorithm: RS256 (preferred) or HS256 (minimum).

## 2. Data Protection
- **Encryption**:
  - Sensitive storage (Tachyon) MUST use **AES-256-GCM** with 32-byte hex keys.
  - All data in transit MUST use TLS 1.3.
- **PII**: Handle Personally Identifiable Information with care, following GDPR/NDPR principles. Data masking must be applied in logs.

## 3. Auditing
- **Mutation Logs**: Every state-changing operation (POST/PUT/DELETE) must be logged via `write_audit()`.
- **Mandatory Audit Fields**:
  - `timestamp` (ISO 8601)
  - `user_id`
  - `action` (e.g., CREATE_MATCH, UPDATE_WALLET)
  - `resource_id`
  - `ip_address`
  - `user_agent`
  - `status` (SUCCESS/FAILURE)

## 4. Vulnerability Disclosure
- Follow the process in `SECURITY.md` (to be created).
