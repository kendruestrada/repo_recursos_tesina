## [Titulo]: Falla en flujo por excepción de tipo (TypeError) al procesar registros incompletos en el DynamoDB Stream
### Resumen: La función encargada del envío de correos se rompe al intentar acceder directamente a la propiedad `.S` de atributos que pueden venir indefinidos, evadiendo la validación de errores programada.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir: Insertar o modificar un ítem en la tabla de base de datos DynamoDB donde se omita intencionalmente alguno de los campos (`email`, `first_name`, `last_name` o `birth_date`). El evento activará la función Lambda del servicio de correos que procesa el stream y fallará de inmediato.
- Esperado vs. Actual: El comportamiento esperado es que la aplicación detecte la falta de datos críticos como el `email` o `first_name`, emita un aviso mediante `console.warn` y continúe con el siguiente registro. El comportamiento actual arroja una excepción no manejada de la forma `TypeError: Cannot read properties of undefined (reading 'S')`, dado que se evalúa la extracción de la propiedad antes de la condición de validación. Al presentarse una falla no controlada, DynamoDB Streams reintentará el lote de manera infinita paralizando los envíos (Poison Pill).
- Ubicacion del error: Fichero `src/handlers/email.ts`, función `handler` (en la etapa de asignación de variables extrayendo desde `newImage`).
- Logs relevantes: Si bien no se suministran logs en este entorno aislado, la excepción visible en CloudWatch ante este fallo indicaría la caída por lectura de propiedades indefinidas en la ejecución de la Lambda.
### Propuesta de Solucion
Se debe implementar *optional chaining* (encadenamiento opcional) en la extracción de los valores provenientes de `newImage` en el evento de la base de datos, de forma que el acceso a `.S` sea seguro en caso de que el nodo de ese atributo no exista. 

Modificar en `src/handlers/email.ts` las asignaciones de la siguiente forma:
```typescript
      const email = newImage.email?.S;
      const firstName = newImage.first_name?.S;
      const lastName = newImage.last_name?.S;
      const birthDate = newImage.birth_date?.S;
```
De esta manera las variables correspondientes a atributos inexistentes adoptarán el valor `undefined` sin lanzar una excepción y el código de manejo de errores subsecuente (`if (!email || !firstName)`) evaluará la condición correctamente permitiendo al sistema descartar el registro sin afectar el funcionamiento general.

# Token Usage

Total Tokens: 141109
Prompt Tokens: 119153
Input Tokens (non-cached): 33864
Response Tokens: 884
Cached Tokens: 85289
Thoughts Tokens: 21072

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.067728
Cached Cost (USD):  $0.017058
Output Cost (USD):  $0.010608
Thoughts Cost (USD):$0.252864
Total Cost (USD):   $0.348258


# Execution time in seconds:

267
