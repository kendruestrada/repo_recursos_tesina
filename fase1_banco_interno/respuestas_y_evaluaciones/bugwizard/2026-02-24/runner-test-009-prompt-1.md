## Análisis del Ticket de Soporte Técnico

**Ticket:** La aplicación presenta degradación de rendimiento después de 2-3 horas de uso, volviéndose lenta y eventualmente dejando de responder completamente.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se identifican patrones críticos de falla:

1. **Errores consistentes de memoria agotada:**
   - `Runtime.OutOfMemory` aparece repetidamente en múltiples requests
   - Memoria configurada: 128 MB
   - Memoria máxima utilizada: 127-128 MB (prácticamente el 100%)

2. **Duración de ejecución creciente:**
   - Duraciones variables desde 5,620ms hasta 31,115ms
   - Timeouts progresivamente más largos antes del fallo por memoria

3. **Patrón temporal de degradación:**
   - Los logs muestran múltiples invocaciones fallidas consecutivas
   - Cada request consume la memoria máxima disponible antes de fallar

## Relación con el código fuente

El análisis del código fuente revela la **causa raíz** del problema:

### Problema Principal: Memory Leak en la función `template()`

```python
# En lambda/report.py - líneas críticas:
count = 0
TEMPLATE_CACHE = []  # Variable global que acumula datos

def template():
    global count
    count += 1
    
    # Creación de lista grande que crece con cada invocación
    my_list = [i for i in range(100000 * count)]
    
    # PROBLEMA: Acumulación en cache global sin límite
    TEMPLATE_CACHE.append({"template": f, "list": my_list})
```

### Análisis del crecimiento de memoria:

1. **Primera invocación:** `my_list` = 100,000 elementos
2. **Segunda invocación:** `my_list` = 200,000 elementos  
3. **Tercera invocación:** `my_list` = 300,000 elementos
4. **Y así sucesivamente...**

Cada lista se almacena permanentemente en `TEMPLATE_CACHE`, causando acumulación exponencial de memoria.

## Ejemplo de ejecución

**Simulación del crecimiento de memoria:**

```python
# Invocación 1: count = 1
my_list_1 = [i for i in range(100000)]  # ~800KB
TEMPLATE_CACHE = [{"template": f1, "list": my_list_1}]

# Invocación 2: count = 2  
my_list_2 = [i for i in range(200000)]  # ~1.6MB
TEMPLATE_CACHE = [
    {"template": f1, "list": my_list_1},  # 800KB
    {"template": f2, "list": my_list_2}   # 1.6MB
]  # Total: ~2.4MB

# Invocación N: count = N
# Memoria total ≈ 800KB * (1 + 2 + 3 + ... + N) = 800KB * N(N+1)/2
```

**Para N=16 invocaciones:** ~109MB (cerca del límite de 128MB)

## Soluciones propuestas

### Solución 1: Eliminar el cache global (Recomendada)
```python
def template():
    global count
    count += 1
    
    elements = [...]
    f = Template(format="A4", elements=elements, title="Sample Invoice")
    f.add_page()
    f["company_name"] = "Sample Company"
    f.render(f"/tmp/template_{count}.pdf")
    
    # Crear lista local sin almacenar en cache
    my_list = [i for i in range(100000 * count)]
    print(f"List size: {sys.getsizeof(my_list)} bytes, count: {count}")
    
    # NO almacenar en TEMPLATE_CACHE
    # La lista se liberará automáticamente al finalizar la función
```

### Solución 2: Implementar límite en el cache
```python
TEMPLATE_CACHE = []
MAX_CACHE_SIZE = 5  # Límite máximo de elementos

def template():
    global count
    count += 1
    
    # ... código existente ...
    
    my_list = [i for i in range(100000 * count)]
    
    # Mantener solo los últimos N elementos
    if len(TEMPLATE_CACHE) >= MAX_CACHE_SIZE:
        TEMPLATE_CACHE.pop(0)  # Remover el más antiguo
    
    TEMPLATE_CACHE.append({"template": f, "list": my_list})
```

### Solución 3: Aumentar memoria Lambda (Temporal)
```typescript
// En el CDK Stack
const reportFunction = new Function(this, 'ReportFunction', {
    // ... otras configuraciones ...
    memorySize: 512,  // Aumentar de 128MB a 512MB
    timeout: Duration.minutes(5)
});
```

### Solución 4: Optimizar generación de datos
```python
def template():
    global count
    count += 1
    
    # ... código del template ...
    
    # Generar datos más eficientemente sin almacenar
    list_size = 100000 * count
    estimated_memory = list_size * 28  # Estimación de bytes por entero
    print(f"Estimated list size: {estimated_memory} bytes, count: {count}")
    
    # No crear la lista real si no es necesaria
    # my_list = [i for i in range(list_size)]
```

## Recomendación final

**Implementar la Solución 1** eliminando completamente el `TEMPLATE_CACHE` global, ya que:
- Resuelve la causa raíz del memory leak
- No requiere cambios en la infraestructura
- Mantiene la funcionalidad sin el overhead innecesario
- Es la solución más eficiente y sostenible

El problema se manifiesta después de 2-3 horas porque corresponde aproximadamente al número de invocaciones necesarias para agotar los 128MB de memoria disponible en la función Lambda.