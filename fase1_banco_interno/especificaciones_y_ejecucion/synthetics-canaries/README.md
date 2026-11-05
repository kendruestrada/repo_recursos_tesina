# AWS Synthetics Canaries - Implementation Guide

## Overview

This project implements AWS Synthetic Canaries tests using an abstract constructor pattern with support for Python Selenium 7.0 runtime. The architecture allows you to:

- Define canaries using an abstract base class
- Add tests as a list to the CDK stack
- Load test code from local files or S3
- Each test has its own folder under `canaries/`

## Project Structure

```
synthetics-canaries/
├── lib/
│   ├── base-canary.ts              # Abstract base class for all canaries
│   └── synthetics-canaries-stack.ts # CDK stack that accepts list of canaries
├── canaries/                        # Folder for all canary tests
│   └── homepage-test/               # Example canary test
│       ├── homepage-canary.ts       # TypeScript CDK construct
│       └── homepage_canary.py       # Python test implementation
└── bin/
    └── synthetics-canaries.ts       # Main CDK app file
```

## Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template

## Architecture

### 1. Abstract Base Class ([lib/base-canary.ts](lib/base-canary.ts))

The `BaseCanary` abstract class provides:

- **Code Source Flexibility**: Load test code from local files OR S3 bucket
- **IAM Role Management**: Automatic creation with proper permissions
- **S3 Artifacts**: Manages artifact bucket for screenshots and logs
- **Extensibility**: Hooks for custom permissions and configurations
- **Type Safety**: TypeScript interfaces ensure correct configuration

**Key Features**:
```typescript
export interface BaseCanaryConfig {
  canaryName: string;
  testPath?: string;              // For local files
  s3CodeBucket?: string;          // For S3 deployment
  s3CodeKey?: string;             // For S3 deployment
  schedule?: synthetics.CfnCanary.ScheduleProperty;
  runtime?: synthetics.Runtime;
  handler?: string;               // Python handler (default: homepage_canary.handler)
  environmentVariables?: { [key: string]: string };
}
```

### 2. Stack with List Pattern ([lib/synthetics-canaries-stack.ts](lib/synthetics-canaries-stack.ts))

The stack accepts an array of canary factory functions:

```typescript
export interface SyntheticsCanariesStackProps extends cdk.StackProps {
  canaries?: Array<(scope: Construct, artifactsBucket: s3.IBucket) => BaseCanary>;
  artifactsBucketName?: string;
}
```

This allows you to add multiple tests easily:

```typescript
new SyntheticsCanariesStack(app, 'Stack', {
  canaries: [
    (scope, bucket) => new HomepageCanary(scope, 'Test1', bucket, config1),
    (scope, bucket) => new ApiCanary(scope, 'Test2', bucket, config2),
    (scope, bucket) => new LoginCanary(scope, 'Test3', bucket, config3),
  ],
});
```

## Creating a New Test

### Step 1: Create Test Folder

```bash
mkdir -p canaries/my-new-test
```

### Step 2: Create CDK Construct (TypeScript)

Create `canaries/my-new-test/my-new-canary.ts`:

```typescript
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface MyNewCanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime'> {
  targetUrl: string;
  // Add your custom config properties
}

export class MyNewCanary extends BaseCanary {
  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: MyNewCanaryConfig) {
    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/my-new-test',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      handler: 'my_new_canary.handler',
      environmentVariables: {
        TARGET_URL: config.targetUrl,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);
  }

  protected addCustomPermissions(_role: iam.Role): void {
    // Add custom IAM permissions if needed
    // Example: role.addToPolicy(new iam.PolicyStatement({ ... }));
  }

  protected customize(): void {
    // Add custom resources or configurations
  }
}
```

### Step 3: Create Python Test Implementation

Create `canaries/my-new-test/my_new_canary.py`:

```python
import os
from aws_synthetics.selenium import synthetics_webdriver as webdriver
from aws_synthetics.common import synthetics_logger as logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def handler(event, context):
    """
    My new canary test handler
    """
    target_url = os.environ.get('TARGET_URL', 'https://example.com')

    logger.info(f'Starting test for: {target_url}')

    browser = webdriver.Chrome()
    browser.set_page_load_timeout(30)

    try:
        # Your test logic here
        browser.get(target_url)

        # Wait for elements
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Perform your tests
        page_title = browser.title
        logger.info(f'Page title: {page_title}')

        # Take screenshot
        browser.save_screenshot('test_success.png')

        logger.info('Test completed successfully')
        return {
            'statusCode': 200,
            'body': 'Test passed'
        }

    except Exception as e:
        logger.error(f'Test failed: {str(e)}')
        browser.save_screenshot('test_failure.png')
        raise Exception(f'Test failed: {str(e)}')

    finally:
        browser.quit()
```

### Step 4: Add to CDK App

In [bin/synthetics-canaries.ts](bin/synthetics-canaries.ts):

```typescript
import { MyNewCanary } from '../canaries/my-new-test/my-new-canary';

new SyntheticsCanariesStack(app, 'SyntheticsCanariesStack', {
  canaries: [
    (scope, artifactsBucket) => new MyNewCanary(
      scope,
      'MyNewCanary',
      artifactsBucket,
      {
        canaryName: 'my-new-test',
        targetUrl: 'https://mywebsite.com',
      }
    ),
  ],
});
```

