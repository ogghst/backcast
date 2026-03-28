# Docker Deployment Guide for Backcast 

This guide covers deploying Backcast  to production using Docker and Traefik with automatic SSL certificates.

## Audience

- DevOps engineers deploying to production
- System administrators setting up the application
- Developers deploying to staging environments

## Prerequisites

### Server Requirements

- **OS**: Linux (Ubuntu 22.04+ recommended) or other Docker-compatible system
- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ recommended
- **Disk**: 50GB+ for data volumes and logs
- **Network**: Public IP with ports 80 and 443 accessible

### Software Requirements

- **Docker**: 24.0+ installed
- **Docker Compose**: 2.20+ installed
- **Domain**: A registered domain with DNS configured

### DNS Configuration

Ensure the following A records point to your server IP:

| Subdomain | Purpose |
|-----------|---------|
| `@` or `*` | Wildcard (covers all subdomains) |
| `api` | Backend API |
| `app` | Frontend application |
| `db` | Adminer database GUI (optional) |
| `traefik` | Traefik dashboard (optional) |

## Architecture Overview

```
                    Internet
                       ↓
                   ┌─────────┐
                   │ Traefik │ (Port 80/443)
                   │   v3    │ ← Let's Encrypt SSL
                   └────┬────┘
                        │
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
   ┌─────────┐    ┌─────────┐    ┌──────────┐
   │ Frontend│    │ Backend │    │ Adminer  │
   │ (nginx) │    │FastAPI  │    │  GUI     │
   └─────────┘    └────┬────┘    └──────────┘
                       │
                ┌──────┴──────┐
                ↓             ↓
           ┌─────────┐   ┌─────────┐
           │ Alembic │   │PostgreSQL│
           │(migrate)│   │  :5432   │
           └─────────┘   └──────────┘
```

### Service Endpoints

| Service | URL | Internal Port | Description |
|---------|-----|---------------|-------------|
| Frontend | `https://app.yourdomain.com` | 8080 | React SPA |
| Backend API | `https://api.yourdomain.com` | 8080 | FastAPI |
| Adminer | `https://db.yourdomain.com` | 8080 | Database GUI |
| Traefik Dashboard | `https://traefik.yourdomain.com` | - | Monitoring |

## Pre-Deployment Checklist

- [ ] Docker and Docker Compose installed
- [ ] Domain DNS configured
- [ ] Firewall allows ports 80 and 443
- [ ] `traefik-public` Docker network created
- [ ] Generated secure `SECRET_KEY`
- [ ] Generated secure database password
- [ ] Configured Traefik ACME email
- [ ] Reviewed IP whitelist for Adminer

## Deployment Steps

### Step 1: Initial Setup

```bash
# Clone repository (if not already done)
git clone <repository-url>
cd backcast_evs

# Create external network for Traefik
docker network create traefik-public
```

### Step 2: Configure Environment

```bash
# Navigate to deploy directory
cd deploy

# Copy environment template
cp .env.production.example .env.production

# Edit with your values
nano .env.production
```

**Required changes in `.env.production`:**

```bash
# Domain Configuration
DOMAIN=yourdomain.com

# Database Configuration (use strong passwords)
POSTGRES_USER=backcast_prod
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_DB=backcast_evs

# Application Security (generate strong secret)
SECRET_KEY=<generate-strong-secret>

# Traefik / Let's Encrypt
TRAEFIK_ACME_EMAIL=admin@yourdomain.com
```

**Generate secure values:**

```bash
# Generate SECRET_KEY
openssl rand -base64 64

# Generate database password
openssl rand -base64 32

# Generate Traefik dashboard auth (htpasswd format)
htpasswd -nb admin <password>
```

### Step 3: Update Traefik Configuration

Edit [deploy/traefik/traefik.yml](deploy/traefik/traefik.yml):

- Replace `yourdomain.com` with your actual domain
- Update `admin@yourdomain.com` with your email

Edit [deploy/traefik/dynamic/middlewares.yml](deploy/traefik/dynamic/middlewares.yml):

- Update `adminer-whitelist` IP ranges with your allowed IPs
- Update `traefik-auth` with the htpasswd hash generated above

### Step 4: Build and Deploy

```bash
# From deploy directory
cd deploy

# Build images
docker-compose --env-file .env.production build

# Start all services
docker-compose --env-file .env.production up -d

# Run database migrations (manual or automatic)
docker compose --env-file .env.production run --rm alembic upgrade head
```

### Step 5: Verify Deployment

```bash
# Check service status
docker compose --env-file .env.production ps

# Check logs
docker compose --env-file .env.production logs -f

# Health checks
curl https://api.yourdomain.com/api/v1/health
curl -I https://app.yourdomain.com
```

### Step 6: Access Applications

