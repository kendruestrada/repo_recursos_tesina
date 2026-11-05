**Resumen de Ejecución de Pruebas**

Se ejecutaron un total de 55 pruebas orientadas a identificar vulnerabilidades, cuellos de botella y fallos arquitectónicos en el código y la infraestructura del sistema. 

**Hallazgos Principales (Agrupados por similitud para brevedad):**

*   **Validación y Manejo de Estados (Pruebas 1-3, 5-6, 47-49):** Fallos silenciosos al procesar compras y direcciones. El sistema enmascara errores de proveedores externos devolviendo códigos 200 falsos y establece estados como "completado" de forma prematura, rompiendo la coherencia de los datos.
*   **Timeouts en Peticiones HTTP (Pruebas 9-10, 12-16):** La omisión de parámetros de límite de tiempo en llamadas síncronas bloquea las funciones Lambda, lo que causa cuelgues, operaciones huérfanas e impide la invalidación de cachés.
*   **Concurrencia, Atomicidad y Deadlocks (Pruebas 20-22, 32-34, 44-46):** La falta de operaciones transaccionales en DynamoDB y el uso incorrecto de variables globales como caché originan condiciones de carrera que permiten saldos negativos. La reserva simultánea de cuentas sin un orden lógico causa interbloqueos (deadlocks) irrecuperables.
*   **Fugas de Memoria y Conexiones (Pruebas 23-25, 35-37):** El almacenamiento acumulativo en variables globales provoca el desbordamiento de memoria de las Lambdas. Adicionalmente, omitir la liberación de conexiones a la base de datos en flujos exitosos agota el pool y bloquea el sistema tras pocas peticiones.
*   **Lógica de Infraestructura y Reintentos (Pruebas 8, 30-31, 38-40):** Errores en la estructura de payloads y reglas duplicadas en EventBridge causan que SQS reintente mensajes infinitamente, provocando el envío múltiple de correos y la asignación doble de puntos de fidelidad.
*   **Almacenamiento y Optimización de BD (Pruebas 41-43, 50-52):** El uso de prefijos genéricos en S3 causa el borrado masivo accidental de archivos de usuario. En DynamoDB, la extracción de atributos pesados supera el límite de 1MB por lectura, degradando drásticamente el rendimiento de las consultas y anulando la paginación.
*   **Errores de Código y Excepciones (Pruebas 4, 7, 11, 26, 29, 53):** Caídas del sistema por incompatibilidad de módulos (CommonJS vs ES Modules), falta de bloques try/catch, variables no inicializadas y excepciones por falta de encadenamiento opcional al procesar eventos.
*   **Codificación y Circuit Breakers (Pruebas 17-19, 27-28):** Un operador invertido en el Circuit Breaker bloquea permanentemente el servicio tras un fallo. Además, el uso de codificación ISO-8859-1 en correos corrompe los caracteres especiales y tildes en los nombres de usuario.
*   **Seguridad (Pruebas 54-55):** Reflejo permisivo de cualquier origen en las cabeceras CORS y omisión en la validación de firmas JWT, lo que permite la suplantación de identidad y filtrado de información a dominios maliciosos.

**Métricas de Ejecución y Costos:**

*   **Total de pruebas ejecutadas:** 55
*   **Tiempo total de ejecución:** 6886 segundos (114.77 minutos)
*   **Tiempo promedio por prueba:** 125.20 segundos (2.09 minutos)
*   **Costo total estimado:** $15.66 USD
*   **Costo promedio por prueba:** $0.28 USD
