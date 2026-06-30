# 06 Security Standards

## 1. Authentication & Authorization
- **Dependency Injection**: Use `Depends(get_current_admin)` for all admin routes.
- **Least Privilege**: Only the required permissions should be granted to service accounts and users.
- **Secrets**: Never hardcode secrets. Use GCP Secret Manager or `app/core/secrets_loader.py`.

## 2. Data Protection
- **Encryption**: Sensitive storage (Tachyon) must use 32-byte hex keys for encryption.
- **PII**: Handle Personally Identifiable Information with care, following GDPR/NDPR principles.

## 3. Auditing
- **Mutation Logs**: Every state-changing operation (POST/PUT/DELETE) must be logged via `write_audit()`.
- **IP Tracking**: Capture IP addresses for all admin actions.

## 4. Vulnerability Disclosure
- Follow the process in `SECURITY.md` (to be created).
