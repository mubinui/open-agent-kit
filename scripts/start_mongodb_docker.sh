#!/usr/bin/env bash
# Helper script to launch the MongoDB session store using Docker.

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
CONTAINER_NAME=${MONGODB_CONTAINER:-orchestration-mongodb}
MONGO_PORT=${MONGODB_PORT:-27017}
MONGO_DB=${MONGODB_DATABASE:-orchestration}
MONGO_USER=${MONGODB_USERNAME:-orchestrator}
MONGO_PASS=${MONGODB_PASSWORD:-orchestrator_pass}
INIT_SCRIPT="$ROOT_DIR/scripts/init-mongodb.js"

start_with_compose() {
  local compose_cmd
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    compose_cmd="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    compose_cmd="docker-compose"
  else
    return 1
  fi

  echo "Using docker compose to start MongoDB..."
  ${compose_cmd} -f "$COMPOSE_FILE" up -d mongodb
  ${compose_cmd} -f "$COMPOSE_FILE" ps mongodb
  return 0
}

start_with_docker_run() {
  echo "docker compose not available; falling back to docker run"
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container ${CONTAINER_NAME} is already running"
    return 0
  fi

  docker run -d \
    --name "$CONTAINER_NAME" \
    -p "${MONGO_PORT}:27017" \
    -e "MONGO_INITDB_ROOT_USERNAME=${MONGODB_ROOT_USER:-mongo_root}" \
    -e "MONGO_INITDB_ROOT_PASSWORD=${MONGODB_ROOT_PASSWORD:-mongo_root_pass}" \
    -e "MONGO_INITDB_DATABASE=${MONGO_DB}" \
    -v "${ROOT_DIR}/mongo-data:/data/db" \
    -v "${INIT_SCRIPT}:/docker-entrypoint-initdb.d/init-mongodb.js:ro" \
    --restart unless-stopped \
    mongo:7.0
}

if [ -f "$COMPOSE_FILE" ] && start_with_compose; then
  echo "MongoDB container started via docker compose."
else
  start_with_docker_run
  echo "MongoDB container started via docker run."
fi

cat <<EOM

Connection string: mongodb://${MONGO_USER}:${MONGO_PASS}@localhost:${MONGO_PORT}/${MONGO_DB}
Set MONGODB_URL accordingly in your .env file.
EOM
