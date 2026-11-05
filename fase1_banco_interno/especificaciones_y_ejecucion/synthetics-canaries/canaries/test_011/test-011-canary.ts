import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import * as iam from 'aws-cdk-lib/aws-iam';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test011CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiEndpoint: string;
  emailFunctionName: string;
}

export class Test011Canary extends BaseCanary {
  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test011CanaryConfig) {

    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_011',

      handler: 'trigger_canary.handler',

      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,

      environmentVariables: {
        API_ENDPOINT: config.apiEndpoint,
        TEST_011_EMAIL_FUNCTION_NAME: config.emailFunctionName,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);

    // Grant permissions to read CloudWatch Metrics
    this.getRole().addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'cloudwatch:GetMetricStatistics',
          'cloudwatch:ListMetrics'
        ],
        resources: ['*'],
      })
    );
  }
}