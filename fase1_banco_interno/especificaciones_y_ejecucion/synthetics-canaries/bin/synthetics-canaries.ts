#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { SyntheticsCanariesStack } from '../lib/synthetics-canaries-stack';
import { HomepageCanary } from '../canaries/homepage-test/homepage-canary';
import { Test009Canary } from '../canaries/test_009/test-009-canary';
import { Test005Canary } from '../canaries/test_005/test-005-canary';
import { Test006Canary } from '../canaries/test_006/test-006-canary';
import { Test011Canary } from '../canaries/test_011/test-011-canary';
import { Test012Canary } from '../canaries/test_012/test-012-canary';
import { Test002Canary } from '../canaries/test_002/test-002-canary';
import { Test013Canary } from '../canaries/test_013/test-013-canary';
import { Test014Canary } from '../canaries/test_014/test-014-canary';
import { Test015Canary } from '../canaries/test_015/test-015-canary';
import { Test018Canary } from '../canaries/test_018/test-018-canary';
import { Test016Canary } from '../canaries/test_016/test-016-canary';
import { Test003Canary } from '../canaries/test_003/test-003-canary';
import { Test007Canary } from '../canaries/test_007/test-007-canary';
import { Test010Canary } from '../canaries/test_010/test-010-canary';
import { Test020Canary } from '../canaries/test_020/test-020-canary';
import { Test004Canary } from '../canaries/test_004/test-004-canary';
import { Test019Canary } from '../canaries/test_019/test-019-canary';
import { Test001Canary } from '../canaries/test_001/test-001-canary';
import { Test008Canary } from '../canaries/test_008/test-008-canary';
import { getEnvironmentConfig, validateEnvironment, printEnvironmentConfig } from '../lib/environment';

// Validate and load environment configuration
validateEnvironment();
const envConfig = getEnvironmentConfig();

// Print configuration for visibility
printEnvironmentConfig();

const app = new cdk.App();

