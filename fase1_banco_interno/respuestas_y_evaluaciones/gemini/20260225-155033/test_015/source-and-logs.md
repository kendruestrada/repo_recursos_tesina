## Eliminacion masiva no intencionada de fotos en S3
### Resumen: La funcion de eliminacion borra todos los archivos del usuario en S3 debido al uso de un prefijo comun de carpeta en lugar de apuntar a la llave especifica del archivo a borrar.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
  1. Subir una foto de perfil y al menos una foto de galeria para un usuario.
  2. Enviar una peticion para eliminar la foto de perfil de dicho usuario.
  3. Enviar una peticion para listar las fotos del mismo usuario.
- Esperado vs. Actual: Se esperaba que al eliminar la foto, solo su archivo especifico desapareciera en S3. Actualmente, el sistema construye un prefijo (`users/{user_id}/`) y elimina todos los archivos en S3 que compartan esa ruta base. Sin embargo, en DynamoDB solo borra el registro de la foto seleccionada, generando registros huerfanos en la base de datos sin sus correspondientes archivos.
- Ubicacion del error (file/function): `delete_photo/app.py` / `lambda_handler`
- Logs relevantes:
  - `{"level":"INFO","location":"lambda_handler:38","message":"Metadata encontrada. S3 Key: users/user_test_7080/profile.jpg"}`
  - `{"level":"INFO","location":"lambda_handler:51","message":"A punto de eliminar 4 objetos!"}`
  - `{"level":"INFO","location":"lambda_handler:62","message":"Metadata eliminada de DynamoDB"}`
  - `{"level":"ERROR","location":"lambda_handler:56","message":"3 fotos en DB sin archivo en S3 (Perdidas!)"}`
### Propuesta de Solucion
Se debe modificar el comportamiento en `delete_photo/app.py` eliminando la logica de busqueda de multiples archivos con `get_paginator('list_objects_v2')`. Dado que se cuenta con el valor exacto de `s3_key` para la foto desde DynamoDB, el codigo debe realizar la eliminacion directa de un solo archivo mediante una unica llamada al metodo `s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)`. Con esto, se solucionara la perdida de los demas archivos en el bucket.

# Token Usage

Total Tokens: 72649
Prompt Tokens: 68368
Input Tokens (non-cached): 48045
Response Tokens: 606
Cached Tokens: 20323
Thoughts Tokens: 3675

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.096090
Cached Cost (USD):  $0.004065
Output Cost (USD):  $0.007272
Thoughts Cost (USD):$0.044100
Total Cost (USD):   $0.151527


# Execution time in seconds:

68
