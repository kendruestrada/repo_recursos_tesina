import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test004CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  apiEndpoint: string;
  userPoolId: string;
  tableName: string;
}

export class Test004Canary extends BaseCanary {
  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test004CanaryConfig) {
    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_004',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      handler: 'test_004_canary.handler',
      environmentVariables: {
        API_ENDPOINT: config.apiEndpoint,
        USER_POOL_ID: config.userPoolId,
        TABLE_NAME: config.tableName,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);

    // Permisos para DynamoDB (Get y Delete para limpieza)
    this.getRole().addToPolicy(new iam.PolicyStatement({
      actions: ['dynamodb:GetItem', 'dynamodb:DeleteItem'],
      resources: [`arn:aws:dynamodb:us-east-1:123456789012:table/${config.tableName}`],
    }));

    // Permisos para Cognito (Create, List y Delete para limpieza)
    this.getRole().addToPolicy(new iam.PolicyStatement({
      actions: [
        'cognito-idp:AdminCreateUser',
        'cognito-idp:AdminDeleteUser',
        'cognito-idp:AdminListGroupsForUser'
      ],
      resources: [`arn:aws:cognito-idp:us-east-1:123456789012:userpool/${config.userPoolId}`],
    }));
  }
}