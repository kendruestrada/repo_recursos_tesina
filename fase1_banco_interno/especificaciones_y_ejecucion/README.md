# BugWizard Tests

## Overview

This project define a list of test cases with different error scenarios. The goal is to check if bugwizard is able to identify root cause properly, and check if other LLMs are able to do it better or not.


## AWS Synthetics Canaries Implementation

To automate applications execution and to generate logs, there's a canaries project with cron based execution for test cases.
Canaries implementation details on: [synthetics-canaries](synthetics-canaries/README.md)

## ClaudeCode

Local configuration of claude-code example, to use aws bedrock, and to use an MCP server to analyse Cloudwatch logs.

### 1.- Install [Claude code](https://code.claude.com/docs/en/setup)

### 2.- Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

### 3.- Configure [Apside aws-cli profile](https://docs.google.com/document/d/1RrKGU8D0RTNsUAmKs3q8NVj-U_IskXvGexixnB73_vA/edit?usp=sharing)

### (Optional) Configure multi-account profiles with AWS SSO example:

Configure on file `~/.aws/config`

```bash
[default]
region = us-east-1

[default]
[profile prod]
sso_session = sso
sso_account_id = 123456789012
sso_role_name = DevRole
region = us-east-1

[profile dev]
sso_session = sso
sso_account_id = 123456789012
sso_role_name = DevRole
region = us-east-1

[sso-session sso]
sso_start_url = https://d-xxxxxxxxxx.awsapps.com/start
sso_region = us-east-1
sso_registration_scopes = sso:account:access

```

### 4.- Configure environment for Claude to use [amazon-bedrock](https://code.claude.com/docs/en/amazon-bedrock) (Or your local subscription)

- Add on file `.zshrc` for mac or `~/.bashrc` for linux:

```bash
# Claude with bedrock
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1
export AWS_PROFILE=your-apside-profile
export ANTHROPIC_MODEL='global.anthropic.claude-sonnet-4-5-20250929-v1:0'
export ANTHROPIC_SMALL_FAST_MODEL='us.anthropic.claude-haiku-4-5-20251001-v1:0'
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=8162
export MAX_THINKING_TOKENS=1024
```

- restart terminal or load env vars

### 5.- Configure Cloudwatch logs access [MCP for Claude](https://github.com/awslabs/Log-Analyzer-with-MCP)

### 6.- ADD MCP server

* replace `/path/to/Log-Analyzer-with-MCP` with your local path
* replace `dev` with aws profile name where logs are located

```bash
# Execute
claude mcp add-json cw-mcp-server \
 '{"type":"stdio","command":"uv","args":["--directory","/path/to/Log-Analyzer-with-MCP/src/cw-mcp-server","run","server.py","--profile","dev"]}'
```

### 7.- Check MCP configuration

```bash
# Execute
claude mcp list
```

```bash
Checking MCP server health...

cw-mcp-server: uv --directory /Users/usuario/Documents/bugwizard/Log-Analyzer-with-MCP/src/cw-mcp-server run server.py --profile dev - ✓ Connected
```

### 8.- Usage example

```bash
╭─── Claude Code v2.1.20 ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                    │ Tips for getting started                                                                                                                                                  │
│            Welcome back!           │ Run /init to create a CLAUDE.md file with instructions for Claude                                                                                                         │
│                                    │ Note: You have launched claude in your home directory. For the best experience, launch it in a project directory instead.                                                 │
│                                    │ ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────                                                 │
│               ▐▛███▜▌              │ Recent activity                                                                                                                                                           │
│              ▝▜█████▛▘             │ No recent activity                                                                                                                                                        │
│                ▘▘ ▝▝               │                                                                                                                                                                           │
│   Sonnet 4.5 · API Usage Billing   │                                                                                                                                                                           │
│          /Users/usuario           │                                                                                                                                                                           │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

  /model to try Opus 4.5. Note: you may need to request access from your cloud provider

❯ hello

⏺ Hello! I'm Claude Code, ready to help you with software engineering tasks. What would you like to work on today?

❯ /cw-mcp-server:list_cloudwatch_log_groups (MCP)

⏺ I'll list the available CloudWatch log groups in your AWS environment.

⏺ cw-mcp-server - list_log_groups (MCP)(limit: 50)
  ⎿  {
       "logGroups": [
         {
     … +103 lines (ctrl+o to expand)

⏺ I found 17 CloudWatch log groups in your AWS environment (us-east-1). Here's a summary:

  Lambda Functions by Environment

  Development (dev-*)
  - /aws/lambda/dev-CacheInvalidationFunction - 2.08 MB
  - /aws/lambda/dev-CheckoutFunction - 1.50 KB

  Test (test-*, bwtest*)
  - /aws/lambda/test-005-CreditEvaluation - 5.10 MB

  CloudWatch Synthetics
  - /aws/lambda/cwsyn-homepage-test-* - 106.18 KB
  - /aws/lambda/cwsyn-test-009-* - 418.96 KB

  Other
  - /aws/lambda/ReportGenerator - 7.39 MB
  - /aws/lambda/lambda-a-create-subscription - 10.09 KB

  I can help you:
  - Search for errors or specific patterns in any log group
  - Analyze log activity and volume trends
  - Correlate logs across multiple services
  - Summarize recent activity

  Which log group would you like to explore?
```

### 9.- ClaudeCode automated bug detection script

On folder [llm-testing-scripts/claude-code](llm-testing-scripts/claude-code) there's a bash script to automate bug detection for test cases.

Get details with:

```bash
./run-tests.sh --help
```