new SyntheticsCanariesStack(app, 'SyntheticsCanariesStack', {
  artifactsBucketName: envConfig.artifactsBucketName,
  canaries: [
    // Example 1: Homepage test using local Python files
    // Runs on weekdays only, every hour starting at 13:00 UTC-3 (16:00 UTC)
    (scope, artifactsBucket) => new HomepageCanary(
      scope,
      'HomepageCanary',
      artifactsBucket,
      {
        canaryName: 'homepage-test',
        targetUrl: envConfig.homepageTargetUrl,
        schedule: {
          expression: 'cron(*/20 13-15 ? * MON-FRI *)'
        }
      }
    ),

    // Test_009: REST API test with SSM authorization
    (scope, artifactsBucket) => new Test009Canary(
      scope,
      'Test009Canary',
      artifactsBucket,
      {
        canaryName: 'test-009',
        apiEndpoint: envConfig.test009ApiEndpoint,
        apiKey: envConfig.test009ApiKey,
        ssmParameterName: envConfig.test009SsmParameterName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_005: REST API test with SSM authorization
    (scope, artifactsBucket) => new Test005Canary(
      scope,
      'Test005Canary',
      artifactsBucket,
      {
        canaryName: 'test-005',
        apiEndpoint: envConfig.test005ApiEndpoint,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_006: Price Inconsistency Test
    (scope, artifactsBucket) => new Test006Canary(
      scope,
      'Test006Canary',
      artifactsBucket,
      {
        canaryName: 'test-006',
        apiEndpoint: envConfig.test006ApiEndpoint,
        tableName: envConfig.test006TableName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),


    (scope, artifactsBucket) => new Test011Canary(
      scope,
      'Test011Canary',
      artifactsBucket,
      {
        canaryName: 'test-011-monitor',
        apiEndpoint: envConfig.test011ApiEndpoint,
        emailFunctionName: envConfig.test011EmailFunctionName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),


    // Test_002: Payments test
    (scope, artifactsBucket) => new Test002Canary(
      scope, 'Test002Canary', artifactsBucket,
      {
        canaryName: 'test-002-payments',
        apiEndpoint: envConfig.test002ApiEndpoint,
        dynamodbTableName: envConfig.test002TableName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),
    // Test_001: Silent Data Corruption Test
    (scope, artifactsBucket) => new Test001Canary(
      scope, 'Test001Canary', artifactsBucket,
      {
        canaryName: 'test-001-address-bug',
        frontendUrl: envConfig.test001FrontendUrl,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_012: Purchase API test with DynamoDB access
    (scope, artifactsBucket) => new Test012Canary(
      scope,
      'Test012Concurrency',
      artifactsBucket,
      {
        canaryName: 'test-012-concurrency',
        apiEndpoint: envConfig.test012ApiEndpoint,
        tableName: envConfig.test012TableName,
        schedule: { expression: 'cron(*/5 13-18 ? * MON-FRI *)' }
      }
    ),


    (scope, artifactsBucket) => new Test013Canary(
      scope, 'Test013Canary', artifactsBucket,
      {
        canaryName: 'test-013-leak',
        apiEndpoint: envConfig.test013ApiEndpoint,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),


    (scope, artifactsBucket) => new Test014Canary(
      scope, 'Test014Canary', artifactsBucket,
      {
        canaryName: 'test-014-idempotency',
        apiEndpoint: envConfig.test014ApiEndpoint,
        userPointsTableName: envConfig.test014UserPointsTableName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_015: Photo Deletion Bug
    (scope, artifactsBucket) => new Test015Canary(
      scope, 'Test015Canary', artifactsBucket,
      {
        canaryName: 'test-015-photo-bug',
        apiEndpoint: envConfig.test015ApiEndpoint,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_018: Saga Compensation Failure
    (scope, artifactsBucket) => new Test018Canary(
      scope, 'Test018Canary', artifactsBucket,
      {
        canaryName: 'test-018-saga-failure',
        apiEndpoint: envConfig.test018ApiEndpoint,
        tableName: envConfig.test018TableName,
        stateMachineArn: envConfig.test018StateMachineArn,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_016: Distributed Deadlock
    (scope, artifactsBucket) => new Test016Canary(
      scope,
      'Test016Canary',
      artifactsBucket,
      {
        canaryName: 'test-016-deadlock',
        transferApiEndpoint: envConfig.test016TransferApiEndpoint,
        initializeFunctionName: envConfig.test016InitializeFunctionName,
        accountsTableName: envConfig.test016AccountsTableName,
        locksTableName: envConfig.test016LocksTableName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_003: Policy Transfer API Test (AGREGAR ESTO)
    (scope, artifactsBucket) => new Test003Canary(
      scope,
      'Test003PolicyTransfer',
      artifactsBucket,
      {
        canaryName: 'test-003-policy-transfer',
        apiEndpoint: envConfig.test003ApiEndpoint,
        policiesTable: envConfig.test003PoliciesTable,
        riskTable: envConfig.test003RiskTable,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_007: REST API test with SSM authorization
    (scope, artifactsBucket) => new Test007Canary(
      scope,
      'Test007Canary',
      artifactsBucket,
      {
        canaryName: 'test-007',
        apiEndpoint: envConfig.test007ApiEndpoint,
        apiKey: envConfig.test007ApiKey,
        ssmParameterName: envConfig.test007SsmParameterName,
        schedule: {
          expression: 'cron(0,30 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_010: Encoding Test
    (scope, artifactsBucket) => new Test010Canary(
      scope,
      'Test010Canary',
      artifactsBucket,
      {
        canaryName: 'test-010-encoding',
        baseUrl: envConfig.test010BaseUrl,
        usersTableName: envConfig.test010UsersTableName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),
    // Test_020: CORS Configuration Test
    (scope, artifactsBucket) => new Test020Canary(
      scope,
      'Test020CORS',
      artifactsBucket,
      {
        canaryName: 'test-020-cors-v3',
        apiUrl: envConfig.test020ApiEndpoint,
        userToken: envConfig.test020UserToken,
        ssmParameterName: envConfig.test020SsmParameterName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),
    // Test_004: Inconsistencia de Suscripción (NUEVO)
    (scope, artifactsBucket) => new Test004Canary(
      scope,
      'Test004Canary',
      artifactsBucket,
      {
        canaryName: 'test-004-inconsistency',
        apiEndpoint: envConfig.test004ApiEndpoint,
        userPoolId: envConfig.test004UserPoolId,
        tableName: envConfig.test004TableName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_019: Hot Partition Bug
    (scope, artifactsBucket) => new Test019Canary(
      scope,
      'Test019Canary',
      artifactsBucket,
      {
        canaryName: 'test-019-hot-partition',
        apiEndpoint: envConfig.test019ApiEndpoint,
        loadGeneratorFunctionName: envConfig.test019LoadGeneratorFunctionName,
        schedule: {
          expression: 'cron(*/5 13-18 ? * MON-FRI *)'
        }
      }
    ),

    // Test_008: Concurrent Transfer Race Condition
    (scope, artifactsBucket) => new Test008Canary(
      scope,
      'Test008Canary',
      artifactsBucket,
      {
        canaryName: 'test-008-race-condition',
        apiEndpoint: envConfig.test008ApiEndpoint,
        schedule: {
          expression: 'cron(*/30 13-15 ? * MON-FRI *)'
        }
      }
    ),

  ],

  /* If you don't specify 'env', this stack will be environment-agnostic.
   * Account/Region-dependent features and context lookups will not work,
   * but a single synthesized template can be deployed anywhere. */

  /* Uncomment the next line to specialize this stack for the AWS Account
   * and Region that are implied by the current CLI configuration. */
  // env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },

  /* Uncomment the next line if you know exactly what Account and Region you
   * want to deploy the stack to. */
  // env: { account: '123456789012', region: 'us-east-1' },

  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});