# AWS Devops agent attemps to identify root cause

## Test with similirar promt like claude:

`check lambda function ReportGenerator for errors and identify root cause on source code Investigation starting point: it is failling from time to time not always `

- Findings from the agent:

```bash
Intermittent Error Pattern with 14.3% Failure Rate
The ReportGenerator function shows 2 errors out of 14 invocations (14.3% error rate) during the primary window, confirming the intermittent failure pattern. Errors occurred at 15:40 and 16:10, showing sporadic rather than continuous failures. No errors were detected in the baseline comparison window (13:00-14:30), indicating this is a new issue starting around the symptom time. The error pattern directly matches the reported "from time to time" failure description.
2 errors detected at 15:40 and 16:10 out of 14 total invocations

Duration Spike to 35 Seconds Correlates with First Error
At 15:40, the duration spiked to exactly 35,000ms (35 seconds), coinciding with the first error. This precise value strongly suggests a Lambda timeout configuration at 35 seconds. Baseline duration across successful invocations averages 4.5-6.3 seconds. The second error at 16:10 shows elevated but non-timeout duration of 6,360ms. This indicates two potential failure modes: complete timeout (15:40) and another issue causing errors without timeout (16:10).
35-second timeout at 15:40 correlates with error; second error at 16:10 shows elevated 6.3s duration

Lambda function failures caused by memory exhaustion and timeout due to accumulating data in memory
The Lambda function exhibits two distinct failure modes directly caused by a memory leak pattern where data accumulates across invocations. The "List size" logs show data growing from 800KB to 4.2MB over consecutive invocations (count: 1→2→3→4→5), correlating with memory usage climbing from 97MB to 127MB (the configured 128MB limit). When memory reaches the limit, the function either times out (35 seconds at 15:40:45) or fails with Runtime.OutOfMemory (at 16:10:16). After failures, the pattern resets and repeats. In the primary window, 2 out of 14 invocations (14%) failed, while the baseline window had 0 failures with no invocations logged. This represents a new problematic pattern introduced in the primary window.
Runtime.OutOfMemory error when Lambda reaches configured memory limit

Progressive memory usage increase correlating with accumulating data size

Application data structure growing from 800KB to 4.2MB across consecutive invocations
Source: cloudwatch
[2026-01-30T15:15:21.959Z] List size: 800984 bytes, count: 1
[2026-01-30T15:20:14.688Z] List size: 1624056 bytes, count: 2
[2026-01-30T15:25:14.997Z] List size: 2601560 bytes, count: 3
[2026-01-30T15:30:15.306Z] List size: 3292664 bytes, count: 4
[2026-01-30T15:35:14.912Z] List size: 4167352 bytes, count: 5

Excellent! I have clear findings from all three investigations. The logs reveal a memory leak where data accumulates across Lambda invocations, causing intermittent failures when memory reaches the 128MB limit. Let me now examine the source code to identify the specific code defect.

Memory leak from global variable accumulating data across Lambda invocations
The ReportGenerator Lambda function contains a coding defect where a data structure (likely a list or dictionary) is declared at module scope (outside the handler function) instead of within the handler. Lambda's execution context reuse causes this global variable to persist and accumulate data across invocations. Log evidence shows 'List size' growing from 800KB (count: 1) to 4.2MB (count: 5) across consecutive invocations, with corresponding memory usage increasing from 97MB to 127MB until reaching the configured 128MB limit. This triggers two failure modes: (1) 35-second timeout when processing can't complete before limit, and (2) Runtime.OutOfMemory error. After failures, the execution context is destroyed and a new one is created, resetting the pattern. This explains the intermittent nature (14.3% failure rate) - failures occur predictably on the 5th or 6th invocation in each execution context lifecycle.

Root causes

1. Memory leak from global variable accumulating data across Lambda invocations
The ReportGenerator Lambda function contains a coding defect where a data structure (likely a list or dictionary) is declared at module scope (outside the handler function) instead of within the handler. Lambda's execution context reuse causes this global variable to persist and accumulate data across invocations. Log evidence shows 'List size' growing from 800KB (count: 1) to 4.2MB (count: 5) across consecutive invocations, with corresponding memory usage increasing from 97MB to 127MB until reaching the configured 128MB limit. This triggers two failure modes: (1) 35-second timeout when processing can't complete before limit, and (2) Runtime.OutOfMemory error. After failures, the execution context is destroyed and a new one is created, resetting the pattern. This explains the intermittent nature (14.3% failure rate) - failures occur predictably on the 5th or 6th invocation in each execution context lifecycle.

Investigation gaps

Unable to examine ReportGenerator source code directly
Could not retrieve the ReportGenerator Lambda function source code to pinpoint the exact variable declaration and code location causing the memory leak. The explore_deployments tool found no deployment history through GitHub, GitLab, or Amazon Pipeline, suggesting the function was deployed manually or via AWS Console. While log analysis provides strong behavioral evidence of a global variable accumulating data (List size growing from 800KB to 4.2MB with incrementing count across invocations), direct code inspection would confirm: (1) the exact variable name and type, (2) the specific file and line number of the problematic declaration, (3) whether multiple global variables are accumulating data, (4) the data being accumulated. To view the actual code, access via AWS Console Lambda editor, AWS CLI 'get-function' command, or local development environment would be required.
```

