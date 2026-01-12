#!/usr/bin/env bash

set -euo pipefail

export APP_NAME=${APP_NAME:-"Clarivo Ingestion Service"}
export ENVIRONMENT=${ENVIRONMENT:-"dev"}
export DEBUG=${DEBUG:-"true"}

exec uvicorn clarivo_ingestion.main:app --host 0.0.0.0 --port "${PORT:-8000}"

