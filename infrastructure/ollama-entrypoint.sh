#!/bin/sh
# Start the server (listening on all interfaces, IPv4 and IPv6), then make sure the model exists.
set -e
ollama serve &
server=$!

# Client commands talk to the local server explicitly.
export OLLAMA_CLIENT_HOST=127.0.0.1:11434
until OLLAMA_HOST=$OLLAMA_CLIENT_HOST ollama list >/dev/null 2>&1; do sleep 1; done
if ! OLLAMA_HOST=$OLLAMA_CLIENT_HOST ollama list | grep -q "^${OLLAMA_MODEL}"; then
  echo "Pulling ${OLLAMA_MODEL}..."
  OLLAMA_HOST=$OLLAMA_CLIENT_HOST ollama pull "${OLLAMA_MODEL}"
fi
echo "Model ${OLLAMA_MODEL} ready."
wait $server