- **Frontend**: <https://app.yourdomain.com>
- **Backend API**: <https://api.yourdomain.com>
- **Adminer**: <https://db.yourdomain.com> (IP restricted)
- **Traefik Dashboard**: <https://traefik.yourdomain.com>

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DOMAIN` | Base domain for all services | - | Yes |
| `POSTGRES_USER` | Database username | - | Yes |
| `POSTGRES_PASSWORD` | Database password | - | Yes |
| `POSTGRES_DB` | Database name | `backcast_evs` | No |
| `SECRET_KEY` | JWT signing key | - | Yes |
| `TRAEFIK_ACME_EMAIL` | Let's Encrypt email | - | Yes |
| `RUN_MIGRATIONS` | Auto-run migrations on startup | `true` | No |

### Resource Limits

Default resource limits configured in [deploy/docker-compose.yml](deploy/docker-compose.yml):

| Service | CPU Limit | Memory Limit |
|---------|-----------|--------------|
| Backend | 2 cores | 2GB |
| Frontend | 1 core | 512MB |
| Adminer | 0.5 cores | 256MB |
| PostgreSQL | (unlimited) | (unlimited) |

## SSL/TLS with Let's Encrypt

### How It Works

1. Traefik uses HTTP-01 challenge for domain validation
2. Certificates automatically generated on first request
3. Auto-renewal handled by Traefik
4. Certificates stored in `traefik-letsencrypt` volume

### Troubleshooting SSL

**Certificate not issued:**

- Verify DNS A records point to correct IP
- Ensure port 80 is accessible from internet
- Check Traefik logs: `docker compose logs traefik`

**Certificate expired:**

- Traefik auto-renews 30 days before expiry
- Check ACME storage volume exists
- Verify `TRAEFIK_ACME_EMAIL` is correct

## Apache Integration (Optional)

When deploying on a server with an existing Apache web server, you need to configure Apache as a reverse proxy to route requests to Traefik.

### Scenario Overview

```
Internet → Apache (80/443) → Traefik (8080/8443) → Services
```

### Step 1: Configure Traefik Ports

Edit [deploy/.env.production](deploy/.env.production.example) to use non-standard ports:

```bash
# Traefik Port Configuration
TRAEFIK_HTTP_PORT=8080
TRAEFIK_HTTPS_PORT=8443
```

### Step 2: Enable Apache Proxy Modules

```bash
# Enable required Apache modules
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_pass
sudo a2enmod ssl
sudo a2enmod rewrite
sudo apache2ctl configtest
sudo systemctl reload apache2
```

### Step 3: Configure Apache VirtualHost

Create VirtualHost configuration files for each subdomain.

#### Frontend VirtualHost

**File**: `/etc/apache2/sites-available/app.yourdomain.com.conf`

```apache
<VirtualHost *:80>
    ServerName app.yourdomain.com
    Redirect permanent / https://app.yourdomain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName app.yourdomain.com

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/yourdomain.com.crt
    SSLCertificateKeyFile /etc/ssl/private/yourdomain.com.key
    # Optional: SSLCertificateChainFile /etc/ssl/certs/yourdomain.com-chain.crt

    # Security Headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "no-referrer-when-downgrade"

    # Proxy to Traefik
    ProxyPreserveHost On
    ProxyRequests Off

    # WebSocket support
    ProxyPass / ws://127.0.0.1:8080/
    ProxyPassReverse / ws://127.0.0.1:8080/

    # HTTP proxy
    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/app.yourdomain.com_error.log
    CustomLog ${APACHE_LOG_DIR}/app.yourdomain.com_access.log combined
</VirtualHost>
```

#### Backend API VirtualHost

**File**: `/etc/apache2/sites-available/api.yourdomain.com.conf`

```apache
<VirtualHost *:80>
    ServerName api.yourdomain.com
    Redirect permanent / https://api.yourdomain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName api.yourdomain.com

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/yourdomain.com.crt
    SSLCertificateKeyFile /etc/ssl/private/yourdomain.com.key

    # Security Headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"

    # CORS handling (if needed for OPTIONS)
    <IfModule mod_rewrite.c>
        RewriteEngine On
        RewriteCond %{REQUEST_METHOD} OPTIONS
        RewriteRule ^(.*)$ $1 [R=200,L]
    </IfModule>

    # Proxy to Traefik
    ProxyPreserveHost On
    ProxyRequests Off

    # WebSocket support
    ProxyPass / ws://127.0.0.1:8080/
    ProxyPassReverse / ws://127.0.0.1:8080/

    # HTTP proxy
    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/api.yourdomain.com_error.log
    CustomLog ${APACHE_LOG_DIR}/api.yourdomain.com_access.log combined
</VirtualHost>
```

#### Adminer VirtualHost (Optional)

**File**: `/etc/apache2/sites-available/db.yourdomain.com.conf`

```apache
<VirtualHost *:443>
    ServerName db.yourdomain.com

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/yourdomain.com.crt
    SSLCertificateKeyFile /etc/ssl/private/yourdomain.com.key

    # IP Whitelist (optional)
    <RequireAll>
        Require ip 127.0.0.1
        Require ip 10.0.0.0/8
        Require ip 172.16.0.0/12
        Require ip 192.168.0.0/16
        # Add your allowed IPs here
    </RequireAll>

    # Proxy to Traefik
    ProxyPreserveHost On
    ProxyRequests Off
    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/

    ErrorLog ${APACHE_LOG_DIR}/db.yourdomain.com_error.log
    CustomLog ${APACHE_LOG_DIR}/db.yourdomain.com_access.log combined
