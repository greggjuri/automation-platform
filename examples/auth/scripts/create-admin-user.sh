#!/bin/bash
# scripts/create-admin-user.sh
# Create an admin user in Cognito User Pool
set -e

REGION="us-east-1"
POOL_NAME="golf-ghost-users"

# Check for email argument
if [ -z "$1" ]; then
  echo "Usage: $0 <email>"
  echo "Example: $0 admin@example.com"
  exit 1
fi

EMAIL=$1

echo "=== Golf Ghost Admin User Creation ==="
echo ""

# Get User Pool ID
echo "Looking up User Pool ID..."
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 --region $REGION \
  --query "UserPools[?Name=='$POOL_NAME'].Id" --output text)

if [ -z "$USER_POOL_ID" ] || [ "$USER_POOL_ID" == "None" ]; then
  echo "Error: User Pool '$POOL_NAME' not found. Run setup-cognito.sh first."
  exit 1
fi

echo "Found User Pool: $USER_POOL_ID"
echo ""

# Check if user already exists
echo "Checking if user already exists..."
USER_EXISTS=$(aws cognito-idp list-users \
  --user-pool-id $USER_POOL_ID \
  --filter "email = \"$EMAIL\"" \
  --region $REGION \
  --query 'Users[0].Username' --output text 2>/dev/null || echo "None")

if [ -n "$USER_EXISTS" ] && [ "$USER_EXISTS" != "None" ]; then
  echo "User with email $EMAIL already exists."
  echo ""
  read -p "Do you want to reset their password? (y/n): " RESET_CONFIRM
  if [ "$RESET_CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 0
  fi
else
  # Create user
  echo "Creating user: $EMAIL..."
  aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
    --message-action SUPPRESS \
    --region $REGION > /dev/null

  echo "User created successfully."
fi

# Prompt for password
echo ""
echo "Password requirements:"
echo "  - At least 8 characters"
echo "  - At least one uppercase letter"
echo "  - At least one lowercase letter"
echo "  - At least one number"
echo "  - At least one symbol (!@#\$%^&*)"
echo ""

read -sp "Enter password for $EMAIL: " PASSWORD
echo ""
read -sp "Confirm password: " PASSWORD_CONFIRM
echo ""

if [ "$PASSWORD" != "$PASSWORD_CONFIRM" ]; then
  echo "Error: Passwords do not match."
  exit 1
fi

# Set permanent password
echo ""
echo "Setting permanent password..."
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username "$EMAIL" \
  --password "$PASSWORD" \
  --permanent \
  --region $REGION

echo ""
echo "============================================"
echo "Admin user created successfully!"
echo ""
echo "Email: $EMAIL"
echo "Status: CONFIRMED"
echo ""
echo "You can now log in at ghost.jurigregg.com/login"
echo "============================================"
