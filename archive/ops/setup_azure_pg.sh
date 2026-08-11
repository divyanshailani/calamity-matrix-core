#!/bin/bash
set -e

echo "[*] Initializing 4GB Swap Shield..."
sudo fallocate -l 4G /swapfile || true
sudo chmod 600 /swapfile
sudo mkswap /swapfile || true
sudo swapon /swapfile || true
grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

echo "[*] Adding PostgreSQL 18 APT Repositories..."
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt install -y curl ca-certificates lsb-release build-essential git
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
sudo sh -c 'echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

echo "[*] Installing PostgreSQL 18 Core Engine..."
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt -y install postgresql-18 postgresql-client-18 postgresql-server-dev-18

echo "[*] Compiling pgvector from source..."
cd /tmp
rm -rf pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

echo "[*] Applying Bare-Metal Thermodynamics (1GB RAM Profile)..."
PG_CONF="/etc/postgresql/18/main/postgresql.conf"
sudo sed -i "s/^[#]*\s*shared_buffers\s*=\s*.*/shared_buffers = 256MB/" $PG_CONF
sudo sed -i "s/^[#]*\s*work_mem\s*=\s*.*/work_mem = 16MB/" $PG_CONF
sudo sed -i "s/^[#]*\s*max_connections\s*=\s*.*/max_connections = 50/" $PG_CONF
sudo sed -i "s/^[#]*\s*listen_addresses\s*=\s*.*/listen_addresses = '*'/" $PG_CONF

echo "[*] Opening Network Access for Orchestrator..."
PG_HBA="/etc/postgresql/18/main/pg_hba.conf"
grep -q "0.0.0.0/0" $PG_HBA || echo "host    all             all             0.0.0.0/0               md5" | sudo tee -a $PG_HBA

echo "[*] Restarting Engine..."
sudo systemctl restart postgresql
echo "[+] Matrix Initialized Successfully. PG18 Online."
