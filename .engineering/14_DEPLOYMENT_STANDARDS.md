# 14 Deployment Standards

## 1. Environments
- **Production**: Cloud Run (`vit` service).
- **Staging/Preview**: Automatic deploys for branch PRs (where supported).

## 2. CI/CD Pipeline
- Use Cloud Build or GitHub Actions.
- Ensure all environment secrets are managed via Secret Manager.

## 3. Verification
- Perform a health check post-deployment.
- Monitor error rates immediately after a new release.
