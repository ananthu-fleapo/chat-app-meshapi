#!/usr/bin/env bash
# Exports the full PostgreSQL schema (DDL only, no data) to a SQL file.
#
# Usage:
#   ./scripts/export_schema.sh                        # uses DATABASE_URL from env or .env
#   ./scripts/export_schema.sh --proxy                # starts Cloud SQL Auth Proxy first
#   ./scripts/export_schema.sh --out schema.sql       # custom output path
#
# Prerequisites:
#   pg_dump (PostgreSQL client tools) OR Docker (used as fallback if pg_dump not on PATH)
#   For --proxy: cloud-sql-proxy + gcloud auth application-default login

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

USE_PROXY=false
OUTPUT_FILE="${BACKEND_DIR}/schema.sql"
PROXY_PID=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --proxy)   USE_PROXY=true; shift ;;
    --out)     OUTPUT_FILE="$2"; shift 2 ;;
    *)         echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# Load .env if DATABASE_URL not already set
if [[ -z "${DATABASE_URL:-}" && -f "${BACKEND_DIR}/.env" ]]; then
  set -o allexport
  # shellcheck source=/dev/null
  source "${BACKEND_DIR}/.env"
  set +o allexport
fi

cleanup() {
  if [[ -n "$PROXY_PID" ]]; then
    echo "Stopping Cloud SQL Auth Proxy (PID $PROXY_PID)..."
    kill "$PROXY_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ "$USE_PROXY" == true ]]; then
  INSTANCE="fair-myth-471110-j2:asia-south1:api-prod-pg"
  PROXY_PORT="${CLOUD_SQL_PORT:-5432}"

  gcloud config set project fair-myth-471110-j2 --quiet

  echo "Starting Cloud SQL Auth Proxy → ${INSTANCE} on port ${PROXY_PORT}..."
  cloud-sql-proxy --port="${PROXY_PORT}" "${INSTANCE}" &
  PROXY_PID=$!

  # Wait for proxy to be ready
  for i in $(seq 1 15); do
    if pg_isready -h localhost -p "${PROXY_PORT}" -q 2>/dev/null; then
      break
    fi
    sleep 1
    if [[ $i -eq 15 ]]; then
      echo "ERROR: Cloud SQL Proxy did not become ready in time." >&2
      exit 1
    fi
  done
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set. Set it in .env or export it before running." >&2
  exit 1
fi

# pg_dump needs a standard postgres:// URL (strip asyncpg driver prefix if present)
PG_URL="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql://}"
PG_URL="${PG_URL/postgresql+psycopg2:\/\//postgresql://}"

OUTPUT_DIR="$(dirname "$OUTPUT_FILE")"
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$(cd "$OUTPUT_DIR" && pwd)/$(basename "$OUTPUT_FILE")"
echo "Exporting schema to: $OUTPUT_FILE"

PG_DUMP_ARGS=(--schema-only --no-owner --no-privileges --no-comments "$PG_URL")

if command -v pg_dump &>/dev/null; then
  pg_dump "${PG_DUMP_ARGS[@]}" > "$OUTPUT_FILE"
elif command -v docker &>/dev/null; then
  echo "(pg_dump not found — using Docker postgres:18-alpine)"
  docker run --rm postgres:18-alpine pg_dump "${PG_DUMP_ARGS[@]}" > "$OUTPUT_FILE"
else
  echo "ERROR: Neither pg_dump nor docker is available. Install PostgreSQL client tools or Docker." >&2
  exit 1
fi

echo "Done. $(wc -l < "$OUTPUT_FILE") lines written."
