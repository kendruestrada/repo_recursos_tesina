import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test006CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiEndpoint: string;
  tableName: string;
}

export class Test006Canary extends BaseCanary {
  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test006CanaryConfig) {
    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_006',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      handler: 'test_006_canary.handler',
      environmentVariables: {
        API_ENDPOINT: config.apiEndpoint,
        TABLE_NAME: config.tableName,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);

    // Grant permission to put items in DynamoDB table
    const tableArn = `arn:aws:dynamodb:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:table/${config.tableName}`;
    this.getRole().addToPolicy(
      new iam.PolicyStatement({
        actions: ['dynamodb:PutItem'],
        resources: [tableArn],
        effect: iam.Effect.ALLOW,
      })
    );
  }
}
