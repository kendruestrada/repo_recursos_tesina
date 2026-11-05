import * as cdk from 'aws-cdk-lib';
import * as synthetics from 'aws-cdk-lib/aws-synthetics';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import * as path from 'path';

export interface BaseCanaryConfig {
  canaryName: string;
  testPath?: string;
  s3CodeBucket?: string;
  s3CodeKey?: string;
  schedule?: synthetics.CfnCanary.ScheduleProperty;
  runtime?: synthetics.Runtime;
  handler: string;
  environmentVariables?: { [key: string]: string };
}

export abstract class BaseCanary extends Construct {
  public readonly canary: synthetics.Canary;
  protected readonly artifactsBucket: s3.IBucket;
  protected readonly config: BaseCanaryConfig;
  protected readonly canaryRole: iam.Role;

  constructor(scope: Construct, id: string, artifactsBucket: s3.IBucket, config: BaseCanaryConfig) {
    super(scope, id);

    this.config = config;
    this.artifactsBucket = artifactsBucket;

    // Create IAM role for the canary
    const canaryRole = new iam.Role(this, 'CanaryRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    this.canaryRole = canaryRole;

    // Grant permissions to write to S3 bucket
    this.artifactsBucket.grantWrite(canaryRole);

    canaryRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetBucketLocation'],
        resources: [this.getArtifactsBucketArn()],
      })
    );

    canaryRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['cloudwatch:PutMetricData'],
        resources: ['*'],
      })
    );

    // Determine code source
    let testCode: synthetics.Code;
    if (this.config.s3CodeBucket && this.config.s3CodeKey) {
      // Load code from S3
      const codeBucket = s3.Bucket.fromBucketName(this, 'CodeBucket', this.config.s3CodeBucket);
      codeBucket.grantRead(canaryRole);
      testCode = synthetics.Code.fromBucket(codeBucket, this.config.s3CodeKey);
    } else if (this.config.testPath) {
      // Load code from local asset
      testCode = synthetics.Code.fromAsset(path.join(__dirname, '..', this.config.testPath));
    } else {
      throw new Error('Either testPath or s3CodeBucket/s3CodeKey must be provided');
    }

    // Determine handler
    const handler = this.config.handler;

    // Create the canary
    this.canary = new synthetics.Canary(this, 'Canary', {
      canaryName: this.config.canaryName,
      runtime: this.config.runtime || synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_7_0,
      test: synthetics.Test.custom({
        code: testCode,
        handler: handler,
      }),
      schedule: this.config.schedule
        ? synthetics.Schedule.expression(this.config.schedule.expression)
        : synthetics.Schedule.rate(cdk.Duration.minutes(5)),
      artifactsBucketLocation: {
        bucket: this.artifactsBucket,
      },
      role: canaryRole,
      environmentVariables: this.config.environmentVariables,
    });

    // Configure CloudWatch Logs retention to 30 days (1 month) for all canaries
    const logGroupName = `/aws/lambda/cwsyn-${this.config.canaryName}`;
    new logs.LogGroup(this, 'CanaryLogGroup', {
      logGroupName: logGroupName,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
  }

  public getRole(): iam.Role {
    return this.canaryRole;
  }

  public getCanaryName(): string {
    return this.config.canaryName;
  }

  public getArtifactsBucketArn(): string {
    return this.artifactsBucket.bucketArn;
  }
}
