#!/bin/bash
# DigitalOcean App Platform Production Startup Script
# This script is used as the Run Command in App Platform

# Exit on error
set -e

echo "🚀 Starting BabbleBeaver on DigitalOcean App Platform..."

# Check if required environment variables are set
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  WARNING: DATABASE_URL not set. Using SQLite (not recommended for production)"
fi

# Determine number of workers (default to 2 if WEB_CONCURRENCY not set)
WORKERS=${WEB_CONCURRENCY:-2}

# Get port from App Platform or default to 8080
PORT=${PORT:-8080}

echo "✓ Port: $PORT"
echo "✓ Workers: $WORKERS"
echo "✓ Database: ${DATABASE_URL:0:20}..." # Only show first 20 chars for security

# Run database migrations if needed (add migration script here if you have one)
# python tools/migrate_database.py --force

# Start Uvicorn with production settings
# --host 0.0.0.0: Listen on all interfaces
# --port: Use App Platform port
# --workers: Number of worker processes
# --no-access-log: Reduce log noise in production
# --log-level: Set to info for production
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level info \
    --no-access-log
