Tengo toda la información necesaria. Aquí está el análisis completo:

---

## Traspaso Fallido de Póliza 144534: Prima de Dependiente Cero

### Summary: La función Lambda rechaza el traspaso de la póliza 144534 porque la prima calculada para uno o más dependientes resulta cero, disparando la regla de negocio `BusinessRuleException`.

### Severity: High

---

### Root Cause Analysis

**Evidencia en logs (`/aws/lambda/TransferPolicyFunction`):**

El error aparece en cada invocación desde al menos el 2026-02-19, de forma sostenida cada ~5 minutos:
```
[ERROR] BusinessRuleException: Prima de carga no puede ser cero
```
No hay ninguna invocación exitosa reciente. El error es **sistémico**, no puntual.

---

**Pasos de ejecución y dónde falla:**

```
lambda_handler()
  → policies_table.get_item(policy_id="144534")   ← OK, póliza encontrada
  → calcular_prima(holder_age, cobertura_base, ...)  ← se ejecuta sin validación
  → for carga in policy['dependents']:
      → calcular_prima(carga['actuarial_age'], cobertura_base, ...)
        → get_risk_factor() → retorna factor (ej: 1.0)
        → prima = cobertura_base * factor
                = 0 * 1.0 = 0   ← AQUI ESTA EL PROBLEMA
      → if prima_carga == 0:     ← condicion verdadera
          raise BusinessRuleException  ← FALLA
```

---

**Ubicación del bug: `src/backend/transfer_policy.py`**

**Causa raiz 1 — Valor por defecto incorrecto de `BASE_COVERAGE` (línea 36):**

```python
cobertura_base = Decimal(os.environ.get('BASE_COVERAGE', '0'))
#                                                          ^^^
#                         Si la variable de entorno no está configurada,
#                         cobertura_base = Decimal('0')
```

Si la variable de entorno `BASE_COVERAGE` no está configurada en la Lambda (o está en `'0'`), entonces `cobertura_base = Decimal('0')`. Cualquier multiplicación `0 * factor = 0`, sin importar qué devuelva la tabla de riesgo.

**Causa raiz 2 — Validación incompleta: no se verifica `cobertura_base` antes de calcular (líneas 36, 46, 52):**

```python
cobertura_base = Decimal(os.environ.get('BASE_COVERAGE', '0'))
# No hay validación de que cobertura_base > 0 antes de operar
```

La regla de negocio que valida `prima_carga == 0` se aplica **después** del cálculo, pero nunca se detecta que el origen del cero es `cobertura_base`, no el factor de riesgo.

**Causa raiz 3 — Asimetría de validación: el titular no se valida (líneas 46-48 vs 50-56):**

```python
prima_titular = calcular_prima(...)
total_prima_poliza += prima_titular     # ← sin validación, prima puede ser 0

for carga in policy.get('dependents', []):
    prima_carga = calcular_prima(...)
    if prima_carga == 0:                # ← solo se valida para dependientes
        raise BusinessRuleException(...)
```

La prima del titular puede ser 0 sin que el sistema lo detecte, pero la prima de cualquier dependiente detiene el proceso.

---

**Ejemplo de ejecución con valores hipotéticos:**

| Variable | Valor |
|---|---|
| `BASE_COVERAGE` (env var) | No configurada → `'0'` |
| `cobertura_base` | `Decimal('0')` |
| `holder_age` | `45` → `factor = 1.2` → `prima_titular = 0 * 1.2 = 0` (silencioso) |
| `dependents[0].actuarial_age` | `20` → `factor = 0.8` → `prima_carga = 0 * 0.8 = 0` → **EXCEPCION** |

**Resultado esperado:** `total_premium = 2800` (asumiendo `BASE_COVERAGE = 1000`)
**Resultado actual:** `HTTP 422 - Prima inválida`

---

### Solution

**1. Corregir la configuración de la Lambda:** Verificar que la variable de entorno `BASE_COVERAGE` esté configurada con un valor mayor a cero en la consola de AWS Lambda.

**2. Validar `cobertura_base` al inicio del handler** (`transfer_policy.py`, después de la línea 36):

```python
cobertura_base = Decimal(os.environ.get('BASE_COVERAGE', '0'))
if cobertura_base <= 0:
    raise BusinessRuleException("Cobertura base no configurada o inválida")
```

**3. Aplicar la misma validación al titular** para mantener consistencia de reglas de negocio:

```python
prima_titular = calcular_prima(int(policy['holder_age']), cobertura_base, risk_table)
if prima_titular == 0:
    raise BusinessRuleException("Prima del titular no puede ser cero")
total_prima_poliza += prima_titular
```

**4. Acción inmediata recomendada:** Revisar en AWS Lambda → `TransferPolicyFunction` → Configuración → Variables de entorno, y confirmar que `BASE_COVERAGE` tenga un valor numérico mayor a cero. Ese cambio resolvería el problema de forma inmediata sin modificar código.

# Total cost USD

0.5965239999999999

# Execution time in seconds: 

107
