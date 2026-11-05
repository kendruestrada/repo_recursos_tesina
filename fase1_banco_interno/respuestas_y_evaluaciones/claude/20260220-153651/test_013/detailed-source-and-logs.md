Tengo toda la información necesaria. Procedo con el análisis completo.

---

## Connection Pool Exhaustion: Conexiones no liberadas en el camino exitoso

### Summary: La función `lambda_handler` adquiere una conexión del pool pero nunca la libera cuando la ejecución es exitosa, agotando el semáforo después de `maxconn` (5) invocaciones en el mismo contenedor Lambda.

### Severity: High

---

### Root Cause Analysis

**Pasos para reproducir:**
1. La misma instancia Lambda recibe 5 invocaciones exitosas seguidas (contenedor caliente).
2. Cada invocación llama `connection_pool.getconn()` que ejecuta `self._semaphore.acquire()`, decrementando el semáforo de 5 a 0.
3. La 6ª invocación llama `getconn()` y queda bloqueada indefinidamente en `self._semaphore.acquire()` porque el semáforo está en 0.
4. Lambda alcanza el timeout de 30 segundos.

**Esperado vs. Actual:**
- **Esperado:** Cada invocación adquiere la conexión, procesa el request, y la devuelve al pool.
- **Actual:** En el camino sin excepción, `putconn(conn)` nunca se llama. La conexión se pierde permanentemente.

**Ubicación del bug:**

`app/app.py:21-41` — La llamada `connection_pool.getconn()` en la línea 21 no tiene contraparte `putconn` en el path feliz. El `putconn` solo existe en el bloque `except` (línea 45).

```python
conn = connection_pool.getconn()   # adquiere el semáforo

try:
    ...
    return {                        # <-- retorna SIN liberar la conexión
        "statusCode": 200,
        "body": json.dumps(result)
    }

except Exception as e:
    connection_pool.putconn(conn)  # solo se libera en error
```

**Evidencia en los logs — patrón exacto por instancia (Node ID):**

| Node ID    | Invocaciones OK (duración) | Invocación que hace timeout |
|------------|----------------------------|-------------------------------|
| `286af8d1` | 5 (86ms, 10ms, 1.67ms, 1.76ms, 1.84ms) | `7f65767f` — 30000ms |
| `5210a6ac` | 5 (68ms, 1.79ms, 3.05ms, 1.83ms, 1.81ms) | `027eaa56` — 30000ms |
| `75c76adb` | 5 (71ms, 1.90ms, 2.00ms, 1.98ms, 2.00ms) | `2696bc75` — 30000ms |
| `df2190b7` | 5 (71ms, 1.83ms, 2.07ms, 2.12ms, 1.86ms) | `2e81e39b` — 30000ms |

El timeout ocurre **exactamente en la 6ª invocación** de cada instancia Lambda, coincidiendo con `maxconn=5` definido en `app.py:11`.

**Ejemplo de ejecución hipotético:**

```
Invocación 1: semaphore.acquire() → semáforo = 4, OK, retorna 200, NO hace release
Invocación 2: semaphore.acquire() → semáforo = 3, OK, retorna 200, NO hace release
Invocación 3: semaphore.acquire() → semáforo = 2, OK, retorna 200, NO hace release
Invocación 4: semaphore.acquire() → semáforo = 1, OK, retorna 200, NO hace release
Invocación 5: semaphore.acquire() → semáforo = 0, OK, retorna 200, NO hace release
Invocación 6: semaphore.acquire() → semáforo = 0, BLOQUEA ← timeout Lambda 30s
```

---

### Solution

La corrección es mover el `putconn` a un bloque `finally` para garantizar que la conexión siempre se devuelva al pool, independientemente del resultado de la ejecución:

**`app/app.py`** — reemplazar la estructura `try/except` actual:

```python
conn = connection_pool.getconn()

try:
    body_raw = event.get("body") if event else "{}"
    if isinstance(body_raw, str):
        body = json.loads(body_raw)
    else:
        body = body_raw
        
    result = {
        "status": "success",
        "data": {
            "id": body.get("id", "0"),
            "node_ref": CID
        }
    }

    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
    
except Exception as e:
    logger.error(f"Execution error: {str(e)}")
    return {
        "statusCode": 500,
        "body": json.dumps({"error": "Internal Processing Error"})
    }

finally:                          # <-- garantiza liberación siempre
    connection_pool.putconn(conn)
```

Con `finally`, el semáforo en `database.py:17` (`self._semaphore.release()`) se ejecuta tanto en éxito como en error, manteniendo el pool disponible a lo largo de toda la vida del contenedor Lambda.

# Total cost USD

0.34715825

# Execution time in seconds: 

66
