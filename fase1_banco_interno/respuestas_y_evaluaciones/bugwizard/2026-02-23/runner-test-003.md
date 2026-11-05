## Análisis del Ticket de Soporte

**Ticket:** La póliza 144534 no pudo ser traspasada - Error en el proceso de transferencia de póliza

## Hallazgos en los logs

Analizando los logs de CloudWatch, se identifica un patrón consistente de errores:

```
[ERROR] BusinessRuleException: Prima de carga no puede ser cero
```

Este error aparece repetidamente en múltiples RequestIds a lo largo del tiempo, indicando que es un problema recurrente en el sistema. El error se produce durante la ejecución de la función Lambda `TransferPolicyFunction`.

## Relación con el código fuente

El error está directamente relacionado con la lógica de validación en el archivo `transfer_policy.py`, específicamente en las líneas 44-48:

```python
for carga in policy.get('dependents', []):
    prima_carga = calcular_prima(int(carga['actuarial_age']), cobertura_base, risk_table)
    
    if prima_carga == 0:
        logger.error(f"BusinessRuleException: Prima de carga no puede ser cero")
        raise BusinessRuleException("Prima de carga no puede ser cero")
```

### Análisis del flujo de ejecución:

1. **Función `calcular_prima`**: Calcula la prima multiplicando `cobertura_base * factor`
2. **Función `get_risk_factor`**: Busca el factor de riesgo en DynamoDB basado en `actuarial_age`
3. **Problema identificado**: Si no encuentra el registro en la tabla `risk_factors`, retorna `Decimal('1.0')` por defecto
4. **Causa raíz**: La variable `cobertura_base` se obtiene del parámetro SSM `/bw-test-003/policy-service/base-coverage` y probablemente está configurada como `0`

## Ejemplo de ejecución

Simulando el escenario problemático:

```python
# Valores de entrada hipotéticos para la póliza 144534
cobertura_base = Decimal('0')  # ← PROBLEMA: Valor configurado como 0
edad_actuarial = 25
factor_riesgo = Decimal('1.0')  # Factor por defecto

# Cálculo de prima
prima_carga = cobertura_base * factor_riesgo
# prima_carga = 0 * 1.0 = 0

# Validación que falla
if prima_carga == 0:  # True
    raise BusinessRuleException("Prima de carga no puede ser cero")
```

## Soluciones propuestas

### Solución 1: Verificar y corregir el parámetro SSM
```bash
# Verificar el valor actual del parámetro
aws ssm get-parameter --name "/bw-test-003/policy-service/base-coverage"

# Actualizar con un valor válido (ejemplo: 1000)
aws ssm put-parameter --name "/bw-test-003/policy-service/base-coverage" --value "1000" --overwrite
```

### Solución 2: Mejorar la validación en el código
Modificar `transfer_policy.py` para incluir validación temprana:

```python
def lambda_handler(event, context):
    # ... código existente ...
    
    cobertura_base = Decimal(os.environ.get('BASE_COVERAGE', '0'))
    
    # NUEVA VALIDACIÓN
    if cobertura_base <= 0:
        logger.error(f"Configuración inválida: BASE_COVERAGE debe ser mayor a 0, actual: {cobertura_base}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Error de configuración del sistema'})
        }
    
    # ... resto del código ...
```

### Solución 3: Validación de datos de dependientes
Agregar validación para asegurar que los factores de riesgo existan:

```python
def get_risk_factor(edad_actuarial, risk_table):
    try:
        response = risk_table.get_item(Key={'actuarial_age': edad_actuarial})
        if 'Item' in response:
            return Decimal(str(response['Item']['factor']))
        else:
            logger.warning(f"Factor de riesgo no encontrado para edad {edad_actuarial}, usando factor por defecto")
            return Decimal('1.0')
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        raise
```

## Recomendación inmediata

La causa raíz más probable es que el parámetro SSM `BASE_COVERAGE` está configurado con valor `0`. Se recomienda:

1. **Verificar inmediatamente** el valor del parámetro SSM
2. **Configurar un valor válido** (mayor a 0) para la cobertura base
3. **Implementar las validaciones adicionales** para prevenir futuros errores similares

Esta solución debería resolver el problema de transferencia de la póliza 144534 y todas las demás pólizas afectadas por el mismo error.