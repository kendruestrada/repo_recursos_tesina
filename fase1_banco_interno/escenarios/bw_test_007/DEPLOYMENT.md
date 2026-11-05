# Quick Deployment Guide

## Step-by-Step Deployment

### 1. Install Dependencies
```bash
npm install
```

### 2. Build the Project
```bash
npm run build
```

### 3. Bootstrap CDK (First Time Only)
```bash
npx cdk bootstrap
```

### 4. Deploy the Stack
```bash
npx cdk deploy
```

### 5. Save the Outputs
After deployment completes, you'll see outputs like:
```
Outputs:
BwTest007Stack.ApiKeyId = xyz123abc456
BwTest007Stack.ApiUrl = https://abc123def.execute-api.us-east-1.amazonaws.com/prod/
BwTest007Stack.PaymentEndpoint = https://abc123def.execute-api.us-east-1.amazonaws.com/prod/payment
BwTest007Stack.PaymentConfirmationFunctionName = BwTest007Stack-PaymentConfirmationFunction-ABC123
BwTest007Stack.OrderProcessingFunctionName = BwTest007Stack-OrderProcessingFunction-XYZ789
BwTest007Stack.EmailServiceFunctionName = BwTest007Stack-EmailServiceFunction-DEF456
```

### 6. Retrieve API Key Value
```bash
aws apigateway get-api-key --api-key <ApiKeyId-from-output> --include-value --query 'value' --output text
```

Save this API key value - you'll need it to make requests!

### 7. Test the API

#### Quick Test (Single Request)
```bash
curl -X POST <PaymentEndpoint-from-output> \
  -H "Content-Type: application/json" \
  -H "x-api-key: <your-api-key-value>" \
  -d '{
    "orderId": "ORDER-12345",
    "email": "test@example.com"
  }'
```

#### Circuit Breaker Test (Multiple Requests)
```bash
./test-api.sh <PaymentEndpoint-from-output> <your-api-key-value> 7
```

This will send 7 requests and demonstrate the circuit breaker opening after 5 failures.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         API Gateway                          │
│                   (Requires API Key)                         │
│                                                              │
│  POST /payment                                              │
│  Body: { "orderId": "...", "email": "..." }                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           Lambda: PaymentConfirmation                        │
│  - Validates request                                        │
│  - Invokes OrderProcessing                                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           Lambda: OrderProcessing                            │
│  - Processes order                                          │
│  - Invokes EmailService                                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           Lambda: EmailService                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Circuit Breaker Pattern                       │  │
│  │  - Threshold: 5 failures                             │  │
│  │  - State: CLOSED → OPEN (after 5 errors)            │  │
│  │  - All-or-Nothing: Blocks all when OPEN             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    AWS SES (Mocked)                          │
│  Returns: 504 Gateway Timeout                               │
└─────────────────────────────────────────────────────────────┘
```

## Expected Test Results

### First 4 Requests
```json
{
  "error": "504 Gateway Timeout - SES service unavailable",
  "orderId": "ORDER-123",
  "email": "test@example.com",
  "circuitBreakerState": "CLOSED",
  "failureCount": 1  // increments with each failure
}
```
**HTTP Status: 504**

### 5th Request (Circuit Opens)
```json
{
  "error": "504 Gateway Timeout - SES service unavailable",
  "orderId": "ORDER-125",
  "email": "test@example.com",
  "circuitBreakerState": "OPEN",
  "failureCount": 5
}
```
**HTTP Status: 504**

### 6th+ Requests (Circuit Breaker Active)
```json
{
  "error": "Circuit breaker is OPEN - all requests blocked",
  "orderId": "ORDER-126",
  "email": "test@example.com",
  "circuitBreakerState": "OPEN",
  "failureCount": 5
}
```
**HTTP Status: 503**

## Cleanup

To remove all resources:
```bash
npx cdk destroy
```

Confirm with 'y' when prompted.

## Troubleshooting

### "Unable to resolve AWS account to use"
- Run `aws configure` to set up AWS credentials
- Or set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### "403 Forbidden" from API
- Verify you're using the correct API key value
- Include header: `x-api-key: <value>`

### "Resource Not Found"
- Ensure you're using the correct API endpoint URL from CDK output
- Check the endpoint includes `/payment` at the end

### Lambda Timeout Errors
- Check CloudWatch Logs for detailed errors
- View logs: `aws logs tail /aws/lambda/<function-name> --follow`

## Monitoring

### View Lambda Logs in Real-Time
```bash
# PaymentConfirmation logs
aws logs tail /aws/lambda/$(aws cloudformation describe-stack-resources --stack-name BwTest007Stack --query "StackResources[?LogicalResourceId=='PaymentConfirmationFunction'].PhysicalResourceId" --output text) --follow

# OrderProcessing logs
aws logs tail /aws/lambda/$(aws cloudformation describe-stack-resources --stack-name BwTest007Stack --query "StackResources[?LogicalResourceId=='OrderProcessingFunction'].PhysicalResourceId" --output text) --follow

# EmailService logs
aws logs tail /aws/lambda/$(aws cloudformation describe-stack-resources --stack-name BwTest007Stack --query "StackResources[?LogicalResourceId=='EmailServiceFunction'].PhysicalResourceId" --output text) --follow
```

### Check API Gateway Metrics
- Go to AWS Console → API Gateway → Your API → Dashboard
- View metrics: requests, latency, errors

### Check Lambda Metrics
- Go to AWS Console → Lambda → Your Function → Monitor
- View metrics: invocations, duration, errors

## Next Steps

1. **Disable Mock Mode**: To use real SES, update environment variable
2. **Add DynamoDB**: For persistent circuit breaker state across Lambda invocations
3. **Add Error Notifications**: SNS topics for circuit breaker open events
4. **Add Retry Logic**: Implement exponential backoff
5. **Add Dead Letter Queue**: For failed processing
6. **Add X-Ray**: For distributed tracing
