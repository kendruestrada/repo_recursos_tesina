Con toda la información recopilada, puedo presentar el analisis completo:

---

## Bug: Eliminacion masiva de archivos S3 al borrar una foto

### Summary: Al eliminar una foto de perfil, se eliminan todos los archivos S3 del usuario, dejando los registros de DynamoDB huerfanos y las fotos restantes inaccesibles.

### Severity: High

---

### Root Cause Analysis

**Pasos para reproducir:**
1. Usuario tiene 1 foto de perfil + 3 fotos de galeria (4 objetos en S3, 4 registros en DynamoDB).
2. Se invoca `DELETE /photos/{photo_id}` con el `photo_id` de la foto de perfil.
3. Se consulta `GET /photos/{user_id}` y se observa que el listado reporta 0 fotos en S3 pero 3 en DynamoDB.

**Evidencia en logs de `dev-DeletePhoto`:**
```
"Metadata encontrada. S3 Key: users/user_test_5775/profile.jpg"
"A punto de eliminar 4 objetos!"   <- deberia ser 1
"Objetos eliminados de S3 exitosamente"
"Metadata eliminada de DynamoDB"   <- solo borra 1 registro
```

**Evidencia en logs de `dev-ListPhotos` (invocacion posterior):**
```
"Encontradas 3 entradas en DynamoDB"
"Encontrados 0 objetos en S3 bajo prefix users/user_test_5775/"
ERROR: "3 fotos en DB sin archivo en S3 (Perdidas!)"
```

**Expected vs Actual:**
| Aspecto | Esperado | Actual |
|---|---|---|
| Objetos eliminados en S3 | 1 (solo `profile.jpg`) | 4 (todos los archivos del usuario) |
| Registros eliminados en DynamoDB | 1 | 1 |
| Estado posterior | 3 fotos visibles | 3 registros huerfanos, 0 archivos |

**Ubicacion del bug:** `delete_photo/app.py`, lineas 40-57

```python
# Linea 40 - calculo incorrecto del prefijo
s3_prefix = s3_key.rsplit('/', 1)[0] + '/'

# Para s3_key = "users/user_test_5775/profile.jpg"
# rsplit('/', 1)[0]  →  "users/user_test_5775"
# + '/'              →  "users/user_test_5775/"   <-- prefijo raiz del usuario
```

El prefijo calculado apunta al **directorio raiz del usuario**, no a la foto especifica. Al listar con ese prefijo se obtienen TODOS los archivos del usuario (perfil + galeria), y todos son eliminados. Sin embargo, `table.delete_item` en la linea 61 solo elimina el registro de la foto solicitada, generando inconsistencia entre S3 y DynamoDB.

**Flujo incorrecto con valores reales:**
```
s3_key      = "users/user_test_5775/profile.jpg"
s3_prefix   = "users/user_test_5775/"          ← demasiado amplio

list_objects_v2(Prefix="users/user_test_5775/")
→ [
    "users/user_test_5775/profile.jpg",      # foto de perfil
    "users/user_test_5775/gallery/foto1.jpg",# galeria
    "users/user_test_5775/gallery/foto2.jpg",# galeria
    "users/user_test_5775/gallery/foto3.jpg" # galeria
  ]

delete_objects(todos los 4)  ← elimina fotos de galeria que no deberia
delete_item(photo_id=profile_...) ← solo 1 registro de dynamo
```

---

### Solution

Reemplazar la logica de eliminacion masiva por prefijo con la eliminacion directa del objeto especifico usando `s3_key`:

**delete_photo/app.py** — reemplazar lineas 40-57:

```python
# ANTES (incorrecto):
s3_prefix = s3_key.rsplit('/', 1)[0] + '/'
objects_to_delete = []
paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_prefix):
    if 'Contents' in page:
        objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])
if objects_to_delete:
    s3.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': objects_to_delete})

# DESPUES (correcto):
s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
```

Esto garantiza que:
- Solo se elimina el archivo S3 correspondiente a la foto solicitada.
- El registro de DynamoDB eliminado coincide exactamente con el archivo S3 eliminado.
- Las demas fotos del usuario permanecen intactas en S3 y en DynamoDB.

# Total cost USD

0.35297449999999997

# Execution time in seconds: 

64
