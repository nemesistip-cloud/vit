# VIT Network — Administrative Gap Register (v5.5.0)

This document maps, reviews, and logs the gaps between the administrative capabilities provided by the backend API and those actually exposed in the frontend admin control panel.

---

## 📋 GAP REGISTER LOG

### 1. Developer API Key Management
- **Feature:** API Key Generation & Management
- **Frontend Status:** Missing (No tab or view exists in `Admin.tsx` to list, edit, or revoke user API keys).
- **Backend Status:** Complete (`app/api/routes/admin.py` has `GET /api-keys`, `PATCH /api-keys/{key_id}`, `DELETE /api-keys/{key_id}`).
- **API Status:** Complete (Prefix: `/api/admin/api-keys`).
- **Database/Config Status:** Complete (`api_keys` table exists in database).
- **Severity:** HIGH
- **Action Required:** Create an "API Keys" section or table in the frontend `Admin.tsx` to query `/api/admin/api-keys` and support revocation/editing.
- **Final Status:** Identified

### 2. Marketplace Listing Approvals
- **Feature:** Peer-to-peer AI Model Listing Approval/Rejection
- **Frontend Status:** Missing (No UI exists to list listings pending admin review).
- **Backend Status:** Complete (`app/api/routes/admin.py` has `GET /marketplace/listings`, `POST /marketplace/listings/{listing_id}/approve`, etc.).
- **API Status:** Complete (Prefix: `/api/admin/marketplace`).
- **Database/Config Status:** Complete (`ai_model_listings` table exists).
- **Severity:** MEDIUM
- **Action Required:** Add a "Marketplace" tab in the frontend admin dashboard to approve/reject AI model listings.
- **Final Status:** Identified

### 3. Core Platform Configuration Editor
- **Feature:** Live Config Management (Setting limits, APYs, Min stake, conversion fees)
- **Frontend Status:** Incomplete (Frontend `config` tab only renders "Feature Flags" and "Raw Config" in read-only pre tags. No form inputs exist to update configuration values).
- **Backend Status:** Complete (`app/api/routes/admin.py` has `GET /config` and `PUT /config/{key}`).
- **API Status:** Complete (Prefix: `/api/admin/config/{key}`).
- **Database/Config Status:** Complete (`platform_configs` table exists).
- **Severity:** HIGH
- **Action Required:** Implement edit form inputs in the frontend `config` tab so admins can submit updates to `/api/admin/config/{key}`.
- **Final Status:** Identified

### 4. AI Model Retraining & Jobs Monitor
- **Feature:** Model retrain triggering & Training Job status tracker
- **Frontend Status:** Missing (No UI exists to monitor `training-jobs` or trigger retraining).
- **Backend Status:** Complete (`app/api/routes/admin.py` has `/models/{model_key}/retrain` and `/training-jobs`).
- **API Status:** Complete (Prefix: `/api/admin/training-jobs`).
- **Database/Config Status:** Complete (`training_jobs` table exists).
- **Severity:** MEDIUM
- **Action Required:** Create a "Training Jobs" tab or component within the "Models" section to view progress of models currently retraining.
- **Final Status:** Identified

### 5. Audit Log Filters
- **Feature:** Advanced Audit Trail Filtering (By Admin ID, Action, Target)
- **Frontend Status:** Incomplete (Frontend `audit` tab displays a list of entries, but has no search or drop-down filtering inputs).
- **Backend Status:** Complete (Backend supports query parameters `admin_id`, `action`, `target_type`, `date_from`, `date_to`).
- **API Status:** Complete (Prefix: `/api/admin/audit-log`).
- **Database/Config Status:** Complete (`audit_logs` table exists).
- **Severity:** LOW
- **Action Required:** Wire frontend search inputs to append query parameters in the `/api/admin/audit-log` fetch request.
- **Final Status:** Identified

---

*Prepared by Jules, Principal Quality Engineer. Last updated: 2026-08-11.*
