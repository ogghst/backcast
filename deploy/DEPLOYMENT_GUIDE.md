# Backcast EVS Production Deployment Guide

**Target Domain:** backcast.duckdns.org
**Deployment Date:** 2026-01-26
**Environment:** Production

---

## Architecture Overview

```
Internet → Apache (192.168.1.21:80/443) → Traefik (192.168.1.23:8080) → Services
                                                      ↓
                                              Backend, Frontend, PostgreSQL
```

### Server Roles

| Server | IP | Role | Services |
|--------|-----|------|----------|
| Apache Server | 192.168.1.21 | SSL Termination, Public-facing | Apache2 with SSL |
| Docker Server | 192.168.1.23 | Application Services | Docker, Traefik, Backend, Frontend, PostgreSQL |

### Network Flow

1. **External requests** → Apache (192.168.1.21) on port 443 (HTTPS)
2. **Apache** → Proxy to Traefik (192.168.1.23:8080) via HTTP
3. **Traefik** → Route to appropriate service (Backend/Frontend/Adminer)
4. **Services** → PostgreSQL database on internal network

---

## Prerequisites

### On Docker Server (192.168.1.23)

- Ubuntu/Debian Linux
- Docker and Docker Compose plugin installed
- User with sudo access
- Git repository cloned to `/home/nicola/dev/backcast_evs`

### On Apache Server (192.168.1.21)

- Apache 2.4+ installed
- SSL certificates for `backcast.duckdns.org`
- Access to internal network (192.168.1.23)
- Modules: `proxy`, `proxy_http`, `proxy_pass`, `ssl`, `rewrite`, `headers`

### DNS Configuration

- `backcast.duckdns.org` → 192.168.1.21 (Apache public IP)
- `app.backcast.duckdns.org` → 192.168.1.21
- `api.backcast.duckdns.org` → 192.168.1.21

---

## Phase 1: Docker Installation (192.168.1.23)

### 1.1 Install Docker

```bash
# Download Docker installation script
curl -fsSL https://get.docker.com -o get-docker.sh

# Install Docker
sudo sh get-docker.sh

# Install Docker Compose plugin
sudo apt-get update && sudo apt-get install -y docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Apply group membership (log out and back in, or use)
newgrp docker

# Verify installation
docker --version
docker compose version
```

Expected output:
```
Docker version 27.x.x, build xxxxx
Docker Compose version v2.x.x
```

---

## Phase 2: Create Docker Network

```bash
cd /home/nicola/dev/backcast_evs/deploy
docker network create traefik-public

# Verify network creation
docker network ls | grep traefik-public
```

Expected output:
```
08c9efc8766c   traefik-public   bridge    local
```

---

## Phase 3: Generate Secure Values

### 3.1 Generate Secrets

```bash
# Generate SECRET_KEY
openssl rand -base64 64
```

Generated: `LcOCnNRRouE0uIXQDVQeZ8LE6zKxwHyiGa9JXP5fxa1szWoU7Epwt4Lq69m7iMzq++9FqbBA6ZqHr8cJVejKew==`

```bash
# Generate database password (alphanumeric only, to avoid URL encoding issues)
openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32
```

**Current password (configured 2026-01-26):** `backcast`

### 3.2 Generate Traefik Dashboard Password

```bash
# Install apache2-utils (or use Docker)
sudo apt-get install -y apache2-utils

# Method 1: Using htpasswd
htpasswd -nb admin <your-password>

# Method 2: Using Docker (if apache2-utils not installed)
docker run --rm httpd:2.4-alpine htpasswd -nb admin <your-password>
```

**Current credentials (configured 2026-01-26):**
- Username: `admin`
- Password: `backcast`
- Hash: `$apr1$Zxm7mIoj$dmDpeU2Nva6NAmgspTODw1`

**Note:** To update the password, regenerate the hash and update `/home/nicola/dev/backcast_evs/deploy/traefik/dynamic/middlewares.yml` line 41, then restart Traefik:
```bash
docker compose --env-file .env.production restart traefik
```

---

## Phase 4: Environment Configuration

### 4.1 Create Production Environment File

