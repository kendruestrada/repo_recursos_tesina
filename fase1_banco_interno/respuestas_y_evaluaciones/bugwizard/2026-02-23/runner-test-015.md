## Análisis del Ticket de Soporte

**Ticket:** La aplicación no muestra todas las fotos registradas después de eliminar la foto de perfil del usuario.

## Hallazgos en los logs

### 1. Error crítico detectado:
```
{"level":"ERROR","location":"lambda_handler:56","message":"3 fotos en DB sin archivo en S3 (Perdidas!)"}
```

### 2. Secuencia de eventos problemática:
1. **22:10:02** - Se suben 3 fotos (1 profile + 2 gallery) correctamente
2. **22:10:04** - Se elimina la foto de perfil (`profile_bb72eaa2`)
3. **22:10:04** - **PROBLEMA**: Se eliminan 4 objetos de S3 en lugar de solo 1
4. **22:10:05** - Al listar fotos: 3 entradas en DynamoDB pero 0 objetos en S3

### 3. Evidencia del comportamiento incorrecto:
```
{"message":"⚠️ A punto de eliminar 4 objetos!"}
{"message":"Objetos eliminados de S3 exitosamente"}
```

## Relación con el código fuente

### Causa raíz identificada en `delete_photo/app.py` (líneas 35-48):

```python
# 🐛 BUG CRÍTICO: Esta lógica es incorrecta
s3_prefix = s3_key.rsplit('/', 1)[0] + '/'

# Lista TODOS los objetos bajo ese prefix
objects_to_delete = []
paginator = s3.get_paginator('list_objects_v2')

for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_prefix):
    if 'Contents' in page:
        objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])
```

### Problema específico:
- Para la foto de perfil con S3 key: `users/user_test_2643/profile.jpg`
- El código calcula el prefix como: `users/user_test_2643/` 
- Esto hace que liste **TODOS** los objetos del usuario, no solo la foto específica
- Resultado: elimina profile.jpg + todas las fotos de gallery/

## Ejemplo de ejecución

### Entrada:
- `photo_id`: "profile_bb72eaa2"
- `s3_key`: "users/user_test_2643/profile.jpg"

### Ejecución paso a paso:
```python
# Paso 1: Calcular prefix (INCORRECTO)
s3_key = "users/user_test_2643/profile.jpg"
s3_prefix = s3_key.rsplit('/', 1)[0] + '/'  # "users/user_test_2643/"

# Paso 2: Listar objetos con ese prefix
# Encuentra: ["users/user_test_2643/profile.jpg", 
#           "users/user_test_2643/gallery/img_0.jpg",
#           "users/user_test_2643/gallery/img_1.jpg", 
#           "users/user_test_2643/gallery/img_2.jpg"]

# Paso 3: Eliminar TODOS (4 objetos) ❌
# Paso 4: Eliminar solo 1 entrada de DynamoDB ❌
```

### Resultado:
- **DynamoDB**: 3 entradas (profile eliminada, 2 gallery quedan)
- **S3**: 0 objetos (todos eliminados por error)
- **Estado**: Inconsistencia - fotos "perdidas"

## Soluciones propuestas

### Solución 1: Eliminación específica (Recomendada)
```python
# Reemplazar líneas 35-48 con:
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
        
        logger.info(f"Metadata encontrada. S3 Key: {s3_key}")
        
        # 2. Eliminar SOLO el objeto específico de S3
        try:
            s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
            logger.info(f"Objeto {s3_key} eliminado de S3")
        except s3.exceptions.NoSuchKey:
            logger.warning(f"Objeto {s3_key} no existe en S3")
        
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

### Solución 2: Reparación de datos existentes
```python
# Script de reparación para restaurar consistencia
def repair_orphaned_metadata():
    """
    Elimina entradas de DynamoDB que no tienen archivo correspondiente en S3
    """
    # Ejecutar para user_test_2643 que tiene fotos perdidas
    # Eliminar las 2 entradas de gallery que quedaron huérfanas
```

### Solución 3: Validación adicional
Agregar verificación antes de eliminar:
```python
# Verificar que el objeto existe en S3 antes de intentar eliminarlo
try:
    s3.head_object(Bucket=BUCKET_NAME, Key=s3_key)
    s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
except s3.exceptions.NoSuchKey:
    logger.warning(f"Objeto {s3_key} no existe en S3, solo eliminando metadata")
```

**Prioridad:** Alta - Este bug causa pérdida de datos y inconsistencias críticas en el sistema.