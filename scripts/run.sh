#!/bin/sh

COMPOSE_FILE="./docker/docker-compose.yml"
ENV_FILE="./docker/.env"

# Prüfen ob .env existiert
if [ ! -f "$ENV_FILE" ]; then
  echo "⚠️  WARNING: .env file not found at $ENV_FILE"
  echo "👉 Please copy docker/.env.example to docker/.env and edit your network settings."
  exit 1
fi

echo "🔧 Building Docker container..."
docker compose -f "$COMPOSE_FILE" build

echo "🚀 Starting FritzDect2MQTT..."
docker compose -f "$COMPOSE_FILE" up -d

echo "📋 Container status:"
docker ps --filter name=FritzDect2MQTT

echo "📑 Follow logs with:"
echo "    docker compose -f $COMPOSE_FILE logs -f"

