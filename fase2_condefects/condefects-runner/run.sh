#!/usr/bin/env bash
set -euo pipefail

# ==== Backend de BugWizard ====
export BACKEND_URL=https://bugwizard.example.com
export BACKEND_WS_URL=wss://bugwizard.example.com

# ==== TOKEN (OBLIGATORIO) ====
export BACKEND_TOKEN=$(curl -s -X POST 'https://cognito-idp.us-east-1.amazonaws.com/' \
  -H 'Content-Type: application/x-amz-json-1.1' \
  -H 'X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth' \
  -d "{\"AuthFlow\":\"USER_PASSWORD_AUTH\",\"ClientId\":\"7a8pu48av0ohnvju1o7aa02v34\",\"AuthParameters\":{\"USERNAME\":\"usuario@example.com\",\"PASSWORD\":\"ag3nT3-1\"}}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["AuthenticationResult"]["AccessToken"])')

echo "Token obtenido (primeros 20): ${BACKEND_TOKEN:0:20}..."

# ==== Entradas ConDefects ====
# Directorio con el checkout (o Code/) de ConDefects.
export CHECKOUT_DIR="../ConDefects/Code"
# Manifiesto generado con: python3 build_manifest.py -w $CHECKOUT_DIR -o manifest.csv -l python
# Para la prueba chica con síntoma real, usar el subconjunto de 6 programas:
export MANIFEST="../condefects-eval/manifest_subset36.csv"
# Dónde guardar las respuestas de BugWizard (una .md por programa).
export PREDICTIONS_DIR="../condefects-eval/predictions"

# Opcional: limitar cuántos programas correr (para una prueba chica).
export LIMIT="36"

# Opcional: contenido del archivo de "log". Por defecto "sin logs".
# Se usa solo si no hay un log específico del programa en LOGS_DIR.
# export LOG_TEXT="entrada:\n3 1 2\nesperado: 6\nobtenido: 0"

# Modo con síntoma real: carpeta con un <program_key>.log por programa
# (generados con condefects-eval/generate_test_logs.py, a partir de los
# casos exitosos/fallidos reales de ConDefects). Si existe el archivo para
# el programa, se sube ese log en vez de LOG_TEXT.
export LOGS_DIR="../condefects-eval/logs"

npx tsx src/index.ts
