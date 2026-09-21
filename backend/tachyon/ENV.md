# Tachyon VESS Environment Variables

Required environment variables for Tachyon storage system:

### Cloud Provider Credentials
- `GDRIVE_SERVICE_ACCOUNT_KEYS`: JSON array of service account key dicts.
- `GDRIVE_CREDENTIALS_DIR`: (Alternative) Path to a directory containing `*.json` service account files.
- `ONEDRIVE_ACCOUNTS`: JSON array of `{tenant_id, client_id, client_secret}`.
- `DROPBOX_TOKENS`: JSON array of Dropbox access tokens.

### Sharding & Redundancy
- `TACHYON_DATA_SHARDS`: Number of data shards for Reed-Solomon (default: `6`).
- `TACHYON_PARITY_SHARDS`: Number of parity shards for Reed-Solomon (default: `3`).

### System Limits
- `TACHYON_MAX_FILE_SIZE_MB`: Maximum file size allowed for upload (default: `100`).

### API Security
- `TACHYON_S3_API_KEY`: HMAC key for S3-compatible API authentication. Can also be set in `PlatformConfig` with key `tachyon_s3_api_key`.
