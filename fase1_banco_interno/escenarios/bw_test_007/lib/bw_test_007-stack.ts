import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { LogGroup, RetentionDays } from 'aws-cdk-lib/aws-logs';
import { RemovalPolicy, Duration } from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as path from 'path';

export class BwTest007Stack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const emailFunctionName = 'EmailServiceFunction'

    const emailLogGroup = new LogGroup(this, 'EmailServiceLogGroup', {
      logGroupName: `/aws/lambda/${emailFunctionName}`,
      retention: RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Create EmailService Lambda
    const emailServiceFunction = new lambda.Function(this, emailFunctionName, {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda/email-service')),
      timeout: cdk.Duration.seconds(30),
      environment: {
        SENDER_EMAIL: 'no-reply@example.com',
        STATUS_CHECK_URL: 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/status?num_cz=0.1'
      },
      logGroup: emailLogGroup,
      functionName: emailFunctionName,
      memorySize: 128,
    });

    // Grant SES permissions (for when mock is disabled)
    emailServiceFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      resources: ['*']
    }));

    const orderFunctionName = 'OrderProcessingFunction'

    const orderLogGroup = new LogGroup(this, 'OrderProcessingLogGroup', {
      logGroupName: `/aws/lambda/${orderFunctionName}`,
      retention: RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Create OrderProcessing Lambda
    const orderProcessingFunction = new lambda.Function(this, orderFunctionName, {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda/order-processing')),
      timeout: cdk.Duration.seconds(60),
      environment: {
        EMAIL_SERVICE_FUNCTION_NAME: emailServiceFunction.functionName
      },
      logGroup: orderLogGroup,
      functionName: orderFunctionName,
      memorySize: 128,
    });

    // Grant OrderProcessing permission to invoke EmailService
    emailServiceFunction.grantInvoke(orderProcessingFunction);

    const paymentFunctionName = 'PaymentConfirmationFunction'

    const paymentLogGroup = new LogGroup(this, 'PaymentConfirmationLogGroup', {
      logGroupName: `/aws/lambda/${paymentFunctionName}`,
      retention: RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Create PaymentConfirmation Lambda
    const paymentConfirmationFunction = new lambda.Function(this, paymentFunctionName, {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda/payment-confirmation')),
      timeout: cdk.Duration.seconds(90),
      environment: {
        ORDER_PROCESSING_FUNCTION_NAME: orderProcessingFunction.functionName
      },
      logGroup: paymentLogGroup,
      functionName: paymentFunctionName,
      memorySize: 128,
    });

    // Grant PaymentConfirmation permission to invoke OrderProcessing
    orderProcessingFunction.grantInvoke(paymentConfirmationFunction);

    // Create API Gateway
    const api = new apigateway.RestApi(this, 'PaymentsApi', {
      restApiName: 'Payments Processing API',
      description: 'API for processing payment confirmations',
      deployOptions: {
        stageName: 'v1'
      }
    });

    // Create API Key
    const apiKey = new apigateway.ApiKey(this, 'PaymentsApiKey', {
      apiKeyName: 'PaymentsApiKey',
      description: 'API Key for Payments Processing API'
    });

    // Create Usage Plan
    const usagePlan = api.addUsagePlan('PaymentsUsagePlan', {
      name: 'PaymentsUsagePlan',
      description: 'Usage plan for Payments API',
      throttle: {
        rateLimit: 100,
        burstLimit: 200
      },
      quota: {
        limit: 10000,
        period: apigateway.Period.MONTH
      }
    });

    // Associate API Key with Usage Plan
    usagePlan.addApiKey(apiKey);
    usagePlan.addApiStage({
      stage: api.deploymentStage
    });

    // Create /payment endpoint
    const paymentResource = api.root.addResource('payment');

    // Create POST method with API Key required
    const paymentIntegration = new apigateway.LambdaIntegration(paymentConfirmationFunction);

    paymentResource.addMethod('POST', paymentIntegration, {
      apiKeyRequired: true,
      requestValidator: new apigateway.RequestValidator(this, 'PaymentRequestValidator', {
        restApi: api,
        requestValidatorName: 'PaymentRequestValidator',
        validateRequestBody: true,
        validateRequestParameters: false
      }),
      requestModels: {
        'application/json': new apigateway.Model(this, 'PaymentRequestModel', {
          restApi: api,
          contentType: 'application/json',
          modelName: 'PaymentRequestModel',
          schema: {
            type: apigateway.JsonSchemaType.OBJECT,
            required: ['orderId'],
            properties: {
              orderId: {
                type: apigateway.JsonSchemaType.STRING,
                description: 'The order ID'
              },
              email: {
                type: apigateway.JsonSchemaType.STRING,
                description: 'Customer email address',
                format: 'email'
              }
            }
          }
        })
      }
    });

    // Outputs
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'API Gateway URL'
    });

    new cdk.CfnOutput(this, 'ApiKeyId', {
      value: apiKey.keyId,
      description: 'API Key ID'
    });

    new cdk.CfnOutput(this, 'PaymentEndpoint', {
      value: `${api.url}payment`,
      description: 'Payment endpoint URL'
    });

    new cdk.CfnOutput(this, 'PaymentConfirmationFunctionName', {
      value: paymentConfirmationFunction.functionName,
      description: 'PaymentConfirmation Lambda function name'
    });

    new cdk.CfnOutput(this, 'OrderProcessingFunctionName', {
      value: orderProcessingFunction.functionName,
      description: 'OrderProcessing Lambda function name'
    });

    new cdk.CfnOutput(this, 'EmailServiceFunctionName', {
      value: emailServiceFunction.functionName,
      description: 'EmailService Lambda function name'
    });
  }
}
