FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY examples/ examples/
RUN mkdir -p generated && useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health')"
# Bind to IPv6 and IPv4 so private networks of either kind can reach the API.
CMD ["sh", "-c", "uvicorn backend.api.main:app --host :: --port ${PORT}"]
