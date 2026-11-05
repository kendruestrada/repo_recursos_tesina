import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import * as iam from 'aws-cdk-lib/aws-iam';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test018CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
    apiEndpoint: string;
    tableName: string;
    stateMachineArn: string;
}

export class Test018Canary extends BaseCanary {
    constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test018CanaryConfig) {

        const baseConfig: BaseCanaryConfig = {
            ...config,
            testPath: 'canaries/test_018',
            handler: 'test_018_canary.handler',
            runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
            environmentVariables: {
                TEST_018_API_ENDPOINT: config.apiEndpoint,
                TEST_018_TABLE_NAME: config.tableName,
                TEST_018_STATE_MACHINE_ARN: config.stateMachineArn,
                ...config.environmentVariables,
            },
        };

        super(scope, id, artifactsBucket, baseConfig);

        // Grant permissions to read DynamoDB
        this.getRole().addToPolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'dynamodb:GetItem',
                    'dynamodb:Query',
                    'dynamodb:Scan'
                ],
                resources: [`arn:aws:dynamodb:*:*:table/${config.tableName}`],
            })
        );

        // Grant permissions to describe Step Functions executions
        // Extract state machine name from ARN for execution resource pattern
        const stateMachineArnParts = config.stateMachineArn.split(':');
        const stateMachineName = stateMachineArnParts[stateMachineArnParts.length - 1];
        const executionArnPrefix = config.stateMachineArn.replace(':stateMachine:', ':execution:');

        this.getRole().addToPolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'states:DescribeExecution',
                    'states:GetExecutionHistory'
                ],
                resources: [
                    `${executionArnPrefix}:*`
                ],
            })
        );
    }
}
