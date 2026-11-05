export BACKEND_URL=https://bugwizard.example.com
export BACKEND_WS_URL=wss://bugwizard.example.com
export BACKEND_TOKEN=<JWT_REDACTADO>

export LLM_USER_PROMPT="existe un error en los logs, revisarlo"

if [[ "$1" == "--destroy" ]]; then
  shift
  npx tsx src/destroy.ts "$@"
else
  npx tsx src/index.ts "$@"
fi