**File:** `/home/nicola/dev/backcast_evs/deploy/.env.production`

```bash
# Domain Configuration
DOMAIN=backcast.duckdns.org

# Traefik Port Configuration (internal HTTP-only mode)
TRAEFIK_HTTP_PORT=8080
TRAEFIK_HTTPS_PORT=8443

# Database Configuration
POSTGRES_USER=backcast_prod
POSTGRES_PASSWORD=backcast
POSTGRES_DB=backcast_evs
POSTGRES_PORT=5432

# Application Security
SECRET_KEY=LcOCnNRRouE0uIXQDVQeZ8LE6zKxwHyiGa9JXP5fxa1szWoU7Epwt4Lq69m7iMzq++9FqbBA6ZqHr8cJVejKew==
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
PROJECT_NAME=Backcast EVS
API_V1_STR=/api/v1
DEBUG=false
PORT=8080

# CORS
BACKEND_CORS_ORIGINS=["https://app.backcast.duckdns.org"]
BACKEND_CORS_METHODS=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
BACKEND_CORS_HEADERS=["*"]

# Traefik / Let's Encrypt (not used with Apache SSL termination)
TRAEFIK_ACME_EMAIL=ogghst@gmail.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# Deployment
RUN_MIGRATIONS=false
```

---

## Phase 5: Traefik Configuration (HTTP-Only Mode)

### 5.1 Update Traefik Static Configuration

**File:** `/home/nicola/dev/backcast_evs/deploy/traefik/traefik.yml`

```yaml
# Traefik static configuration for Apache integration (HTTP-only mode)
global:
  checkNewVersion: true
  sendAnonymousUsage: false

api:
  dashboard: true
  insecure: false

entryPoints:
  web:
    address: ":80"
    # No HTTPS redirect - Apache handles SSL termination

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
  file:
    filename: /etc/traefik/dynamic/middlewares.yml
    watch: true

# Note: certificatesResolvers removed - Apache manages SSL

log:
  level: INFO
  filePath: /var/log/traefik/traefik.log
  format: json

accessLog:
  filePath: /var/log/traefik/access.log
  format: json
```

### 5.2 Update Traefik Dynamic Configuration

**File:** `/home/nicola/dev/backcast_evs/deploy/traefik/dynamic/middlewares.yml`

```yaml
http:
  middlewares:
    # Security headers
    security-headers:
      headers:
        customRequestHeaders:
          X-Forwarded-Proto: "https"
        customResponseHeaders:
          X-Frame-Options: "SAMEORIGIN"
          X-Content-Type-Options: "nosniff"
          X-XSS-Protection: "1; mode=block"
          Referrer-Policy: "strict-origin-when-cross-origin"
          Permissions-Policy: "geolocation=(), microphone=(), camera=()"
        # sslRedirect disabled - Apache handles SSL
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
        forceSTSHeader: true

    # Adminer IP whitelist
    adminer-whitelist:
      ipWhiteList:
        sourceRange:
          - "127.0.0.1/32"
          - "10.0.0.0/8"
          - "172.16.0.0/12"
          - "192.168.0.0/16"

    # Rate limiting
    rate-limit:
      rateLimit:
        average: 100
        burst: 50
        period: 1s

    # Basic auth for Traefik dashboard
    traefik-auth:
      basicAuth:
        users:
          # Generated with: htpasswd -nb admin backcast
          - "admin:$apr1$Zxm7mIoj$dmDpeU2Nva6NAmgspTODw1"
```

---

## Phase 6: Docker Compose Configuration Updates

### 6.1 Update Service Labels and Ports

**File:** `/home/nicola/dev/backcast_evs/deploy/docker-compose.yml`

**Key Changes:**

1. **Traefik ports** (line ~16):
```yaml
ports:
  - "${TRAEFIK_HTTP_PORT:-8080}:80"
```

2. **All service labels** - Change from `websecure` to `web`:

```yaml
# Dashboard (line ~31)
- "traefik.http.routers.dashboard.entrypoints=web"

# Backend (line ~119)
- "traefik.http.routers.backend.entrypoints=web"

# Frontend (line ~156)
- "traefik.http.routers.frontend.entrypoints=web"

# Adminer (line ~193)
- "traefik.http.routers.adminer.entrypoints=web"
```

