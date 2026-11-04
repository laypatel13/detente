#!/usr/bin/env bash
# Write switch/.env once, with fresh secrets. Later runs keep the existing file.
set -euo pipefail
file="$(dirname "$0")/../switch/.env"
[ -f "$file" ] && exit 0

secret() { openssl rand -hex 24; }

cat > "$file" <<EOF
SWITCH_VERSION=0.31.0
DB_USER=switch_app
DB_PASSWORD=$(secret)
DB_OWNER_USER=postgres
DB_OWNER_PASSWORD=$(secret)
DB_NAME=switch
AGENT_REGISTRATION_TOKEN=$(secret)
SECRET_KEYS=local:$(openssl rand -hex 32)
GATEWAY_ADMIN_EMAIL=admin@switch.local
GATEWAY_ADMIN_PASSWORD=$(secret)
MATTERMOST_ADMIN_USER=admin
MATTERMOST_ADMIN_PASSWORD=$(secret)
MATTERMOST_TEAM_NAME=switch
MATTERMOST_USER=user
MATTERMOST_USER_PASSWORD=$(secret)
EOF
echo "Wrote $file"
