#!/usr/bin/env bash
set -euo pipefail

NAME="carla"
docker rm -f "$NAME" >/dev/null 2>&1 || true
echo "🛑 CARLA container removed."