#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Calamity Matrix — SSL Certificate Setup
#  Run AFTER DNS is pointed to your Droplet IP.
#  Usage: bash deploy/scripts/ssl.sh calamityai.tech
# ═══════════════════════════════════════════════════════════════

set -e

DOMAIN=${1:-"api.calamityai.tech"}
EMAIL="divyanshailani@gmail.com"

echo ""
echo "🔐 Setting up SSL for: $DOMAIN"
echo ""

# Stop Nginx temporarily for standalone cert issuance
echo "[1/3] Stopping Nginx temporarily..."
systemctl stop nginx

# Issue certificate
echo "[2/3] Issuing Let's Encrypt certificate..."
certbot certonly --standalone \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive

# Restart Nginx with SSL
echo "[3/3] Restarting Nginx with SSL..."
systemctl start nginx

echo ""
echo "✅ SSL certificate issued for $DOMAIN"
echo "   Certificate path: /etc/letsencrypt/live/$DOMAIN/"
echo "   Auto-renewal: configured via cron"
echo ""
