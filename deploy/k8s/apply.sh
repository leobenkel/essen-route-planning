#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Validate required environment variables
if [ -z "$KUBE_SSH_HOST" ]; then
  echo -e "${RED}Error: KUBE_SSH_HOST environment variable is not set${NC}"
  echo "Please set KUBE_SSH_HOST in .env file (copy from .env.sample)"
  exit 1
fi

if [ -z "$DOMAIN" ]; then
  echo -e "${RED}Error: DOMAIN environment variable is not set${NC}"
  echo "Please set DOMAIN in .env file (copy from .env.sample)"
  exit 1
fi

if [ -z "$REGISTRY" ]; then
  echo -e "${RED}Error: REGISTRY environment variable is not set${NC}"
  echo "Please set REGISTRY in .env file (copy from .env.sample)"
  exit 1
fi

echo -e "${BLUE}Deploying Essen Route Planning API to Kubernetes...${NC}"
echo -e "${BLUE}Domain: ${DOMAIN}${NC}"
echo -e "${BLUE}Registry: ${REGISTRY}${NC}"
echo -e "${BLUE}Kubernetes Host: ${KUBE_SSH_HOST}${NC}"
echo ""

# Navigate to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Apply manifests in order (using envsubst for variable substitution)
echo -e "${BLUE}1. Creating namespace...${NC}"
envsubst < namespace.yaml | ssh "$KUBE_SSH_HOST" kubectl apply -f -
echo -e "${GREEN}✓ Namespace created${NC}"
echo ""

echo -e "${BLUE}2. Creating persistent volume claim...${NC}"
envsubst < pvc.yaml | ssh "$KUBE_SSH_HOST" kubectl apply -f -
echo -e "${GREEN}✓ PVC created${NC}"
echo ""

echo -e "${BLUE}3. Creating middleware...${NC}"
envsubst < middleware.yaml | ssh "$KUBE_SSH_HOST" kubectl apply -f -
echo -e "${GREEN}✓ Middleware created${NC}"
echo ""

echo -e "${BLUE}4. Creating service...${NC}"
envsubst < service.yaml | ssh "$KUBE_SSH_HOST" kubectl apply -f -
echo -e "${GREEN}✓ Service created${NC}"
echo ""

echo -e "${BLUE}5. Creating deployment...${NC}"
envsubst < deployment.yaml | ssh "$KUBE_SSH_HOST" kubectl apply -f -
echo -e "${GREEN}✓ Deployment created${NC}"
echo ""

echo -e "${BLUE}6. Creating ingress...${NC}"
envsubst < ingress.yaml | ssh "$KUBE_SSH_HOST" kubectl apply -f -
echo -e "${GREEN}✓ Ingress created${NC}"
echo ""

echo -e "${GREEN}Deployment complete!${NC}"
echo ""

echo -e "${BLUE}Checking pod status...${NC}"
ssh "$KUBE_SSH_HOST" kubectl get pods -n essen
echo ""

echo -e "${BLUE}Checking ingress status...${NC}"
ssh "$KUBE_SSH_HOST" kubectl get ingress -n essen
echo ""

echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Wait for pod to be ready: ssh $KUBE_SSH_HOST kubectl get pods -n essen -w"
echo "  2. Check logs: ssh $KUBE_SSH_HOST kubectl logs -n essen -l app=essen-route-planning"
echo "  3. Verify DNS: nslookup $DOMAIN"
echo "  4. Wait for TLS certificate: ssh $KUBE_SSH_HOST kubectl get certificate -n essen"
echo "  5. Test the API: curl https://$DOMAIN/health"
echo ""
echo -e "${GREEN}Once ready, the API will be available at: https://$DOMAIN${NC}"
