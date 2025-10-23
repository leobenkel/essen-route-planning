#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Populating Essen data in Kubernetes deployment...${NC}"
echo ""

# Check if data exists locally
if [ ! -f "../../data/output/essen_exhibitors.json" ] || [ ! -f "../../data/output/essen_products.json" ]; then
    echo -e "${YELLOW}Essen data not found locally. Fetching from API...${NC}"

    # Check if we're in a venv
    if [ ! -d "../../venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        cd ../..
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd deploy/k8s
    else
        cd ../..
        source venv/bin/activate
        cd deploy/k8s
    fi

    echo -e "${BLUE}Running step 3 to fetch Essen data...${NC}"
    python3 ../../src/steps/step3_fetch_essen_data.py

    echo -e "${GREEN}✓ Essen data fetched${NC}"
    echo ""
fi

# Get pod name
POD_NAME=$(kubectl get pods -n essen-api -l app=essen-route-planning -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo -e "${YELLOW}No pod found. Make sure deployment is running.${NC}"
    echo "Run: kubectl get pods -n essen-api"
    exit 1
fi

echo -e "${BLUE}Found pod: ${POD_NAME}${NC}"
echo ""

# Copy Essen data to pod
echo -e "${BLUE}Copying Essen exhibitor data...${NC}"
kubectl cp ../../data/output/essen_exhibitors.json essen-api/${POD_NAME}:/app/data/output/essen_exhibitors.json

echo -e "${BLUE}Copying Essen product data...${NC}"
kubectl cp ../../data/output/essen_products.json essen-api/${POD_NAME}:/app/data/output/essen_products.json

echo -e "${GREEN}✓ Data copied successfully${NC}"
echo ""

# Verify
echo -e "${BLUE}Verifying data in pod...${NC}"
kubectl exec -n essen-api ${POD_NAME} -- ls -lh /app/data/output/

echo ""
echo -e "${GREEN}Done! The API should now have access to Essen data.${NC}"
echo ""
echo "Test with: curl https://\${DOMAIN}/where?id=418354"