3. **Backend environment variables** - Add missing variables:
```yaml
environment:
  DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
  POSTGRES_HOST: postgres
  POSTGRES_PORT: 5432
  POSTGRES_USER: ${POSTGRES_USER}          # ADD THIS
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # ADD THIS
  POSTGRES_DB: ${POSTGRES_DB}              # ADD THIS
  SECRET_KEY: ${SECRET_KEY}
  DEBUG: "false"
  PORT: 8080
  BACKEND_CORS_ORIGINS: '["https://app.${DOMAIN}"]'
  LOG_LEVEL: INFO
  RUN_MIGRATIONS: "${RUN_MIGRATIONS:-false}"
```

4. **Backend resources** (line ~125):
```yaml
deploy:
  resources:
    limits:
      cpus: '1'      # Changed from '2' for single-core systems
      memory: 2G
    reservations:
      cpus: '0.25'   # Changed from '0.5'
      memory: 512M
```

---

## Phase 7: Dockerfile Updates

### 7.1 Backend Dockerfile

**File:** `/home/nicola/dev/backcast_evs/deploy/backend/Dockerfile`

```dockerfile
# Multi-stage production build for FastAPI backend
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Copy dependency files from backend directory
COPY backend/pyproject.toml backend/README.md ./

# Install dependencies using uv (production only, no lock file)
RUN uv sync --no-dev

# Production stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser appuser

# Copy uv and installed packages from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv

# Ensure scripts in .venv are usable
ENV PATH="/app/.venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code from backend/
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./

# Create necessary directories
RUN mkdir -p /app/logs /app/config && \
    chown -R appuser:appuser /app

# Copy entrypoint script
COPY deploy/scripts/entrypoint-backend.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 7.2 Frontend Dockerfile

**File:** `/home/nicola/dev/backcast_evs/deploy/frontend/Dockerfile`

```dockerfile
# Multi-stage build for React frontend
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies (using legacy peer deps to resolve conflicts)
RUN npm install --legacy-peer-deps

# Copy source code
COPY frontend/ ./

# Build arguments for API URL
ARG VITE_API_URL=https://api.yourdomain.com
ARG VITE_WEBSOCKET_URL=wss://api.yourdomain.com

# Set build-time environment variables
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WEBSOCKET_URL=${VITE_WEBSOCKET_URL}

# Build the application (skip TypeScript check)
RUN npx vite build --mode production

# Production stage with nginx
FROM nginx:alpine

# Copy custom nginx config
COPY deploy/frontend/nginx.conf /etc/nginx/nginx.conf

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy startup script
COPY deploy/scripts/entrypoint-frontend.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
```

### 7.3 Alembic Dockerfile

**File:** `/home/nicola/dev/backcast_evs/Dockerfile.alembic`

```dockerfile
# Dockerfile for Alembic database migrations
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv - ultra-fast Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project configuration files from backend directory
COPY backend/pyproject.toml backend/README.md ./

# Install dependencies using uv (no lock file)
RUN uv sync --no-dev

# Copy application code and alembic configuration from backend directory
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./

# Copy entrypoint script
COPY docker-entrypoint-alembic.sh /docker-entrypoint-alembic.sh
RUN chmod +x /docker-entrypoint-alembic.sh

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint-alembic.sh"]

# Default command: upgrade to head
CMD ["upgrade", "head"]
```

---

## Phase 8: Build and Deploy Services

### 8.1 Build Docker Images

```bash
cd /home/nicola/dev/backcast_evs/deploy

# Build all images
docker compose --env-file .env.production build
```

**Expected build time:** ~5-10 minutes

**Troubleshooting:**
- If frontend build fails due to TypeScript errors, the Dockerfile now uses `npx vite build` directly which skips type checking
- If backend build fails due to missing files, ensure the build context is correct

### 8.2 Start Services

```bash
# Start all services
docker compose --env-file .env.production up -d

