## [Titulo]: Codificacion incorrecta de caracteres en correos electronicos
### Resumen: Los correos de bienvenida se envian utilizando la codificacion ISO-8859-1, lo que impide renderizar correctamente tildes y caracteres especiales en los nombres.
### Severidad: Medium
### Analisis de causa raiz
- Pasos para reproducir:
  1. Registrar un usuario a traves del formulario web ingresando un nombre con tildes (por ejemplo, "José").
  2. La API Gateway procesa la peticion y la funcion Lambda `UserRegistrationFunction` guarda exitosamente los datos (incluyendo las tildes) en la tabla DynamoDB.
  3. DynamoDB dispara el evento hacia la funcion Lambda `SendEmailServiceFunction`.
  4. La funcion de correo construye el comando para AWS SES asignando a la propiedad `Charset` el valor de la variable de entorno `EMAIL_CHARSET` (configurada como `ISO-8859-1` via AWS SSM).
  5. El cliente de correo recibe el mensaje, pero por la incompatibilidad de la codificacion ISO-8859-1 con caracteres especiales de formato UTF-8, el nombre se rompe o se trunca mostrando solo "Jos".
- Esperado vs. Actual:
  - Esperado: El cliente de correo muestra correctamente "Hola José García," al reconocer los caracteres especiales.
  - Actual: El cliente de correo falla al procesar la codificacion y muestra "Hola Jos" u omite el resto del texto tras el caracter especial.
- Ubicacion del error (file/function):
  - `src/handlers/email.ts` en la funcion `handler` (lineas donde se usa la variable `EMAIL_CHARSET`).
  - `template.yaml` (donde se inyecta la variable de entorno `EMAIL_CHARSET: '{{resolve:ssm:/bw-010/email/charset}}'`).
- Logs relevantes:
  - En CloudWatch (`/aws/lambda/SendEmailServiceFunction`), se registra el payload enviado a SES mostrando el uso de ISO-8859-1 en los atributos Charset:
  `{"event":"DispatchingEmailToSES",...,"ses_payload":{..."Message":{"Subject":{"Data":"Welcome to our Service","Charset":"ISO-8859-1"},"Body":{"Text":{"Data":"\n        Hello Jos\u00e9 Garc\u00eda,\n...","Charset":"ISO-8859-1"}}}}}`
### Propuesta de Solucion
1. Actualizar el parametro en AWS Systems Manager (SSM) `/bw-010/email/charset` para que su valor sea `UTF-8` en vez de `ISO-8859-1`.
2. Alternativamente, actualizar el fichero `src/handlers/email.ts` para forzar la propiedad `Charset` a `"UTF-8"` (harcodeado) de forma que se garantice soporte universal para cualquier alfabeto y se eviten dependencias externas de configuracion que causen truncamientos en los clientes de correo.

# Token Usage

Total Tokens: 480766
Prompt Tokens: 472167
Input Tokens (non-cached): 96468
Response Tokens: 989
Cached Tokens: 375699
Thoughts Tokens: 7610

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.192936
Cached Cost (USD):  $0.075140
Output Cost (USD):  $0.011868
Thoughts Cost (USD):$0.091320
Total Cost (USD):   $0.371264


# Execution time in seconds:

165