## Mitigation plan, where it gives u the commands to apply a rollback:

```bash
Increase Lambda function memory allocation from 128MB to 512MB as a temporary measure to reduce failure frequency, followed by permanent code fix to eliminate memory leak
The root cause analysis identified a pre-existing code defect in the ReportGenerator Lambda function (arn:aws:lambda:us-east-1:123456789012:function:ReportGenerator) where a global variable accumulates data across invocations due to Lambda execution context reuse. This causes intermittent failures (14.3% rate) when memory reaches the 128MB limit after 5-6 invocations. The function was last deployed on 2026-01-22, and no deployment pipeline context exists (manual deployment). Since this is a latent code defect that requires development work rather than a recent deployment that can be rolled back, the mitigation strategy combines: (1) an immediate temporary operational action to increase memory capacity 4x, reducing failure frequency and buying time for development, and (2) a code change specification for the permanent fix to move global variables inside the handler function. The memory increase is a temporary workaround that reduces but does not eliminate failures - the code fix is required for complete resolution.
Immediate mitigation
Step 1: Prepare
Identify current system status before any changes.
1.1
Record the current memory size (128MB) and timeout (35s) settings before making changes
aws lambda get-function-configuration --function-name ReportGenerator --region us-east-1


Step 2: Pre-validate
Test the preconditions to ensure your system is ready for the change.
2.1
Check CloudWatch metrics for the past 3 hours to confirm current failure rate and establish pre-mitigation baseline
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value=ReportGenerator --start-time 2026-01-30T14:49:26Z --end-time 2026-01-30T17:49:26Z --period 300 --statistics Sum --region us-east-1


Step 3: Apply
Execute the change in your environment.
3.1
Increase memory from 128MB to 512MB to provide 4x capacity buffer, reducing frequency of memory-related failures from every 5-6 invocations to approximately every 20-24 invocations
aws lambda update-function-configuration --function-name ReportGenerator --memory-size 512 --region us-east-1


Increasing Lambda memory from 128MB to 512MB will increase execution costs by approximately 4x (Lambda pricing scales linearly with memory allocation). Monitor AWS Cost Explorer for the ReportGenerator function to track cost impact. This temporary measure should be reversed once the permanent code fix is deployed to avoid ongoing increased costs.
Step 4: Post-validate
Monitor system health and key metrics to confirm the change mitigated the issue.
4.1
Verify the MemorySize field shows 512MB in the function configuration
aws lambda get-function-configuration --function-name ReportGenerator --region us-east-1


4.2
Check CloudWatch error metrics for 30-60 minutes post-change to verify error rate has decreased compared to pre-mitigation baseline
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value=ReportGenerator --start-time 2026-01-30T17:49:26Z --end-time 2026-01-30T18:49:26Z --period 300 --statistics Sum --region us-east-1


The memory increase is a temporary workaround that reduces failure frequency but does not eliminate the root cause. The memory leak will continue to accumulate data across invocations, just at a slower rate. Expect failures to still occur, but less frequently (approximately every 20-24 invocations instead of every 5-6 invocations). The permanent code fix documented in the code change specification must be implemented to fully resolve the issue.
```

## Other not related issue:

There was a missconfiguration with the canaries project where an env var was removed, so the canary test execution was failing when calling the test009 app. The agent was able to identify root cause and which deployment cause the issue:

```bash
CloudFormation deployment on 2026-01-28T18:06:43Z introduced buggy canary code
A CloudFormation stack update to SyntheticsCanariesStack executed by user aws-cdk-eboni at 2026-01-28T18:06:20Z deployed new code to the test-009 canary via UpdateCanary operation at 18:06:43Z. This deployment loaded code from S3 bucket cdk-hnb659fds-assets-123456789012-us-east-1 with key c03de4598a735d3d3291d2f2b1f25eeb6a84968722e1e5b6b3b5fdcbe6c72682.zip into Lambda layer version 6. The deployment occurred just 1 minute and 33 seconds after the canary's last successful run at 18:05:10Z. This new code contained two critical bugs: (1) logic error causing the SSM parameter name to be None/null, and (2) Python variable scoping error where urllib3 is referenced in an exception handler before being assigned. The canary began failing after this deployment and has failed consistently since. A subsequent deployment at 2026-01-29T19:40:16Z deployed the same buggy code (identical S3 key) to layer version 7, which is why the canary continued failing after that deployment as well.

Key findings

1. SSM parameter name is None/null in canary code
The canary code attempts to fetch an SSM parameter with name 'None' (literally None/null in Python), causing botocore.exceptions.ParamValidationError: 'Invalid type for parameter Name, value: None, type: <class 'NoneType'>, valid types: <class 'str'>'. The logs show the canary logging 'Fetching authorization token from SSM: None' at line 23 in test_009_canary.py when calling ssm_client.get_parameter(). This indicates the code logic for determining the SSM parameter name is returning None instead of the expected parameter name (likely '/canary/dev/test-009/api-key'). This bug was introduced in the code deployed from S3 key c03de4598a735d3d3291d2f2b1f25eeb6a84968722e1e5b6b3b5fdcbe6c72682.zip at 2026-01-28T18:06:43Z.

2. Python variable scoping bug in test_009_canary.py exception handler

The canary code in test_009_canary.py has a Python UnboundLocalError at line 81 where an exception handler attempts to catch 'urllib3.exceptions.HTTPError' but the urllib3 variable is not in scope at that point. The stack trace shows: 'File "/opt/python/test_009_canary.py", line 81, in handler: except urllib3.exceptions.HTTPError as e: UnboundLocalError: cannot access local variable urllib3 where it is not associated with a value'. This is a classic Python scoping error where a variable is referenced before being assigned in the function. The bug exists in the canary code deployed from S3 key c03de4598a735d3d3291d2f2b1f25eeb6a84968722e1e5b6b3b5fdcbe6c72682.zip at 2026-01-28T18:06:43Z.


```

