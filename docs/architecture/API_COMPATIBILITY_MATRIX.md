# API COMPATIBILITY MATRIX

| Endpoint | Previous Path | Current Path | Router File | Registration | Git Evidence | Breaking | Recommended Action | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Auth Register | /auth/register | /api/auth/register | app/auth/routes.py | main.py (prefix=/api/auth) | N/A | Yes | Support both paths | High |
| Auth Login | /auth/login | /api/auth/login | app/auth/routes.py | main.py (prefix=/api/auth) | N/A | Yes | Support both paths | High |
| Auth Me | /auth/me | /api/auth/me | app/auth/routes.py | main.py (prefix=/api/auth) | N/A | Yes | Support both paths | High |
| Auth Refresh | /auth/refresh | /api/auth/refresh | app/auth/routes.py | main.py (prefix=/api/auth) | N/A | Yes | Support both paths | High |
| System Status | /system/status | /system/status | main.py | app.get() | N/A | No | None | High |
| Blockchain Predictions Stake | /api/blockchain/predictions/{id}/stake | /api/blockchain/predictions/{id}/stake | app/modules/blockchain/routes.py | Unmounted | N/A | Yes | Mount router | High |
| Matches List | /matches | /api/matches | app/api/routes/matches.py | main.py (prefix=/api) | N/A | Yes | Support both paths | High |
| Predict | /predict | /api/predict | app/api/routes/predict.py | main.py (prefix=/api) | N/A | Yes | Support both paths | High |
| Sports Sync | /sports/sync/fixtures | /api/sports/sync/fixtures | app/api/routes/sports.py | main.py (prefix=/api) | N/A | Yes | Support both paths | High |

## Failure Classifications
1. **Auth failures**: Backwards compatibility regression (moved from /auth to /api/auth).
2. **Blockchain Predictions**: Router registration defect (app/modules/blockchain/routes.py not mounted).
3. **System Status**: Passing (test might have failed due to collection or other logic).
4. **Matches/Predict/Sports**: Backwards compatibility regression (moved to /api prefix).
