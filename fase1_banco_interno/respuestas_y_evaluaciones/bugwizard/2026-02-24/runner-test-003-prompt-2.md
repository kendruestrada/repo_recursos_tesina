## Análisis del Ticket de Soporte

**Ticket:** La póliza 144534 no pudo ser traspasada a través del sistema de transferencia de pólizas.

## Hallazgos en los logs

Después de analizar exhaustivamente los logs de CloudWatch, se identificó un patrón consistente de errores:

```
[ERROR] BusinessRuleException: Prima de carga no puede ser cero
```

Este error aparece repetidamente en múltiples RequestIds a lo largo del período analizado (desde febrero 18 hasta febrero 23, 2026), indicando que es un problema sistemático que afecta el procesamiento de pólizas con dependientes.

## Relación con el código fuente

El error se origina en el archivo `transfer_policy.py`, específicamente en la función `lambda_handler`, en el siguiente bloque de código:

```python
for carga in policy.get('dependents', []):
    prima_carga = calcular_prima(int(carga['actuarial_age']), cobertura_base, risk_table)
    
    if prima_carga == 0:
        logger.error(f"BusinessRuleException: Prima de carga no puede ser cero")
        raise BusinessRuleException("Prima de carga no puede ser cero")
    
    total_prima_poliza += prima_carga
```

### Análisis del flujo de ejecución:

1. **Función `calcular_prima`**: Calcula la prima multiplicando `cobertura_base * factor`
2. **Función `get_risk_factor`**: Busca el factor de riesgo en DynamoDB basado en `actuarial_age`
3. **Problema identificado**: Si no encuentra el registro en la tabla `risk_factors`, retorna `Decimal('1.0')` por defecto
4. **Causa raíz**: La variable `cobertura_base` se obtiene de `os.environ.get('BASE_COVERAGE', '0')` y se convierte a `Decimal('0')`

## Ejemplo de ejecución

Simulando el escenario problemático:

```python
# Valores de entrada para póliza 144534
cobertura_base = Decimal('0')  # Valor por defecto del environment
factor_riesgo = Decimal('1.0')  # Valor por defecto si no se encuentra en tabla

# Cálculo de prima para dependiente
prima_carga = cobertura_base * factor_riesgo
# prima_carga = Decimal('0') * Decimal('1.0') = Decimal('0')

# Validación que falla
if prima_carga == 0:  # True
    raise BusinessRuleException("Prima de carga no puede ser cero")
```

## Soluciones propuestas

### Solución 1: Configurar correctamente el parámetro BASE_COVERAGE
```bash
# Establecer el valor correcto en AWS Systems Manager Parameter Store
aws ssm put-parameter \
    --name "/bw-test-003/policy-service/base-coverage" \
    --value "1000" \
    --type "String" \
    --overwrite
```

### Solución 2: Modificar el código para manejar mejor los valores por defecto
```python
# En transfer_policy.py, línea donde se obtiene cobertura_base
cobertura_base = Decimal(os.environ.get('BASE_COVERAGE', '1000'))  # Cambiar '0' por '1000'
```

### Solución 3: Agregar validación temprana
```python
def lambda_handler(event, context):
    # ... código existente ...
    
    cobertura_base = Decimal(os.environ.get('BASE_COVERAGE', '0'))
    
    # Validación temprana
    if cobertura_base == 0:
        logger.error("BASE_COVERAGE no está configurado correctamente")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Configuración de sistema incorrecta'})
        }
```

### Solución 4: Mejorar el manejo de factores de riesgo faltantes
```python
def get_risk_factor(edad_actuarial, risk_table):
    try:
        response = risk_table.get_item(Key={'actuarial_age': edad_actuarial})
        if 'Item' in response:
            return Decimal(str(response['Item']['factor']))
        
        # Log cuando no se encuentra el factor
        logger.warning(f"Factor de riesgo no encontrado para edad {edad_actuarial}")
        return Decimal('1.0')
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        raise
```

## Recomendación principal

La **causa raíz** del problema es que el parámetro `BASE_COVERAGE` en AWS Systems Manager Parameter Store no está configurado con un valor válido, resultando en el valor por defecto de '0'. Esto hace que todas las primas calculadas para dependientes sean cero, activando la validación de negocio que impide el traspaso.

**Acción inmediata recomendada**: Configurar el parámetro `/bw-test-003/policy-service/base-coverage` con un valor apropiado (ej: "1000") en AWS Systems Manager Parameter Store.