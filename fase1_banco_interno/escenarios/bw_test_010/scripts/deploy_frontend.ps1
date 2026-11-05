#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$STACK_NAME = "test-010"
$PROFILE = "DevRole-123456789012"  # Cambiado aquí

Write-Host "Fetching stack outputs for $STACK_NAME..." -ForegroundColor Green
$OUTPUTS = aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs' --output json --profile $PROFILE | ConvertFrom-Json

# Mostrar outputs para debug
$OUTPUTS | ConvertTo-Json -Depth 3

$API_URL = ($OUTPUTS | Where-Object { $_.OutputKey -eq "WebEndpoint" }).OutputValue
$BUCKET_NAME = ($OUTPUTS | Where-Object { $_.OutputKey -eq "FrontendBucket" }).OutputValue
$WEBSITE_URL = ($OUTPUTS | Where-Object { $_.OutputKey -eq "FrontendURL" }).OutputValue

if ([string]::IsNullOrEmpty($API_URL) -or [string]::IsNullOrEmpty($BUCKET_NAME)) {
    Write-Host "Error: Could not retrieve API URL or Bucket Name from stack outputs." -ForegroundColor Red
    Write-Host "Make sure the stack is deployed." -ForegroundColor Yellow
    exit 1
}

Write-Host "API URL: $API_URL" -ForegroundColor Cyan
Write-Host "Bucket Name: $BUCKET_NAME" -ForegroundColor Cyan

# Create a temporary directory for the build
Write-Host "Preparing frontend..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path ".frontend_build" | Out-Null
Copy-Item "frontend/index.html" ".frontend_build/index.html" -Force

# Inject the API URL into index.html
Write-Host "Injecting API URL into index.html..." -ForegroundColor Green
$indexContent = Get-Content ".frontend_build/index.html" -Raw
$indexContent = $indexContent -replace 'const API_URL = ".*";', "const API_URL = `"$API_URL`";"
$indexContent | Set-Content ".frontend_build/index.html" -NoNewline

Write-Host "Uploading to S3..." -ForegroundColor Green
aws s3 cp ".frontend_build/index.html" "s3://$BUCKET_NAME/index.html" --content-type text/html --profile $PROFILE

Write-Host "--------------------------------------------------" -ForegroundColor Yellow
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "Website URL: $WEBSITE_URL" -ForegroundColor Cyan
Write-Host "--------------------------------------------------" -ForegroundColor Yellow