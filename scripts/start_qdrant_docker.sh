#!/bin/bash
# Start Qdrant vector database in Docker
#
# This script starts a local Qdrant instance for development.
# Data is persisted in a Docker volume.
#
# Usage:
#   ./scripts/start_qdrant_docker.sh

set -e

CONTAINER_NAME="orchestration-qdrant-dev"
QDRANT_VERSION="v1.7.4"
HTTP_PORT="6333"
GRPC_PORT="6334"
VOLUME_NAME="orchestration_qdrant_dev_data"

echo "🚀 Starting Qdrant Vector Database..."
echo "   Container: $CONTAINER_NAME"
echo "   Version: $QDRANT_VERSION"
echo "   HTTP Port: $HTTP_PORT"
echo "   gRPC Port: $GRPC_PORT"

# Check if container already exists
if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    echo "⚠️  Container $CONTAINER_NAME already exists."
    
    # Check if it's running
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        echo "✅ Container is already running."
        docker ps -f name=$CONTAINER_NAME
        exit 0
    else
        echo "▶️  Starting existing container..."
        docker start $CONTAINER_NAME
        echo "✅ Container started successfully!"
        docker ps -f name=$CONTAINER_NAME
        exit 0
    fi
fi

# Create volume if it doesn't exist
if ! docker volume inspect $VOLUME_NAME > /dev/null 2>&1; then
    echo "📦 Creating Docker volume: $VOLUME_NAME"
    docker volume create $VOLUME_NAME
fi

# Start new container
echo "🔧 Creating and starting new Qdrant container..."
docker run -d \
  --name $CONTAINER_NAME \
  -p $HTTP_PORT:6333 \
  -p $GRPC_PORT:6334 \
  -e QDRANT__SERVICE__GRPC_PORT=6334 \
  -e QDRANT__SERVICE__HTTP_PORT=6333 \
  -v $VOLUME_NAME:/qdrant/storage \
  --restart unless-stopped \
  qdrant/qdrant:$QDRANT_VERSION

echo ""
echo "⏳ Waiting for Qdrant to become healthy..."
sleep 5

# Wait for health check
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:$HTTP_PORT/readyz > /dev/null 2>&1; then
        echo ""
        echo "✅ Qdrant is ready!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo ""
        echo "❌ Qdrant failed to become healthy after $MAX_RETRIES attempts"
        echo "   Check container logs: docker logs $CONTAINER_NAME"
        exit 1
    fi
done

echo ""
echo "📊 Qdrant Status:"
docker ps -f name=$CONTAINER_NAME

echo ""
echo "🔗 Connection Information:"
echo "   HTTP API: http://localhost:$HTTP_PORT"
echo "   gRPC API: http://localhost:$GRPC_PORT"
echo "   Dashboard: http://localhost:$HTTP_PORT/dashboard"
echo ""
echo "📝 Environment Variable:"
echo "   QDRANT_URL=http://localhost:$HTTP_PORT"
echo ""
echo "🔍 Useful Commands:"
echo "   View logs:    docker logs $CONTAINER_NAME"
echo "   Stop:         docker stop $CONTAINER_NAME"
echo "   Restart:      docker restart $CONTAINER_NAME"
echo "   Remove:       docker rm -f $CONTAINER_NAME"
echo "   Remove data:  docker volume rm $VOLUME_NAME"
echo ""
echo "✅ Qdrant is ready for use!"
