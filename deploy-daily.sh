#!/bin/bash
# Daily deployment script for Backcast
# Automatically pulls latest from main and runs the existing redeploy script

set -e  # Exit on error

LOG_FILE="/home/nicola/backcast/logs/deploy-daily.log"
REDEPLOY_SCRIPT="/home/nicola/backcast/deploy/scripts/redeploy.sh"
PROJECT_ROOT="/home/nicola/backcast"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Starting daily deployment ==="

# Check if redeploy script exists
if [ ! -f "$REDEPLOY_SCRIPT" ]; then
    log "ERROR: Redeploy script not found at $REDEPLOY_SCRIPT"
    exit 1
fi

# Make sure redeploy script is executable
chmod +x "$REDEPLOY_SCRIPT"

# Run the redeploy script with options for non-interactive mode:
# -y: Auto-confirm all prompts (non-interactive)
# -b main: Pull from main branch
log "Running redeploy script (branch: main, non-interactive mode)..."

if "$REDEPLOY_SCRIPT" -y -b main >> "$LOG_FILE" 2>&1; then
    log "=== Deployment completed successfully ==="
    exit 0
else
    log "ERROR: Deployment failed. Check logs for details."
    exit 1
fi
