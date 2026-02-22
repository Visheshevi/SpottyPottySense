#!/bin/bash

###############################################################################
# SpottyPottySense - Spotify OAuth Setup Script
#
# This script helps you authenticate with Spotify and obtain OAuth tokens
# (refresh_token and access_token) for your account.
#
# Prerequisites:
# - Spotify Developer App created with Client ID/Secret
# - Client credentials stored in AWS Secrets Manager
# - Python 3 installed (for local callback server)
#
# Usage:
#   ./scripts/setup-spotify-oauth.sh
#
###############################################################################

set -e

# Configuration
REGION="${AWS_REGION:-us-east-2}"
CLIENT_SECRET_NAME="spotty-potty-sense/spotify/client"
REDIRECT_URI="http://127.0.0.1:8888/callback"
SCOPES="user-read-playback-state user-modify-playback-state user-read-currently-playing"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

###############################################################################
# Helper Functions
###############################################################################

print_header() {
  echo ""
  echo -e "${BLUE}🎵 SpottyPottySense Spotify OAuth Setup${NC}"
  echo "========================================"
  echo ""
}

print_step() {
  echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ Error: $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

###############################################################################
# Main Script
###############################################################################

print_header

# Step 1: Get Spotify client credentials from Secrets Manager
print_step "Retrieving Spotify client credentials from AWS Secrets Manager..."

if ! CLIENT_CREDS=$(aws secretsmanager get-secret-value \
  --secret-id "$CLIENT_SECRET_NAME" \
  --region "$REGION" \
  --query SecretString \
  --output text 2>&1); then
  print_error "Failed to retrieve Spotify client credentials"
  echo ""
  echo "Please create the secret first:"
  echo ""
  echo "aws secretsmanager create-secret \\"
  echo "  --name \"$CLIENT_SECRET_NAME\" \\"
  echo "  --secret-string '{\"client_id\":\"YOUR_CLIENT_ID\",\"client_secret\":\"YOUR_CLIENT_SECRET\"}' \\"
  echo "  --region $REGION"
  echo ""
  exit 1
fi

CLIENT_ID=$(echo "$CLIENT_CREDS" | python3 -c "import sys, json; print(json.load(sys.stdin)['client_id'])")
CLIENT_SECRET=$(echo "$CLIENT_CREDS" | python3 -c "import sys, json; print(json.load(sys.stdin)['client_secret'])")

print_success "Retrieved client credentials"

# Step 2: Generate authorization URL
print_step "Generating Spotify authorization URL..."

AUTH_URL="https://accounts.spotify.com/authorize"
AUTH_URL="${AUTH_URL}?client_id=${CLIENT_ID}"
AUTH_URL="${AUTH_URL}&response_type=code"
AUTH_URL="${AUTH_URL}&redirect_uri=${REDIRECT_URI}"
AUTH_URL="${AUTH_URL}&scope=${SCOPES// /%20}"

echo ""
echo -e "${YELLOW}Authorization URL:${NC}"
echo "$AUTH_URL"
echo ""

# Step 3: Start local callback server and wait for authorization
print_step "Starting local callback server on http://127.0.0.1:8888"

# Create temporary Python callback server
CALLBACK_SCRIPT=$(mktemp)
cat > "$CALLBACK_SCRIPT" << 'PYTHON_EOF'
import http.server
import urllib.parse
import sys
import threading
import time

auth_code = None
server_ready = False

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = '''
                <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #1DB954;">Success!</h1>
                    <p>Authorization complete. You can close this window.</p>
                    <p style="color: #666;">Return to your terminal.</p>
                </body></html>
            '''
            self.wfile.write(html.encode('utf-8'))
        elif 'error' in params:
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = f'<html><body><h1>Error</h1><p>{params["error"][0]}</p></body></html>'
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write('Waiting for authorization...'.encode('utf-8'))
        
    def log_message(self, format, *args):
        pass  # Suppress server logs

try:
    server = http.server.HTTPServer(('127.0.0.1', 8888), CallbackHandler)
    server.timeout = 1  # 1 second timeout per request
    
    # Signal that server is ready
    print("SERVER_READY", flush=True)
    
    # Handle requests until we get the auth code (max 5 minutes)
    start_time = time.time()
    while auth_code is None and (time.time() - start_time) < 300:
        server.handle_request()
    
    if auth_code:
        print(auth_code)
    else:
        print("ERROR: Timeout waiting for authorization", file=sys.stderr)
        sys.exit(1)
        
except KeyboardInterrupt:
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF

# Start Python server in background and capture output
echo ""
echo "Starting callback server..."
python3 "$CALLBACK_SCRIPT" > /tmp/spotify_oauth_output.txt 2>&1 &
SERVER_PID=$!

# Wait for server to be ready (max 5 seconds)
for i in {1..10}; do
  if grep -q "SERVER_READY" /tmp/spotify_oauth_output.txt 2>/dev/null; then
    print_success "Callback server is listening on http://127.0.0.1:8888"
    break
  fi
  if ! kill -0 $SERVER_PID 2>/dev/null; then
    print_error "Server failed to start"
    cat /tmp/spotify_oauth_output.txt
    rm -f "$CALLBACK_SCRIPT" /tmp/spotify_oauth_output.txt
    exit 1
  fi
  sleep 0.5
done

# Open browser now that server is ready
echo ""
echo "Opening browser for Spotify authorization..."
echo "Please log in and approve the permissions."
echo ""

if command -v open > /dev/null; then
  open "$AUTH_URL"  # macOS
elif command -v xdg-open > /dev/null; then
  xdg-open "$AUTH_URL"  # Linux
elif command -v start > /dev/null; then
  start "$AUTH_URL"  # Windows
else
  echo "Please open this URL in your browser manually:"
  echo "$AUTH_URL"
fi

# Wait for the server to complete and get the auth code
print_step "Waiting for authorization callback..."
wait $SERVER_PID
SERVER_EXIT=$?

if [ $SERVER_EXIT -ne 0 ]; then
  rm -f "$CALLBACK_SCRIPT"
  cat /tmp/spotify_oauth_output.txt
  rm -f /tmp/spotify_oauth_output.txt
  print_error "Authorization failed or timed out"
  exit 1
fi

# Read the auth code from output
AUTH_CODE=$(grep -v "SERVER_READY" /tmp/spotify_oauth_output.txt | grep -v "^ERROR" | head -n 1)
rm -f /tmp/spotify_oauth_output.txt

rm -f "$CALLBACK_SCRIPT"

if [ -z "$AUTH_CODE" ] || echo "$AUTH_CODE" | grep -q "ERROR"; then
  print_error "No authorization code received"
  exit 1
fi

print_success "Authorization code received!"

# Step 4: Exchange authorization code for tokens
print_step "Exchanging authorization code for tokens..."

TOKEN_RESPONSE=$(curl -s -X POST "https://accounts.spotify.com/api/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=$AUTH_CODE" \
  -d "redirect_uri=$REDIRECT_URI" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET")

if ! echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
  print_error "Token exchange failed"
  echo "$TOKEN_RESPONSE" | python3 -m json.tool
  exit 1
fi

REFRESH_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['refresh_token'])")
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
EXPIRES_IN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['expires_in'])")

