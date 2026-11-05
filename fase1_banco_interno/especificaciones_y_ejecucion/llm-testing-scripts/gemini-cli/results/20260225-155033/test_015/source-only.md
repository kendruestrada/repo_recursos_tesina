## Borrado masivo involuntario de archivos en S3 por manejo incorrecto de prefijos
### Resumen: La funcion de eliminacion borra todos los archivos de S3 que comparten el mismo directorio en lugar de eliminar exclusivamente el archivo solicitado, generando severas inconsistencias de datos.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
  1. Ejecutar la subida de multiples fotos para un mismo usuario (por ejemplo, subir una foto de perfil y varias en la galeria).
  2. Invocar el endpoint de eliminacion proporcionando el identificador de una sola foto.
  3. Invocar el endpoint de listado de fotos para el mismo usuario. Se detectara que los archivos fisicos ya no existen en S3 aunque su metadata siga presente en la base de datos.
- Esperado vs. Actual: Se espera que el sistema elimine unicamente el archivo en S3 que corresponde a la clave exacta de la foto solicitada, junto con su registro en DynamoDB. Actualmente, el sistema extrae el directorio padre de la ruta del archivo, lista todos los objetos que se encuentran bajo ese directorio en S3 y los elimina masivamente, pero solo borra el registro de la foto solicitada en DynamoDB.
- Ubicacion del error: Archivo `delete_photo/app.py`, funcion `lambda_handler`.
- Logs relevantes: Mensajes que indican la cantidad anormal de objetos eliminados ("A punto de eliminar N objetos!") en el proceso de borrado, y posteriores errores de inconsistencia ("N fotos en DB sin archivo en S3 (Perdidas!)") en el proceso de listado.
### Propuesta de Solucion
Se debe modificar la rutina de eliminacion en S3 para que no realice busquedas ni iteraciones basadas en el directorio del archivo. La solucion consiste en tomar la clave exacta del archivo obtenida desde DynamoDB y ejecutar una operacion de borrado de un unico objeto en S3 utilizando unicamente esa clave especifica, asegurando asi que la eliminacion fisica y logica ocurran estrictamente sobre el mismo elemento.

# Token Usage

Total Tokens: 15641
Prompt Tokens: 12849
Input Tokens (non-cached): 4772
Response Tokens: 445
Cached Tokens: 8077
Thoughts Tokens: 2347

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.009544
Cached Cost (USD):  $0.001615
Output Cost (USD):  $0.005340
Thoughts Cost (USD):$0.028164
Total Cost (USD):   $0.044663


# Execution time in seconds:

51
