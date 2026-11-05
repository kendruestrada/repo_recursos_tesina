import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test020CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiUrl: string;
  userToken: string;
  ssmParameterName: string;
}

export class Test020Canary extends BaseCanary {
  public readonly ssmParameter: ssm.StringParameter;

  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test020CanaryConfig) {
    // Creamos el parámetro SSM con el token del .env
    const ssmParameter = new ssm.StringParameter(scope, `${id}SsmParameter`, {
      parameterName: config.ssmParameterName,
      stringValue: config.userToken,
      tier: ssm.ParameterTier.STANDARD,
    });

    const baseConfig: BaseCanaryConfig = {
      ...config,
      canaryName: 'test-020-cors-v3', // Nombre nuevo para evitar conflictos de Drift
      testPath: 'canaries/test_020',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      handler: 'test_020_canary.handler',
      environmentVariables: {
        API_URL: config.apiUrl,
        SSM_PARAMETER_NAME: config.ssmParameterName,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);
    this.ssmParameter = ssmParameter;

    // Permisos para que el Canary lea su propio parámetro
    this.getRole().addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter'],
        resources: [this.ssmParameter.parameterArn],
      })
    );
  }
}