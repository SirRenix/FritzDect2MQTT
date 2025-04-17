#!/bin/sh

echo "🔧 Building Docker container..."
docker compose build

echo "🚀 Starting FritzDect2MQTT..."
docker compose up -d

echo "📋 Container status:"
docker ps --filter name=FritzDect2MQTT

echo "📑 Follow logs with:"
echo "    docker compose logs -f"

