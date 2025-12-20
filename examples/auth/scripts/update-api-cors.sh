#!/bin/bash
# scripts/update-api-cors.sh
# Update CORS configuration on existing API Gateway to include Authorization header
set -e

REGION="us-east-1"
API_NAME="golf-ghost-api"

echo "=== Golf Ghost API Gateway CORS Update ==="
echo ""

# Get API Gateway ID
echo "Looking up API Gateway..."
API_ID=$(aws apigatewayv2 get-apis --region $REGION \
  --query "Items[?Name=='$API_NAME'].ApiId" --output text)

if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
  echo "Error: API Gateway '$API_NAME' not found."
  exit 1
fi
echo "Found API Gateway: $API_ID"

# Update CORS configuration
echo ""
echo "Updating CORS configuration to include Authorization header..."
aws apigatewayv2 update-api \
  --api-id $API_ID \
  --cors-configuration '{
    "AllowOrigins": ["https://ghost.jurigregg.com", "http://localhost:3000"],
    "AllowMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "AllowHeaders": ["Content-Type", "Authorization"],
    "AllowCredentials": false
  }' \
  --region $REGION > /dev/null

echo ""
echo "============================================"
echo "CORS updated successfully!"
echo ""
echo "AllowHeaders now includes: Content-Type, Authorization"
echo "============================================"
