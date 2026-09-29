#!/usr/bin/env bash
# One-time preparation of a fresh Ubuntu/Debian server for the bot.
# Run on the server as a user with sudo rights:
#   curl -fsSL https://raw.githubusercontent.com/aaaaaaaalesha/iu8_queue_bot/main/deploy/setup-server.sh | bash
set -euo pipefail

APP_DIR=/opt/queue-bot

if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sudo sh
fi
sudo systemctl enable --now docker

# Allow the current (deploy) user to run docker without sudo.
sudo usermod -aG docker "$USER"

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"
chmod 700 "$APP_DIR"

echo "Done. Re-login (or run 'newgrp docker') so that the docker group applies."
echo "Deploy directory: $APP_DIR"
