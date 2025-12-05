#!/bin/bash
#
# LegalEase Infrastructure Configuration
#
# This file contains all project-level configuration for GCP/Firebase.
# Source this file in deployment scripts to ensure consistency.
#
# Usage:
#   source ../config.sh
#   echo $PROJECT_ID
#

# ============================================
# Core Project Configuration
# ============================================

# GCP/Firebase Project ID
export PROJECT_ID="legalease-420"

# Default GCP region for Cloud Run, Cloud Functions, etc.
export REGION="us-central1"

# Firebase Storage bucket
export STORAGE_BUCKET="${PROJECT_ID}.firebasestorage.app"

# ============================================
# Service Names
# ============================================

# Document extraction service (Docling on Cloud Run)
export DOCLING_SERVICE_NAME="docling-extraction"

# ============================================
# Service Account Configuration
# ============================================

# Docling Cloud Run service account
export DOCLING_SERVICE_ACCOUNT="docling-runner@${PROJECT_ID}.iam.gserviceaccount.com"

# Default compute service account (for Firebase Functions)
export COMPUTE_SERVICE_ACCOUNT="1029046565992-compute@developer.gserviceaccount.com"

# Firebase Admin SDK service account
export FIREBASE_ADMIN_SERVICE_ACCOUNT="firebase-adminsdk-fbsvc@${PROJECT_ID}.iam.gserviceaccount.com"

# ============================================
# URLs (populated after deployment)
# ============================================

# These are derived from deployments - update after deploying
export API_BASE_URL="https://legalease-api-${PROJECT_ID}.run.app"

# Function to get Cloud Run service URL
get_service_url() {
  local service_name=$1
  local region=${2:-$REGION}
  gcloud run services describe "$service_name" \
    --region "$region" \
    --project "$PROJECT_ID" \
    --format 'value(status.url)' 2>/dev/null
}

# ============================================
# Validation
# ============================================

validate_config() {
  echo "Validating configuration..."

  # Check PROJECT_ID is set
  if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: PROJECT_ID is not set"
    return 1
  fi

  # Check gcloud is authenticated
  if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1 | grep -q '@'; then
    echo "ERROR: Not authenticated with gcloud. Run: gcloud auth login"
    return 1
  fi

  # Check project exists and is accessible
  if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
    echo "ERROR: Cannot access project $PROJECT_ID"
    echo "Run: gcloud config set project $PROJECT_ID"
    return 1
  fi

  echo "Configuration valid:"
  echo "  PROJECT_ID: $PROJECT_ID"
  echo "  REGION: $REGION"
  echo "  STORAGE_BUCKET: $STORAGE_BUCKET"
  return 0
}

# Print configuration summary
print_config() {
  echo "=== LegalEase Infrastructure Config ==="
  echo "PROJECT_ID:       $PROJECT_ID"
  echo "REGION:           $REGION"
  echo "STORAGE_BUCKET:   $STORAGE_BUCKET"
  echo "DOCLING_SA:       $DOCLING_SERVICE_ACCOUNT"
  echo "COMPUTE_SA:       $COMPUTE_SERVICE_ACCOUNT"
  echo "======================================="
}

# If script is run directly, print config
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  print_config
fi
