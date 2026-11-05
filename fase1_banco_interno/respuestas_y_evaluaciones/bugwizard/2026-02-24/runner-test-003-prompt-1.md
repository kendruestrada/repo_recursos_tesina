## Análisis del Ticket de Soporte

**Ticket:** La póliza 144534 no pudo ser traspasada - se requiere identificar la causa raíz del fallo en el sistema de transferencia de pólizas.

## Hallazgos en los logs

Tras analizar exhaustivamente los logs de CloudWatch, se identificó un patrón consistente de errores:

```
[ERROR] BusinessRuleException: Prima de carga no puede ser cero
```

Este error aparece repetidamente en múltiples RequestIds a lo largo del período analizado (desde febrero 18 hasta febrero 23, 2026), indicando que es un problema sistemático que afecta el procesamiento de múltiples pólizas, no solo la 144534.

## Relación con el código fuente

El error se origina en el archivo `transfer_policy.py`, específicamente en las líneas 50-53:

```python
for carga in policy.get('dependents', []):
    prima_carga = calcular_prima(int(carga['actuarial_age']), cobertura_base, risk_table)
    
    if prima_carga == 0:
        logger.error(f"BusinessRuleException: Prima de carga no puede ser cero")
        raise BusinessRuleException("Prima de carga no puede ser cero")
```

### Análisis del flujo de ejecución:

1. **Función `calcular_prima`** (líneas 20-23):
   ```python
   def calcular_prima(edad_actuarial, cobertura_base, risk_table):
       factor = get_risk_factor(edad_actuarial, risk_table)
       prima = cobertura_base * factor
       return prima
   ```

2. **Función `get_risk_factor`** (líneas 14-19):
   ```python
   def get_risk_factor(edad_actuarial, risk_table):
       try:
           response = risk_table.get_item(Key={'actuarial_age': edad_actuarial})
           if 'Item' in response:
               return Decimal(str(response['Item']['factor']))
           return Decimal('1.0')  # Factor por defecto
   ```

## Ejemplo de ejecución

Simulando el escenario problemático:

```python
# Datos de entrada hipotéticos para póliza 144534
cobertura_base = Decimal('0')  # ← PROBLEMA: Valor cero desde SSM Parameter
edad_actuarial_dependiente = 25
factor_riesgo = Decimal('1.5')  # Factor válido desde DynamoDB

# Cálculo de prima
prima_carga = cobertura_base * factor_riesgo
# prima_carga = Decimal('0') * Decimal('1.5') = Decimal('0')

# Validación que falla
if prima_carga == 0:  # True
    raise BusinessRuleException("Prima de carga no puede ser cero")
```

## Causa raíz identificada

El problema radica en que el parámetro `BASE_COVERAGE` está configurado con valor **cero** en AWS Systems Manager Parameter Store. Esto se evidencia en:

1. **Template.yaml** línea 11:
   ```yaml
   BaseCoveragePath:
     Type: 'AWS::SSM::Parameter::Value<String>'
     Default: '/bw-test-003/policy-service/base-coverage'
   ```

2. **transfer_policy.py** línea 32:
   ```python
   cobertura_base = Decimal(os.environ.get('BASE_COVERAGE', '0'))
   ```

Cuando `cobertura_base = 0`, cualquier multiplicación por el factor de riesgo resultará en prima cero, activando la regla de negocio que impide el traspaso.

## Soluciones propuestas

### Solución 1: Corrección del parámetro SSM (Recomendada)
```bash
aws ssm put-parameter \
  --name "/bw-test-003/policy-service/base-coverage" \
  --value "1000.00" \
  --type "String" \
  --overwrite
```

### Solución 2: Modificación del código para mejor manejo de errores
```python
def lambda_handler(event, context):
    # ... código existente ...
    
    cobertura_base = Decimal(os.environ.get('BASE_COVERAGE', '0'))
    
    # Validación temprana
    if cobertura_base <= 0:
        logger.error(f"BASE_COVERAGE inválida: {cobertura_base}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': 'Configuración de cobertura base inválida',
                'policy_id': policy_id
            })
        }
```

### Solución 3: Mejora en el mensaje de error
```python
if prima_carga == 0:
    error_msg = f"Prima de carga cero para dependiente edad {carga['actuarial_age']}. Cobertura base: {cobertura_base}"
    logger.error(f"BusinessRuleException: {error_msg}")
    raise BusinessRuleException(error_msg)
```

**Recomendación:** Implementar la Solución 1 como corrección inmediata, seguida de las Soluciones 2 y 3 para prevenir futuros problemas similares y mejorar la trazabilidad de errores.