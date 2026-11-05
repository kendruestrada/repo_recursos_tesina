## Eliminacion masiva no intencionada de fotografias en S3
### Resumen: La lógica de borrado utiliza un prefijo de S3 demasiado amplio, provocando la eliminación de todos los archivos de un usuario al intentar borrar solo uno.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir
1. Cargar múltiples fotos para un usuario (por ejemplo, una foto de perfil y varias de galería).
2. Solicitar la eliminación de la foto de perfil utilizando su identificador.
3. Solicitar el listado de las fotos del usuario para observar que los archivos en S3 de las fotos de la galería ya no existen, aunque su metadata siga en base de datos.
- Esperado vs. Actual
El comportamiento esperado es que se elimine únicamente el objeto en S3 que corresponde a la foto solicitada, manteniendo las demás fotos intactas. En la actualidad, el sistema calcula la carpeta base del usuario (ej. `users/user_id/`) a través de un truncado de la ruta y elimina todos los objetos en S3 que contengan ese prefijo.
- Ubicacion del error (file/function)
`delete_photo/app.py` en la función `lambda_handler`
- Logs relevantes
```json
{"level":"INFO","location":"lambda_handler:38","message":"Metadata encontrada. S3 Key: users/user_test_7080/profile.jpg"}
{"level":"INFO","location":"lambda_handler:51","message":"A punto de eliminar 4 objetos!"}
{"level":"INFO","location":"lambda_handler:44","message":"Encontrados 0 objetos en S3 bajo prefix users/user_test_7080/"}
{"level":"ERROR","location":"lambda_handler:56","message":"3 fotos en DB sin archivo en S3 (Perdidas!)"}
```
### Propuesta de Solucion
Se debe eliminar la lógica que lista objetos usando paginación basada en un prefijo (`s3_prefix`). En lugar de realizar un borrado por lotes de todo lo que coincide en esa ruta, la llamada hacia S3 debe apuntar de manera directa a la clave `s3_key` obtenida previamente en el registro de DynamoDB utilizando la operación `delete_object` o especificando un único objeto en la lista de borrado de `delete_objects`.

# Token Usage

Total Tokens: 69803
Prompt Tokens: 65955
Input Tokens (non-cached): 45634
Response Tokens: 601
Cached Tokens: 20321
Thoughts Tokens: 3247

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.091268
Cached Cost (USD):  $0.004064
Output Cost (USD):  $0.007212
Thoughts Cost (USD):$0.038964
Total Cost (USD):   $0.141508


# Execution time in seconds:

65
