## Análisis del Ticket de Soporte

**Ticket:** La aplicación de generación de reportes PDF presenta degradación de rendimiento después de 2-3 horas de uso, volviéndose lenta y eventualmente dejando de responder. Se requiere que la aplicación mantenga un rendimiento constante independientemente del número de reportes generados.

## Hallazgos en los Logs

Los logs revelan un patrón crítico y consistente de errores:

1. **Error Runtime.OutOfMemory**: Todas las ejecuciones fallan con este error específico
2. **Memoria máxima utilizada**: Consistentemente 127-128 MB (límite de la función Lambda)
3. **Duración de ejecución**: Varía entre 5-31 segundos antes del fallo
4. **Patrón temporal**: Los errores ocurren de forma continua en múltiples invocaciones

Ejemplos de errores encontrados:
```
REPORT RequestId: 4f9ab3e0-f860-46e6-893d-cdfd14c0f225
Duration: 31115.34 ms	Billed Duration: 31116 ms	
Memory Size: 128 MB	Max Memory Used: 127 MB	
Status: error	Error Type: Runtime.OutOfMemory
```

## Relación con el Código Fuente

### Problema Principal: Memory Leak en la función `template()`

El análisis del código revela una **fuga de memoria crítica** en el archivo `test_009/lambda/report.py`:

```python
count = 0
TEMPLATE_CACHE = []  # ← Variable global que acumula datos

def template():
    global count
    count += 1
    
    # Creación de objetos pesados en cada invocación
    elements = [...]  # Array con múltiples elementos
    f = Template(format="A4", elements=elements, title="Sample Invoice")
    f.add_page()
    f["company_name"] = "Sample Company"
    f.render(f"/tmp/template_{count}.pdf")
    
    # ¡PROBLEMA CRÍTICO!
    my_list = [i for i in range(100000 * count)]  # Lista que crece exponencialmente
    print(f"List size: {sys.getsizeof(my_list)} bytes, count: {count}")
    
    # Acumulación en cache global - NUNCA SE LIMPIA
    TEMPLATE_CACHE.append({"template": f, "list": my_list})
```

### Problemas Identificados:

1. **Crecimiento exponencial de memoria**: `range(100000 * count)` hace que cada invocación consuma más memoria
2. **Cache global sin límites**: `TEMPLATE_CACHE` acumula objetos sin liberarlos nunca
3. **Objetos Template pesados**: Se almacenan objetos FPDF completos en memoria
4. **Archivos temporales**: Se generan archivos en `/tmp/` sin limpieza

## Ejemplo de Ejecución

**Simulación del crecimiento de memoria:**

```python
# Invocación 1: count = 1
my_list = [i for i in range(100000)]  # ~800KB
TEMPLATE_CACHE = [{"template": Template_obj, "list": 100k_items}]

# Invocación 2: count = 2  
my_list = [i for i in range(200000)]  # ~1.6MB
TEMPLATE_CACHE = [
    {"template": Template_obj1, "list": 100k_items},
    {"template": Template_obj2, "list": 200k_items}
]

# Invocación 3: count = 3
my_list = [i for i in range(300000)]  # ~2.4MB
TEMPLATE_CACHE = [
    {"template": Template_obj1, "list": 100k_items},
    {"template": Template_obj2, "list": 200k_items}, 
    {"template": Template_obj3, "list": 300k_items}
]
```

**Cálculo de memoria acumulada:**
- Después de 10 invocaciones: ~40MB solo en listas
- Después de 20 invocaciones: ~160MB (excede límite Lambda)
- Más objetos Template, elementos, y archivos temporales

## Soluciones Propuestas

### Solución 1: Eliminación del Cache Global (Recomendada)
```python
def template():
    global count
    count += 1
    
    elements = [...]
    f = Template(format="A4", elements=elements, title="Sample Invoice")
    f.add_page()
    f["company_name"] = "Sample Company"
    f.render(f"/tmp/template_{count}.pdf")
    
    # ELIMINAR estas líneas problemáticas:
    # my_list = [i for i in range(100000 * count)]
    # TEMPLATE_CACHE.append({"template": f, "list": my_list})
    
    # Limpiar archivo temporal
    import os
    try:
        os.remove(f"/tmp/template_{count}.pdf")
    except:
        pass
```

### Solución 2: Implementar Cache con Límites
```python
from collections import deque

TEMPLATE_CACHE = deque(maxlen=5)  # Máximo 5 elementos

def template():
    # ... código existente ...
    
    # Cache limitado (opcional, si realmente se necesita)
    if len(TEMPLATE_CACHE) >= 5:
        TEMPLATE_CACHE.popleft()  # Remover el más antiguo
    
    # Reducir tamaño de lista de prueba
    my_list = [i for i in range(1000)]  # Tamaño fijo pequeño
    TEMPLATE_CACHE.append({"template": f, "list": my_list})
```

### Solución 3: Aumentar Memoria Lambda (Temporal)
```typescript
// En el CDK Stack
const lambdaFunction = new lambda.Function(this, 'ReportFunction', {
    memorySize: 512,  // Aumentar de 128MB a 512MB
    timeout: Duration.seconds(30),
    // ... otras configuraciones
});
```

### Solución 4: Refactorización Completa
```python
def handler(event, context):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('helvetica', size=14)
        
        text = lorem.paragraphs(50)
        pdf.cell(200, 10, txt='PDF report', ln=True, align='C')
        pdf.write(text=text)
        
        pdf_bytes = pdf.output(dest='S')
        encoded_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # ELIMINAR la llamada a template() si no es necesaria
        # template()
        
        return {
            'statusCode': 200,
            'body': encoded_pdf,
            'headers': {
                'Content-Disposition': 'attachment;filename=my_document.pdf',
                'Content-Type': 'application/pdf'
            },
            'isBase64Encoded': True,
        }
    except Exception as e:
        # ... manejo de errores ...
```

## Recomendación Final

**Implementar la Solución 1** eliminando completamente el cache global y las listas de prueba, ya que:
- Resuelve la causa raíz del problema
- Mantiene la funcionalidad core intacta
- Permite escalabilidad ilimitada
- Es la solución más simple y efectiva

El problema no está en la generación del PDF sino en el código de prueba/debug que acumula memoria innecesariamente.