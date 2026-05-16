#!/bin/bash
# Anomaly Detection Pipeline Challenge - Submission Script
#
# This script validates your submission locally and pushes to the remote repository.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo " Anomaly Detection Pipeline Challenge"
echo " Submission Validator"
echo "========================================"
echo ""

# Check if docker compose is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker is not installed${NC}"
    exit 1
fi

# Check docker-compose.yml is not the default template
if grep -q "placeholder:" docker-compose.yml 2>/dev/null; then
    echo -e "${YELLOW}Warning: docker-compose.yml still contains the placeholder service.${NC}"
    echo -e "${YELLOW}Make sure you have defined your pipeline services.${NC}"
    echo ""
fi

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ] && [ ! -f "Dockerfile.template" ]; then
    echo -e "${YELLOW}Warning: No Dockerfile found. Make sure docker-compose.yml references a valid build context.${NC}"
    echo ""
fi

# Validate output directory
echo "Checking output directory..."
mkdir -p output

# Try building
echo ""
echo "Building Docker images..."
if docker compose build 2>&1; then
    echo -e "${GREEN}Build successful!${NC}"
else
    echo -e "${RED}Build failed. Please fix the errors above.${NC}"
    exit 1
fi

# Try running
echo ""
echo "Running pipeline..."
START_TIME=$(date +%s)

if docker compose up --abort-on-container-exit 2>&1; then
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    echo -e "${GREEN}Pipeline completed in ${ELAPSED} seconds${NC}"
else
    echo -e "${RED}Pipeline execution failed. Please fix the errors above.${NC}"
    docker compose down 2>/dev/null
    exit 1
fi

docker compose down 2>/dev/null

# Validate outputs
echo ""
echo "Validating outputs..."
ERRORS=0

if [ -f "output/anomalies.json" ]; then
    size=$(wc -c < "output/anomalies.json" | tr -d ' ')
    echo -e "  ${GREEN}✓${NC} Anomaly Detection (anomalies.json, ${size} bytes)"
else
    echo -e "  ${RED}✗${NC} Anomaly Detection (anomalies.json) - MISSING"
    ERRORS=$((ERRORS + 1))
fi

echo ""
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Output file missing. Please check your pipeline.${NC}"
    exit 1
fi

echo -e "${GREEN}Output file present!${NC}"
echo ""

# JSON validation
echo "Validating JSON format..."
if [ -f "output/anomalies.json" ]; then
    if python -c "import json; json.load(open('output/anomalies.json'))" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} anomalies.json is valid JSON"
    else
        echo -e "  ${RED}✗${NC} anomalies.json is not valid JSON"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Validation failed. Please fix the errors above before submitting.${NC}"
    exit 1
fi

echo -e "${GREEN}========================================"
echo " All validations passed!"
echo "========================================${NC}"
echo ""

# Git submission
echo "Ready to submit?"
echo "This will commit and push your changes to the remote repository."
read -p "Proceed? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Submitting..."
    git add -A
    git commit -m "Submit pipeline solution" || true
    git push origin HEAD
    echo ""
    echo -e "${GREEN}Submission complete!${NC}"
    echo "Your solution will be automatically graded. You will receive your score shortly."
else
    echo "Submission cancelled."
    echo "Run this script again when you're ready to submit."
fi
