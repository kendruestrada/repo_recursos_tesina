import * as cdk from 'aws-cdk-lib/core';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { BaseCanary } from './base-canary';

export interface SyntheticsCanariesStackProps extends cdk.StackProps {
  canaries?: Array<(scope: Construct, artifactsBucket: s3.IBucket) => BaseCanary>;
  artifactsBucketName?: string;
}

export class SyntheticsCanariesStack extends cdk.Stack {
  public readonly artifactsBucket: s3.Bucket;
  public readonly canaries: BaseCanary[] = [];

  constructor(scope: Construct, id: string, props?: SyntheticsCanariesStackProps) {
    super(scope, id, props);

    // Create S3 bucket for canary artifacts
    this.artifactsBucket = new s3.Bucket(this, 'CanaryArtifactsBucket', {
      bucketName: props?.artifactsBucketName,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Create canaries from the provided list
    if (props?.canaries) {
      props.canaries.forEach((canaryFactory) => {
        const canary = canaryFactory(this, this.artifactsBucket);
        this.canaries.push(canary);
      });
    }

    // Output the bucket name and canary information
    new cdk.CfnOutput(this, 'ArtifactsBucketName', {
      value: this.artifactsBucket.bucketName,
      description: 'S3 bucket for canary artifacts',
    });

    this.canaries.forEach((canary, index) => {
      new cdk.CfnOutput(this, `Canary${index}Name`, {
        value: canary.getCanaryName(),
        description: `Canary ${index} name`,
      });
    });
  }
}
