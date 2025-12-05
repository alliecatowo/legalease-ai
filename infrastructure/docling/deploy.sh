#!/bin/bash
#
# Deploy Docling to Cloud Run
#
# Uses declarative YAML configuration for reproducible deployments.
# Images are stored in Artifact Registry (Cloud Run requires this).
#
# Usage:
#   ./deploy.sh                    # Deploy CPU version (default)
#   ./deploy.sh --gpu              # Deploy GPU version (faster, costs more)
#   ./deploy.sh --sync-images      # Sync images from quay.io to Artifact Registry
#

set -e

# Source central config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

# Artifact Registry paths
AR_REPO="us-central1-docker.pkg.dev/${PROJECT_ID}/docker-images"
DOCLING_GPU_IMAGE="${AR_REPO}/docling-serve:latest"
DOCLING_CPU_IMAGE="${AR_REPO}/docling-serve-cpu:latest"

# Quay.io source images
QUAY_GPU_IMAGE="quay.io/docling-project/docling-serve:latest"
QUAY_CPU_IMAGE="quay.io/docling-project/docling-serve-cpu:latest"

# Parse arguments
USE_GPU=false
SYNC_IMAGES=false
for arg in "$@"; do
  case $arg in
    --gpu)
      USE_GPU=true
      ;;
    --sync-images)
      SYNC_IMAGES=true
      ;;
  esac
done

# Function to sync images from quay.io to Artifact Registry
sync_images() {
  echo ""
  echo "=== Syncing images to Artifact Registry ==="
  echo ""

  # Ensure Artifact Registry repo exists
  echo "Ensuring Artifact Registry repository exists..."
  gcloud artifacts repositories create docker-images \
    --repository-format=docker \
    --location=us-central1 \
    --project="$PROJECT_ID" \
    --description="Docker images for LegalEase" 2>/dev/null || true

  # Configure docker auth
  gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

  if [ "$USE_GPU" = true ]; then
    echo ""
    echo "Pulling GPU image from quay.io..."
    docker pull "$QUAY_GPU_IMAGE"

    echo "Tagging for Artifact Registry..."
    docker tag "$QUAY_GPU_IMAGE" "$DOCLING_GPU_IMAGE"

    echo "Pushing to Artifact Registry..."
    docker push "$DOCLING_GPU_IMAGE"
  else
    echo ""
    echo "Pulling CPU image from quay.io..."
    docker pull "$QUAY_CPU_IMAGE"

    echo "Tagging for Artifact Registry..."
    docker tag "$QUAY_CPU_IMAGE" "$DOCLING_CPU_IMAGE"

    echo "Pushing to Artifact Registry..."
    docker push "$DOCLING_CPU_IMAGE"
  fi

  echo ""
  echo "Image sync complete!"
}

# Main deployment
main() {
  # Validate configuration
  if ! validate_config; then
    echo ""
    echo "Fix the configuration issues above and try again."
    exit 1
  fi

  echo ""
  print_config
  echo ""
  echo "Service: $DOCLING_SERVICE_NAME"
  echo "GPU: $USE_GPU"
  echo ""

  # Sync images if requested
  if [ "$SYNC_IMAGES" = true ]; then
    sync_images
  fi

  # Enable required APIs
  echo "Enabling required APIs..."
  gcloud services enable run.googleapis.com --project "$PROJECT_ID"
  gcloud services enable artifactregistry.googleapis.com --project "$PROJECT_ID"

  # Check if image exists in Artifact Registry
  IMAGE_TO_USE=$([ "$USE_GPU" = true ] && echo "$DOCLING_GPU_IMAGE" || echo "$DOCLING_CPU_IMAGE")
  if ! gcloud artifacts docker images describe "$IMAGE_TO_USE" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo ""
    echo "ERROR: Image not found in Artifact Registry: $IMAGE_TO_USE"
    echo ""
    echo "Run with --sync-images to pull from quay.io and push to Artifact Registry:"
    echo "  ./deploy.sh$([ "$USE_GPU" = true ] && echo " --gpu") --sync-images"
    echo ""
    exit 1
  fi

  # Deploy using gcloud run deploy (more reliable than YAML for GPU settings)
  echo ""
  if [ "$USE_GPU" = true ]; then
    echo "Deploying GPU version (nvidia-l4)..."
    echo "Note: GPU instances cost more but are ~6x faster"
    echo ""

    gcloud run deploy "$DOCLING_SERVICE_NAME" \
      --image "$IMAGE_TO_USE" \
      --region "$REGION" \
      --project "$PROJECT_ID" \
      --port 5001 \
      --memory 16Gi \
      --cpu 4 \
      --gpu 1 \
      --gpu-type nvidia-l4 \
      --no-gpu-zonal-redundancy \
      --min-instances 0 \
      --max-instances 1 \
      --timeout 900 \
      --concurrency 1 \
      --set-env-vars "OMP_NUM_THREADS=4,DOCLING_SERVE_MAX_SYNC_WAIT=600,DOCLING_SERVE_ENABLE_UI=false" \
      --no-allow-unauthenticated \
      --service-account "$DOCLING_SERVICE_ACCOUNT"
  else
    echo "Deploying CPU version..."
    echo ""

    gcloud run deploy "$DOCLING_SERVICE_NAME" \
      --image "$IMAGE_TO_USE" \
      --region "$REGION" \
      --project "$PROJECT_ID" \
      --port 5001 \
      --memory 8Gi \
      --cpu 4 \
      --min-instances 0 \
      --max-instances 10 \
      --timeout 900 \
      --concurrency 1 \
      --set-env-vars "OMP_NUM_THREADS=4,DOCLING_SERVE_MAX_SYNC_WAIT=600,DOCLING_SERVE_ENABLE_UI=false" \
      --no-allow-unauthenticated \
      --service-account "$DOCLING_SERVICE_ACCOUNT"
  fi

  # Get service URL
  SERVICE_URL=$(get_service_url "$DOCLING_SERVICE_NAME")

  echo ""
  echo "=== Deployment Complete ==="
  echo ""
  echo "Service URL: $SERVICE_URL"
  echo ""

  # Grant invoker permissions
  echo "Granting Cloud Run Invoker role to compute service account..."
  gcloud run services add-iam-policy-binding "$DOCLING_SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --member "serviceAccount:$COMPUTE_SERVICE_ACCOUNT" \
    --role "roles/run.invoker" \
    --quiet

  gcloud run services add-iam-policy-binding "$DOCLING_SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --member "serviceAccount:$FIREBASE_ADMIN_SERVICE_ACCOUNT" \
    --role "roles/run.invoker" \
    --quiet

  echo ""
  echo "=== Configuration ==="
  echo ""
  echo "Add to your Firebase Functions environment (.env or secrets):"
  echo ""
  echo "  DOCLING_SERVICE_URL=$SERVICE_URL"
  echo "  EXTRACTION_PROVIDER=docling"
  echo ""
  echo "=== Testing ==="
  echo ""
  echo "Test the service with:"
  echo ""
  echo "  # Get ID token"
  echo "  TOKEN=\$(gcloud auth print-identity-token)"
  echo ""
  echo "  # Health check"
  echo "  curl -H \"Authorization: Bearer \$TOKEN\" $SERVICE_URL/health"
  echo ""
}

main
