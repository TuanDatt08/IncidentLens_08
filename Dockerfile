# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install packages in a shared virtual environment readable by appuser.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY . .

# Create data directory with correct ownership
RUN mkdir -p /app/backend/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health')" || exit 1

CMD ["python", "-m", "deploy.render_start"]
