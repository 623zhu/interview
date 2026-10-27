#!/bin/sh
set -e
alembic upgrade head
python scripts/import_topic_cards.py
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips="*"
