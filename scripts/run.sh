#!/usr/bin/env bash
set -euo pipefail

# Ensure the .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env missing, creating from .env.example"
    cp .env.example .env
fi

docker compose up --build
