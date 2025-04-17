#!/bin/sh

COMPOSE_FILE="./docker/docker-compose.yml"

echo "🔧 Building Docker container..."
docker compose -f "$COMPOSE_FILE" build

echo "🚀 Starting FritzDect2MQTT..."
docker compose -f "$COMPOSE_FILE" up -d

echo "📋 Container status:"
docker ps --filter name=FritzDect2MQTT

echo "📑 Follow logs with:"
echo "    docker compose -f $COMPOSE_FILE logs -f"

