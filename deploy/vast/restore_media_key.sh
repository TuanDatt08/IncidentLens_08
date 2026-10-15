#!/bin/bash
# Restore only the existing Render media key after Vast refreshes authorized_keys.
set -euo pipefail
public_file=${1:-/workspace/render_media_ed25519.pub}
authorized_file=${2:-/root/.ssh/authorized_keys}
[ -s "$public_file" ] || exit 0
ssh-keygen -lf "$public_file" >/dev/null
read -r key_type key_data comment < "$public_file"
[ "$key_type" = ssh-ed25519 ]
key_data=${key_data%$'\r'}
mkdir -p "$(dirname "$authorized_file")"
touch "$authorized_file"
chmod 600 "$authorized_file"
if ! grep -Fq -- "$key_data" "$authorized_file"; then
    printf '\nrestrict,port-forwarding,permitopen="127.0.0.1:18000",command="/bin/false" %s %s incidentlens-render-media\n' "$key_type" "$key_data" >> "$authorized_file"
fi
