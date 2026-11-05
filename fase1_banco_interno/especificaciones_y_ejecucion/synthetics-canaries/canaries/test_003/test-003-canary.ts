import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test003CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiEndpoint: string;
  policiesTable: string;
  riskTable: string;
}

export class Test003Canary extends BaseCanary {
  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test003CanaryConfig) {
    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_003',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      handler: 'test_003_canary.handler',
      environmentVariables: {
        API_ENDPOINT: config.apiEndpoint,
        POLICIES_TABLE: config.policiesTable,
        RISK_TABLE: config.riskTable,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);

    const stack = cdk.Stack.of(this);

    // Permisos para usar las tablas de DynamoDB que ya existen
    this.getRole().addToPolicy(new iam.PolicyStatement({
      actions: ['dynamodb:PutItem', 'dynamodb:GetItem'],
      resources: [
        `arn:aws:dynamodb:${stack.region}:${stack.account}:table/${config.policiesTable}`,
        `arn:aws:dynamodb:${stack.region}:${stack.account}:table/${config.riskTable}`
      ]
    }));
  }
}