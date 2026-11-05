/**
 * Environment configuration for Synthetics Canaries
 *
 * This file manages environment-specific configurations.
 * Values can be provided via environment variables or default values.
 */

import * as dotenv from 'dotenv';
import * as path from 'path';
import * as fs from 'fs';

// Load .env file if it exists
const envPath = path.resolve(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  console.log(`Loading environment from: ${envPath}`);
  dotenv.config({ path: envPath });
} else {
  console.log('No .env file found, using environment variables only');
}

export interface EnvironmentConfig {
  // General settings
  environment: string;

  // S3 Bucket
  artifactsBucketName: string;

  // Test_009 API Configuration
  test009ApiEndpoint: string;
  test009ApiKey: string;
  test009SsmParameterName: string;
  test005ApiEndpoint: string;

  // Test_006 Price Inconsistency Test
  test006ApiEndpoint: string;
  test006TableName: string;

  // test_011 
  test011ApiEndpoint: string;
  test011EmailFunctionName: string;

  // Test_002 API Config
  test002ApiEndpoint: string;
  test002TableName: string;

  // Test_012 Concurrency Test (NUEVO)
  test012ApiEndpoint: string;
  test012TableName: string;

  // test_013


  // test_013
  test013ApiEndpoint: string;

  // Test_014: Idempotency
  // Test_014: Idempotency
  test014ApiEndpoint: string;
  test014UserPointsTableName: string;

  // Test 015: Photo Deletion Bug
  test015ApiEndpoint: string;

  // Test 018: Saga Compensation Failure
  test018ApiEndpoint: string;
  test018TableName: string;
  test018StateMachineArn: string;

  // Test 019: Hot Partition Bug
  test019ApiEndpoint: string;
  test019LoadGeneratorFunctionName: string;

  // Test 016: Distributed Deadlock
  test016TransferApiEndpoint: string;
  test016InitializeFunctionName: string;
  test016AccountsTableName: string;
  test016LocksTableName: string;

  // Test 003: Config
  test003ApiEndpoint: string;
  test003PoliciesTable: string;
  test003RiskTable: string

  // Test_007 API Configuration
  test007ApiEndpoint: string;
  test007ApiKey: string;
  test007SsmParameterName: string;

  // Test 010: Encoding Test
  test010BaseUrl: string;
  test010UsersTableName: string;

  // Test 020: New Test Configuration
  test020ApiEndpoint: string;
  test020UserToken: string;
  test020SsmParameterName: string;

  // Test_004 API Configuration
  test004ApiEndpoint: string;
  test004UserPoolId: string;
  test004TableName: string;

  // Test_001 Configuration
  test001ApiEndpoint: string;
  test001FrontendUrl: string;

  // Test_008 Concurrent Transfer Test
  test008ApiEndpoint: string;

  // Homepage Test Configuration
  homepageTargetUrl: string;

  // AWS Configuration
  awsRegion?: string;
  awsAccount?: string;
}

/**
 * Get environment configuration from environment variables
 * with fallback to default values
 */
