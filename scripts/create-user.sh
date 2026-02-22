#!/bin/bash

###############################################################################
# Create Cognito User Account
#
# Creates a new user in the Cognito User Pool for SpottyPottySense.
#
# Usage:
#   ./scripts/create-user.sh
#
###############################################################################

set -e

REGION="${AWS_REGION:-us-east-2}"
STACK_NAME="spotty-potty-sense"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BLUE}👤 Create SpottyPottySense User${NC}"
echo "==============================="
echo ""

# Get User Pool ID from CloudFormation
echo "Fetching Cognito User Pool ID..."
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

if [ -z "$USER_POOL_ID" ]; then
  echo -e "${RED}✗ Could not find User Pool ID${NC}"
  echo "Make sure the stack '$STACK_NAME' is deployed."
  exit 1
fi

echo -e "${GREEN}✓ User Pool: $USER_POOL_ID${NC}"
echo ""

# Get user details
read -p "Email address: " EMAIL
read -sp "Temporary password (min 8 chars, uppercase, lowercase, number, special): " PASSWORD
echo ""

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo -e "${RED}✗ Email and password are required${NC}"
  exit 1
fi

# Validate password strength
if [ ${#PASSWORD} -lt 8 ]; then
  echo -e "${RED}✗ Password must be at least 8 characters${NC}"
  exit 1
fi

# Create user
echo ""
echo "Creating user account..."

USER_OUTPUT=$(aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$EMAIL" \
  --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
  --temporary-password "$PASSWORD" \
  --message-action SUPPRESS \
  --region "$REGION" 2>&1)

if [ $? -ne 0 ]; then
  if echo "$USER_OUTPUT" | grep -q "UsernameExistsException"; then
    echo -e "${YELLOW}⚠ User already exists: $EMAIL${NC}"
    
    # Get existing user
    USER_SUB=$(aws cognito-idp admin-get-user \
      --user-pool-id "$USER_POOL_ID" \
      --username "$EMAIL" \
      --region "$REGION" \
      --query 'UserAttributes[?Name==`sub`].Value' \
      --output text)
    
    echo ""
    echo -e "${GREEN}User ID (sub): $USER_SUB${NC}"
    echo ""
    echo "To reset password:"
    echo "aws cognito-idp admin-set-user-password \\"
    echo "  --user-pool-id $USER_POOL_ID \\"
    echo "  --username $EMAIL \\"
    echo "  --password 'NewPassword123!' \\"
    echo "  --permanent \\"
    echo "  --region $REGION"
    echo ""
    exit 0
  else
    echo -e "${RED}✗ Failed to create user${NC}"
    echo "$USER_OUTPUT"
    exit 1
  fi
fi

# Extract user sub (unique ID)
USER_SUB=$(echo "$USER_OUTPUT" | python3 -c "import sys, json; attrs=json.load(sys.stdin)['User']['Attributes']; print(next(a['Value'] for a in attrs if a['Name']=='sub'))")

echo ""
echo -e "${GREEN}✓ User created successfully!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}User Details:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Email:     $EMAIL"
echo "User ID:   $USER_SUB"
echo "Status:    FORCE_CHANGE_PASSWORD (temporary)"
echo ""
echo -e "${YELLOW}⚠ Important:${NC} User must change password on first login."
echo ""

# Offer to set permanent password
read -p "Set permanent password now? (y/n): " SET_PASSWORD

if [ "$SET_PASSWORD" = "y" ] || [ "$SET_PASSWORD" = "Y" ]; then
  echo ""
  read -sp "New permanent password: " NEW_PASSWORD
  echo ""
  
  if [ ! -z "$NEW_PASSWORD" ]; then
    aws cognito-idp admin-set-user-password \
      --user-pool-id "$USER_POOL_ID" \
      --username "$EMAIL" \
      --password "$NEW_PASSWORD" \
      --permanent \
      --region "$REGION"
    
    echo ""
    echo -e "${GREEN}✓ Password set and confirmed${NC}"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Next Steps:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Save your User ID: $USER_SUB"
echo "2. Setup Spotify OAuth: ./scripts/setup-spotify-oauth.sh"
echo "3. Register sensor: ./scripts/register-sensor.sh"
echo ""
