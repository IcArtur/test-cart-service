#!/usr/bin/env bash
set -euo pipefail
docker compose run --rm web sh -c "python manage.py migrate && python -m pytest"
