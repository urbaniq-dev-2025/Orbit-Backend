# Docker Setup Guide

This guide explains how to set up and run the Aubergine-Clarivo project using Docker.

## Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+
- Make (optional, for convenience commands)

## Quick Start

1. **Copy environment files:**
   ```bash
   cp env.example .env
   cp backend/env.example backend/.env
   cp backend/ingestion/env.example backend/ingestion/.env
   ```

2. **Update `.env` files** with your configuration values (especially `JWT_SECRET_KEY`)

3. **Start all services:**
   ```bash
   make start
   # or
   docker-compose up -d
   ```

4. **Verify services are running:**
   ```bash
   make docker-ps
   # or
   docker-compose ps
   ```

## Services

The Docker Compose setup includes:

- **PostgreSQL** (port 5432): Database for backend API
- **Backend API** (port 8001): Main FastAPI application
- **Ingestion Service** (port 8000): Document ingestion and processing service

## Available Commands

### Using Make (Recommended)

```bash
make help              # Show all available commands
make start             # Start all services
make stop              # Stop all services
make docker-build      # Build all Docker images
make docker-up         # Start services in detached mode
make docker-down       # Stop services
make docker-logs       # View logs from all services
make docker-logs-backend      # View backend API logs
make docker-logs-ingestion    # View ingestion service logs
make docker-restart    # Restart all services
make docker-clean      # Remove all containers, volumes, and images
make migrate           # Run database migrations
```

### Using Docker Compose Directly

```bash
docker-compose up -d              # Start services
docker-compose down               # Stop services
docker-compose logs -f            # View logs
docker-compose restart <service>  # Restart a specific service
docker-compose exec <service> sh  # Execute shell in container
```

## Development Mode

For development with hot-reload:

1. **Copy the override file:**
   ```bash
   cp docker-compose.override.yml.example docker-compose.override.yml
   ```

2. **Start services:**
   ```bash
   docker-compose up
   ```

The override file enables:
- Hot-reload for code changes
- Volume mounts for live code editing
- Debug logging

## Environment Variables

### Root `.env` (Docker Compose)
- `POSTGRES_USER`: PostgreSQL username (default: postgres)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: postgres)
- `POSTGRES_DB`: Database name (default: orbit)
- `BACKEND_PORT`: Backend API port (default: 8001)
- `INGESTION_PORT`: Ingestion service port (default: 8000)

### Backend API `.env`
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: Secret key for JWT tokens (⚠️ change in production!)
- `CORS_ORIGINS`: Allowed CORS origins (JSON array)

### Ingestion Service `.env`
- `APP_NAME`: Service name
- `ENVIRONMENT`: Environment (dev/prod)
- `DEBUG`: Enable debug mode

## Database Migrations

Run migrations after starting services:

```bash
make migrate
# or
docker-compose exec backend-api alembic upgrade head
```

Create a new migration:

```bash
make migrate-create MESSAGE="add new table"
# or
docker-compose exec backend-api alembic revision --autogenerate -m "add new table"
```

## Health Checks

All services include health checks. Check service health:

```bash
docker-compose ps
```

Services will show as "healthy" when ready.

## Troubleshooting

### Services won't start
- Check if ports are already in use: `lsof -i :8000 -i :8001 -i :5432`
- Verify `.env` files exist and are properly configured
- Check logs: `make docker-logs`

### Database connection errors
- Ensure PostgreSQL container is healthy: `docker-compose ps postgres`
- Verify `DATABASE_URL` in `backend/.env` matches PostgreSQL credentials
- Wait a few seconds after starting for PostgreSQL to initialize

### Permission errors
- Ensure Docker has proper permissions
- Check volume mounts in `docker-compose.yml`

### Clean restart
```bash
make docker-clean  # Remove everything
make docker-build  # Rebuild images
make start         # Start fresh
```

## Production Considerations

⚠️ **Before deploying to production:**

1. Change all default passwords and secrets
2. Use strong `JWT_SECRET_KEY` (generate with: `openssl rand -hex 32`)
3. Set `ENVIRONMENT=production`
4. Disable debug mode
5. Configure proper CORS origins
6. Set up proper volume backups for PostgreSQL
7. Use Docker secrets or external secret management
8. Configure resource limits in `docker-compose.yml`
9. Set up monitoring and logging aggregation
10. Use HTTPS/TLS for all services

## Virtual Environment Setup (Local Development)

For local development without Docker:

```bash
make setup
```

This will:
- Create virtual environments for backend and ingestion services
- Install dependencies
- Copy environment example files

Then activate virtual environments:

```bash
# Backend API
cd backend && source .venv/bin/activate

# Ingestion Service
cd backend/ingestion && source .venv/bin/activate
```

