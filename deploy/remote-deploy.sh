#!/usr/bin/env bash
# Runs on the server (called by .github/workflows/deploy.yaml).
# Usage: remote-deploy.sh <image> <registry-user>, registry token on stdin.
set -euo pipefail

BOT_IMAGE=$1
REGISTRY_USER=$2
REGISTRY=${BOT_IMAGE%%/*}
export BOT_IMAGE

cd "$(dirname "$0")"

# The token is the job's GITHUB_TOKEN: it expires when the job ends, and the
# server logs out right after pulling anyway.
docker login "$REGISTRY" -u "$REGISTRY_USER" --password-stdin
trap 'docker logout "$REGISTRY" >/dev/null' EXIT

docker compose pull
docker compose up -d --remove-orphans
docker image prune -f >/dev/null

# Make sure the new container survived startup (bad token, broken DB, ...).
sleep 15
docker compose ps
container=$(docker compose ps --all --quiet bot)
state=$(docker inspect --format '{{.State.Status}} {{.RestartCount}}' "$container")
if [ "$state" != "running 0" ]; then
    docker compose logs --tail 50 bot
    echo "The bot is not running properly (state: $state)" >&2
    exit 1
fi
docker compose logs --tail 20 bot
