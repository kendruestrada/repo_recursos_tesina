import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test015CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiEndpoint: string;
}

export class Test015Canary extends BaseCanary {
  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test015CanaryConfig) {
    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_015',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0, // Using Python runtime
      handler: 'test_015_canary.handler',
      environmentVariables: {
        TEST_015_API_ENDPOINT: config.apiEndpoint,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);
  }
}
