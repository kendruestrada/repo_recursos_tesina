import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test016CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
  transferApiEndpoint: string;
  initializeFunctionName: string;
  accountsTableName: string;
  locksTableName: string;
}

export class Test016Canary extends BaseCanary {
  // ✅ Mantenemos la propiedad tal como querías
  private readonly config016: Test016CanaryConfig;

  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test016CanaryConfig) {
    const baseConfig: BaseCanaryConfig = {
      ...config,
      testPath: 'canaries/test_016',
      runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      handler: 'test_016_canary.handler',
      environmentVariables: {
        TRANSFER_API: config.transferApiEndpoint,
        INITIALIZE_FUNCTION: config.initializeFunctionName,
        ACCOUNTS_TABLE: config.accountsTableName,
        LOCKS_TABLE: config.locksTableName,
        ...config.environmentVariables,
      },
    };

    super(scope, id, artifactsBucket, baseConfig);
    
    this.config016 = config;

    this.applyDeadlockPermissions();
  }

private applyDeadlockPermissions(): void {
    const stack = cdk.Stack.of(this);

    // Permiso para invocar la Lambda de setup
    this.canaryRole.addToPolicy(new iam.PolicyStatement({
      actions: ['lambda:InvokeFunction'],
      resources: [`arn:aws:lambda:${stack.region}:${stack.account}:function:${this.config016.initializeFunctionName}`],
    }));

    this.canaryRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'dynamodb:Scan', 
        'dynamodb:GetItem', 
        'dynamodb:PutItem', 
        'dynamodb:DeleteItem',
        'dynamodb:BatchWriteItem'
      ],
      resources: [
        `arn:aws:dynamodb:${stack.region}:${stack.account}:table/${this.config016.accountsTableName}`,
        `arn:aws:dynamodb:${stack.region}:${stack.account}:table/${this.config016.locksTableName}`,
      ],
    }));
  }
}