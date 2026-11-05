import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import * as iam from 'aws-cdk-lib/aws-iam';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test002CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiEndpoint: string;
  dynamodbTableName: string;
}

export class Test002Canary extends BaseCanary {
  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test002CanaryConfig) {

    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_002', // Ruta a la carpeta del test
      handler: 'test_002_canary.handler',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      environmentVariables: {
        API_ENDPOINT: config.apiEndpoint,
        DYNAMODB_TABLE_NAME: config.dynamodbTableName,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);

    const tableArn = `arn:aws:dynamodb:*:*:table/${config.dynamodbTableName}`;

    this.getRole().addToPolicy(new iam.PolicyStatement({
      actions: [
        'dynamodb:GetItem',
      ],
      resources: [tableArn],
    }));
  }
}