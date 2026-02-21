#!/usr/bin/env bash
set -euo pipefail

IMAGE="carlasim/carla:0.9.15"
NAME="carla"

echo "[1/3] Pulling CARLA image: $IMAGE"
docker pull "$IMAGE"

echo "[2/3] Removing old container (if any)"
docker rm -f "$NAME" >/dev/null 2>&1 || true

echo "[3/3] Starting CARLA headless..."
docker run -d --name "$NAME" \
  --restart unless-stopped \
  --gpus all \
  -p 2000-2002:2000-2002 \
  "$IMAGE" \
  /bin/bash -lc "./CarlaUE4.sh -RenderOffScreen -carla-rpc-port=2000"

echo "✅ CARLA started."
echo "Logs: docker logs -f $NAME"