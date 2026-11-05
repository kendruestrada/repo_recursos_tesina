import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test008CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiEndpoint: string;
}

export class Test008Canary extends BaseCanary {
  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test008CanaryConfig) {

    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_008',
      handler: 'test_008_canary.handler',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      environmentVariables: {
        API_ENDPOINT: config.apiEndpoint,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);
  }
}
