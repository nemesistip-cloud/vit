variable "project_id" {
  description = "GCP project ID (pay-as-you-go)"
  type        = string
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "europe-west1"
}

variable "db_password" {
  description = "PostgreSQL app user password (store in Secret Manager, not here)"
  type        = string
  sensitive   = true
}

variable "ops_email" {
  description = "Email address for monitoring alerts and ops notifications"
  type        = string
  default     = "admin@vit.network"
}