export function getEnvironmentConfig(): EnvironmentConfig {
  const environment = process.env.ENVIRONMENT || 'dev';

  return {
    environment,

    // S3 Bucket - use env var or default with environment suffix
    artifactsBucketName:
      process.env.ARTIFACTS_BUCKET_NAME ||
      `synthetics-canaries-artifacts-${environment}`,

    // Test_009 Configuration
    test009ApiEndpoint:
      process.env.TEST_009_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/v1/report',

    test009ApiKey:
      process.env.TEST_009_API_KEY ||
      'REPLACE_WITH_YOUR_API_TOKEN',

    test009SsmParameterName:
      process.env.TEST_009_SSM_PARAMETER_NAME ||
      `/canary/${environment}/test-009/api-key`,

    // Test_005 Configuration
    test005ApiEndpoint:
      process.env.TEST_005_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/credit',

    // Test_006 Configuration
    test006ApiEndpoint:
      process.env.TEST_006_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev',

    test006TableName:
      process.env.TEST_006_TABLE_NAME ||
      'dev-products',

    // test_011 Configuration (Agregado)
    test011ApiEndpoint:
      process.env.TEST_011_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/v1/report',

    test011EmailFunctionName:
      process.env.TEST_011_EMAIL_FUNCTION_NAME ||
      'EmailSenderFunction',

    // Test_002 Config
    test002ApiEndpoint:
      process.env.TEST_002_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/payment-callback',

    test002TableName:
      process.env.TEST_002_TABLE_NAME ||
      'bw-002-PaymentsTable',

    // Test_012 Configuration (Mapeo de variables)
    test012ApiEndpoint:
      process.env.TEST_012_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/purchase/',

    test012TableName:
      process.env.TEST_012_TABLE_NAME ||
      'bwtest-012-InventoryTable-1XYUTEJJMYZJM',


    test013ApiEndpoint: 
      process.env.TEST_013_API_ENDPOINT || 
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/process',

    // Test_014 Configuration
    // Test_014 Configuration
    test014ApiEndpoint:
      process.env.TEST_014_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/points/',

    test014UserPointsTableName:
      process.env.TEST_014_USER_POINTS_TABLE_NAME ||
      'UserPointsTable',

    // Test 015 Configuration
    test015ApiEndpoint:
      process.env.TEST_015_API_ENDPOINT ||
      'https://example-api.execute-api.us-east-1.amazonaws.com/dev',

    // Test 018 Configuration
    test018ApiEndpoint:
      process.env.TEST_018_API_ENDPOINT ||
      'https://example-api.execute-api.us-east-1.amazonaws.com/Prod/order',

    test018TableName:
      process.env.TEST_018_TABLE_NAME ||
      'OrdersTable-Test018',

    test018StateMachineArn:
      process.env.TEST_018_STATE_MACHINE_ARN ||
      'arn:aws:states:us-east-1:123456789012:stateMachine:OrderSagaStateMachine',
    
    // Test 001 Configuration
    test001ApiEndpoint:
      process.env.TEST_001_API_ENDPOINT || 
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod',
    test001FrontendUrl:
      process.env.TEST_001_FRONTEND_URL ||
      'http://bwtest001-stack-frontendbucket-gydmqtluv7aj.s3-website-us-east-1.amazonaws.com',

    // Test 019 Configuration
    test019ApiEndpoint:
      process.env.TEST_019_API_ENDPOINT || '',
    test019LoadGeneratorFunctionName:
      process.env.TEST_019_LOAD_GENERATOR_FUNCTION_NAME || '',

    // Test 016 Configuration
    test016TransferApiEndpoint: process.env.TEST_016_TRANSFER_API || '',
    test016InitializeFunctionName: process.env.TEST_016_INITIALIZE_FUNCTION || 'test-016-acc-setup',
    test016AccountsTableName: process.env.TEST_016_ACCOUNTS_TABLE || 'test-016-account-ledger',
    test016LocksTableName: process.env.TEST_016_LOCKS_TABLE || 'test-016-transaction-tracker',

    // Test_003 Configuration
    test003ApiEndpoint:
      process.env.TEST_003_API_ENDPOINT || '',
    test003PoliciesTable:
      process.env.TEST_003_POLICIES_TABLE || 'test003-policies-dev',
    test003RiskTable:
      process.env.TEST_003_RISK_FACTORS_TABLE || 'test003-risk-factors-dev',

    // Test_007 Configuration
    test007ApiEndpoint:
      process.env.TEST_007_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/v1/payment',

    test007ApiKey:
      process.env.TEST_007_API_KEY ||
      'REPLACE_WITH_YOUR_API_TOKEN',

    test007SsmParameterName:
      process.env.TEST_007_SSM_PARAMETER_NAME ||
      `/canary/${environment}/test-007/api-key`,
      
    // Test_010 Configuration
    test010BaseUrl:
      process.env.TEST_010_BASE_URL ||
      'https://example-api.execute-api.us-east-1.amazonaws.com/Prod',
    test010UsersTableName:
      process.env.TEST_010_USERS_TABLE_NAME ||
      'Users',

    // Test 020 Configuration
    test020ApiEndpoint: process.env.TEST_020_API_ENDPOINT || '',
    test020UserToken: process.env.TEST_020_USER_TOKEN || '',
    test020SsmParameterName: process.env.TEST_020_SSM_PARAMETER_NAME || `/canary/${environment}/test-020/user-token`,

    // Test_004 Configuration
    test004ApiEndpoint: process.env.TEST_004_API_ENDPOINT || '',
    test004UserPoolId: process.env.TEST_004_USER_POOL_ID || '',
    test004TableName: process.env.TEST_004_TABLE_NAME || 'subscriptions',

    // Test_008 Configuration
    test008ApiEndpoint:
      process.env.TEST_008_API_ENDPOINT ||
      'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod',

    // Homepage Test Configuration
    homepageTargetUrl:
      process.env.HOMEPAGE_TARGET_URL ||
      'https://example.com',

    // AWS Configuration
    awsRegion: process.env.AWS_REGION || process.env.CDK_DEFAULT_REGION,
    awsAccount: process.env.AWS_ACCOUNT || process.env.CDK_DEFAULT_ACCOUNT,
  };
}

/**
 * Validate required environment variables
 */
