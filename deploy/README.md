# Calamity Matrix — Production Deployment Guide

## Architecture

```
Internet
   │
   ▼
[Nginx :443]  ← SSL terminated here (Let's Encrypt)
   │
   ▼
[FastAPI :8000]  ← Calamity Matrix Core API
   │
   ▼
[Supabase pgvector]  ← RAG vector database (external)
   │
   ▼
[Hugging Face API]  ← Embeddings inference
```

## Stack

| Layer | Technology |
|---|---|
| **Server** | DigitalOcean Droplet (4GB RAM, 2 vCPU, Ubuntu 22.04) |
| **Container** | Docker + Docker Compose |
| **Reverse Proxy** | Nginx (alpine) |
| **SSL** | Let's Encrypt via Certbot |
| **Firewall** | UFW (ports 22, 80, 443 only) |
| **API** | FastAPI + Uvicorn |
| **Database** | Supabase pgvector (external) |
| **Domain** | calamityai.tech |

---

## First-Time Deployment

### Step 1 — Create DigitalOcean Droplet
- OS: Ubuntu 22.04 LTS
- Size: 4GB RAM / 2 vCPU ($24/month)
- Region: Bangalore (BLR1)
- Add your SSH key during creation

### Step 2 — SSH into the Droplet
```bash
ssh root@YOUR_DROPLET_IP
```

### Step 3 — Run the Setup Script
```bash
curl -fsSL https://raw.githubusercontent.com/divyanshailani/calamity-matrix-core/main/deploy/scripts/setup.sh | bash
```

### Step 4 — Configure Environment Variables
```bash
nano /opt/calamity/calamity-matrix-core/.env
```

Fill in all values (see `.env.example`):
```env
DATABASE_URL=postgresql://...  # Supabase Transaction Pooler URL
HF_TOKEN=hf_...
POSTGRES_PASSWORD=...
```

### Step 5 — Point DNS to Droplet
Go to your .TECH domain registrar and add:
```
A    calamityai.tech      →  YOUR_DROPLET_IP
A    www.calamityai.tech  →  YOUR_DROPLET_IP
```
Wait ~5 minutes for DNS propagation.

### Step 6 — Issue SSL Certificate
```bash
bash /opt/calamity/calamity-matrix-core/deploy/scripts/ssl.sh calamityai.tech
```

### Step 7 — Deploy
```bash
bash /opt/calamity/calamity-matrix-core/deploy/scripts/deploy.sh
```

---

## Updating the Deployment

Every time you push new code to GitHub, deploy with one command:
```bash
ssh root@YOUR_DROPLET_IP "bash /opt/calamity/calamity-matrix-core/deploy/scripts/deploy.sh"
```

---

## Useful Commands

```bash
# View running containers
docker ps

# View API logs (live)
docker logs calamity_api -f

# View Nginx logs
docker logs calamity_nginx -f

# Restart API only
docker compose -f deploy/docker-compose.prod.yml restart api

# Stop everything
docker compose -f deploy/docker-compose.prod.yml down

# Check server resources
htop

# Check disk usage
df -h

# Check firewall status
ufw status verbose
```

---

## Health Check

```bash
curl https://calamityai.tech/health
# Expected: {"status": "ok", ...}
```

---

## Cost Breakdown

| Resource | Cost |
|---|---|
| 4GB Droplet | $24/month |
| Domain (calamityai.tech) | FREE (GitHub Student Pack) |
| SSL Certificate | FREE (Let's Encrypt) |
| Supabase pgvector | FREE (free tier) |
| **Total** | **$24/month** |

> 💡 This is covered entirely by the DigitalOcean student credits ($46 total).
