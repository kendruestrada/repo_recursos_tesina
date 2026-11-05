## Análisis del Ticket de Soporte

**Ticket:** La aplicación no muestra todas las fotos registradas después de eliminar la foto de perfil. El usuario reporta que tras eliminar su foto de perfil, el listado de fotos no refleja correctamente las fotos restantes.

## Hallazgos en los logs

Al analizar los logs de CloudWatch, se identifican patrones críticos que revelan el problema:

1. **Errores recurrentes de inconsistencia de datos:**
   ```
   "3 fotos en DB sin archivo en S3 (Perdidas!)"
   ```
   Este error aparece sistemáticamente en múltiples ejecuciones del endpoint de listado.

2. **Patrón de ejecución normal seguido de inconsistencias:**
   - Los logs muestran que el servicio encuentra correctamente las entradas en DynamoDB
   - Sin embargo, detecta que los archivos correspondientes no existen en S3
   - Esto indica que la operación de eliminación está afectando más archivos de los esperados

## Relación con el código fuente

### Problema identificado en `delete_photo/app.py`

El código de eliminación contiene un **bug crítico** en las líneas 32-44:

```python
s3_prefix = s3_key.rsplit('/', 1)[0] + '/'

# 🐛 Lista TODOS los objetos bajo ese prefix
objects_to_delete = []
paginator = s3.get_paginator('list_objects_v2')

for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_prefix):
    if 'Contents' in page:
        objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])

logger.info(f"⚠️ A punto de eliminar {len(objects_to_delete)} objetos!")

if objects_to_delete:
    s3.delete_objects(
        Bucket=BUCKET_NAME,
        Delete={'Objects': objects_to_delete}
    )
```

**Análisis del problema:**
- Cuando se elimina una foto de perfil con S3 key `users/user_123/profile.jpg`
- El código calcula el prefix como `users/user_123/`
- Luego elimina **TODOS** los objetos bajo ese prefix, incluyendo fotos de galería
- Solo elimina el registro específico de DynamoDB, creando inconsistencia

## Ejemplo de ejecución

**Escenario:** Usuario tiene 3 fotos:
- `users/user_123/profile.jpg` (foto de perfil)
- `users/user_123/gallery/photo1.jpg` 
- `users/user_123/gallery/photo2.jpg`

**Al eliminar la foto de perfil:**

1. **Input:** `photo_id = "profile_abc123"`
2. **DynamoDB lookup:** Encuentra `s3_key = "users/user_123/profile.jpg"`
3. **Cálculo de prefix:** `s3_prefix = "users/user_123/"`
4. **S3 list_objects:** Encuentra 3 objetos bajo el prefix
5. **S3 delete_objects:** Elimina los 3 archivos
6. **DynamoDB delete:** Solo elimina el registro de la foto de perfil
7. **Resultado:** 2 registros huérfanos en DynamoDB sin archivos en S3

**Verificación en `list_photos/app.py`:**
- Encuentra 2 entradas en DynamoDB
- No encuentra archivos correspondientes en S3
- Reporta: "2 fotos en DB sin archivo en S3 (Perdidas!)"

## Soluciones propuestas

### Solución 1: Eliminación específica (Recomendada)
Modificar `delete_photo/app.py` para eliminar solo el archivo específico:

```python
# Reemplazar las líneas 32-44 con:
logger.info(f"Eliminando archivo específico: {s3_key}")

# Eliminar solo el archivo específico
s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
logger.info("Archivo específico eliminado de S3")
```

### Solución 2: Validación de prefix para fotos de perfil
Si se requiere mantener la lógica de eliminación por prefix, agregar validación:

```python
# Solo para fotos de perfil que no deberían tener subcarpetas
if photo['type'] == 'profile':
    # Eliminar solo el archivo específico
    s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
else:
    # Lógica actual para otros tipos de foto
    s3_prefix = s3_key.rsplit('/', 1)[0] + '/'
    # ... resto del código actual
```

### Solución 3: Implementar transacciones
Para mayor robustez, implementar eliminación transaccional que revierta cambios en caso de error:

```python
try:
    # Eliminar de S3 primero
    s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
    
    # Si S3 es exitoso, eliminar de DynamoDB
    table.delete_item(Key={'photo_id': photo_id})
    
except Exception as e:
    logger.error(f"Error en eliminación, revertir cambios si es necesario")
    raise e
```

**Recomendación:** Implementar la Solución 1 inmediatamente para resolver el problema crítico, seguida de la Solución 3 para mejorar la robustez del sistema.