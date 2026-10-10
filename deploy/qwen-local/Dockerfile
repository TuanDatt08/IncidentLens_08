FROM node:22-bookworm-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_USE_MOCK_API=false NEXT_PUBLIC_API_BASE_URL=/api/v1 NEXT_PUBLIC_API_V2_BASE_URL=/api/v2
# Packaging only; compile the unchanged checkout frontend as a standalone app.
RUN node -e "import('./next.config.mjs').then(({default:config})=>require('fs').writeFileSync('next.config.mjs','export default '+JSON.stringify({...config,output:'standalone'})))"
RUN npm run typecheck && npm run lint && npm run build

# Reuse the installed PostgreSQL/llama.cpp/Node/Python runtime, not its app source.
FROM incidentlens:unified-baseline
WORKDIR /app
USER root
RUN python -c "import shutil; [shutil.rmtree(p) for p in ('/app/backend','/app/api','/app/frontend','/app/deploy')]"
COPY --chown=appuser:appuser backend/ /app/backend/
COPY --chown=appuser:appuser api/ /app/api/
COPY --chown=appuser:appuser deploy/qwen-local/unified.py deploy/qwen-local/unified-health.py deploy/qwen-local/unified-nginx.conf /app/deploy/
COPY --from=frontend-build --chown=appuser:appuser /frontend/.next/standalone/ /app/frontend/
COPY --from=frontend-build --chown=appuser:appuser /frontend/.next/static/ /app/frontend/.next/static/
USER appuser
CMD ["python", "/app/deploy/unified.py"]
