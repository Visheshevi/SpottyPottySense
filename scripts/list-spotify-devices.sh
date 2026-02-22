#!/bin/bash

###############################################################################
# List Available Spotify Devices
#
# Shows all Spotify devices (speakers, computers, phones) that can play music.
#
# Usage:
#   ./scripts/list-spotify-devices.sh [USER_ID]
#
###############################################################################

set -e

REGION="${AWS_REGION:-us-east-2}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}🔊 Available Spotify Devices${NC}"
echo "============================"
echo ""

# Get user ID
if [ -z "$1" ]; then
  read -p "Enter your User ID (from setup-spotify-oauth.sh): " USER_ID
else
  USER_ID="$1"
fi

if [ -z "$USER_ID" ]; then
  echo -e "${YELLOW}⚠ No user ID provided${NC}"
  exit 1
fi

# Get access token from Secrets Manager
# AWS Secrets Manager doesn't allow colons, replace with hyphens
SECRET_USER_ID="${USER_ID//:/-}"
SECRET_NAME="spotty-potty-sense/spotify/users/${SECRET_USER_ID}"

echo "Fetching tokens from Secrets Manager..."
if ! SECRET_VALUE=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_NAME" \
  --region "$REGION" \
  --query SecretString \
  --output text 2>&1); then
  echo -e "${RED}✗ Failed to get tokens for user: $USER_ID${NC}"
  echo "Make sure you've run ./scripts/setup-spotify-oauth.sh first"
  exit 1
fi

ACCESS_TOKEN=$(echo "$SECRET_VALUE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Get devices from Spotify API
echo "Fetching devices from Spotify..."
DEVICES_RESPONSE=$(curl -s -X GET "https://api.spotify.com/v1/me/player/devices" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

# Check for errors
if echo "$DEVICES_RESPONSE" | grep -q "error"; then
  ERROR_MSG=$(echo "$DEVICES_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error', {}).get('message', 'Unknown error'))" 2>/dev/null || echo "Unknown error")
  echo -e "${RED}✗ Spotify API Error: $ERROR_MSG${NC}"
  
  if echo "$ERROR_MSG" | grep -q "token"; then
    echo ""
    echo "Your token may have expired. Try running:"
    echo "./scripts/setup-spotify-oauth.sh"
  fi
  exit 1
fi

# Parse and display devices
DEVICE_COUNT=$(echo "$DEVICES_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['devices']))")

if [ "$DEVICE_COUNT" -eq 0 ]; then
  echo -e "${YELLOW}⚠ No Spotify devices found${NC}"
  echo ""
  echo "Make sure you have:"
  echo "1. Spotify app open on at least one device"
  echo "2. A Spotify Premium account (required for playback control)"
  echo ""
  exit 0
fi

echo ""
echo -e "${GREEN}Found $DEVICE_COUNT device(s):${NC}"
echo ""

# Create temporary Python script to parse and display devices
PARSE_SCRIPT=$(mktemp)
cat > "$PARSE_SCRIPT" << 'PYTHON_EOF'
import sys
import json

data = json.load(sys.stdin)
devices = data['devices']

for i, device in enumerate(devices, 1):
    print(f"{i}. {device['name']}")
    print(f"   ID: {device['id']}")
    print(f"   Type: {device['type']}")
    print(f"   Active: {'Yes' if device['is_active'] else 'No'}")
    if device.get('volume_percent') is not None:
        print(f"   Volume: {device['volume_percent']}%")
    print()

# Output device IDs as JSON for easy parsing
print("---DEVICE_IDS---")
print(json.dumps([d['id'] for d in devices]))
PYTHON_EOF

OUTPUT=$(echo "$DEVICES_RESPONSE" | python3 "$PARSE_SCRIPT")
rm -f "$PARSE_SCRIPT"

# Extract and display devices
DEVICE_LIST=$(echo "$OUTPUT" | sed '/---DEVICE_IDS---/q' | sed '$d')
DEVICE_IDS=$(echo "$OUTPUT" | grep -A1 "---DEVICE_IDS---" | tail -n 1)

echo "$DEVICE_LIST"

# Prompt to copy a device ID
echo ""
read -p "Enter device number to copy ID (or press Enter to skip): " CHOICE

if [ ! -z "$CHOICE" ]; then
  if [ "$CHOICE" -ge 1 ] && [ "$CHOICE" -le "$DEVICE_COUNT" ] 2>/dev/null; then
    # Calculate array index (device number - 1)
    INDEX=$((CHOICE - 1))
    
    # Extract device ID directly from the original response
    SELECTED_ID=$(echo "$DEVICES_RESPONSE" | python3 -c "import sys, json; devices=json.load(sys.stdin)['devices']; print(devices[$INDEX]['id'])")
    
    if [ ! -z "$SELECTED_ID" ]; then
      # Copy to clipboard
      if command -v pbcopy > /dev/null; then
        echo "$SELECTED_ID" | pbcopy
        echo ""
        echo -e "${GREEN}✓ Copied device ID to clipboard${NC}"
      elif command -v xclip > /dev/null; then
        echo "$SELECTED_ID" | xclip -selection clipboard
        echo ""
        echo -e "${GREEN}✓ Copied device ID to clipboard${NC}"
      else
        echo ""
        echo -e "${GREEN}Device ID:${NC} $SELECTED_ID"
        echo "(Clipboard not available - copy manually)"
      fi
      
      echo ""
      echo "Use this ID when registering your sensor."
    else
      echo "Failed to extract device ID."
    fi
  else
    echo "Invalid selection."
  fi
fi

echo ""
echo "Next step: ./scripts/register-sensor.sh"
echo ""