</VirtualHost>
```

### Step 4: Enable Sites and Reload Apache

```bash
# Enable the sites
sudo a2ensite app.yourdomain.com
sudo a2ensite api.yourdomain.com
sudo a2ensite db.yourdomain.com  # optional

# Test configuration
sudo apache2ctl configtest

# Reload Apache
sudo systemctl reload apache2
```

### Step 5: Configure Traefik for HTTP-Only Mode

When Apache acts as the SSL terminator, Traefik should run in HTTP-only mode. Update [deploy/traefik/traefik.yml](deploy/traefik/traefik.yml):

```yaml
# Traefik static configuration for Apache integration
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

# Remove certificatesResolvers section - Apache handles SSL

log:
  level: INFO
  filePath: /var/log/traefik/traefik.log
  format: json

accessLog:
  filePath: /var/log/traefik/access.log
  format: json
```

Key changes from the default configuration:

- **Removed** `websecure` entryPoint (port 443) - not needed internally
- **Removed** automatic HTTP-to-HTTPS redirect
- **Removed** `certificatesResolvers.letsencrypt` section - Apache manages SSL

### Step 6: Update Docker Compose Labels

The service labels in [deploy/docker-compose.yml](deploy/docker-compose.yml) reference the `websecure` entryPoint. Update them to use `web` instead:

```yaml
labels:
  - "traefik.http.routers.backend.entrypoints=web"  # Changed from websecure
  - "traefik.http.routers.frontend.entrypoints=web"  # Changed from websecure
  - "traefik.http.routers.adminer.entrypoints=web"  # Changed from websecure
```

Apply these changes to all service labels (backend, frontend, adminer).

### Step 7: Redeploy Traefik

```bash
cd deploy

# Recreate Traefik container with new configuration
docker compose --env-file .env.production up -d --force-recreate traefik
```

### Step 8: Verify the Setup

```bash
# Test Traefik directly (should respond on HTTP)
curl -I http://127.0.0.1:8080

# Test via Apache (should respond with HTTPS)
curl -I https://app.yourdomain.com

# Check Traefik logs
docker compose --env-file .env.production logs -f traefik
```

### Common Issues

**502 Bad Gateway from Apache:**

- Verify Traefik is running: `curl http://127.0.0.1:8080`
- Check Traefik is listening on configured ports
- Review Apache error logs: `tail -f /var/log/apache2/app.yourdomain.com_error.log`

**WebSocket Connection Failures:**

- Ensure `proxy_pass` with `ws://` protocol is configured
- Check Apache timeout settings are sufficient

**CORS Errors:**

- Backend CORS origins should include the Apache-routed domain
- Verify `BACKEND_CORS_ORIGINS` in `.env.production`

## Maintenance

### View Logs

```bash
cd deploy
docker compose --env-file .env.production logs -f <service>
```

### Update Application

```bash
cd deploy
git pull  # Update code
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d
```

### Database Backup

```bash
# Manual backup
docker compose exec postgres pg_dump -U backcast_prod backcast_evs > backup.sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U backcast_prod backcast_evs
```

### Restart Services

```bash
cd deploy
docker compose --env-file .env.production restart <service>
```

## Troubleshooting

### Common Issues

**Services won't start:**

```bash
# Check if traefik-public network exists
docker network ls | grep traefik-public

# Create if missing
docker network create traefik-public
```

**Database connection errors:**

```bash
# Check database health
docker compose exec postgres pg_isready -U backcast_prod

# View database logs
docker compose logs postgres
```

**Frontend shows 502 Bad Gateway:**

```bash
# Verify backend is running
docker ps | grep backend

# Check backend health
docker compose exec backend curl http://localhost:8080/api/v1/health
```

**SSL certificate warnings:**

- Wait 5-10 minutes for Let's Encrypt propagation
- Verify domain DNS is correct
- Check port 80 is not blocked by firewall

### Useful Commands

```bash
# Enter container shell
docker compose exec -it backend bash

# View container resource usage
docker stats

# Clean up old images
docker system prune -a

# View container details
docker inspect backcast_evs_backend
```

## Security Checklist

- [ ] Changed default passwords
- [ ] Configured IP whitelist for Adminer
- [ ] Set up Traefik dashboard authentication
- [ ] Enabled firewall (only ports 80/443)
- [ ] Regular database backups configured
- [ ] SSL certificates valid
- [ ] CORS limited to production domain only
- [ ] DEBUG mode disabled
- [ ] Log rotation configured

## Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Compose File | `docker-compose.yml` (root) | `deploy/docker-compose.yml` |
| Hot Reload | Enabled | Disabled |
| Port Exposure | Direct (8020, 5173) | Via Traefik |
| SSL | None | Let's Encrypt |
| Health Checks | Basic | Comprehensive |
| Resource Limits | None | Configured |

## Additional Resources

- [Architecture Documentation](../02-architecture/) - System design details
- [User Guide: EVCS](./evcs-wbe-user-guide.md) - Working with versioned entities
- [Main README](../../README.md) - Project overview
