## Análisis del Ticket de Soporte

**Ticket:** La aplicación no muestra todas las fotos registradas después de eliminar la foto de perfil del usuario.

## Hallazgos en los logs

Al analizar los logs de CloudWatch, se identifican múltiples errores críticos:

```
{"level":"ERROR","location":"lambda_handler:56","message":"3 fotos en DB sin archivo en S3 (Perdidas!)"}
```

Este error se repite consistentemente en múltiples ejecuciones de la función `ListPhotos`, indicando que existen **3 fotos registradas en DynamoDB que no tienen su archivo correspondiente en S3**. Esto sugiere que los archivos fueron eliminados de S3 pero sus metadatos permanecen en la base de datos.

## Relación con el código fuente

### Código problemático en `delete_photo/app.py`:

El error radica en las líneas 32-42 del código de eliminación:

```python
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

### Problema identificado:

1. **Construcción incorrecta del prefix**: En la línea 26, se construye el prefix como:
   ```python
   s3_prefix = s3_key.rsplit('/', 1)[0] + '/'
   ```

2. **Eliminación masiva no controlada**: El código elimina TODOS los objetos que coincidan con el prefix, no solo el archivo específico solicitado.

## Ejemplo de ejecución

**Escenario:** Usuario tiene una foto de perfil en `users/user123/profile.jpg`

1. **Estado inicial en S3:**
   - `users/user123/profile.jpg`
   - `users/user123/gallery/photo1.jpg`
   - `users/user123/gallery/photo2.jpg`

2. **Al eliminar la foto de perfil:**
   - `s3_key = "users/user123/profile.jpg"`
   - `s3_prefix = "users/user123/" + "/" = "users/user123/"`

3. **Resultado:** Se eliminan TODOS los archivos del usuario:
   - ❌ `users/user123/profile.jpg` (correcto)
   - ❌ `users/user123/gallery/photo1.jpg` (incorrecto)
   - ❌ `users/user123/gallery/photo2.jpg` (incorrecto)

4. **En DynamoDB:** Solo se elimina el registro de la foto de perfil, pero quedan los metadatos de las fotos de galería sin sus archivos correspondientes.

## Soluciones propuestas

### Solución 1: Eliminación específica (Recomendada)
```python
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    try:
        photo_id = event['pathParameters']['photo_id']
        logger.info(f"Iniciando borrado para foto_id: {photo_id}")
        
        # 1. Obtener metadata de DynamoDB
        response = table.get_item(Key={'photo_id': photo_id})
        
        if 'Item' not in response:
            logger.warning("Foto no encontrada en DynamoDB")
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Foto no encontrada'})
            }
        
        photo = response['Item']
        s3_key = photo['s3_key']
        
        logger.info(f"Eliminando archivo específico: {s3_key}")
        
        # 2. Eliminar SOLO el archivo específico de S3
        try:
            s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
            logger.info(f"Archivo {s3_key} eliminado de S3")
        except s3.exceptions.NoSuchKey:
            logger.warning(f"Archivo {s3_key} no existe en S3")
        
        # 3. Eliminar metadata de DynamoDB
        table.delete_item(Key={'photo_id': photo_id})
        logger.info("Metadata eliminada de DynamoDB")
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'mensaje': 'Foto eliminada correctamente',
                'photo_id': photo_id,
                's3_key': s3_key
            })
        }
        
    except Exception as e:
        logger.exception("Error procesando eliminación")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
```

### Solución 2: Script de limpieza para datos huérfanos
```python
def cleanup_orphaned_metadata():
    """
    Script para limpiar metadatos huérfanos en DynamoDB
    """
    # Escanear toda la tabla
    response = table.scan()
    items = response.get('Items', [])
    
    orphaned_items = []
    
    for item in items:
        s3_key = item['s3_key']
        try:
            s3.head_object(Bucket=BUCKET_NAME, Key=s3_key)
        except s3.exceptions.NoSuchKey:
            orphaned_items.append(item)
    
    # Eliminar metadatos huérfanos
    for item in orphaned_items:
        table.delete_item(Key={'photo_id': item['photo_id']})
        logger.info(f"Eliminado metadata huérfano: {item['photo_id']}")
```

### Solución 3: Mejora en la función ListPhotos
```python
# En list_photos/app.py, línea 56, cambiar el nivel de log:
if orphaned_metadata:
    logger.warning(  # Cambiar de ERROR a WARNING
        f"{len(orphaned_metadata)} fotos en DB sin archivo en S3 - ejecutar limpieza"
    )
    
    # Opcional: Auto-limpieza
    for s3_key in orphaned_metadata:
        # Encontrar y eliminar el metadata huérfano
        pass
```

La causa raíz es el **bug crítico en la función de eliminación** que borra más archivos de los solicitados, creando inconsistencias entre DynamoDB y S3. La solución inmediata es corregir la lógica de eliminación y ejecutar un script de limpieza para los datos huérfanos existentes.