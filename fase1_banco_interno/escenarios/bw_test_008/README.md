# Banking API

A serverless banking application built with AWS SAM featuring account management and transfer processing with audit logging.

## Architecture

The application consists of:

- **API Gateway**: RESTful API with three endpoints
- **Lambda Functions**: Serverless compute for API handlers and internal processing
- **DynamoDB Tables**:
  - BankingTable: Stores account information with Balance field
  - TransferAuditTable: Stores transfer audit logs
- **CloudWatch Logs**: Log groups with 14-day retention

### Components

**API Endpoints:**
- `GET /account` - Retrieve account details by accountId
- `POST /account` - Create a new account with initial balance
- `POST /transfer` - Submit a list of transfers for processing

**Lambda Functions:**
- `GetAccountFunction` - Handles GET /account requests
- `CreateAccountFunction` - Handles POST /account requests
- `TransferApiFunction` - Handles POST /transfer requests, invokes internal processor
- `TransferProcessorFunction` - Internal function that processes individual transfers and writes audit logs

**DynamoDB Tables:**
- `BankingTable` - Stores accounts (AccountId, Balance)
- `TransferAuditTable` - Stores transfer logs (TransferId, Timestamp, SourceAccountId, DestAccountId, Amount, Status)

## Prerequisites

- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed
- Node.js 20.x
- npm

## Installation

Install dependencies:

```bash
npm install
```

## Deployment

### Build the application

```bash
sam build
```

### Deploy to AWS

For first-time deployment:

```bash
sam deploy --guided
```

Follow the prompts:
- Stack Name: Choose a stack name (e.g., banking-api)
- AWS Region: Select your preferred region
- Confirm changes before deploy: Y
- Allow SAM CLI IAM role creation: Y
- Disable rollback: N
- Save arguments to configuration file: Y

For subsequent deployments:

```bash
sam deploy
```

### Deploy with custom parameters

```bash
sam deploy --stack-name banking-api --region us-east-1 --capabilities CAPABILITY_IAM
```

## Usage

After deployment, the API Gateway URL will be displayed in the outputs. Export it for convenience:

```bash
export API_URL=$(aws cloudformation describe-stacks --stack-name banking-api --query 'Stacks[0].Outputs[?OutputKey==`BankingApiUrl`].OutputValue' --output text)
```

### Create an account

```bash
curl -X POST ${API_URL}account \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "ACC001",
    "balance": 1000
  }'
```

Response:
```json
{
  "message": "Account created successfully",
  "account": {
    "AccountId": "ACC001",
    "Balance": 1000
  }
}
```

### Get account details

```bash
curl "${API_URL}account?accountId=ACC001"
```

Response:
```json
{
  "AccountId": "ACC001",
  "Balance": 1000
}
```

### Submit transfers

```bash
curl -X POST ${API_URL}transfer \
  -H "Content-Type: application/json" \
  -d '{
    "transfers": [
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 100
      },
      {
        "sourceAccountId": "ACC002",
        "destAccountId": "ACC003",
        "amount": 50
      }
    ]
  }'
```

Response:
```json
{
  "message": "Processed 2 transfers successfully, 0 failed",
  "successful": [
    {
      "transfer": {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 100
      },
      "result": {
        "statusCode": 200,
        "transferId": "uuid",
        "message": "Transfer completed successfully"
      }
    }
  ],
  "failed": []
}
```

## Monitoring

### View logs

```bash
sam logs -n GetAccountFunction --stack-name banking-api --tail
sam logs -n CreateAccountFunction --stack-name banking-api --tail
sam logs -n TransferApiFunction --stack-name banking-api --tail
sam logs -n TransferProcessorFunction --stack-name banking-api --tail
```

### Query audit logs

```bash
aws dynamodb scan --table-name TransferAuditTable
```

## Local Testing

### Start local API

```bash
sam local start-api
```

The API will be available at `http://127.0.0.1:3000`

### Invoke a function locally

```bash
sam local invoke TransferProcessorFunction -e events/transfer.json
```

## Cleanup

Delete the stack and all resources:

```bash
sam delete --stack-name banking-api
```

## Configuration

Log retention is set to 14 days (2 weeks) for all Lambda functions in the CloudWatch Log Groups.

## Security Considerations

- API Gateway endpoints are public by default
- Consider adding API keys, IAM authorization, or Cognito for production use
- Enable encryption at rest for DynamoDB tables in production
- Review and adjust IAM policies to follow least privilege principle
