"""Maintain a restricted SSH media tunnel alongside the Render API."""
import os
import subprocess
import tempfile
from pathlib import Path
from threading import Event, Thread

import uvicorn


def main():
    stop = Event()
    process = []
    with tempfile.TemporaryDirectory(prefix='incidentlens-ssh-') as directory:
        key = os.environ.get('GPU_SSH_PRIVATE_KEY', '')
        if key:
            root = Path(directory)
            private_key, known_hosts = root / 'key', root / 'known_hosts'
            private_key.write_text(key.replace('\\n', '\n').strip() + '\n')
            private_key.chmod(0o600)
            known_hosts.write_text(os.environ['GPU_SSH_KNOWN_HOSTS'].strip() + '\n')
            command = ['ssh', '-NT', '-i', str(private_key), '-o', 'BatchMode=yes',
                       '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={known_hosts}',
                       '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=15',
                       '-o', 'ServerAliveCountMax=3', '-o', 'ConnectTimeout=15',
                       '-L', '127.0.0.1:18000:127.0.0.1:18000',
                       '-p', os.environ['GPU_SSH_PORT'], os.environ['GPU_SSH_TARGET']]

            def tunnel():
                while not stop.is_set():
                    child = subprocess.Popen(command)
                    process[:] = [child]
                    child.wait()
                    if not stop.wait(5):
                        print('GPU media tunnel disconnected; reconnecting.', flush=True)

            Thread(target=tunnel, daemon=True).start()
        try:
            uvicorn.run('api.main:app', host='0.0.0.0', port=int(os.environ.get('PORT', '8000')))
        finally:
            stop.set()
            if process:
                process[0].terminate()
                process[0].wait(timeout=10)


if __name__ == '__main__':
    main()
