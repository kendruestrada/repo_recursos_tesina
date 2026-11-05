# Resumen de hallazgos

## Hallazgos

### 1) Error de configuración SAM (alta probabilidad en build/deploy)

En `template.yaml` el `CodeUri` apuntaba a `src/inventory_handler/`, pero ese directorio no existe en el proyecto. Esto provoca fallos al construir/desplegar (SAM no encuentra el código). Se corrigió a `CodeUri: inventory_handler/`.

### 2) Riesgo de fallo funcional por lógica de stock (alta probabilidad en runtime)

En `app.py` se usaba un `internal_cache` global para validar stock. Ese cache puede quedar obsoleto entre invocaciones y permitir compras con stock insuficiente, pudiendo terminar en stock negativo o respuestas inconsistentes.

### 3) Condición de carrera / pérdida de actualizaciones (alta probabilidad con concurrencia)

La secuencia `get_item` + `put_item` no es atómica. Con llamadas simultáneas, dos compras pueden leer el mismo stock y sobrescribir resultados (“lost update”).

### 4) Manejo de entrada y errores insuficiente (riesgo de 500)

El handler no validaba adecuadamente `body`, `sku` y `quantity`. Casos comunes (body vacío, JSON inválido, `quantity` como string/null) podían generar excepciones y devolver **500**.

## Mejora aplicada (fix mínimo y robusto)

Se reemplazó la actualización por una operación atómica en DynamoDB usando `update_item` con `ConditionExpression` (stock >= cantidad), evitando condiciones de carrera y bloqueando compras sin stock. Se agregó validación básica de payload y respuesta JSON consistente.

## Riesgo operativo adicional (según entorno local)

En `samconfig.toml` se usa un profile específico (`DevRole-123456789012`). Si el cliente no tiene ese perfil configurado, `sam deploy` puede fallar por credenciales/perfil inexistente.