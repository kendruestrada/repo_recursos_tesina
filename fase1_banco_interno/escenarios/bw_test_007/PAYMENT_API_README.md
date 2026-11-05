# Payments Processing API

A serverless payments processing API built with AWS CDK (TypeScript) and Lambda functions (Python).

## Architecture

The API follows a chain of Lambda functions:

```
API Gateway (with API Key)
    → PaymentConfirmation Lambda
        → OrderProcessing Lambda
            → EmailService Lambda
                → AWS SES (mocked)
```

## Features

- **API Gateway with API Key**: Secured endpoint requiring API key authentication
- **Chain of Lambda Functions**: Three interconnected Lambda functions
- **Circuit Breaker Pattern**: EmailService implements circuit breaker (closes after 5 errors)
- **Mock SES Integration**: Simulates 504 Gateway Timeout errors for testing

## Project Structure

```
.
├── bin/
│   └── bw_test_007.ts              # CDK app entry point
├── lib/
│   └── bw_test_007-stack.ts        # CDK stack definition
├── lambda/
│   ├── payment-confirmation/
│   │   └── index.py                # Entry point Lambda
│   ├── order-processing/
│   │   └── index.py                # Middle Lambda
│   └── email-service/
│       └── index.py                # Final Lambda with circuit breaker
└── PAYMENT_API_README.md           # This file
```

## Lambda Functions

### 1. PaymentConfirmation (Entry Point)
- Receives POST requests from API Gateway
- Validates `orderId` and `email` from JSON body
- Invokes OrderProcessing Lambda

### 2. OrderProcessing
- Processes order logic
- Invokes EmailService Lambda
- Returns success/failure based on email sending

### 3. EmailService (Circuit Breaker)
- Implements circuit breaker pattern (5 error threshold)
- Calls AWS SES (or mock)
- **Circuit Breaker States**:
  - `CLOSED`: Normal operation, requests pass through
  - `OPEN`: After 5 failures, all requests blocked immediately
  - Circuit remains OPEN until manually reset (stateless Lambda limitation)

## Deployment

### Prerequisites
- AWS CLI configured with credentials
- Node.js and npm installed
- AWS CDK CLI installed: `npm install -g aws-cdk`

### Deploy Steps

1. Install dependencies:
```bash
npm install
```

2. Bootstrap CDK (first time only):
```bash
cdk bootstrap
```

3. Build the project:
```bash
npm run build
```

4. Deploy the stack:
```bash
cdk deploy
```