## Deployment Options

### Option 1: Local Files (Development)

Use `testPath` for local development:

```typescript
{
  canaryName: 'my-test',
  testPath: 'canaries/my-test',  // Local files
  targetUrl: 'https://example.com',
}
```

### Option 2: S3 Bucket (Production)

Use S3 for production deployments:

1. **Package your test**:
```bash
cd canaries/my-test
zip -r my-test.zip *.py
```

2. **Upload to S3**:
```bash
aws s3 cp my-test.zip s3://my-canary-code-bucket/canaries/my-test.zip
```

3. **Configure canary**:
```typescript
{
  canaryName: 'my-test',
  s3CodeBucket: 'my-canary-code-bucket',
  s3CodeKey: 'canaries/my-test.zip',
  targetUrl: 'https://example.com',
}
```

## Python Runtime: SYNTHETICS_PYTHON_SELENIUM_7_0

The project uses `SYNTHETICS_PYTHON_SELENIUM_7_0` which provides:

- **Python 3.11+**
- **Selenium 4.x** with WebDriver
- **Chrome Browser** (headless mode)
- **AWS Synthetics SDK** for logging and reporting

### Available Imports

```python
from aws_synthetics.selenium import synthetics_webdriver as webdriver
from aws_synthetics.common import synthetics_logger as logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
```

### Handler Requirements

- Function must be named `handler`
- Must accept `event` and `context` parameters
- Return value is logged but not required
- Exceptions cause the canary to fail
- Screenshots are automatically uploaded to S3

## Example: Homepage Canary

The included [homepage-test](canaries/homepage-test/) demonstrates:

✅ Loading a webpage
✅ Verifying page title
✅ Checking page content
✅ Measuring page load time
✅ Taking screenshots
✅ Error handling

**Files**:
- [canaries/homepage-test/homepage-canary.ts](canaries/homepage-test/homepage-canary.ts) - CDK construct
- [canaries/homepage-test/python/homepage_canary.py](canaries/homepage-test/python/homepage_canary.py) - Python implementation

## Running Schedule

Default schedule: Every 5 minutes

To customize:

```typescript
{
  canaryName: 'my-test',
  schedule: {
    expression: 'rate(10 minutes)'  // or 'cron(0 */1 * * ? *)'
  },
  // ... other config
}
```

## Deployment Commands

```bash
# Build the project
npm run build

# Synthesize CloudFormation template
cdk synth

# Deploy to AWS
cdk deploy SyntheticsCanariesStack

# Destroy stack
cdk destroy SyntheticsCanariesStack
```

## Monitoring

After deployment, monitor your canaries:

1. **AWS CloudWatch Synthetics Console**
   - View canary runs and success rates
   - See screenshots and HAR files

2. **CloudWatch Logs**
   - Detailed execution logs
   - `/aws/lambda/cwsyn-<canary-name>-*`

3. **S3 Bucket**
   - Screenshots on success/failure
   - HAR files with network activity
   - Logs and artifacts

## Best Practices

1. **One test per folder** - Each canary in its own directory
2. **Descriptive names** - Use clear canary names (e.g., `homepage-test`, `api-health-check`)
3. **Environment variables** - Pass configuration through environment variables
4. **Error screenshots** - Always capture screenshots on failure
5. **S3 for production** - Use S3-based deployment for production environments
6. **Custom permissions** - Override `addCustomPermissions()` for AWS resource access
7. **Timeouts** - Set appropriate page load timeouts
8. **Logging** - Use logger extensively for debugging

## Benefits of This Architecture

✅ **Reusable** - Abstract base class eliminates boilerplate
✅ **Flexible** - Support for local files and S3 deployment
✅ **Type-Safe** - TypeScript ensures correct configuration
✅ **Extensible** - Easy to add custom permissions and resources
✅ **Organized** - Each test in its own folder
✅ **Scalable** - Add tests as array items to the stack
✅ **Maintainable** - Clear separation of concerns

## Troubleshooting

### Build Errors

Run `npm run build` to check for TypeScript errors.

### Deployment Failures

Check IAM permissions for CDK deployment.

### Canary Failures

1. Check CloudWatch Logs for detailed error messages
2. Review screenshots in S3 bucket
3. Verify environment variables are set correctly
4. Test the target URL is accessible

### S3 Code Not Found

Ensure:
- S3 bucket exists
- Code is uploaded to correct key
- IAM role has s3:GetObject permission

## AWS Synthetics Canaries Cost Estimation

Understanding the cost of running Synthetics Canaries helps with budget planning. Below are realistic cost examples based on AWS pricing (as of 2024).

### Pricing Components

AWS CloudWatch Synthetics charges for:
1. **Canary runs** - $0.0012 per canary run
2. **S3 storage** - Standard S3 pricing for artifacts
3. **CloudWatch Logs** - Standard CloudWatch Logs pricing

### Cost Calculation Formula

```
Monthly Cost = (Runs per Month × $0.0012) + S3 Storage + CloudWatch Logs
```

