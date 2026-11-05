# Análisis / diagnóstico

La app es un stack SAM (API Gateway + Lambda Node 18 + DynamoDB) definido en `template.yaml`, con el handler en `profile_service.js`.

## Principal sospecha: error en producción (deploy/update)

Si el síntoma es fallo de deploy/update, la causa más probable es la presencia de recursos con nombres “fijos” que suelen chocar entre entornos o con recursos ya existentes:

- **DynamoDB:** `TableName: user-profiles-prod` en `template.yaml`.
- **API:** `StageName: prod` en `template.yaml`.
- **Lambda:** `FunctionName: UserProfileFunction` en `template.yaml`.
- **CloudWatch Logs:** se crea explícitamente un `AWS::Logs::LogGroup` con nombre `/aws/lambda/${UserProfileFunction}` en `template.yaml`. Si el log group ya fue autocreado por Lambda antes, CloudFormation puede fallar con “AlreadyExists”.

## Principal sospecha: error en runtime (502/500 intermitente)

El handler asumía que `event.headers` y `event.requestContext.requestId` siempre existen. Si llega un evento sin esas propiedades, podía crashear fuera de `try/catch`.

## Hallazgo adicional (riesgo)

El CORS y el handler reflejan el `Origin` de entrada y aceptan credenciales; esto parece intencional tipo laboratorio (ver scripts `01_setup_env.ps1` y `02_simulate_attack.ps1`), pero en producción es un riesgo.

## Historial Git

Historial Git (3 commits): el último commit “fix log group names” es el más sospechoso si el problema apareció “de repente”, porque introduce `FunctionName` y el LogGroup gestionado por CloudFormation, que es un patrón típico de rotura en updates.

## Mitigación aplicada

Endurecí `profile_service.js` para:

- Tolerar `headers`/`requestContext` ausentes.
- Manejar `OPTIONS`.
- Validar `TABLE_NAME`.
- Evitar que el parseo de JWT reviente la función.

Esto apunta a reducir 5xx por excepciones de código.