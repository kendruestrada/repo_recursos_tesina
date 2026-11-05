Con el análisis del código fuente y los logs de CloudWatch, tengo toda la información necesaria para determinar la causa raiz.

---

## Bug: Eliminacion masiva de archivos S3 al borrar foto de perfil

### Summary: Al eliminar la foto de perfil, se borran todos los archivos S3 del usuario (incluyendo fotos de galeria), dejando metadata huerfana en DynamoDB que impide mostrar las fotos restantes.

### Severity: Critical

---

### Root Cause Analysis

**Evidencia en logs** (`dev-ListPhotos`):

El error se repite de forma consistente en multiples invocaciones del 2026-02-20:
```
"3 fotos en DB sin archivo en S3 (Perdidas!)"
location: lambda_handler:56
```
Esto confirma que despues de un `DELETE`, DynamoDB conserva registros de 3 fotos cuyos archivos ya no existen en S3.

**Ubicacion del bug**: `delete_photo/app.py`, lineas 40-49

**Flujo defectuoso**:

El codigo extrae el `s3_key` de la foto a eliminar (por ejemplo `users/user_123/profile.jpg`) y construye un prefijo S3 recortando el nombre del archivo:

```python
# linea 40
s3_prefix = s3_key.rsplit('/', 1)[0] + '/'
# "users/user_123/profile.jpg" → s3_prefix = "users/user_123/"
```

Luego lista y elimina **todos los objetos bajo ese prefijo**:

```python
# lineas 45-57
for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_prefix):
    if 'Contents' in page:
        objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])
...
s3.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': objects_to_delete})
```

**Ejemplo de ejecucion con datos hipoteticos**:

| Item | DynamoDB photo_id | S3 key |
|---|---|---|
| Foto de perfil (a borrar) | `profile_abc` | `users/user_123/profile.jpg` |
| Galeria 1 | `gallery_def` | `users/user_123/gallery/vacaciones.jpg` |
| Galeria 2 | `gallery_ghi` | `users/user_123/gallery/cumple.jpg` |
| Galeria 3 | `gallery_jkl` | `users/user_123/gallery/boda.jpg` |

El prefijo calculado es `users/user_123/`. La paginacion lista los 4 objetos. Se eliminan los 4 de S3. Pero `table.delete_item` (linea 61) solo borra `profile_abc` de DynamoDB.

**Resultado**: `gallery_def`, `gallery_ghi` y `gallery_jkl` permanecen en DynamoDB apuntando a claves S3 que ya no existen → **3 fotos perdidas**, coincidiendo exactamente con el error en logs.

**Expected vs Actual**:
- **Esperado**: Se elimina unicamente `users/user_123/profile.jpg` de S3 y su registro en DynamoDB.
- **Actual**: Se eliminan todos los archivos bajo `users/user_123/`, destruyendo tambien las fotos de galeria en S3.

---

### Solution

Reemplazar la logica de borrado masivo por prefijo con la eliminacion directa del `s3_key` especifico de la foto solicitada. En `delete_photo/app.py`, las lineas 40-57 deben sustituirse por:

```python
# Eliminar unicamente el objeto S3 correspondiente a esta foto
s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
```

Esto garantiza que solo se borra el archivo de la foto indicada por `photo_id`, sin afectar el resto del contenido del usuario en S3.

# Total cost USD

0.2943145

# Execution time in seconds: 

84
