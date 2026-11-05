## Eliminacion Masiva No Intencional en S3: `delete_photo/app.py`

### Summary: Al eliminar una foto, el codigo construye un prefijo S3 a partir de la clave y borra TODOS los objetos bajo ese prefijo en lugar de solo el archivo especifico.

### Severity: Critical

---

### Root Cause Analysis

**Pasos para reproducir:**

1. Subir multiples fotos de galeria para `user_123`:
   - `users/user_123/gallery/foto_a.jpg`
   - `users/user_123/gallery/foto_b.jpg`
2. Llamar a `DELETE /photos/{photo_id}` usando el ID de `foto_a.jpg`

**Expected vs. Actual:**

| | Esperado | Actual |
|---|---|---|
| Objetos eliminados en S3 | 1 (`users/user_123/gallery/foto_a.jpg`) | 2 (`foto_a.jpg` + `foto_b.jpg`) |
| Registros eliminados en DynamoDB | 1 | 1 (solo el registro de `foto_a`) |

Resultado: datos huerfanos — `foto_b.jpg` sigue en DynamoDB pero ya no existe en S3.

**Ubicacion del bug:** `delete_photo/app.py`, lineas 40-57

---

**Flujo del error — linea a linea:**

```
s3_key = "users/user_123/gallery/foto_a.jpg"

# Linea 40: Extrae el directorio padre
s3_prefix = s3_key.rsplit('/', 1)[0] + '/'
# => s3_prefix = "users/user_123/gallery/"

# Lineas 45-49: Lista TODOS los objetos bajo ese prefix
# Encuentra: foto_a.jpg, foto_b.jpg, foto_c.jpg ...

# Lineas 53-57: Elimina TODOS, no solo el solicitado
```

Para fotos de perfil es aun mas destructivo:

```
s3_key = "users/user_123/profile.jpg"
# s3_prefix = "users/user_123/"
# Elimina profile.jpg + TODA la galeria del usuario
```

**Causa raiz:** La logica en `delete_photo/app.py:40` construye un prefijo de directorio (`rsplit('/', 1)[0]`) en lugar de usar directamente el `s3_key` exacto. Luego itera y elimina todo lo que queda bajo ese prefijo, afectando archivos de otras fotos del mismo usuario o directorio.

---

### Solution

Reemplazar el bloque de listado y borrado masivo (lineas 40-57) por una eliminacion directa del objeto especifico usando el `s3_key` ya conocido:

```python
# delete_photo/app.py - lineas 40-57 (reemplazar)

# ANTES (elimina todo el directorio)
s3_prefix = s3_key.rsplit('/', 1)[0] + '/'
objects_to_delete = []
paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_prefix):
    ...
s3.delete_objects(...)

# DESPUES (elimina solo el objeto exacto)
s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
```

# Total cost USD

0.1250935

# Execution time in seconds: 

32
