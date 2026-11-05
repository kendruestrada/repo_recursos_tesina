# Environment Configuration Guide

This project uses environment variables for configuration management, allowing you to deploy to different environments (dev, staging, prod) with different settings.

## Quick Start

1. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values**:
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Set your API key**:
   ```env
   TEST_009_API_KEY=your-actual-api-key-here
   ```

4. **Deploy the stack**:
   ```bash
   npm run build
   cdk deploy
   ```

## Environment Variables

### General Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Environment name (dev, staging, prod) | `dev` | No |
| `AWS_REGION` | AWS Region for deployment | CDK default | No |
| `AWS_ACCOUNT` | AWS Account ID | CDK default | No |

### S3 Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ARTIFACTS_BUCKET_NAME` | S3 bucket for canary artifacts | `synthetics-canaries-artifacts-${ENVIRONMENT}` | No |

### Homepage Test

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `HOMEPAGE_TARGET_URL` | Target URL to test | `https://example.com` | No |

### Test_009 API Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TEST_009_API_ENDPOINT` | API endpoint URL | See .env.example | No |
| `TEST_009_API_KEY` | API authorization token | `REPLACE_WITH_YOUR_API_TOKEN` | **Yes** |
| `TEST_009_SSM_PARAMETER_NAME` | SSM parameter name for API key | `/canary/${ENVIRONMENT}/test-009/api-key` | No |

## Multi-Environment Setup

### Development Environment

```bash
# .env
ENVIRONMENT=dev
TEST_009_API_KEY=dev-api-key
HOMEPAGE_TARGET_URL=https://dev.example.com
```

### Staging Environment

```bash
# .env.staging
ENVIRONMENT=staging
TEST_009_API_KEY=staging-api-key
HOMEPAGE_TARGET_URL=https://staging.example.com
```

### Production Environment

```bash
# .env.production
ENVIRONMENT=prod
TEST_009_API_KEY=prod-api-key
HOMEPAGE_TARGET_URL=https://www.example.com
ARTIFACTS_BUCKET_NAME=synthetics-canaries-artifacts-prod
```

## Deploying to Different Environments

### Option 1: Using different .env files

```bash
# Deploy to dev (default)
cdk deploy

# Deploy to staging
cp .env.staging .env
cdk deploy

# Deploy to production
cp .env.production .env
cdk deploy
```

### Option 2: Using environment variables directly

```bash
# Deploy to dev
ENVIRONMENT=dev TEST_009_API_KEY=dev-key cdk deploy

# Deploy to prod
ENVIRONMENT=prod TEST_009_API_KEY=prod-key cdk deploy
```

### Option 3: Using dotenv-cli (recommended for CI/CD)

```bash
# Install dotenv-cli
npm install -g dotenv-cli

# Deploy with specific env file
dotenv -e .env.dev -- cdk deploy
dotenv -e .env.staging -- cdk deploy
dotenv -e .env.production -- cdk deploy
```

## Environment Configuration Flow

```
1. Load environment variables from .env file (if exists)
2. Override with system environment variables (if set)
3. Validate required values
4. Print configuration for review
5. Deploy with CDK
```

## Security Best Practices

### ✅ DO:
- Store `.env` files locally only (they're in `.gitignore`)
- Use different API keys for each environment
- Rotate API keys regularly
- Use AWS Secrets Manager for production secrets
- Review printed configuration before deployment

### ❌ DON'T:
- Commit `.env` files to git
- Share API keys in Slack/email
- Use production keys in development
- Hard-code secrets in the code

## Updating SSM Parameters After Deployment

If you need to update the API key after deployment without redeploying:

```bash
# Update the SSM parameter
aws ssm put-parameter \
  --name "/canary/dev/test-009/api-key" \
  --value "new-api-key" \
  --type "String" \
  --overwrite

# The canary will use the new value on next run
```

## Viewing Current Configuration

The configuration is printed when you run `cdk synth` or `cdk deploy`:

```
📋 Environment Configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Environment:           dev
Artifacts Bucket:      synthetics-canaries-artifacts-dev
Test_009 API Endpoint: https://api.example.com/v1/report
Test_009 API Key:      your-actual-api-key...
Test_009 SSM Param:    /canary/dev/test-009/api-key
Homepage URL:          https://example.com
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Troubleshooting

### Error: "TEST_009_API_KEY is not set"

**Solution**: Create a `.env` file and set `TEST_009_API_KEY`:
```bash
echo "TEST_009_API_KEY=your-key-here" >> .env
```

### Warning: "Using default placeholder value"

This warning appears when `TEST_009_API_KEY` is not set. The deployment will succeed but the canary will fail until you update the SSM parameter with a valid API key.

### Error: "ARTIFACTS_BUCKET_NAME already exists"

S3 bucket names are globally unique. Choose a different name:
```env
ARTIFACTS_BUCKET_NAME=synthetics-canaries-artifacts-mycompany-dev
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Deploy to Dev
  env:
    ENVIRONMENT: dev
    TEST_009_API_KEY: ${{ secrets.DEV_API_KEY }}
    AWS_REGION: us-east-1
  run: |
    npm run build
    cdk deploy --require-approval never
```

### GitLab CI

```yaml
deploy:dev:
  variables:
    ENVIRONMENT: dev
    TEST_009_API_KEY: $DEV_API_KEY
  script:
    - npm run build
    - cdk deploy --require-approval never
```

## Example Files

- `.env.example` - Template with all available variables
- `.env.production.example` - Production configuration template
