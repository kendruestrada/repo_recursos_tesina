---

## Memory Leak en Lambda: Acumulacion de objetos en estado global entre invocaciones warm

### Summary: La funcion `template()` acumula objetos y listas de tamano creciente en la variable global `TEMPLATE_CACHE` que persiste entre invocaciones warm de Lambda, agotando los 128 MB de memoria configurados.

### Severity: Critical

---

### Root Cause Analysis

**Steps to reproduce**
1. La Lambda recibe multiples requests con el mismo contenedor warm (mantenido por `provisionedConcurrentExecutions: 1`)
2. Cada invocacion llama a `template()` en `lambda/report.py:30`
3. `count` se incrementa en 1 por cada llamada (variable global persistente)
4. Se crea una lista de `100000 * count` enteros y se agrega junto con el objeto `Template` a `TEMPLATE_CACHE`
5. `TEMPLATE_CACHE` nunca se limpia

**Expected vs. Actual**

| Invocacion | Tamano de lista esperado (si fuera stateless) | Tamano real acumulado en TEMPLATE_CACHE |
|---|---|---|
| count=1 | 800,984 bytes | 800,984 bytes |
| count=2 | ~800 KB | 800 KB + 1.6 MB = 2.4 MB acumulados |
| count=3 | ~800 KB | 2.4 MB + 2.6 MB = 5 MB acumulados |
| count=5 | ~800 KB | ~12 MB acumulados solo en listas |

Los logs confirman el crecimiento lineal por invocacion:
```
List size: 800984 bytes,  count: 1
List size: 1624056 bytes, count: 2
List size: 2601560 bytes, count: 3
List size: 3292664 bytes, count: 4
List size: 4167352 bytes, count: 5
→ REPORT ... Max Memory Used: 127 MB  Status: error  Error Type: Runtime.OutOfMemory
```

El patron se repite identico cada ciclo: el contenedor muere por OOM, AWS lo reinicia (count vuelve a 1), y el ciclo comienza de nuevo.

**Location of the bug**

| Archivo | Linea | Descripcion |
|---|---|---|
| `lambda/report.py` | 9 | `TEMPLATE_CACHE = []` — lista global que acumula sin limite |
| `lambda/report.py` | 63–64 | `count` global que crece indefinidamente en contenedores warm |
| `lambda/report.py` | 81 | `my_list = [i for i in range(100000 * count)]` — lista de tamano creciente sin proposito funcional |
| `lambda/report.py` | 84 | `TEMPLATE_CACHE.append({"template": f, "list": my_list})` — acumulacion de objetos grandes |
| `lib/test_009-stack.ts` | 35 | `memorySize: 128` — limite de memoria demasiado bajo |
| `lib/test_009-stack.ts` | 44 | `provisionedConcurrentExecutions: 1` — garantiza que el contenedor siempre este warm, haciendo el leak determinista |

---

### Solution

**Causa 1 — Eliminar `TEMPLATE_CACHE` y `my_list` (critico)**

`TEMPLATE_CACHE` y `my_list` no tienen proposito funcional en la logica del handler. `my_list` es una lista de enteros que se crea, se mide y se descarta; `TEMPLATE_CACHE` guarda objetos `Template` ya renderizados que nunca se reutilizan. Ambos deben eliminarse.

En `lambda/report.py`:
- Eliminar las lineas 8–9 (`count = 0` y `TEMPLATE_CACHE = []`)
- Dentro de `template()`, eliminar las lineas 63–64 (declaracion de `count` global e incremento), linea 81 (`my_list`) y linea 84 (el `append` a `TEMPLATE_CACHE`)
- El archivo renderizado en `/tmp/template_{count}.pdf` tambien debe gestionarse o eliminarse tras su uso, dado que `/tmp` en Lambda es de 512 MB compartido entre invocaciones warm

**Causa 2 — Aumentar `memorySize` (recomendado)**

128 MB es insuficiente para generar PDFs con `fpdf2` y texto lorem de 50 parrafos. Se recomienda subir a al menos 512 MB en `lib/test_009-stack.ts:35`:

```typescript
memorySize: 512,  // era 128
```

**Causa 3 — Revisar `provisionedConcurrentExecutions`**

`provisionedConcurrentExecutions: 1` mantiene el contenedor siempre vivo, haciendo que cualquier leak en estado global sea permanente hasta el OOM. Si no hay un requisito de latencia estricto, evaluar si esta configuracion es necesaria. Si se mantiene, es imperativo que el codigo del handler sea completamente stateless (sin variables globales mutables).

# Total cost USD

0.277522

# Execution time in seconds: 

74