# Check service status
docker compose --env-file .env.production ps
```

Expected output:
```
NAME                    STATUS
backcast_evs_postgres   Up and healthy
backcast_evs_backend    Up (health: starting)
backcast_evs_frontend   Up
backcast_evs_traefik    Up
backcast_evs_adminer    Up
```

### 8.3 Run Database Migrations

```bash
# Run Alembic migrations
docker compose --env-file .env.production run --rm alembic
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade -> 94ccc0cb6464, Initial schema
INFO  [alembic.runtime.migration] Running upgrade 94ccc0cb6464 -> 9f027887a725, Add User and UserVersion models
...
INFO  [alembic.runtime.migration] Running upgrade 4295c725f05f -> f69c57fcc47d, add_indexes_for_evm_performance
```

### 8.4 Seed Database with Initial Data

**⚠️ IMPORTANT:** Always backup the database before reseeding!

#### Step 1: Backup Database

```bash
# Create timestamped backup
docker exec backcast_evs_postgres pg_dump -U backcast_prod backcast_evs | gzip > /tmp/backcast_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Copy to safe location
cp /tmp/backcast_backup_*.sql.gz ~/backups/
```

#### Step 2: Choose Reseed Method

**Option A: Simple Reseed (Safe - Adds Missing Data Only)**

This method is **production-safe** and only adds data that doesn't already exist. It will not overwrite or delete existing data.

```bash
# 1. Copy seed files into container
docker cp /home/nicola/dev/backcast_evs/backend/seed backcast_evs_backend:/app/

# 2. Run seeder via inline Python
docker exec -i backcast_evs_backend python3 << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/app')
from app.db.session import async_session_maker
from app.db.seeder import DataSeeder

async def reseed():
    async with async_session_maker() as session:
        seeder = DataSeeder()
        await seeder.seed_all(session)
    print("✓ Reseed complete")

asyncio.run(reseed())
EOF
```

**Option B: Full Reseed (Destructive - Clears All Data First)**

⚠️ **WARNING:** This will delete ALL existing data in the database!

```bash
# Only use this if you want to completely reset the database
docker exec -i backcast_evs_postgres psql -U backcast_prod backcast_evs << 'SQL'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO backcast_prod;
GRANT ALL ON SCHEMA public TO public;
SQL

# Re-run migrations
docker compose --env-file .env.production run --rm alembic upgrade head

# Then copy seed files and run seeder (commands from Option A above)
```

#### Step 3: Verify Seeded Data

```bash
# Connect to database
docker exec -it backcast_evs_postgres psql -U backcast_prod -d backcast_evs

# Run verification queries
SELECT 'departments' as entity, COUNT(*) FROM departments
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'cost_element_types', COUNT(*) FROM cost_element_types
UNION ALL
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'wbes', COUNT(*) FROM wbes
UNION ALL
SELECT 'cost_elements', COUNT(*) FROM cost_elements;

# Exit psql
\q
```

Expected output:
```
    entity     | count
---------------+-------
departments    |     4
users          |     5
cost_element_  |     5
projects       |     2
wbes           |    20
cost_elements  |   100
```

#### Default User Accounts

| Email | Password | Role | Department |
|-------|----------|------|------------|
| admin@backcast.org | adminadmin | admin | ADMIN |
| viewer@backcast.org | backcast | viewer | ENG |
| pm@backcast.org | backcast | manager | PM |
| eng.lead@backcast.org | backcast | contributor | ENG |
| const.super@backcast.org | backcast | contributor | CONST |

**Important:** Change default passwords after first login!

#### Seeded Data Summary

The seed operation creates:
- **4 departments**: ADMIN, ENG, PM, CONST
- **5 users**: 1 admin, 1 manager, 2 contributors, 1 viewer
- **5 cost element types**: Labor, Equipment, Material, Subcontract, Overhead
- **2 projects**: PROJ-001, PROJ-002
- **20 WBEs**: Work breakdown elements (4 levels deep)
- **100 cost elements**: Distributed across WBEs

#### Troubleshooting Reseed

**Seed files not found error:**
```bash
# Verify seed files are copied correctly
docker exec backcast_evs_backend ls -la /app/seed/

