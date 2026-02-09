#!/bin/bash
#
# Run Integration Tests for SpottyPottySense
#
# Usage: ./scripts/run-integration-tests.sh [test_name]
#
# Examples:
#   ./scripts/run-integration-tests.sh                    # Run all tests
#   ./scripts/run-integration-tests.sh test_001           # Run specific test
#   ./scripts/run-integration-tests.sh --verbose          # Verbose output

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="us-east-2"
STACK_NAME="spotty-potty-sense"
TEST_DIR="backend/tests/integration"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       SpottyPottySense Integration Test Runner                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest not found. Please install it: pip install pytest${NC}"
    exit 1
fi

# Check if stack exists
echo -e "${YELLOW}Checking CloudFormation stack...${NC}"
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo -e "${RED}✗ Stack '$STACK_NAME' not found in region '$AWS_REGION'${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Stack found${NC}"
echo ""

# Get API Gateway URL
echo -e "${YELLOW}Retrieving API Gateway endpoint...${NC}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayEndpoint`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -n "$API_URL" ]; then
    echo -e "${GREEN}✓ API Gateway: $API_URL${NC}"
else
    echo -e "${YELLOW}  No API Gateway URL found (may not be exposed)${NC}"
fi
echo ""

# Set up environment
export AWS_DEFAULT_REGION="$AWS_REGION"
export STACK_NAME="$STACK_NAME"

# Determine test to run
TEST_PATTERN="${1:-test_e2e_flow.py}"

# Check if running verbose mode
PYTEST_ARGS="-v"
if [[ "$1" == "--verbose" ]] || [[ "$2" == "--verbose" ]]; then
    PYTEST_ARGS="-v -s"
fi

# Run tests
echo -e "${BLUE}Running integration tests...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if pytest "$TEST_DIR/$TEST_PATTERN" $PYTEST_ARGS --tb=short; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✓ All Integration Tests Passed!                  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║              ✗ Some Integration Tests Failed                   ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
