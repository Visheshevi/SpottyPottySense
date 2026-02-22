#!/bin/bash

###############################################################################
# Register Sensor with Full Configuration
#
# Registers a sensor with user, location, and Spotify playback settings.
#
# Prerequisites:
# - Device provisioned (./scripts/provision-esp8266.sh)
# - User created (./scripts/create-user.sh)
# - Spotify OAuth tokens stored (./scripts/setup-spotify-oauth.sh)
# - Spotify device ID identified (./scripts/list-spotify-devices.sh)
#
# Usage:
#   ./scripts/register-sensor.sh
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
echo -e "${BLUE}🔧 Register Sensor with Configuration${NC}"
echo "======================================"
echo ""

# Get Lambda function name (try output first, then search by name pattern)
FUNCTION_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`DeviceRegistrationFunctionName`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$FUNCTION_NAME" ] || [ "$FUNCTION_NAME" = "None" ]; then
  echo "Searching for DeviceRegistrationFunction..."
  FUNCTION_NAME=$(aws lambda list-functions \
    --region "$REGION" \
    --query 'Functions[?contains(FunctionName, `DeviceRegistration`) || contains(FunctionName, `device-registration`)].FunctionName' \
    --output text | head -n 1)
fi

if [ -z "$FUNCTION_NAME" ]; then
  echo -e "${RED}✗ Could not find DeviceRegistrationFunction${NC}"
  echo "Make sure the backend is deployed: sam build && sam deploy"
  exit 1
fi

echo -e "${GREEN}✓ Found function: $FUNCTION_NAME${NC}"
echo ""

# Collect sensor details
read -p "Sensor ID [bathroom-main]: " SENSOR_ID
SENSOR_ID=${SENSOR_ID:-bathroom-main}

read -p "Location [Main Bathroom]: " LOCATION
LOCATION=${LOCATION:-Main Bathroom}

read -p "Sensor Name [${SENSOR_ID}]: " SENSOR_NAME
SENSOR_NAME=${SENSOR_NAME:-${SENSOR_ID}}

read -p "User ID (from create-user.sh): " USER_ID

if [ -z "$USER_ID" ]; then
  echo -e "${RED}✗ User ID is required${NC}"
  exit 1
fi

read -p "Spotify Device ID (from list-spotify-devices.sh): " SPOTIFY_DEVICE_ID

if [ -z "$SPOTIFY_DEVICE_ID" ]; then
  echo -e "${YELLOW}⚠ Warning: No Spotify device ID provided${NC}"
  echo "Playback may not work until you update the sensor configuration."
fi

read -p "Playlist URI [spotify:playlist:37i9dQZF1DXcBWIGoYBM5M]: " PLAYLIST_URI
PLAYLIST_URI=${PLAYLIST_URI:-spotify:playlist:37i9dQZF1DXcBWIGoYBM5M}

read -p "Timeout Minutes [5]: " TIMEOUT_MINUTES
TIMEOUT_MINUTES=${TIMEOUT_MINUTES:-5}

read -p "Motion Debounce Minutes [2]: " DEBOUNCE_MINUTES
DEBOUNCE_MINUTES=${DEBOUNCE_MINUTES:-2}

# Build registration payload
PAYLOAD=$(cat <<EOF
{
  "action": "register",
  "sensorId": "$SENSOR_ID",
  "location": "$LOCATION",
  "name": "$SENSOR_NAME",
  "userId": "$USER_ID",
  "spotifyDeviceId": "$SPOTIFY_DEVICE_ID",
  "playlistUri": "$PLAYLIST_URI",
  "timeoutMinutes": $TIMEOUT_MINUTES,
  "motionDebounceMinutes": $DEBOUNCE_MINUTES
}
EOF
)

echo ""
echo -e "${BLUE}Registration Payload:${NC}"
echo "$PAYLOAD" | python3 -m json.tool
echo ""

read -p "Proceed with registration? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  echo "Cancelled."
  exit 0
fi

# Invoke DeviceRegistrationFunction
echo ""
echo "Registering sensor..."

# Use temporary file to capture response
RESPONSE_FILE=$(mktemp)
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --payload "$PAYLOAD" \
  --cli-binary-format raw-in-base64-out \
  "$RESPONSE_FILE" > /dev/null

RESPONSE=$(cat "$RESPONSE_FILE")
rm -f "$RESPONSE_FILE"

# Parse response
STATUS_CODE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('statusCode', 500))" 2>/dev/null || echo "500")

if [ "$STATUS_CODE" -ne 200 ]; then
  echo -e "${RED}✗ Registration failed${NC}"
  echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
  exit 1
fi

echo ""
echo -e "${GREEN}✓ Sensor registered successfully!${NC}"
echo ""

# Display summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Registration Summary:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Sensor ID:       $SENSOR_ID"
echo "Location:        $LOCATION"
echo "User ID:         $USER_ID"
echo "Spotify Device:  ${SPOTIFY_DEVICE_ID:0:20}..."
echo "Playlist:        $PLAYLIST_URI"
echo "Timeout:         $TIMEOUT_MINUTES minutes"
echo "Debounce:        $DEBOUNCE_MINUTES minutes"
echo ""

# Verify in DynamoDB
echo "Verifying registration in DynamoDB..."
SENSORS_TABLE=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`SensorsTableName`].OutputValue' \
  --output text)

if [ ! -z "$SENSORS_TABLE" ]; then
  SENSOR_RECORD=$(aws dynamodb get-item \
    --table-name "$SENSORS_TABLE" \
    --key "{\"sensorId\":{\"S\":\"$SENSOR_ID\"}}" \
    --region "$REGION" \
    --output json 2>/dev/null || echo "{}")
  
  if echo "$SENSOR_RECORD" | grep -q "Item"; then
    echo -e "${GREEN}✓ Sensor record found in DynamoDB${NC}"
  else
    echo -e "${YELLOW}⚠ Could not verify sensor in DynamoDB${NC}"
  fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Sensor Registration Complete! ✓               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "🎉 Ready to test! Trigger motion on your ESP8266 sensor."
echo ""
echo "Monitor progress:"
echo "  • Serial Monitor: Watch ESP8266 output"
echo "  • AWS IoT Test Client: Subscribe to sensors/$SENSOR_ID/motion"
echo "  • Lambda Logs: aws logs tail /aws/lambda/spotty-potty-sense-MotionHandlerFunction --follow --region $REGION"
echo ""
