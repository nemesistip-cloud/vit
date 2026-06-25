terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "vit-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ── Enable required GCP APIs ──────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "vpcaccess.googleapis.com",
    "redis.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "compute.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "storage.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ── Artifact Registry ─────────────────────────────────────────────────────────
resource "google_artifact_registry_repository" "vit_repo" {
  location      = var.region
  repository_id = "vit-repo"
  description   = "VIT Network Docker images"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# ── VPC Network ───────────────────────────────────────────────────────────────
resource "google_compute_network" "vit_vpc" {
  name                    = "vit-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "vit_subnet" {
  name          = "vit-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vit_vpc.id
}

resource "google_vpc_access_connector" "vit_connector" {
  name          = "vit-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vit_vpc.name
  min_instances = 2
  max_instances = 10
}

# ── Cloud SQL (PostgreSQL 15) ─────────────────────────────────────────────────
resource "google_sql_database_instance" "vit_postgres" {
  name             = "vit-postgres"
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = true

  settings {
    tier              = "db-g1-small"
    availability_type = "REGIONAL"
    disk_size         = 20
    disk_autoresize   = true
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 14
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vit_vpc.id
    }

    database_flags {
      name  = "max_connections"
      value = "200"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false
    }
  }
}

resource "google_sql_database" "vit_db" {
  name     = "vit_db"
  instance = google_sql_database_instance.vit_postgres.name
}

resource "google_sql_user" "vit_user" {
  name     = "vit_app"
  instance = google_sql_database_instance.vit_postgres.name
  password = var.db_password
}

# ── Memorystore Redis ─────────────────────────────────────────────────────────
resource "google_redis_instance" "vit_redis" {
  name           = "vit-redis"
  tier           = "STANDARD_HA"
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.vit_vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version     = "REDIS_7_0"
  display_name      = "VIT Network Redis"
  reserved_ip_range = "10.0.1.0/29"
}

# ── Cloud Storage ─────────────────────────────────────────────────────────────
resource "google_storage_bucket" "vit_assets" {
  name          = "${var.project_id}-vit-assets"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 90 noncurrent_version = true }
  }

  cors {
    origin          = ["https://vit-897838355273.europe-west1.run.app"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

resource "google_storage_bucket" "vit_ml_models" {
  name          = "${var.project_id}-vit-ml-models"
  location      = var.region
  force_destroy = false
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket" "terraform_state" {
  name          = "vit-terraform-state"
  location      = var.region
  force_destroy = false
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# ── Secret Manager ────────────────────────────────────────────────────────────
resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(["vit-jwt-secret", "vit-secret-key", "vit-database-url", "vit-redis-url", "vit-admin-password"])
  secret_id = each.value
  replication {
    auto {}
  }
}

# ── Service Accounts ──────────────────────────────────────────────────────────
resource "google_service_account" "vit_api" {
  account_id   = "vit-api"
  display_name = "VIT API Service Account"
  description  = "Service account for VIT Cloud Run API service"
}

resource "google_service_account" "vit_worker" {
  account_id   = "vit-api-worker"
  display_name = "VIT Worker Service Account"
  description  = "Service account for VIT background worker"
}

resource "google_service_account" "vit_cloudbuild" {
  account_id   = "vit-cloudbuild"
  display_name = "VIT Cloud Build Service Account"
  description  = "Service account for Cloud Build CI/CD"
}

# ── IAM Bindings ──────────────────────────────────────────────────────────────
locals {
  api_roles = [
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/storage.objectViewer",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
  ]
  worker_roles = [
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
  ]
  cloudbuild_roles = [
    "roles/run.admin",
    "roles/storage.admin",
    "roles/artifactregistry.writer",
    "roles/iam.serviceAccountUser",
    "roles/cloudsql.admin",
    "roles/secretmanager.secretAccessor",
  ]
}

resource "google_project_iam_member" "vit_api_roles" {
  for_each = toset(local.api_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.vit_api.email}"
}

resource "google_project_iam_member" "vit_worker_roles" {
  for_each = toset(local.worker_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.vit_worker.email}"
}

resource "google_project_iam_member" "vit_cloudbuild_roles" {
  for_each = toset(local.cloudbuild_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.vit_cloudbuild.email}"
}

# ── Cloud Run — VIT API ───────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "vit_api" {
  name     = "vit"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.vit_api.email

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    vpc_access {
      connector = google_vpc_access_connector.vit_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "europe-west1-docker.pkg.dev/${var.project_id}/vit-repo/vit-network:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle          = false
        startup_cpu_boost = true
      }

      ports {
        container_port = 8080
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }


      env {
        name  = "PORT"
        value = "8080"
      }

      env {
        name = "JWT_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["vit-jwt-secret"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["vit-secret-key"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["vit-database-url"].secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 6
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 30
        timeout_seconds       = 5
        period_seconds        = 30
        failure_threshold     = 3
      }
    }

    cloud_sql_instance {
      instances = ["${var.project_id}:${var.region}:vit-postgres"]
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "vit_api_public" {
  location = google_cloud_run_v2_service.vit_api.location
  name     = google_cloud_run_v2_service.vit_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Cloud Scheduler — periodic tasks ─────────────────────────────────────────
resource "google_cloud_scheduler_job" "clv_monitor" {
  name        = "vit-clv-monitor"
  description = "Daily CLV streak monitor — auto-demotes under-performing models"
  schedule    = "0 4 * * *"
  time_zone   = "UTC"
  region      = var.region

  http_target {
    uri         = "${google_cloud_run_v2_service.vit_api.uri}/api/admin/clv/check"
    http_method = "POST"

    oidc_token {
      service_account_email = google_service_account.vit_api.email
    }
  }

  retry_config {
    retry_count = 3
    min_backoff_duration = "5s"
    max_backoff_duration = "300s"
  }
}

resource "google_cloud_scheduler_job" "model_accountability" {
  name        = "vit-model-accountability"
  description = "6-hourly model accountability loop"
  schedule    = "0 */6 * * *"
  time_zone   = "UTC"
  region      = var.region

  http_target {
    uri         = "${google_cloud_run_v2_service.vit_api.uri}/api/admin/models/accountability"
    http_method = "POST"

    oidc_token {
      service_account_email = google_service_account.vit_api.email
    }
  }
}

# ── Cloud Monitoring alerts ───────────────────────────────────────────────────
resource "google_monitoring_notification_channel" "email_alert" {
  display_name = "VIT Ops Email"
  type         = "email"
  labels = {
    email_address = var.ops_email
  }
}

resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "VIT API — High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 5%"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class!=\"2xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email_alert.name]
  severity              = "ERROR"
}

resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "VIT API — High Latency (p95 > 5s)"
  combiner     = "OR"

  conditions {
    display_name = "p95 latency > 5000ms"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5000
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email_alert.name]
  severity              = "WARNING"
}
