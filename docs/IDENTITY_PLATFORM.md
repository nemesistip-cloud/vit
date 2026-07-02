# VIT Identity & Authentication Platform Architecture

## Executive Summary
The VIT Identity Platform is the single authoritative identity service for the VIT ecosystem. It provides enterprise-grade identity management, authentication, and security features as a first-class platform plugin.

## Identity Model
- **Global Identity ID (GID)**: Immutable, cryptographically derived identifier.
- **Identity Types**: Individual, Admin, Validator, Institution, Organization, Team, Service Account, System Account, External.
- **Verification**: Built-in verification status tracking (Unverified, Pending, Verified, Rejected).

## Core Components
- **IdentityManager**: CRUD operations on Global Identities.
- **AuthenticationManager**: Orchestrates multi-method authentication flows.
- **SessionManager**: Secure session lifecycle and concurrent session control.
- **TokenManager**: JWT access and refresh token issuance/validation.
- **MFAService**: TOTP-based multi-factor authentication.
- **PasswordService**: Secure hashing (Bcrypt) and policy enforcement.
- **DeviceTrustManager**: Device tracking and risk assessment.
- **IdentityEventPublisher**: Standardized event emission via the platform Event Bus.

## Authentication Flow
1. User provides Identifier (Email/Username) and Password.
2. `AuthenticationManager` verifies credentials.
3. If successful, `SessionManager` creates a session.
4. `TokenManager` issues JWT access and refresh tokens.
5. `LoginSucceeded` event is published.

## Session Lifecycle
- **Created**: Upon successful login.
- **Validated**: On every authenticated request.
- **Revoked**: On logout, password change, or administrative action.
- **Expired**: Automatically after the configured TTL (default 24h).

## Event Integration
Published events:
- `UserRegistered`
- `LoginSucceeded`
- `LoginFailed`
- `SessionCreated`
- `DeviceRegistered`
- `IdentityUpdated`
...and more.

## Performance
- Login: < 300ms (Target)
- Token Validation: < 50ms (Target)
- Identity Lookup: < 50ms (Target)

## Security
- Password Hashing: Bcrypt with 12 rounds.
- Brute-force protection: Automatic account lockout after 5 failed attempts.
- Replay protection: Unique JTI for every JWT.
- Isolation: Plugin-based architecture ensures separation of concerns.
