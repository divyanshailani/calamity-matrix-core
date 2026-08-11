#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Calamity Matrix — DigitalOcean Droplet Setup Script
#  Run once on a fresh Ubuntu 22.04 LTS droplet as root.
#  Usage: bash setup.sh
# ═══════════════════════════════════════════════════════════════

set -e  # Exit on any error

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Calamity Matrix — Server Setup Starting          ║"
echo "║     Ubuntu 22.04 LTS | DigitalOcean Droplet          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. System Update ──────────────────────────────────────────
echo "[1/8] Updating system packages..."
apt-get update -y && apt-get upgrade -y
apt-get install -y curl git ufw htop unzip nano

# ── 2. Install Docker ─────────────────────────────────────────
echo "[2/8] Installing Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Install Docker Compose plugin
apt-get install -y docker-compose-plugin
echo "      Docker version: $(docker --version)"
echo "      Compose version: $(docker compose version)"

# ── 3. Install Nginx ──────────────────────────────────────────
echo "[3/8] Installing Nginx..."
apt-get install -y nginx
systemctl enable nginx
systemctl start nginx

# ── 4. Install Certbot (SSL) ──────────────────────────────────
echo "[4/8] Installing Certbot for SSL..."
apt-get install -y certbot python3-certbot-nginx
echo "      Certbot installed. Run certbot after DNS is pointed."

# ── 5. Configure UFW Firewall ─────────────────────────────────
echo "[5/8] Configuring UFW firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
echo "      Firewall status:"
ufw status verbose

# ── 6. Create deploy user ─────────────────────────────────────
echo "[6/8] Creating calamity deploy user..."
if ! id "calamity" &>/dev/null; then
    useradd -m -s /bin/bash calamity
    usermod -aG docker calamity
    echo "      User 'calamity' created and added to docker group"
else
    echo "      User 'calamity' already exists"
fi

# ── 7. Clone Repository ───────────────────────────────────────
echo "[7/8] Cloning calamity-matrix-core repository..."
mkdir -p /opt/calamity
cd /opt/calamity

if [ ! -d "calamity-matrix-core" ]; then
    git clone https://github.com/divyanshailani/calamity-matrix-core.git
    echo "      Repository cloned to /opt/calamity/calamity-matrix-core"
else
    echo "      Repository already exists, pulling latest..."
    cd calamity-matrix-core && git pull && cd ..
fi

chown -R calamity:calamity /opt/calamity

# ── 8. Setup .env ─────────────────────────────────────────────
echo "[8/8] Environment setup..."
if [ ! -f "/opt/calamity/calamity-matrix-core/.env" ]; then
    cp /opt/calamity/calamity-matrix-core/.env.example \
       /opt/calamity/calamity-matrix-core/.env
    echo ""
    echo "  ⚠️  ACTION REQUIRED:"
    echo "  Edit /opt/calamity/calamity-matrix-core/.env with your secrets:"
    echo "  nano /opt/calamity/calamity-matrix-core/.env"
    echo ""
fi

# ── Setup auto-renewal for SSL ────────────────────────────────
echo "0 12 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" \
    > /etc/cron.d/certbot-renew

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                  Setup Complete! ✅                   ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Next steps:                                         ║"
echo "║  1. nano /opt/calamity/calamity-matrix-core/.env     ║"
echo "║  2. Point calamityai.tech DNS → this server IP       ║"
echo "║  3. Run: bash deploy/scripts/ssl.sh calamityai.tech  ║"
echo "║  4. Run: bash deploy/scripts/deploy.sh               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
