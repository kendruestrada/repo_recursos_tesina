# Sistema de Registro de Usuarios con AWS SAM

Este proyecto implementa un sistema completo de registro de usuarios "serverless" utilizando AWS SAM (Serverless Application Model). Incluye un backend con funciones Lambda, una base de datos DynamoDB, envío de correos con SES, y un frontend estático alojado en S3.

## Estructura del Proyecto

El proyecto está organizado de la siguiente manera:

*   **`src/handlers/`**: Código fuente de las funciones Lambda (TypeScript).
    *   `register.ts`: Maneja el registro de nuevos usuarios (POST).
    *   `search.ts`: Permite buscar usuarios por email o listar todos (GET).
    *   `email.ts`: Servicio que escucha eventos de DynamoDB y envía correos de bienvenida vía SES.
*   **`frontend/`**: Código del sitio web estático.
    *   `index.html`: Interfaz de usuario simple para registrar y buscar usuarios.
*   **`scripts/`**: Scripts de utilidad.
    *   `deploy_frontend.sh`: Script automatizado para configurar y desplegar el frontend en S3.
*   **`template.yaml`**: Plantilla de AWS SAM que define toda la infraestructura (IaC).
*   **`package.json`**: Dependencias de Node.js para el backend.

## Recursos Principales

La infraestructura desplegada incluye:

1.  **API Gateway (HTTP API)**: Punto de entrada público para las peticiones del frontend. Configurado con CORS global.
2.  **DynamoDB (`UsersTable`)**: Base de datos NoSQL donde se almacena la información de los usuarios.
3.  **Lambda Functions**:
    *   `UserRegistrationFunction`: Procesa los datos del formulario y los guarda en DynamoDB.
    *   `SearchUsersFunction`: Recupera datos de usuarios.
    *   `EmailServiceFunction`: Se dispara automáticamente cuando se inserta un nuevo usuario (DynamoDB Stream) y envía un correo.
4.  **Amazon SES**: Servicio utilizado para el envío de correos electrónicos.
5.  **Amazon S3 (`FrontendBucket`)**: Bucket configurado para alojamiento de sitios web estáticos.

## Instrucciones de Despliegue

### Prerrequisitos
*   AWS CLI configurado.
*   AWS SAM CLI instalado.
*   Node.js instalado.
*   Una identidad verificada en Amazon SES (email o dominio) para poder enviar correos.

### 1. Construir y Desplegar el Backend

Ejecuta los siguientes comandos en la raíz del proyecto para compilar el código TypeScript y desplegar la infraestructura en AWS:

```bash
# Instalar dependencias
npm install

# Compilar el proyecto
sam build

# Desplegar en AWS
sam deploy --guided
```

Sigue las instrucciones en pantalla. SAM creará todos los recursos necesarios.

### 2. Desplegar el Frontend

Una vez que el backend esté desplegado exitosamente, utiliza el script proporcionado para desplegar el frontend. Este script actualizará automáticamente la URL de la API en el archivo `index.html` y lo subirá al bucket S3.

```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x scripts/deploy_frontend.sh

# Ejecutar el despliegue
./scripts/deploy_frontend.sh
```

Al finalizar, el script mostrará la **URL del sitio web**. Puedes abrir esa URL en tu navegador para usar la aplicación.

## Notas Importantes

*   **CORS**: El proyecto ya tiene configurado CORS para permitir que el frontend se comunique con la API sin problemas.
*   **SES Sandbox**: Si tu cuenta de AWS está en el "Sandbox" de SES, solo podrás enviar correos a direcciones previamente verificadas. Asegúrate de verificar tanto el remitente (en `src/handlers/email.ts`) como el destinatario para las pruebas.
*   **Actualizaciones**: Si modificas el código del backend, corre `sam build && sam deploy`. Si modificas el frontend, corre `./scripts/deploy_frontend.sh`.
