# Resumen ejecutivo

Identifiqué 2 problemas principales:

- Uno que provoca errores 500 en el endpoint de listado (query de DynamoDB mal construido).
- Otro que puede causar un incidente grave de borrado masivo en S3 (borrado por prefijo en vez de por objeto).

## Hallazgos clave

- **Falla funcional en producción (alta probabilidad de 500):** en `app.py` se usaba `Table.query()` con `KeyConditionExpression` como string (`"user_id = :uid"`). En boto3 (resource API), `KeyConditionExpression` debe ser una condición tipo `Key("user_id").eq(user_id)`. Esto puede romper en runtime y devolver 500 al listar fotos.
- **Riesgo crítico de borrado masivo (incidente de datos):** en `app.py` la Lambda derivaba un `prefix` desde `s3_key`, listaba `list_objects_v2` y ejecutaba `delete_objects` sobre todo lo encontrado. Resultado: al borrar una foto se puede eliminar todo un directorio de usuario (p. ej. toda la galería o todas las fotos del usuario).
- **Origen en historial:** ambos problemas están presentes desde el “Initial commit”; los commits recientes se enfocaron en CORS/estética/logs, no en corregir la lógica del query ni del borrado.

## Acciones tomadas (correcciones aplicadas en el repo)

- **ListPhotos:** corregí el `query()` para usar `Key("user_id").eq(user_id)` y añadí paginación con `LastEvaluatedKey` para evitar resultados incompletos por límite de 1MB. Cambios en `app.py`.
- **DeletePhoto:** cambié el borrado a `s3.delete_object(Bucket, Key=s3_key)` para eliminar solo el objeto exacto asociado a la foto, evitando borrado por prefijo. Cambios en `app.py`.

## Riesgos/observaciones adicionales

- En `template.yaml` se crean LogGroup con nombres fijos; si ya existen fuera del stack, el deploy podría fallar por conflictos (depende del historial del entorno).
- `upload_photo` puede generar inconsistencias (ej. `profile.jpg` se sobrescribe en S3 pero puede quedar metadata duplicada en DynamoDB), lo que afecta integridad aunque no necesariamente cause caída inmediata.

## Recomendación

Desplegar el fix primero en dev/staging, validar los 3 endpoints (upload/list/delete) y monitorear CloudWatch logs para confirmar que desaparecen los 500 y que no hay borrados inesperados en S3.