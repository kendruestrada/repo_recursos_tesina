## Error en Validacion de Prima del Titular: Regla de Negocio Aplicada de Forma Asimetrica

### Summary: La validacion `prima == 0` se aplica solo a las cargas (dependientes), pero no al titular de la poliza, permitiendo traspasos con prima total de cero.

### Severity: High

---

### Root Cause Analysis

**Ubicacion del bug:** `src/backend/transfer_policy.py`, lineas 59-69

Al analizar el flujo de calculo de primas en `lambda_handler`:

```python
# Linea 59-60: prima del titular — SIN validacion
prima_titular = calcular_prima(int(policy['holder_age']), cobertura_base, risk_table)
total_prima_poliza += prima_titular

# Lineas 62-69: prima de cargas — CON validacion
for carga in policy.get('dependents', []):
    prima_carga = calcular_prima(int(carga['actuarial_age']), cobertura_base, risk_table)
    
    if prima_carga == 0:          # <-- Solo valida dependientes
        raise BusinessRuleException("Prima de carga no puede ser cero")
    
    total_prima_poliza += prima_carga
```

La funcion `calcular_prima` retorna `cobertura_base * factor`. Si `cobertura_base = 0` (variable `BASE_COVERAGE` con valor `'0'` — valor por defecto en `os.environ.get('BASE_COVERAGE', '0')`) o si el factor de riesgo en DynamoDB es `0`, entonces `prima_titular = 0`.

**Flujo de ejecucion con el bug activo:**

| Escenario | Titular | Dependientes | Resultado |
|---|---|---|---|
| `BASE_COVERAGE=0`, sin dependientes | prima=0, sin validacion | (no aplica) | HTTP 200, `total_premium="0"` — **incorrecto** |
| `BASE_COVERAGE=0`, con dependientes | prima=0, sin validacion | prima=0, lanza excepcion | HTTP 422 — correcto |

- **Pasos para reproducir:** Configurar SSM `/bw-test-003/policy-service/base-coverage` con valor `0`, invocar el endpoint con una poliza sin dependientes.
- **Esperado:** HTTP 422 con `BusinessRuleException`
- **Actual:** HTTP 200 con `total_premium: "0"`, traspaso aprobado con prima invalida.

---

### Solution

Agregar la misma validacion del titular inmediatamente despues de calcular `prima_titular` en `transfer_policy.py:60`:

```python
prima_titular = calcular_prima(int(policy['holder_age']), cobertura_base, risk_table)

if prima_titular == 0:                           # <-- validacion faltante
    logger.error("BusinessRuleException: Prima del titular no puede ser cero")
    raise BusinessRuleException("Prima del titular no puede ser cero")

total_prima_poliza += prima_titular
```

Esto garantiza que la regla de negocio se aplique de forma consistente tanto para el titular como para los dependientes, evitando traspasos con primas de valor cero independientemente de la composicion de la poliza.

# Total cost USD

0.18597750000000002

# Execution time in seconds: 

59