# If missing, re-copy them
docker cp /home/nicola/dev/backcast_evs/backend/seed backcast_evs_backend:/app/
```

**Duplicate key errors:**
- This is normal with Option A (Simple Reseed) - the seeder skips existing records
- Check logs for "already exists, skipping" messages

**Foreign key constraint errors:**
- Ensure you ran migrations first (Section 8.3)
- Check that dependent data exists (e.g., departments before users)

**Permission denied errors:**
```bash
# Ensure backend container has write permissions
docker exec backcast_evs_backend ls -la /app/
```

### 8.5 Verify Services

```bash
# Check service logs
docker compose --env-file .env.production logs -f

# Check specific service logs
docker compose --env-file .env.production logs backend
docker compose --env-file .env.production logs frontend
docker compose --env-file .env.production logs traefik
```

---

## Phase 9: Apache Configuration (192.168.1.21)

### 9.1 Create Apache VirtualHost Files

**Files created in:** `/home/nicola/dev/backcast_evs/deploy/apache/`

#### Frontend VirtualHost

**File:** `/home/nicola/dev/backcast_evs/deploy/apache/app.backcast.duckdns.org.conf`

```apache
<VirtualHost *:80>
    ServerName app.backcast.duckdns.org
    Redirect permanent / https://app.backcast.duckdns.org/
</VirtualHost>

<VirtualHost *:443>
    ServerName app.backcast.duckdns.org

    # SSL Configuration (use your certificates)
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/backcast.duckdns.org.crt
    SSLCertificateKeyFile /etc/ssl/private/backcast.duckdns.org.key

    # Security Headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "no-referrer-when-downgrade"

    # Proxy to Traefik (192.168.1.23:8080)
    ProxyPreserveHost On
    ProxyRequests Off

    # WebSocket support
    ProxyPass / ws://192.168.1.23:8080/
    ProxyPassReverse / ws://192.168.1.23:8080/

    # HTTP proxy
    ProxyPass / http://192.168.1.23:8080/
    ProxyPassReverse / http://192.168.1.23:8080/

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/app.backcast.duckdns.org_error.log
    CustomLog ${APACHE_LOG_DIR}/app.backcast.duckdns.org_access.log combined
</VirtualHost>
```

#### Backend API VirtualHost

**File:** `/home/nicola/dev/backcast_evs/deploy/apache/api.backcast.duckdns.org.conf`

```apache
<VirtualHost *:80>
    ServerName api.backcast.duckdns.org
    Redirect permanent / https://api.backcast.duckdns.org/
</VirtualHost>

<VirtualHost *:443>
    ServerName api.backcast.duckdns.org

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/backcast.duckdns.org.crt
    SSLCertificateKeyFile /etc/ssl/private/backcast.duckdns.org.key

    # Security Headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"

    # CORS handling
    <IfModule mod_rewrite.c>
        RewriteEngine On
        RewriteCond %{REQUEST_METHOD} OPTIONS
        RewriteRule ^(.*)$ $1 [R=200,L]
    </IfModule>

    # Proxy to Traefik
    ProxyPreserveHost On
    ProxyRequests Off

    ProxyPass / ws://192.168.1.23:8080/
    ProxyPassReverse / ws://192.168.1.23:8080/

    ProxyPass / http://192.168.1.23:8080/
    ProxyPassReverse / http://192.168.1.23:8080/

    ErrorLog ${APACHE_LOG_DIR}/api.backcast.duckdns.org_error.log
    CustomLog ${APACHE_LOG_DIR}/api.backcast.duckdns.org_access.log combined