export function validateEnvironment(): void {
  const config = getEnvironmentConfig();
  const errors: string[] = [];

  // Warn about default API key
  if (config.test009ApiKey === 'REPLACE_WITH_YOUR_API_TOKEN') {
    console.warn(
      '\n⚠️  WARNING: TEST_009_API_KEY is not set. ' +
      'Using default placeholder value.\n' +
      'Set TEST_009_API_KEY environment variable or update SSM parameter after deployment.\n'
    );
  }

  // Validate API endpoint format
  if (!config.test009ApiEndpoint.startsWith('http')) {
    errors.push('TEST_009_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }

  if (!config.test006ApiEndpoint.startsWith('http')) {
    errors.push('TEST_006_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }

  // Validación del Test 012
  if (!config.test012ApiEndpoint.startsWith('http')) {
    errors.push('TEST_012_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }

  if (!config.test015ApiEndpoint.startsWith('http')) {
    errors.push('TEST_015_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }
  if (config.test019ApiEndpoint && !config.test019ApiEndpoint.startsWith('http')) {
    errors.push('TEST_019_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }
  if (!config.test003ApiEndpoint.startsWith('http')) {
    errors.push('TEST_003_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }

  if (!config.test010BaseUrl.startsWith('http')) {
    errors.push('TEST_010_BASE_URL must be a valid HTTP/HTTPS URL');
  }
  if(!config.test013ApiEndpoint.startsWith('http')) {
    errors.push('TEST_013_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }
  if (!config.test020ApiEndpoint.startsWith('http')) {
    errors.push('TEST_020_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }
  if (!config.test004ApiEndpoint.startsWith('http')) {
    errors.push('TEST_004_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }
  if(!config.test001ApiEndpoint.startsWith('http')) {
    errors.push('TEST_001_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }
  if (!config.test008ApiEndpoint.startsWith('http')) {
    errors.push('TEST_008_API_ENDPOINT must be a valid HTTP/HTTPS URL');
  }
  
  // Validación del Test 016
  if (!config.test016TransferApiEndpoint || !config.test016TransferApiEndpoint.startsWith('http')) {
    errors.push('TEST_016_TRANSFER_API must be a valid HTTP/HTTPS URL');
  }
  if (errors.length > 0) {
    throw new Error(
      'Environment validation failed:\n' +
      errors.map(e => `  - ${e}`).join('\n')
    );
  }
}

/**
 * Print current environment configuration (for debugging)
 */
export function printEnvironmentConfig(): void {
  const config = getEnvironmentConfig();

  console.log('\n📋 Environment Configuration:');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`Environment:           ${config.environment}`);
  console.log(`Artifacts Bucket:      ${config.artifactsBucketName}`);
  console.log(`Test_009 API Endpoint: ${config.test009ApiEndpoint}`);
  console.log(`Test_009 API Key:      ${config.test009ApiKey.substring(0, 5)}...`);
  console.log(`Test_009 SSM Param:    ${config.test009SsmParameterName}`);
  console.log(`Test_006 API Endpoint: ${config.test006ApiEndpoint}`);
  console.log(`Test_006 Table Name:   ${config.test006TableName}`);
  console.log(`Test_011 API Endpoint: ${config.test011ApiEndpoint}`);
  console.log(`Test_011 Email Func:   ${config.test011EmailFunctionName}`);
  console.log(`Test_012 API Endpoint: ${config.test012ApiEndpoint}`);
  console.log(`Test_012 Table Name:   ${config.test012TableName}`);
  console.log(`Test_002 API Endpoint: ${config.test002ApiEndpoint}`);
  console.log(`Test_002 Table Name:   ${config.test002TableName}`);
  console.log(`Test_013 API Endpoint: ${config.test013ApiEndpoint}`);
  console.log(`Test_014 API Endpoint: ${config.test014ApiEndpoint}`);
  console.log(`Test_014 Table Name:   ${config.test014UserPointsTableName}`);
  console.log(`Test_015 API Endpoint: ${config.test015ApiEndpoint}`);
  console.log(`Test_019 API Endpoint: ${config.test019ApiEndpoint}`);
  console.log(`Test_019 Load Gen:     ${config.test019LoadGeneratorFunctionName}`);
  console.log(`Test_003 API Endpoint: ${config.test003ApiEndpoint}`);
  console.log(`Test_003 Policies Table: ${config.test003PoliciesTable}`);
  console.log(`Test_003 Risk Table: ${config.test003RiskTable}`);
  console.log(`Test_010 Base URL:     ${config.test010BaseUrl}`);
  console.log(`Test_010 Users Table:  ${config.test010UsersTableName}`);
  console.log(`Test_020 API Endpoint: ${config.test020ApiEndpoint}`);
  console.log(`Test_020 SSM Param:    ${config.test020SsmParameterName}`);
  console.log(`Test_004 API Endpoint: ${config.test004ApiEndpoint}`);
  console.log(`Test_016 API Endpoint: ${config.test016TransferApiEndpoint}`);
  console.log(`Test_016 Init Func:    ${config.test016InitializeFunctionName}`);
  console.log(`Test_016 Accounts Tab: ${config.test016AccountsTableName}`);
  console.log(`Test_016 Locks Table:  ${config.test016LocksTableName}`);
  console.log(`Test_001 API Endpoint: ${config.test001ApiEndpoint}`);
  console.log(`Test_001 Frontend URL: ${config.test001FrontendUrl}`);
  console.log(`Test_008 API Endpoint: ${config.test008ApiEndpoint}`);
  console.log(`Homepage URL:          ${config.homepageTargetUrl}`);
  if (config.awsRegion) {
    console.log(`AWS Region:            ${config.awsRegion}`);
  }
  if (config.awsAccount) {
    console.log(`AWS Account:           ${config.awsAccount}`);
  }
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
}
