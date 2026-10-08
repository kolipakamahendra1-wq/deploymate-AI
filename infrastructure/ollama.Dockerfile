# Ollama server that downloads its model on first start (kept on the mounted volume).
FROM ollama/ollama:latest

ENV OLLAMA_MODEL=qwen2.5:3b \
    OLLAMA_HOST=[::]:11434 \
    OLLAMA_KEEP_ALIVE=5m
COPY infrastructure/ollama-entrypoint.sh /ollama-entrypoint.sh
RUN chmod +x /ollama-entrypoint.sh

EXPOSE 11434
ENTRYPOINT ["/ollama-entrypoint.sh"]
