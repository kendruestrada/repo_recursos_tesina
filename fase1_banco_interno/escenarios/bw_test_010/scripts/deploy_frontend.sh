#!/bin/bash
set -e

STACK_NAME="test-010"
PROFILE="tests-bw"

echo "Fetching stack outputs for $STACK_NAME..."
OUTPUTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs' --output json --profile $PROFILE)
echo $OUTPUTS

API_URL=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="WebEndpoint") | .OutputValue')
BUCKET_NAME=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="FrontendBucket") | .OutputValue')
WEBSITE_URL=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="FrontendURL") | .OutputValue')

if [ -z "$API_URL" ] || [ -z "$BUCKET_NAME" ]; then
    echo "Error: Could not retrieve API URL or Bucket Name from stack outputs."
    echo "Make sure the stack is deployed."
    exit 1
fi

echo "API URL: $API_URL"
echo "Bucket Name: $BUCKET_NAME"

# Create a temporary directory for the build
echo "Preparing frontend..."
mkdir -p .frontend_build
cp frontend/index.html .frontend_build/index.html

# Inject the API URL into index.html
# Use a flexible sed command to handle different URL formats
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS requires an empty string argument for -i
    sed -i '' "s|const API_URL = \".*\";|const API_URL = \"$API_URL\";|g" .frontend_build/index.html
else
    sed -i "s|const API_URL = \".*\";|const API_URL = \"$API_URL\";|g" .frontend_build/index.html
fi

echo "Uploading to S3..."
aws s3 cp .frontend_build/index.html s3://$BUCKET_NAME/index.html --content-type text/html --profile tests-bw

echo "--------------------------------------------------"
echo "Deployment Complete!"
echo "Website URL: $WEBSITE_URL"
echo "--------------------------------------------------"