# Calculate expiration timestamp
EXPIRES_AT=$(date -u -v+${EXPIRES_IN}S +%s 2>/dev/null || date -u -d "+${EXPIRES_IN} seconds" +%s)

print_success "Token exchange successful!"

# Step 5: Get Spotify user ID
print_step "Fetching your Spotify user profile..."

USER_PROFILE=$(curl -s -X GET "https://api.spotify.com/v1/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

SPOTIFY_USER_ID=$(echo "$USER_PROFILE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
SPOTIFY_EMAIL=$(echo "$USER_PROFILE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('email', 'N/A'))")

print_success "Profile retrieved"
echo "   User ID: $SPOTIFY_USER_ID"
echo "   Email: $SPOTIFY_EMAIL"

# Step 6: Store tokens in Secrets Manager
print_step "Storing tokens in AWS Secrets Manager..."

# Use Cognito username as user ID (or Spotify ID if Cognito not yet set up)
# Prompt user for their Cognito user ID
echo ""
read -p "Enter your Cognito User ID (or press Enter to use Spotify ID): " COGNITO_USER_ID

if [ -z "$COGNITO_USER_ID" ]; then
  USER_ID="spotify:$SPOTIFY_USER_ID"
  print_warning "Using Spotify ID as user identifier. Update to Cognito ID later."
else
  USER_ID="$COGNITO_USER_ID"
fi

# AWS Secrets Manager doesn't allow colons in names, so replace with hyphens
SECRET_USER_ID="${USER_ID//:/-}"
SECRET_NAME="spotty-potty-sense/spotify/users/${SECRET_USER_ID}"

SECRET_VALUE=$(cat <<EOF
{
  "refresh_token": "$REFRESH_TOKEN",
  "access_token": "$ACCESS_TOKEN",
  "expires_at": $EXPIRES_AT,
  "spotify_user_id": "$SPOTIFY_USER_ID",
  "email": "$SPOTIFY_EMAIL"
}
EOF
)

aws secretsmanager create-secret \
  --name "$SECRET_NAME" \
  --description "Spotify tokens for user $USER_ID" \
  --secret-string "$SECRET_VALUE" \
  --region "$REGION" > /dev/null 2>&1 || \
aws secretsmanager update-secret \
  --secret-id "$SECRET_NAME" \
  --secret-string "$SECRET_VALUE" \
  --region "$REGION" > /dev/null

print_success "Tokens stored in AWS Secrets Manager"
echo "   Secret: $SECRET_NAME"
echo "   User ID: $USER_ID"

# Step 7: Create/update user record in DynamoDB
print_step "Creating user record in DynamoDB..."

# Get Users table name
USERS_TABLE=$(aws cloudformation describe-stacks \
  --stack-name spotty-potty-sense \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`UsersTableName`].OutputValue' \
  --output text 2>/dev/null || echo "spotty-potty-sense-UsersTable")

if [ -z "$USERS_TABLE" ]; then
  print_error "Could not find UsersTable name"
  exit 1
fi

USER_ITEM=$(cat <<EOF
{
  "userId": {"S": "$USER_ID"},
  "email": {"S": "$SPOTIFY_EMAIL"},
  "spotifyUserId": {"S": "$SPOTIFY_USER_ID"},
  "isActive": {"BOOL": true},
  "createdAt": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
  "updatedAt": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
}
EOF
)

aws dynamodb put-item \
  --table-name "$USERS_TABLE" \
  --item "$USER_ITEM" \
  --region "$REGION" > /dev/null

print_success "User record created"

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Spotify OAuth Setup Complete! ✓             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Your User ID: $USER_ID"
echo ""
echo "Next steps:"
echo "1. List your Spotify devices: ./scripts/list-spotify-devices.sh"
echo "2. Register your sensor: ./scripts/register-sensor.sh"
echo "3. Test motion detection!"
echo ""
