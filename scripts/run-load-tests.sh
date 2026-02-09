#!/bin/bash
#
# Run Load Tests for SpottyPottySense API
#
# Usage: ./scripts/run-load-tests.sh [profile]
#
# Profiles:
#   smoke    - Quick smoke test (low load)
#   standard - Standard load test
#   stress   - Stress test (high load)
#   spike    - Spike test (sudden load increase)

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
AWS_REGION="us-east-2"
STACK_NAME="spotty-potty-sense"
LOAD_TEST_DIR="load-testing"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          SpottyPottySense Load Test Runner                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Artillery is installed
if ! command -v artillery &> /dev/null; then
    echo -e "${YELLOW}Artillery not found. Installing...${NC}"
    npm install -g artillery
fi

# Get API Gateway URL
echo -e "${YELLOW}Retrieving API Gateway endpoint...${NC}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayEndpoint`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -z "$API_URL" ]; then
    echo -e "${RED}✗ Could not retrieve API Gateway URL${NC}"
    echo -e "${YELLOW}  Please update load-testing/artillery-config.yml manually${NC}"
    exit 1
fi

echo -e "${GREEN}✓ API Gateway: $API_URL${NC}"
echo ""

# Update Artillery config with API URL
sed -i.bak "s|target: \".*\"|target: \"$API_URL\"|g" "$LOAD_TEST_DIR/artillery-config.yml"
echo -e "${GREEN}✓ Updated Artillery configuration${NC}"
echo ""

# Determine test profile
PROFILE="${1:-standard}"

case $PROFILE in
    smoke)
        echo -e "${BLUE}Running smoke test (low load)...${NC}"
        artillery run "$LOAD_TEST_DIR/artillery-config.yml" \
            --config '{"phases":[{"duration":30,"arrivalRate":1}]}' \
            --output "$LOAD_TEST_DIR/results/smoke-$(date +%Y%m%d-%H%M%S).json"
        ;;
    
    standard)
        echo -e "${BLUE}Running standard load test...${NC}"
        artillery run "$LOAD_TEST_DIR/artillery-config.yml" \
            --output "$LOAD_TEST_DIR/results/standard-$(date +%Y%m%d-%H%M%S).json"
        ;;
    
    stress)
        echo -e "${BLUE}Running stress test (high load)...${NC}"
        artillery run "$LOAD_TEST_DIR/artillery-config.yml" \
            --config '{"phases":[{"duration":60,"arrivalRate":100}]}' \
            --output "$LOAD_TEST_DIR/results/stress-$(date +%Y%m%d-%H%M%S).json"
        ;;
    
    spike)
        echo -e "${BLUE}Running spike test (sudden load)...${NC}"
        artillery run "$LOAD_TEST_DIR/artillery-config.yml" \
            --config '{"phases":[{"duration":10,"arrivalRate":5},{"duration":30,"arrivalRate":200},{"duration":10,"arrivalRate":5}]}' \
            --output "$LOAD_TEST_DIR/results/spike-$(date +%Y%m%d-%H%M%S).json"
        ;;
    
    *)
        echo -e "${RED}Unknown profile: $PROFILE${NC}"
        echo "Available profiles: smoke, standard, stress, spike"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Load Test Complete!                          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Results saved to: $LOAD_TEST_DIR/results/${NC}"