### Example 1: Single Homepage Test (Low Frequency)

**Configuration:**
- 1 canary testing homepage
- Runs every 5 minutes
- ~8,640 runs/month (24h × 365 days / 12 months × 12 runs/hour)

**Cost Breakdown:**
```
Canary runs:      8,640 runs × $0.0012  = $10.37/month
S3 storage:       ~100 MB                 = $0.02/month
CloudWatch Logs:  ~500 MB                 = $0.25/month
─────────────────────────────────────────────────────
TOTAL:                                    ≈ $10.64/month
```

### Example 2: Two Canaries (Current Project Configuration)

**Cost Breakdown per Canary:**
```
Homepage Canary (Every 20 minutes on weekdays only, 3 hours/day):

  Calculation: 5 days/week × 4 weeks × 3 hours × 3 runs/hour = 180 runs/month
  Runs:           180 runs × $0.0012     = $0.22/month
  S3 storage:     ~50 MB                 = $0.01/month
  CloudWatch Logs: ~300 MB               = $0.15/month
  Subtotal:                              = $0.38/month

Test_009 Canary (Every 5 minutes on weekdays only, 3 hours/day):

  Calculation: 5 days/week × 4 weeks × 3 hours × 12 runs/hour = 180 runs/month
  Runs:           720 runs × $0.0012     = $0.87/month
  S3 storage:     ~50 MB                 = $0.01/month
  CloudWatch Logs: ~300 MB               = $0.15/month
  Subtotal:                              = $1.03/month

─────────────────────────────────────────────────────
TOTAL (both canaries):                   ≈ $1.5/month
```


### Cost Optimization Tips

#### 1. **Optimize Run Frequency**
```typescript
// Instead of every minute (expensive)
schedule: { expression: 'rate(1 minute)' }  // ~43,200 runs/month

// Use every 5 minutes (cost-effective)
schedule: { expression: 'rate(5 minutes)' } // ~8,640 runs/month

// Save 80%: $51.84/month → $10.37/month per canary
```

#### 2. **Run Only During Business Hours**
```typescript
// Our current config (weekdays, business hours only)
schedule: {
  expression: 'cron(*/5 16-18 ? * MON-FRI *)'  // ~1,800 runs/month
}

// vs 24/7 every 5 minutes: 8,640 runs/month
// Saves ~79%: $10.37/month → $2.16/month per canary
```

#### 3. **Use Appropriate Runtimes**
- Python Selenium runtime is suitable for browser-based tests
- For API-only tests, consider using simpler HTTP checks
- Faster tests = lower execution time = less cost

#### 4. **Manage S3 Lifecycle**
```typescript
lifecycleRules: [
  {
    id: 'DeleteOldArtifacts',
    enabled: true,
    expiration: cdk.Duration.days(30),  // Delete after 30 days
  },
]
```

#### 5. **Archive CloudWatch Logs**
- Export old logs to S3 Glacier for long-term storage
- Reduce CloudWatch Logs retention period

### Cost Comparison by Schedule

| Schedule | Runs/Month | Cost/Month (per canary) |
|----------|------------|------------------------|
| Every 1 minute | 43,200 | $51.84 |
| Every 5 minutes | 8,640 | $10.37 |
| Every 10 minutes | 4,320 | $5.18 |
| Every 30 minutes | 1,440 | $1.73 |
| Every 1 hour | 720 | $0.86 |
| Business hours only (8h/day) | 2,880 | $3.46 |
| Weekdays only (8h/day, 5 days) | 1,920 | $2.30 |


### Annual Cost Estimates

| Configuration | Monthly | Annual |
|---------------|---------|--------|
| This project (2 canaries, limited hours) | $3.38 | $40.56 |
| Small team (5 canaries, business hours) | $17.30 | $207.60 |
| Medium team (10 canaries, 24/7) | $103.70 | $1,244.40 |
| Enterprise (20 canaries, 24/7) | $178.12 | $2,137.44 |

### Free Tier

AWS offers a limited free tier for CloudWatch Synthetics:
- **100 canary runs per month** (free)
- After that, standard pricing applies

### Cost Monitoring

Set up AWS Budgets to track your Synthetics costs:

```bash
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://synthetics-budget.json
```

Example budget configuration:
```json
{
  "BudgetName": "CloudWatch-Synthetics-Budget",
  "BudgetLimit": {
    "Amount": "50",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

### Summary

- **Development/Testing**: $3-10/month (1-2 canaries, limited schedule)
- **Small Production**: $15-30/month (3-5 canaries, business hours)
- **Medium Production**: $50-150/month (10-20 canaries, varied schedules)
- **Enterprise**: $150-500/month (20+ canaries, 24/7 monitoring)

**Key Takeaway**: The schedule frequency has the biggest impact on cost. Running canaries every 5 minutes instead of every minute can save you 80% on costs while still providing adequate monitoring coverage.

## Next Steps

1. Create additional canary tests in separate folders
2. Customize schedules for different test frequencies
3. Add CloudWatch alarms for canary failures
4. Set up SNS notifications for alerts
5. Create dashboard for monitoring multiple canaries
