#!/usr/bin/env bash
# =============================================================================
# RouterV — Cloud Monitoring: Alert Policies
# =============================================================================
# Applies all alert policy YAML files in monitoring/alerts/.
#
# Prerequisites:
#   1. Run setup_log_metrics.sh first (alert policies reference log metrics).
#   2. Create at least one notification channel and paste the ID below,
#      or add channels manually in the Console after applying policies.
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   export NOTIFICATION_CHANNEL="projects/$PROJECT_ID/notificationChannels/XXXXX"
#   bash monitoring/setup_alerts.sh
#
# Create a notification channel (email example):
#   gcloud beta monitoring channels create \
#     --display-name="RouterV Alerts" \
#     --type=email \
#     --channel-labels=email_address=you@example.com
# =============================================================================

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID before running this script}"

gcloud config set project "$PROJECT_ID"

ALERTS_DIR="$(dirname "$0")/alerts"
CHANNEL="${NOTIFICATION_CHANNEL:-}"

apply_policy() {
  local file="$1"
  local name
  name=$(basename "$file" .yaml)

  echo "Applying: $name"

  # If a notification channel is provided, inject it into the YAML on the fly.
  if [[ -n "$CHANNEL" ]]; then
    sed "s|notificationChannels: \[\]|notificationChannels:\n  - $CHANNEL|" "$file" \
      | gcloud monitoring policies create --policy-from-file=/dev/stdin 2>/dev/null \
      || echo "  → $name already exists or failed (check manually)"
  else
    gcloud monitoring policies create --policy-from-file="$file" 2>/dev/null \
      || echo "  → $name already exists or failed (check manually)"
  fi
}

for yaml_file in "$ALERTS_DIR"/*.yaml; do
  apply_policy "$yaml_file"
done

echo ""
echo "✓ Alert policies applied."
echo "  View at: https://console.cloud.google.com/monitoring/alerting?project=$PROJECT_ID"
if [[ -z "$CHANNEL" ]]; then
  echo ""
  echo "  ⚠  No NOTIFICATION_CHANNEL set — alerts exist but won't notify anyone."
  echo "     Create a channel and update policies in the Console, or re-run with:"
  echo "     export NOTIFICATION_CHANNEL=projects/$PROJECT_ID/notificationChannels/XXXXX"
fi
