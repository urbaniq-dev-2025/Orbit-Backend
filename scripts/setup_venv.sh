#!/bin/bash
# Setup script for creating virtual environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Setting up virtual environments for Aubergine-Clarivo project..."

# Backend API virtual environment
if [ ! -d "$PROJECT_ROOT/backend/.venv" ]; then
    echo "📦 Creating virtual environment for backend API..."
    cd "$PROJECT_ROOT/backend"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✅ Backend API virtual environment created"
else
    echo "ℹ️  Backend API virtual environment already exists"
fi

# Ingestion service virtual environment
if [ ! -d "$PROJECT_ROOT/backend/ingestion/.venv" ]; then
    echo "📦 Creating virtual environment for ingestion service..."
    cd "$PROJECT_ROOT/backend/ingestion"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✅ Ingestion service virtual environment created"
else
    echo "ℹ️  Ingestion service virtual environment already exists"
fi

# Copy env.example files if .env doesn't exist
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "📝 Copying env.example to .env..."
    cp "$PROJECT_ROOT/env.example" "$PROJECT_ROOT/.env"
    echo "⚠️  Please update .env with your configuration values"
fi

if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
    echo "📝 Copying backend/env.example to backend/.env..."
    cp "$PROJECT_ROOT/backend/env.example" "$PROJECT_ROOT/backend/.env"
    echo "⚠️  Please update backend/.env with your configuration values"
fi

if [ ! -f "$PROJECT_ROOT/backend/ingestion/.env" ]; then
    echo "📝 Copying backend/ingestion/env.example to backend/ingestion/.env..."
    cp "$PROJECT_ROOT/backend/ingestion/env.example" "$PROJECT_ROOT/backend/ingestion/.env"
    echo "⚠️  Please update backend/ingestion/.env with your configuration values"
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "To activate backend API virtual environment:"
echo "  cd backend && source .venv/bin/activate"
echo ""
echo "To activate ingestion service virtual environment:"
echo "  cd backend/ingestion && source .venv/bin/activate"
echo ""
echo "To start services with Docker:"
echo "  docker-compose up -d"
echo ""

