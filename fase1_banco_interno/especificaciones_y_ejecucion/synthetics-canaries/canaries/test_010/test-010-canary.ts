import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import { BaseCanary, BaseCanaryConfig } from '../../lib/base-canary';

export interface Test010CanaryConfig extends Omit<BaseCanaryConfig, 'handler'> {
    baseUrl: string;
    usersTableName: string;
}

export class Test010Canary extends BaseCanary {
    constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: Test010CanaryConfig) {
        const baseConfig: BaseCanaryConfig = {
            ...config,
            testPath: 'canaries/test_010',
            runtime: synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
            handler: 'test_010_canary.handler',
            environmentVariables: {
                BASE_URL: config.baseUrl,
                USERS_TABLE_NAME: config.usersTableName,
                ...config.environmentVariables,
            },
        };

        super(scope, id, artifactsBucket, baseConfig);

        const tableArn = `arn:aws:dynamodb:*:*:table/${config.usersTableName}`;

        this.getRole().addToPolicy(new iam.PolicyStatement({
            actions: [
                'dynamodb:GetItem',
                'dynamodb:Query',
                'dynamodb:Scan',
                'dynamodb:DeleteItem'
            ],
            resources: [tableArn],
        }));
    }
}
