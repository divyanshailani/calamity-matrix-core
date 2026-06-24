#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Calamity Matrix — Deploy / Update Script
#  Run on the DigitalOcean Droplet to deploy or update.
#  Usage: bash deploy/scripts/deploy.sh
# ═══════════════════════════════════════════════════════════════

set -e

REPO_DIR="/opt/calamity/calamity-matrix-core"
COMPOSE_FILE="$REPO_DIR/deploy/docker-compose.prod.yml"

echo ""
echo "🚀 Calamity Matrix — Deploying..."
echo "   Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ── 1. Pull latest code ───────────────────────────────────────
echo "[1/4] Pulling latest code from GitHub..."
cd "$REPO_DIR"
git pull origin main
echo "      ✅ Code updated: $(git log -1 --format='%h %s')"

# ── 2. Build Docker image ─────────────────────────────────────
echo "[2/4] Building Docker image..."
docker compose -f "$COMPOSE_FILE" build --no-cache api
echo "      ✅ Image built"

# ── 3. Restart containers ─────────────────────────────────────
echo "[3/4] Restarting containers..."
docker compose -f "$COMPOSE_FILE" up -d --force-recreate
echo "      ✅ Containers restarted"

# ── 4. Health check ───────────────────────────────────────────
echo "[4/4] Running health check..."
sleep 5  # Give the API time to boot

if curl -sf http://localhost:8000/health > /dev/null; then
    echo "      ✅ API is healthy!"
else
    echo "      ❌ Health check FAILED. Checking logs..."
    docker compose -f "$COMPOSE_FILE" logs api --tail=50
    exit 1
fi

# ── Cleanup old images ────────────────────────────────────────
echo "      Cleaning up old Docker images..."
docker image prune -f > /dev/null 2>&1

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║          Deployment Complete! ✅              ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  API:   https://calamityai.tech              ║"
echo "║  Health: https://calamityai.tech/health      ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
