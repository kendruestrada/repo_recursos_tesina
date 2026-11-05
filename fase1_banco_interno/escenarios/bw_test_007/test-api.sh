#!/bin/bash

# Test script for Payments Processing API
# Usage: ./test-api.sh <api-url> <api-key> [num-requests]

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <api-url> <api-key> [num-requests]"
    echo ""
    echo "Example:"
    echo "  $0 https://abc123.execute-api.us-east-1.amazonaws.com/prod/payment YOUR_API_KEY 5"
    echo ""
    echo "Get API URL from CDK output: PaymentEndpoint"
    echo "Get API Key value using: aws apigateway get-api-key --api-key <ApiKeyId> --include-value --query 'value' --output text"
    exit 1
fi

API_URL=$1
API_KEY=$2
NUM_REQUESTS=${3:-5}

echo "========================================="
echo "Testing Payments Processing API"
echo "========================================="
echo "API URL: $API_URL"
echo "Number of requests: $NUM_REQUESTS"
echo ""

for i in $(seq 1 $NUM_REQUESTS); do
    echo "------- Request $i -------"

    RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d "{
            \"orderId\": \"ORDER-$(date +%s)-$i\",
            \"email\": \"test$i@example.com\"
        }")

    HTTP_BODY=$(echo "$RESPONSE" | sed -e 's/HTTP_STATUS:.*//')
    HTTP_STATUS=$(echo "$RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

    echo "Status: $HTTP_STATUS"
    echo "Response: $HTTP_BODY" | jq '.' 2>/dev/null || echo "$HTTP_BODY"
    echo ""

    sleep 1
done