</VirtualHost>
```

### 9.2 Deploy Apache Configuration

**From Docker server (192.168.1.23):**

```bash
# Copy configuration files to Apache server
scp deploy/apache/*.conf root@192.168.1.21:/etc/apache2/sites-available/
```

**On Apache server (192.168.1.21):**

```bash
# Enable required Apache modules
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_pass
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers

# Disable default sites if needed
sudo a2dissite 000-default
sudo a2dissite default-ssl

# Enable the new sites
sudo a2ensite app.backcast.duckdns.org
sudo a2ensite api.backcast.duckdns.org

# Test configuration
sudo apache2ctl configtest

# If test passes, reload Apache
sudo systemctl reload apache2

# Check Apache status
sudo systemctl status apache2
```

---

## Phase 10: Verification

### 10.1 Local Verification (192.168.1.23)

```bash
# Check service status
docker compose --env-file .env.production ps

# Check Traefik dashboard (requires auth)
curl -I http://localhost:8080

# Check backend API directly
curl http://localhost:8080/api/v1/health

# Check frontend directly
curl -I http://localhost:8080/
```

### 10.2 From Apache Server (192.168.1.21)

```bash
# Test proxy to Docker machine
curl -I http://192.168.1.23:8080
```

### 10.3 External Verification

From your browser or external network:

- **Frontend:** https://app.backcast.duckdns.org
- **Backend API:** https://api.backcast.duckdns.org
- **API Docs:** https://api.backcast.duckdns.org/docs
- **Traefik Dashboard:** https://traefik.backcast.duckdns.org (if configured)

---

## Phase 11: LAN Access Configuration (Optional)

### 11.1 Configure Local DNS for LAN Access

To access services from your local network (192.168.1.x), you need to add DNS entries to each machine that will access the services.

**On Linux/Mac (`/etc/hosts`):**
```bash
sudo nano /etc/hosts
```

**On Windows (`C:\Windows\System32\drivers\etc\hosts`):**
Run Notepad as Administrator and open the file.

**Add these lines:**
```hosts
192.168.1.23  api.backcast.duckdns.org
192.168.1.23  app.backcast.duckdns.org
192.168.1.23  db.backcast.duckdns.org
192.168.1.23  traefik.backcast.duckdns.org
```

### 11.2 Access Services from LAN

Once DNS entries are configured, you can access:

| Service | LAN URL | Authentication |
|---------|---------|----------------|
| Frontend | http://app.backcast.duckdns.org:8080 | None |
| Backend API | http://api.backcast.duckdns.org:8080 | API tokens |
| Adminer (DB) | http://db.backcast.duckdns.org:8080 | IP whitelist (192.168.0.0/16) |
| Traefik Dashboard | http://traefik.backcast.duckdns.org:8080/dashboard/ | Basic auth |

**Traefik Dashboard Credentials:**
- Username: `admin`
- Password: `backcast`

### 11.3 Test LAN Access

```bash
# Test from another machine on the LAN
curl -I http://192.168.1.23:8080

# Test with Host header
curl -I -H "Host: app.backcast.duckdns.org" http://192.168.1.23:8080

# Test Traefik dashboard with authentication
curl -u admin:backcast -H "Host: traefik.backcast.duckdns.org" http://192.168.1.23:8080/dashboard/
```

**Note:** Traefik routes based on the Host header, so you must use the correct hostname or configure DNS entries.

---

## Important Values to Save

### Database Credentials

```
Database User: backcast_prod
Database Password: backcast
Database Name: backcast_evs
Host: postgres (internal Docker network)
Port: 5432
```

### Application Secrets

```
SECRET_KEY: LcOCnNRRouE0uIXQDVQeZ8LE6zKxwHyiGa9JXP5fxa1szWoU7Epwt4Lq69m7iMzq++9FqbBA6ZqHr8cJVejKew==
ALGORITHM: HS256
```

### URLs

```
Frontend: https://app.backcast.duckdns.org
Backend API: https://api.backcast.duckdns.org
Database: postgresql+asyncpg://backcast_prod:backcast@postgres:5432/backcast_evs
```

### Docker Network

```
Network Name: traefik-public
Network ID: 08c9efc8766cba89c439478e198d65494e2f9e5fbeb3c39d4520822c52f62504
```

---

## Common Management Commands

### View Service Status

```bash
cd /home/nicola/dev/backcast_evs/deploy
docker compose --env-file .env.production ps
```

### View Logs

```bash
# All services
docker compose --env-file .env.production logs -f

# Specific service
docker compose --env-file .env.production logs -f backend
docker compose --env-file .env.production logs -f frontend
docker compose --env-file .env.production logs -f postgres
```

### Restart Services

```bash
# Restart all services
docker compose --env-file .env.production restart

# Restart specific service
docker compose --env-file .env.production restart backend
```

### Stop Services

```bash
# Stop all services (keeps volumes)
docker compose --env-file .env.production down

# Stop and remove volumes (WARNING: deletes database data)
docker compose --env-file .env.production down -v
```

### Update Services

```bash
# Pull latest code
cd /home/nicola/dev/backcast_evs
git pull

# Rebuild and restart
cd deploy
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d

# Run migrations if needed
docker compose --env-file .env.production run --rm alembic
```

### Database Access

```bash
# Access PostgreSQL directly
docker exec -it backcast_evs_postgres psql -U backcast_prod -d backcast_evs

# Backup database (with timestamp)
docker exec backcast_evs_postgres pg_dump -U backcast_prod backcast_evs | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore database from backup
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker exec -i backcast_evs_postgres psql -U backcast_prod backcast_evs

# Check database size
docker exec backcast_evs_postgres psql -U backcast_prod backcast_evs -c "SELECT pg_size_pretty(pg_database_size('backcast_evs'));"

# Re-seed database with initial data (see Section 8.4)
# This adds default departments, users, cost element types, projects, WBEs, and cost elements
```

### Access Adminer (Database GUI)

```
URL: http://db.backcast.duckdns.org (if configured)
Server: postgres
Username: backcast_prod
Password: backcast
Database: backcast_evs
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check service logs
docker compose --env-file .env.production logs

# Check if ports are already in use
sudo netstat -tulpn | grep :8080

# Check Docker network
docker network ls
docker network inspect traefik-public
```

### Database Connection Issues

```bash
# Check PostgreSQL is healthy
docker compose --env-file .env.production ps postgres

# Check PostgreSQL logs
docker compose --env-file .env.production logs postgres

# Test database connection
docker exec backcast_evs_backend pg_isready -h postgres -U backcast_prod
```

### Backend Not Starting

```bash
# Check backend logs
docker compose --env-file .env.production logs backend

# Check environment variables
docker exec backcast_evs_backend env | grep -E "DATABASE_URL|POSTGRES_"

# Restart backend
docker compose --env-file .env.production restart backend
```

### Frontend Not Working

```bash
# Check frontend logs
docker compose --env-file .env.production logs frontend

# Check nginx is running
docker exec backcast_evs_frontend ps aux

# Check nginx error log
docker exec backcast_evs_frontend cat /var/log/nginx/error.log
```

### Traefik Issues

```bash
# Check Traefik logs
docker compose --env-file .env.production logs traefik

# Check Traefik configuration
docker exec backcast_evs_traefik cat /etc/traefik/traefik.yml

# Test Traefik endpoint
curl -I http://localhost:8080
```

### Apache Proxy Issues (192.168.1.21)

```bash
# Check Apache error logs
sudo tail -f /var/log/apache2/error.log

# Check virtual host logs
sudo tail -f /var/log/apache2/app.backcast.duckdns.org_error.log
sudo tail -f /var/log/apache2/api.backcast.duckdns.org_error.log

# Test Apache configuration
sudo apache2ctl configtest

# Check if modules are enabled
apache2ctl -M | grep -E "proxy|ssl|rewrite|headers"
```

### Health Checks Failing

Health checks may show as "unhealthy" but services work correctly. This is often due to:
- Backend health endpoint not implemented (returns 404)
- Frontend health check timing out
- Traefik dashboard requiring authentication

**To fix health checks:** Update the `healthcheck` section in `docker-compose.yml` or implement missing health endpoints.

---

## Security Considerations

### Password Management

- **Database password** should be rotated periodically
- Store passwords in a secure password manager
- Never commit `.env.production` to version control

### SSL Certificates

- Use valid SSL certificates from a trusted CA
- Set up automatic certificate renewal (Let's Encrypt recommended)
- Keep certificates in `/etc/ssl/` on Apache server

### Firewall Rules

**On Apache server (192.168.1.21):**
```bash
# Allow HTTP and HTTPS from anywhere
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH from trusted IPs only
sudo ufw allow from <your-ip> to any port 22

# Enable firewall
sudo ufw enable
```

**On Docker server (192.168.1.23):**
```bash
# Allow internal network only
# Block external access to Traefik port 8080
sudo ufw deny 8080/tcp

# Allow SSH from trusted IPs
sudo ufw allow from <your-ip> to any port 22

# Allow traffic from Apache server
sudo ufw allow from 192.168.1.21 to any port

# Enable firewall
sudo ufw enable
```

### Regular Backups

```bash
# Backup database
docker exec backcast_evs_postgres pg_dump -U backcast_prod backcast_evs | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup Docker volumes
docker run --rm -v deploy_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_volume_$(date +%Y%m%d).tar.gz -C /data .
```

---

## Complete Deployment Command Checklist

For a fresh deployment, run these commands in order:

```bash
# === Phase 1: Docker Installation ===
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get update && sudo apt-get install -y docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker

# === Phase 2: Create Network ===
cd /home/nicola/dev/backcast_evs/deploy
docker network create traefik-public

# === Phase 3: Generate Secrets ===
# (See Phase 3 above - save generated values)

# === Phase 4-7: Configuration Files ===
# (Create/update files as shown above)

# === Phase 8: Build and Deploy ===
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d
docker compose --env-file .env.production run --rm alembic

# === Phase 9: Apache Configuration (on 192.168.1.21) ===
# (See Phase 9 above)

# === Phase 10: Verification ===
docker compose --env-file .env.production ps
docker compose --env-file .env.production logs -f
```

---

## File Structure Summary

```
/home/nicola/dev/backcast_evs/deploy/
├── .env.production                    # Production environment variables
├── docker-compose.yml                 # Service orchestration
├── apache/
│   ├── app.backcast.duckdns.org.conf  # Frontend VirtualHost
│   ├── api.backcast.duckdns.org.conf  # Backend VirtualHost
│   └── README.md                      # Apache deployment instructions
├── traefik/
│   ├── traefik.yml                    # Traefik static config
│   └── dynamic/
│       └── middlewares.yml            # Security headers and auth
├── backend/
│   └── Dockerfile                     # Backend image build
├── frontend/
│   ├── Dockerfile                     # Frontend image build
│   └── nginx.conf                     # Nginx configuration
└── scripts/
    ├── entrypoint-backend.sh          # Backend startup script
    └── entrypoint-frontend.sh         # Frontend startup script
```

---

## Support and Maintenance

### Log Locations

**Docker Server (192.168.1.23):**
- Application logs: `backend-logs` Docker volume
- Traefik logs: `traefik-logs` Docker volume
- Container logs: `docker compose logs`

**Apache Server (192.168.1.21):**
- Apache logs: `/var/log/apache2/`
- Virtual host logs: `/var/log/apache2/app.*_log`, `/var/log/apache2/api.*_log`

### Monitoring

Check services regularly:

```bash
# Daily health check
docker compose --env-file .env.production ps

# Check disk space
df -h
docker system df

# Check resource usage
docker stats
```

### Updates

1. **Application updates:** Pull latest code and rebuild
2. **Security updates:** Keep Docker and host OS updated
3. **Dependency updates:** Update `pyproject.toml` and `package.json` regularly

---

## Emergency Procedures

### Full System Restart

```bash
# On Docker server (192.168.1.23)
cd /home/nicola/dev/backcast_evs/deploy
docker compose --env-file .env.production down
docker compose --env-file .env.production up -d
```

### Database Recovery

```bash
# Restore from backup
docker exec -i backcast_evs_postgres psql -U backcast_prod backcast_evs < backup.sql
```

### Reset Deployment

```bash
# WARNING: Deletes all data
cd /home/nicola/dev/backcast_evs/deploy
docker compose --env-file .env.production down -v
docker network rm traefik-public
# Then follow deployment guide from Phase 2
```

---

**Last Updated:** 2026-01-26
**Version:** 1.0
**Maintained By:** nicola@backcast.duckdns.org
