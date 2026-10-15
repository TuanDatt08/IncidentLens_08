#!/bin/bash
# Run as root inside the existing Vast instance after copying code and worker.env.
set -euo pipefail
base=/workspace/incidentlens
mkdir -p "$base" /workspace/incidentlens-media /workspace/incidentlens-logs
sed -i 's/\r$//' "$base/worker.env"
chmod 600 "$base/worker.env"
for service in gpu-media gpu-worker; do
    if [ "$service" = gpu-media ]; then
        command='/workspace/incidentlens-venv/bin/python -m uvicorn api.gpu_media:app --host 127.0.0.1 --port 18000'
        automatic=true
    else
        command='/workspace/incidentlens-venv/bin/python -m backend.gpu_worker'
        automatic=false
    fi
    cat > "/opt/supervisor-scripts/incidentlens-$service.sh" <<EOF
#!/bin/bash
set -e
. /opt/supervisor-scripts/utils/logging.sh
set -a
. $base/worker.env
set +a
cd $base
exec $command
EOF
    chmod 700 "/opt/supervisor-scripts/incidentlens-$service.sh"
    cat > "/etc/supervisor/conf.d/incidentlens-$service.conf" <<EOF
[program:incidentlens-$service]
environment=PROC_NAME="%(program_name)s",PYTHONUNBUFFERED="1"
command=/opt/supervisor-scripts/incidentlens-$service.sh
autostart=$automatic
autorestart=true
startsecs=5
stopasgroup=true
killasgroup=true
stopwaitsecs=30
stdout_logfile=/dev/stdout
redirect_stderr=true
stdout_logfile_maxbytes=0
EOF
done
supervisorctl reread
supervisorctl update
echo 'Media service installed. Start worker after media migration: supervisorctl start incidentlens-gpu-worker'
