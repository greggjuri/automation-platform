#!/bin/bash
# scripts/setup-cognito-authorizer.sh
# Add JWT authorizer to API Gateway for protected routes
set -e

REGION="us-east-1"
ACCOUNT_ID="490004610151"
API_NAME="golf-ghost-api"
POOL_NAME="golf-ghost-users"
AUTHORIZER_NAME="golf-ghost-cognito-auth"

echo "=== Golf Ghost Cognito Authorizer Setup ==="
echo ""

# Get User Pool ID
echo "Looking up User Pool..."
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 --region $REGION \
  --query "UserPools[?Name=='$POOL_NAME'].Id" --output text)

if [ -z "$USER_POOL_ID" ] || [ "$USER_POOL_ID" == "None" ]; then
  echo "Error: User Pool '$POOL_NAME' not found. Run setup-cognito.sh first."
  exit 1
fi
echo "Found User Pool: $USER_POOL_ID"

# Get App Client ID
echo "Looking up App Client..."
CLIENT_ID=$(aws cognito-idp list-user-pool-clients \
  --user-pool-id $USER_POOL_ID \
  --region $REGION \
  --query "UserPoolClients[?ClientName=='golf-ghost-web'].ClientId" --output text)

if [ -z "$CLIENT_ID" ] || [ "$CLIENT_ID" == "None" ]; then
  echo "Error: App Client not found. Run setup-cognito.sh first."
  exit 1
fi
echo "Found App Client: $CLIENT_ID"

# Get API Gateway ID
echo "Looking up API Gateway..."
API_ID=$(aws apigatewayv2 get-apis --region $REGION \
  --query "Items[?Name=='$API_NAME'].ApiId" --output text)

if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
  echo "Error: API Gateway '$API_NAME' not found. Run setup-api-gateway.sh first."
  exit 1
fi
echo "Found API Gateway: $API_ID"

# Construct issuer URL
ISSUER="https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}"
echo ""
echo "JWT Issuer: $ISSUER"
echo "JWT Audience: $CLIENT_ID"

# Check if authorizer exists
echo ""
echo "Checking for existing authorizer..."
EXISTING_AUTHORIZER=$(aws apigatewayv2 get-authorizers \
  --api-id $API_ID \
  --region $REGION \
  --query "Items[?Name=='$AUTHORIZER_NAME'].AuthorizerId" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_AUTHORIZER" ] && [ "$EXISTING_AUTHORIZER" != "None" ]; then
  echo "Authorizer already exists: $EXISTING_AUTHORIZER"
  AUTHORIZER_ID=$EXISTING_AUTHORIZER

  # Update existing authorizer
  echo "Updating authorizer configuration..."
  aws apigatewayv2 update-authorizer \
    --api-id $API_ID \
    --authorizer-id $AUTHORIZER_ID \
    --jwt-configuration "Issuer=$ISSUER,Audience=$CLIENT_ID" \
    --region $REGION > /dev/null
else
  # Create JWT authorizer
  echo "Creating JWT authorizer..."
  AUTHORIZER_ID=$(aws apigatewayv2 create-authorizer \
    --api-id $API_ID \
    --name $AUTHORIZER_NAME \
    --authorizer-type JWT \
    --identity-source '$request.header.Authorization' \
    --jwt-configuration "Issuer=$ISSUER,Audience=$CLIENT_ID" \
    --region $REGION \
    --query 'AuthorizerId' --output text)

  echo "Created authorizer: $AUTHORIZER_ID"
fi

# Function to add authorizer to a route
add_auth_to_route() {
  local ROUTE_KEY=$1

  echo "  Updating route: $ROUTE_KEY"

  # Get route ID
  ROUTE_ID=$(aws apigatewayv2 get-routes \
    --api-id $API_ID \
    --region $REGION \
    --query "Items[?RouteKey=='$ROUTE_KEY'].RouteId" --output text)

  if [ -z "$ROUTE_ID" ] || [ "$ROUTE_ID" == "None" ]; then
    echo "    Warning: Route '$ROUTE_KEY' not found, skipping..."
    return 0
  fi

  # Update route with authorizer
  aws apigatewayv2 update-route \
    --api-id $API_ID \
    --route-id $ROUTE_ID \
    --authorization-type JWT \
    --authorizer-id $AUTHORIZER_ID \
    --region $REGION > /dev/null

  echo "    Added JWT auth to route: $ROUTE_KEY"
}

# Add authorizer to protected routes
echo ""
echo "Adding authorizer to protected routes..."
add_auth_to_route "POST /courses"
add_auth_to_route "PUT /courses/{id}"
add_auth_to_route "DELETE /courses/{id}"

# Verify public routes have no auth
echo ""
echo "Verifying public routes remain open..."
for ROUTE_KEY in "GET /courses" "POST /generate-score"; do
  ROUTE_ID=$(aws apigatewayv2 get-routes \
    --api-id $API_ID \
    --region $REGION \
    --query "Items[?RouteKey=='$ROUTE_KEY'].RouteId" --output text)

  if [ -n "$ROUTE_ID" ] && [ "$ROUTE_ID" != "None" ]; then
    AUTH_TYPE=$(aws apigatewayv2 get-route \
      --api-id $API_ID \
      --route-id $ROUTE_ID \
      --region $REGION \
      --query 'AuthorizationType' --output text)

    if [ "$AUTH_TYPE" == "NONE" ] || [ "$AUTH_TYPE" == "None" ]; then
      echo "  $ROUTE_KEY: Public (no auth) - OK"
    else
      echo "  Warning: $ROUTE_KEY has auth type: $AUTH_TYPE"
      # Remove auth from public routes
      aws apigatewayv2 update-route \
        --api-id $API_ID \
        --route-id $ROUTE_ID \
        --authorization-type NONE \
        --region $REGION > /dev/null
      echo "  $ROUTE_KEY: Reset to public"
    fi
  fi
done

# Get API endpoint
API_ENDPOINT=$(aws apigatewayv2 get-api --api-id $API_ID --region $REGION \
  --query 'ApiEndpoint' --output text)

echo ""
echo "============================================"
echo "Cognito Authorizer Setup Complete!"
echo ""
echo "Authorizer ID: $AUTHORIZER_ID"
echo "API Endpoint: $API_ENDPOINT/prod"
echo ""
echo "Protected Routes (require JWT):"
echo "  - POST /courses"
echo "  - PUT /courses/{id}"
echo "  - DELETE /courses/{id}"
echo ""
echo "Public Routes (no auth):"
echo "  - GET /courses"
echo "  - POST /generate-score"
echo ""
echo "============================================"
echo ""
echo "Test protected route without token (should return 401):"
echo "  curl -X POST ${API_ENDPOINT}/prod/courses -H 'Content-Type: application/json' -d '{\"name\":\"Test\"}'"
echo ""
echo "Test public route (should work):"
echo "  curl ${API_ENDPOINT}/prod/courses"
