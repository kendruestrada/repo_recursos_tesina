$PROFILE = "DevRole-123456789012"
$REGION = "us-east-1"
$STACK = "test-020"
$HTML_PATH = "src/web/index.html"

$URL = aws cloudformation describe-stacks --stack-name $STACK --profile $PROFILE --region $REGION --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text

$Item = '{"userId":{"S":"user_123"},"email":{"S":"usuario@example.com"},"fullName":{"S":"Maximiliano Lopez"},"sensitive_data":{"S":"BUGWIZARD_KEY_8822"},"session_active":{"BOOL":false}}'
Set-Content -Path item.json -Value $Item
aws dynamodb put-item --table-name user-profiles-prod --item file://item.json --profile $PROFILE --region $REGION
Remove-Item item.json

$content = Get-Content $HTML_PATH -Raw
$newContent = $content -replace 'const API_URL = ".*?";', "const API_URL = `"$URL`";"
$newContent | Set-Content $HTML_PATH -NoNewline
Write-Host "Entorno configurado y resetado." -ForegroundColor Green