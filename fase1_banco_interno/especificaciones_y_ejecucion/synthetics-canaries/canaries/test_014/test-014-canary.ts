import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import * as iam from 'aws-cdk-lib/aws-iam';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test014CanaryConfig extends Omit<BaseCanaryConfig, 'testPath' | 'runtime' | 'handler'> {
    apiEndpoint: string; // Changed from functionArn to apiEndpoint
    userPointsTableName: string;
}

export class Test014Canary extends BaseCanary {

    constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test014CanaryConfig) {

        const baseConfig: BaseCanaryConfig = {
            ...config,
            testPath: 'canaries/test_014',
            handler: 'test_014_canary.handler',
            runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
            environmentVariables: {
                TEST_014_API_ENDPOINT: config.apiEndpoint,
                TEST_014_USER_POINTS_TABLE_NAME: config.userPointsTableName,
                ...config.environmentVariables,
            },
        };

        super(scope, id, artifactsBucket, baseConfig);

        // FIX: Using correct method to access role (inherited protected property or method)
        // BaseCanary exposes access via this.getRole() or this.canary.role
        this.getRole().addToPolicy(new iam.PolicyStatement({
            actions: ['dynamodb:GetItem', 'dynamodb:PutItem', 'dynamodb:UpdateItem'],
            resources: [`arn:aws:dynamodb:*:*:table/${config.userPointsTableName}`],
        }));
    }
}
