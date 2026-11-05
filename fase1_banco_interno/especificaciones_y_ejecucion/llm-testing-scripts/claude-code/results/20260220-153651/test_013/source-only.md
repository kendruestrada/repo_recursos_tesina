---

## [Connection Leak]: Conexion del pool nunca se libera en el flujo exitoso

### Summary: En el flujo de exito de `lambda_handler`, la conexion obtenida del pool nunca se devuelve, agotando el semaforo y bloqueando todas las invocaciones posteriores.

### Severity: Critical

---

### Root Cause Analysis

**Pasos para reproducir:**
1. Realizar 5 llamadas exitosas consecutivas al endpoint `/process` (maxconn=5)
2. En la 6ta llamada, `getconn()` ejecuta `self._semaphore.acquire()` que bloquea indefinidamente
3. La Lambda expira por timeout (30s)

**Expected vs. Actual:**

| | Esperado | Actual |
|---|---|---|
| Flujo exitoso | `conn` se devuelve al pool tras cada request | `conn` nunca se devuelve |
| `_semaphore` | Release al finalizar cada request | Solo se hace release en el `except` |
| 6ta llamada | Obtiene conexion normalmente | Se bloquea indefinidamente |

**Ubicacion del bug:**

`app/app.py` — funcion `lambda_handler`

El problema tiene dos dimensiones:

**1. `putconn` ausente en el flujo exitoso** (`app.py:38-41`):

```python
return {
    "statusCode": 200,
    "body": json.dumps(result)
}
# putconn(conn) NUNCA se llama aqui
```

**2. `getconn` esta fuera del bloque `try`** (`app.py:21`):

```python
conn = connection_pool.getconn()   # linea 21 — fuera del try

try:
    ...
    return { "statusCode": 200 ... }  # conn nunca se libera

except Exception as e:
    connection_pool.putconn(conn)     # linea 45 — solo se libera en error
```

Dado que `getconn()` esta en la linea 21 fuera del `try`, si ocurre un error antes de llegar al `except` (imposible en este caso pero estructuralmente fragil), la conexion tampoco seria liberada.

---

### Solution

Mover `putconn` al bloque `finally` para garantizar que la conexion siempre se libere, independientemente del resultado:

```python
conn = connection_pool.getconn()

try:
    ...
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

finally:
    connection_pool.putconn(conn)   # siempre se ejecuta
```

Esto garantiza que el semaforo (`_semaphore.release()`) se llame en cada path de ejecucion, evitando el agotamiento del pool tras 5 requests exitosos.

# Total cost USD

0.12791225

# Execution time in seconds: 

39
