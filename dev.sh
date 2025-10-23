#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Essen Route Planning - Local Development${NC}"
echo ""

# Check if Essen data exists
if [ ! -f "data/output/essen_exhibitors.json" ] || [ ! -f "data/output/essen_products.json" ]; then
    echo -e "${YELLOW}⚠️  Essen data not found locally!${NC}"
    echo ""
    echo "The API needs Essen exhibitor and product data to work."
    echo "You have two options:"
    echo ""
    echo "  1. Fetch data using the CLI tool:"
    echo "     ${BLUE}./scripts/step_03${NC}"
    echo ""
    echo "  2. Continue without data (API will return 503 errors)"
    echo ""
    read -p "Fetch Essen data now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Fetching Essen data...${NC}"

        # Check if venv exists
        if [ ! -d "venv" ]; then
            echo -e "${BLUE}Creating virtual environment...${NC}"
            python3 -m venv venv
            source venv/bin/activate
            pip install -r requirements.txt
        else
            source venv/bin/activate
        fi

        # Run step 3
        python3 src/steps/step3_fetch_essen_data.py

        echo -e "${GREEN}✓ Essen data fetched${NC}"
        echo ""
    fi
fi

# Build the image
echo -e "${BLUE}Building Docker image...${NC}"
docker build -f deploy/docker/Dockerfile.dev -t essen-api-dev .
echo -e "${GREEN}✓ Image built${NC}"
echo ""

# Run the container
echo -e "${BLUE}Starting Docker container...${NC}"
echo -e "${YELLOW}API will be available at: http://localhost:8000${NC}"
echo ""

docker run --rm -it \
  -p 8000:8000 \
  -v "$(pwd)/src:/app/src:ro" \
  -v "$(pwd)/data:/app/data" \
  --name essen-api-dev \
  essen-api-dev

# Note: --rm removes container on exit, -it for interactive logs
# Volume mounts enable live reload