There's a option to generate a mitigation plan, where it give u the commands to apply a rollback:

```bash
Roll back CloudWatch Synthetics canary 'test-009' to last known good code version from deployment at 2026-01-30T15:10:50Z
The investigation identified that a CloudFormation deployment at 2026-01-30T16:24:57Z introduced buggy canary code (S3 key c03de4598a735d3d3291d2f2b1f25eeb6a84968722e1e5b6b3b5fdcbe6c72682.zip) containing two critical code defects: (1) SSM parameter name logic returns None/null causing ParamValidationError, and (2) Python variable scoping error where urllib3 is referenced in an exception handler before being assigned, causing UnboundLocalError. The canary has been continuously failing since this deployment. The last successful deployment at 2026-01-30T15:10:50Z used different code (S3 key ff9681d0862f291b2a593db06765d821073060ca7709ba7c18a029224a1b70c5.zip) with the SSM_PARAMETER_NAME environment variable properly set to '/canary/dev/test-009/api-key'. Rolling back to this known good version will restore canary functionality. Impacted resources: arn:aws:synthetics:us-east-1:123456789012:canary:test-009 in AWS account 123456789012.

Step 1: Prepare
Identify current system status before any changes.
1.1
Capture the current canary configuration for potential rollback if the mitigation causes unexpected issues
aws synthetics get-canary --name test-009 --region us-east-1


Verify that the backup operation captures all necessary configuration details including code location and environment variables
1.2
Confirm that the last known good deployment artifact exists in S3 before attempting rollback
aws s3api head-object --bucket cdk-hnb659fds-assets-123456789012-us-east-1 --key ff9681d0862f291b2a593db06765d821073060ca7709ba7c18a029224a1b70c5.zip --region us-east-1


Verify that the backup operation captures all necessary configuration details including code location and environment variables
Step 2: Pre-validate
Test the preconditions to ensure your system is ready for the change.
2.1
Verify that the canary is currently experiencing failures before proceeding with rollback
aws synthetics get-canary-runs --name test-009 --max-results 3 --region us-east-1


Step 3: Apply
Execute the change in your environment.
3.1
Roll back the canary to the last known good code version from 2026-01-30T15:10:50Z deployment, restoring working code and SSM parameter configuration
aws synthetics update-canary --name test-009 --code Handler=test_009_canary.handler,S3Bucket=cdk-hnb659fds-assets-123456789012-us-east-1,S3Key=ff9681d0862f291b2a593db06765d821073060ca7709ba7c18a029224a1b70c5.zip --run-config EnvironmentVariables={API_ENDPOINT=https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/v1/report,SSM_PARAMETER_NAME=/canary/dev/test-009/api-key} --region us-east-1


Step 4: Post-validate
Monitor system health and key metrics to confirm the change mitigated the issue.
4.1
Verify that the canary configuration has been successfully updated with the correct code S3 key and environment variables
aws synthetics get-canary --name test-009 --region us-east-1


4.2
Confirm that the canary runs successfully after rollback with PASSED status, indicating the code bugs have been resolved
Wait for the next scheduled canary run (runs every 5 minutes during weekdays 13:00-18:00 UTC) and then execute: aws synthetics get-canary-runs --name test-009 --max-results 3 --region us-east-1

Rollback
When and how to revert to the previous state if problems occur.
Restore the canary to its pre-mitigation state if the rollback causes unexpected issues or complications
aws synthetics update-canary --name test-009 --code Handler=test_009_canary.handler,S3Bucket=cdk-hnb659fds-assets-123456789012-us-east-1,S3Key=c03de4598a735d3d3291d2f2b1f25eeb6a84968722e1e5b6b3b5fdcbe6c72682.zip --run-config EnvironmentVariables={API_ENDPOINT=https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/v1/report} --region us-east-1



```