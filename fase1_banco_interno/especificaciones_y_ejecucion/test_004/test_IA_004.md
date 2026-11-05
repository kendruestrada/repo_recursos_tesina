# Errores destacados y correcciones recomendadas

- **Error seguro**: en `template.yaml` la política `DynamoDBStreamReadPolicy` está definida con `TableName` y también `StreamName`. El policy template de SAM solo acepta `TableName`. Quitar la línea `StreamName: !GetAtt SubscriptionsTable.StreamArn` o usar una política IAM personalizada.
- **Posible problema de despliegue**: en `template.yaml` `Globals -> Function -> Runtime: python3.13`. Si tu entorno SAM/AWS no soporta `python3.13`, cámbialo a `python3.11` (o al runtime soportado por tu cuenta).
- **Dependencias**: `requirements.txt` incluye `requests` (bien). `requirements.txt` no necesita `requests`. Asegúrate de que las dependencias estén empaquetadas para cada Lambda si despliegas con SAM.