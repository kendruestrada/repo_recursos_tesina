import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test009CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiEndpoint: string;
  ssmParameterName: string;
  apiKey: string;
}

export class Test009Canary extends BaseCanary {
  public readonly ssmParameter: ssm.StringParameter;

  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test009CanaryConfig) {
    // Create SSM Parameter for API authorization token
    const ssmParameter = new ssm.StringParameter(scope, `${id}SsmParameter`, {
      parameterName: config.ssmParameterName,
      stringValue: config.apiKey,
      description: 'API Authorization token for test_009 canary',
      tier: ssm.ParameterTier.STANDARD,
    });

    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_009',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      handler: 'test_009_canary.handler',
      environmentVariables: {
        API_ENDPOINT: config.apiEndpoint,
        SSM_PARAMETER_NAME: config.ssmParameterName,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);
    this.ssmParameter = ssmParameter;

    // Add SSM GetParameter permission
    this.getRole().addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter'],
        resources: [this.ssmParameter.parameterArn],
      })
    );
  }

}
