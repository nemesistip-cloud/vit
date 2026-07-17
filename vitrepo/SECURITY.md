# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | ✅ Active support  |
| < 1.1   | ❌ No longer supported |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a vulnerability, email **security@vit.network** with:

1. **Description** — a clear summary of the issue and potential impact.
2. **Reproduction steps** — minimal steps to reproduce the vulnerability.
3. **Affected component** — which endpoint, module, or subsystem is affected.
4. **Suggested severity** — your assessment of Critical / High / Medium / Low.
5. **Proof-of-concept** (optional) — a non-destructive PoC if you have one.

### What to expect

| Milestone | Target SLA |
| --- | --- |
| Acknowledgement | 48 hours |
| Triage & severity assessment | 5 business days |
| Patch or mitigation | 30 days (Critical: 7 days) |
| Public disclosure | Coordinated with reporter; minimum 30 days after patch |

We follow responsible disclosure. Reporters who follow this policy will be credited in the release notes unless they prefer to remain anonymous.

## Scope

**In scope:**
- Authentication & authorization bypass
- SQL injection, XSS, CSRF vulnerabilities
- Remote code execution
- Sensitive data exposure (PII, private keys, API credentials)
- Cryptographic weaknesses in wallet or blockchain subsystems
- Privilege escalation (role / permission issues)
- Webhook signature bypass (Paystack, etc.)

**Out of scope:**
- Denial of service via extremely high request volumes (rate limiting already in place)
- Issues in third-party dependencies without a VIT-specific attack vector
- Social engineering

## Security Controls

- JWT-based authentication with short-lived access tokens and refresh tokens
- HMAC-verified Paystack webhooks (`PAYSTACK_WEBHOOK_SECRET`)
- Rate limiting middleware on all public endpoints
- CORS restricted to explicit origin allowlist in production (`CORS_ALLOWED_ORIGINS`)
- Security headers (HSTS, X-Content-Type-Options, X-Frame-Options, CSP) applied globally
- All secrets managed via environment variables — never committed to source

## Bug Bounty

There is no formal bug bounty programme at this time. We deeply appreciate
responsible security research and will credit contributors publicly.