5. Note the outputs:
   - `ApiUrl`: Base API Gateway URL
   - `ApiKeyId`: The API Key ID (you'll need to retrieve the actual key value)
   - `PaymentEndpoint`: Full payment endpoint URL

### Retrieve API Key Value

After deployment, get the API key value:

```bash
aws apigateway get-api-key --api-key <ApiKeyId> --include-value --query 'value' --output text
```

Replace `<ApiKeyId>` with the value from CDK output.

## API Usage

### Endpoint
```
POST /payment
```

### Headers
```
Content-Type: application/json
x-api-key: <your-api-key-value>
```

### Request Body
```json
{
  "orderId": "ORDER-12345",
  "email": "customer@example.com"
}
```

### Example cURL Request
```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/payment \
  -H "Content-Type: application/json" \
  -H "x-api-key: <your-api-key>" \
  -d '{
    "orderId": "ORDER-12345",
    "email": "customer@example.com"
  }'
```

## Testing Circuit Breaker

The EmailService is configured with `MOCK_SES_ENDPOINT=mock` to simulate failures.

### Test Scenario 1: Trigger Circuit Breaker
Make 5 consecutive requests to the API:

```bash
for i in {1..5}; do
  curl -X POST https://<api-url>/payment \
    -H "Content-Type: application/json" \
    -H "x-api-key: <your-api-key>" \
    -d "{\"orderId\": \"ORDER-$i\", \"email\": \"test@example.com\"}"
  echo "\n---Request $i complete---\n"
done
```

**Expected Results**:
- Requests 1-4: Return 504 (Gateway Timeout)
- Request 5: Circuit breaker OPENS, returns 503 (Service Unavailable)
- Subsequent requests: Blocked by circuit breaker (503)

### Test Scenario 2: Check Circuit Breaker State
The response body includes circuit breaker diagnostics:

```json
{
  "error": "504 Gateway Timeout - SES service unavailable",
  "orderId": "ORDER-123",
  "email": "test@example.com",
  "circuitBreakerState": "OPEN",
  "failureCount": 5
}
```

### Reset Circuit Breaker
Since Lambda functions are stateless, the circuit breaker resets when:
- The Lambda container is recycled (after inactivity)
- You update the function's environment variables
- You manually update the function code

To force a reset:
```bash
aws lambda update-function-configuration \
  --function-name <EmailServiceFunctionName> \
  --environment Variables={MOCK_SES_ENDPOINT=mock,SENDER_EMAIL=no-reply@example.com,RESET=true}
```

## Disable Mock Mode (Use Real SES)

To use real AWS SES instead of mock:

1. Update the EmailService environment variable:
```bash
aws lambda update-function-configuration \
  --function-name <EmailServiceFunctionName> \
  --environment Variables={MOCK_SES_ENDPOINT=real,SENDER_EMAIL=<verified-ses-email>}
```

2. Ensure your AWS account has SES access and verified email addresses
3. Update `SENDER_EMAIL` to a verified SES email address

## Monitoring

### CloudWatch Logs
Each Lambda function logs to CloudWatch Logs:
- `/aws/lambda/BwTest007Stack-PaymentConfirmationFunction<hash>`
- `/aws/lambda/BwTest007Stack-OrderProcessingFunction<hash>`
- `/aws/lambda/BwTest007Stack-EmailServiceFunction<hash>`

### View Logs
```bash
aws logs tail /aws/lambda/<function-name> --follow
```

## Response Codes

| Code | Description |
|------|-------------|
| 200  | Success - Payment processed, order processed, email sent |
| 400  | Bad Request - Missing orderId or email |
| 500  | Internal Server Error - Lambda function error |
| 503  | Service Unavailable - Circuit breaker is OPEN |
| 504  | Gateway Timeout - SES service unavailable (mock mode) |

## Cleanup

To delete all resources:

```bash
cdk destroy
```

## Implementation Notes

### Circuit Breaker Pattern
- **All-or-Nothing**: Once open, ALL requests are blocked
- **Threshold**: 5 consecutive failures
- **State Persistence**: Limited by Lambda's stateless nature (resets with container)
- **Production Consideration**: For production, use DynamoDB or ElastiCache to persist circuit breaker state across Lambda invocations

### Lambda Chain
- Functions use synchronous invocation (`RequestResponse`)
- Each function waits for the downstream function to complete
- Timeouts cascade: PaymentConfirmation (90s) > OrderProcessing (60s) > EmailService (30s)

### API Gateway
- Throttling: 100 requests/second, burst 200
- Quota: 10,000 requests/month
- Adjust in `lib/bw_test_007-stack.ts` as needed

## Security Considerations

- API Key authentication required for all requests
- Lambda functions use least-privilege IAM roles
- SES permissions only on EmailService function
- Functions can only invoke their direct downstream dependency

## Troubleshooting

### Issue: API returns 403 Forbidden
**Solution**: Ensure you're including the `x-api-key` header with correct value

### Issue: Circuit breaker doesn't reset
**Solution**: Lambda containers may be cached. Force update the function or wait for container recycling

### Issue: Lambda timeout
**Solution**: Check CloudWatch Logs for detailed error messages. Ensure downstream functions are responding within timeout limits

## Development

### Local Testing
Test Lambda functions locally using the AWS SAM CLI or by mocking the event structure.

### Update Lambda Code
After modifying Python code:
```bash
npm run build
cdk deploy
```

### Add New Dependencies
For Python dependencies, create `requirements.txt` in each Lambda directory and use Lambda Layers or bundled dependencies.
