#!/usr/bin/env bash
# Starts Cloud SQL Auth Proxy for local dev against the prod Cloud SQL instance.
# After running, set: DATABASE_URL=postgresql+asyncpg://postgres:<PASSWORD>@localhost:5432/routersvc
#
# Prerequisites:
#   brew install cloud-sql-proxy   (or download from https://cloud.google.com/sql/docs/postgres/sql-proxy)
#   gcloud auth application-default login

set -euo pipefail

gcloud config set project fair-myth-471110-j2 --quiet

INSTANCE="fair-myth-471110-j2:asia-south1:api-prod-pg"
PORT="${CLOUD_SQL_PORT:-5432}"

echo "Starting Cloud SQL Auth Proxy → ${INSTANCE} on localhost:${PORT}"
echo "Press Ctrl+C to stop."

exec cloud-sql-proxy --port="${PORT}" "${INSTANCE}"
