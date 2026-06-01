output "cloud_run_url" {
  description = "Primary VIT API Cloud Run URL"
  value       = google_cloud_run_v2_service.vit_api.uri
}

output "artifact_registry" {
  description = "Docker image registry path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/vit-repo/vit-network"
}

output "cloud_sql_connection" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.vit_postgres.connection_name
}

output "redis_host" {
  description = "Memorystore Redis host"
  value       = google_redis_instance.vit_redis.host
  sensitive   = true
}

output "assets_bucket" {
  description = "GCS bucket for static assets"
  value       = google_storage_bucket.vit_assets.name
}

output "ml_models_bucket" {
  description = "GCS bucket for ML model artifacts"
  value       = google_storage_bucket.vit_ml_models.name
}

output "vit_api_service_account" {
  description = "VIT API service account email"
  value       = google_service_account.vit_api.email
}
