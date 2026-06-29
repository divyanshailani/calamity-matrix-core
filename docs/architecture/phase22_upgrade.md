# Calamity Matrix Core: Phase 22 Architecture Report

This document serves as the official post-mortem and architectural summary of **Phase 22**, which focused on migrating the data layer away from Supabase to a custom Azure Bare Metal instance, establishing a Tri-API autonomous crawler, and building a secure GitHub Actions pipeline.

---

## 1. The Azure pgvector Migration (Bare Metal Provisioning)
Due to scale and cost constraints with Supabase, we migrated the database infrastructure to a self-hosted Azure Ubuntu VM (`helpvm2`).

### Engineering Highlights
* **Thermodynamics & Resource Tuning:** Because the VM operates on just 1GB of RAM, we provisioned a **4GB Swap Shield** (`fallocate -l 4G /swapfile`) to prevent Out-Of-Memory (OOM) kernel panics during heavy embedding operations. We also tuned `postgresql.conf` for a low-memory profile (`shared_buffers = 256MB`, `work_mem = 16MB`, `max_connections = 50`).
* **Source Compilation:** PostgreSQL 18 introduced signature changes (e.g., `vacuum_delay_point`), which broke standard package manager installations of the pgvector extension. We bypassed this by cloning the `pgvector` v0.8.0 repository and compiling it directly from source (`make && make install`).
* **Schema Re-initialization:** We recreated the `disaster_events` table utilizing `pgvector`'s `vector(1024)` type to store the dense embeddings required for the RAG (Retrieval-Augmented Generation) pipeline.

---

## 2. Tri-API Autonomous Crawler & Pre-Fetch Shield
To keep the Calamity Matrix up-to-date with current global events (post-2000), we built `scripts/live_ingestion.py`, an autonomous web crawler that aggregates real-time data from three major endpoints.

### Data Sources
1. **USGS (Earthquakes):** Minimum magnitude 4.5 thresholds.
2. **NASA EONET (Wildfires, Storms, Volcanoes):** Geospatial bounding data.
3. **ReliefWeb (Humanitarian SITREPs):** Complex narrative disaster reports.

### Compute Optimization & Database Armor
* **Pre-Fetch Shield:** Generating embeddings via Hugging Face (`BAAI/bge-large-en-v1.5`) is computationally expensive. To optimize this, the script first queries the Azure database to fetch all existing event URLs from the last 7 days. Only strictly *new* URLs are passed to the embedding model.
* **Database Armor:** We enforced a `UNIQUE` constraint on the `url` column in the database and utilized `ON CONFLICT (url) DO NOTHING` in our `execute_values` bulk insert. This ensures database entropy is protected from duplicates in the event of pipeline retries or overlapping fetches.
* **Tone Synthesis:** To match the established persona, we formatted the ingested data into cold, objective SITREP narratives.

---

## 3. GitHub Actions & The DigitalOcean Proxy
Rather than running the massive Python ingestion script directly on GitHub Actions runners—which would require installing heavy ML dependencies and exposing the raw Azure database credentials—we engineered a serverless proxy pattern.

* **The Proxy Endpoint:** We added a new POST endpoint (`/api/v1/trigger_ingestion`) to the DigitalOcean FastAPI orchestrator.
* **Background Tasks:** To prevent the HTTP request from timing out during the heavy embedding phase, FastAPI immediately returns `HTTP 200 OK` and executes the ingestion script via Starlette's `BackgroundTasks`.
* **Security:** The endpoint is shielded by a hardcoded secret header (`X-Ingestion-Secret`).
* **The CRON Trigger:** A lightweight GitHub Actions workflow (`live_ingestion.yml`) runs every Sunday at midnight. It simply sends a `curl` request containing the secret key to the DigitalOcean proxy, offloading all compute to the Droplet.

---

## 4. Incident Log: Debugging the Deployment
The deployment phase encountered a cascading series of infrastructural failures that required deep systems debugging. 

> [!WARNING]
> **Issue 1: Docker Build Omission (ModuleNotFoundError)**
> **Symptom:** The proxy endpoint failed to execute the ingestion script, crashing with `ModuleNotFoundError: No module named 'scripts.live_ingestion'`.
> **Root Cause:** The production `Dockerfile` had a hardcoded `COPY scripts/api_orchestrator.py` directive, completely ignoring the new `live_ingestion.py` file.
> **Resolution:** Modified the Dockerfile locally to `COPY scripts/ ./scripts/`, pushed the code, and rebuilt the `calamity_api` Docker image on the Droplet.

> [!CAUTION]
> **Issue 2: The libpq Connection Refused (Abstract Unix Socket Bug)**
> **Symptom:** The API container entered a crash-loop, throwing `psycopg2.OperationalError: connection to server on socket "@@###!!!Global@40.81.234.20/.s.PGSQL.5432" failed: Connection refused`.
> **Root Cause:** The database password (`8765@@@###!!!Global`) contained unescaped `@` symbols. When parsed by the underlying C library (`libpq`), it incorrectly split the string at the *first* `@`. It treated `@@###!!!Global@40.81.234.20` as the hostname. Because it began with an `@`, PostgreSQL treated it as an Abstract Unix Domain Socket rather than an IP address, instantly throwing a connection refused error.
> **Resolution:** We URL-encoded the special characters directly in the DigitalOcean `.env` file (`%40` for `@`, `%23` for `#`, etc.).

> [!IMPORTANT]
> **Issue 3: Nginx 502 Bad Gateway (Azure NSG Block)**
> **Symptom:** After fixing the database URL, the container stopped crashing but began hanging indefinitely. Hitting the endpoint via HTTPS returned a `502 Bad Gateway`. Running a deep `nc -vz 40.81.234.20 5432` ping from the Droplet revealed 100% packet loss.
> **Root Cause:** The FastAPI `lifespan` function was attempting to establish the TCP connection pool, but the Azure Network Security Group (NSG) firewall was dropping all inbound packets on port `5432`.
> **Resolution:** Navigated the Azure Portal and added a manual "Inbound Port Rule" for TCP `5432` from `Source: Any`. Once applied, the TCP handshake succeeded, the `lifespan` unblocked, and the API successfully booted.
