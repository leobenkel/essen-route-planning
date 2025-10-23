#!/bin/bash
set -e

# Validate required environment variable
if [ -z "$REGISTRY" ]; then
  echo "Error: REGISTRY environment variable is not set"
  echo "Please set REGISTRY in .env file (copy from .env.sample)"
  exit 1
fi

# Configuration
IMAGE_NAME="essen-route-planner/www"
TAG="${1:-latest}"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${TAG}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building Essen Route Planning API Docker image...${NC}"
echo -e "${BLUE}Image: ${FULL_IMAGE}${NC}"
echo ""

# Navigate to project root (two levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

# Build the image
echo -e "${BLUE}Building image...${NC}"
docker build \
    -f deploy/docker/Dockerfile \
    -t "${FULL_IMAGE}" \
    .

echo -e "${GREEN}✓ Image built successfully${NC}"
echo ""

# Ask if user wants to push
read -p "Push image to ${REGISTRY}? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${BLUE}Pushing image to registry...${NC}"
    docker push "${FULL_IMAGE}"
    echo -e "${GREEN}✓ Image pushed successfully${NC}"
    echo ""
    echo -e "${GREEN}Image available at: ${FULL_IMAGE}${NC}"
else
    echo "Skipping push. Image available locally as: ${FULL_IMAGE}"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Next steps:"
echo "  1. Update deploy/k8s/deployment.yaml with the image tag if needed"
echo "  2. Apply Kubernetes manifests: cd deploy/k8s && ./apply.sh"
