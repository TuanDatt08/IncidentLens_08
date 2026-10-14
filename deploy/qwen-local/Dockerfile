FROM node:22-bookworm-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_USE_MOCK_API=false NEXT_PUBLIC_ENABLE_AUTH=true NEXT_PUBLIC_ENABLE_V2_WORKSPACE=false NEXT_PUBLIC_API_BASE_URL=/api/v1 NEXT_PUBLIC_API_V2_BASE_URL=/api/v2
# Packaging only; compile the unchanged checkout frontend as a standalone app.
RUN node -e "import('./next.config.mjs').then(({default:config})=>require('fs').writeFileSync('next.config.mjs','export default '+JSON.stringify({...config,output:'standalone'})))"
RUN npm run typecheck && npm run lint && npm run build

FROM ollama/ollama:0.40.3
USER root
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ffmpeg nginx ca-certificates libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 NEXT_TELEMETRY_DISABLED=1
RUN useradd --create-home --uid 10001 appuser && mkdir -p /data /models && chown appuser:appuser /data /models
COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node
COPY --chown=appuser:appuser backend/ /app/backend/
COPY --chown=appuser:appuser api/ /app/api/
COPY --chown=appuser:appuser alembic.ini /app/alembic.ini
COPY --chown=appuser:appuser deploy/qwen-local/ /app/deploy/
COPY --from=frontend-build --chown=appuser:appuser /frontend/.next/standalone/ /app/frontend/
COPY --from=frontend-build --chown=appuser:appuser /frontend/.next/static/ /app/frontend/.next/static/
ENV HOME=/home/appuser OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS=/models OLLAMA_NO_CLOUD=1
USER appuser
EXPOSE 8088
HEALTHCHECK --interval=15s --timeout=10s --start-period=20m --retries=4 CMD ["python", "/app/deploy/unified-health.py"]
ENTRYPOINT ["python", "/app/deploy/unified.py"]
CMD []
