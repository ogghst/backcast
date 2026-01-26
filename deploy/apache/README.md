# Apache Configuration Deployment

These Apache VirtualHost configuration files are for the Apache server at **192.168.1.21**.

## Overview

The Apache server acts as:
- SSL terminator (HTTPS → HTTP)
- Public-facing gateway
- Reverse proxy to Traefik (192.168.1.23:8080)

## Architecture

```
Internet (HTTPS)
    ↓
Apache (192.168.1.21:443) - SSL Termination
    ↓
HTTP Proxy to Traefik (192.168.1.23:8080)
    ↓
Docker Services (Backend/Frontend)
```

## Files

| File | Purpose |
|------|---------|
| `app.backcast.duckdns.org.conf` | Frontend VirtualHost configuration |
| `api.backcast.duckdns.org.conf` | Backend API VirtualHost configuration |
| `README.md` | This file |

---

## Deployment Steps

### Step 1: Copy Configuration Files

**From Docker server (192.168.1.23):**

```bash
cd /home/nicola/dev/backcast_evs/deploy
scp apache/*.conf root@192.168.1.21:/etc/apache2/sites-available/
```

### Step 2: Enable Required Apache Modules

**On Apache server (192.168.1.21):**

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_pass
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers
```

**Expected output:**
```
Enabling module proxy.
Enabling module proxy_http.
Enabling module proxy_pass.
Enabling module ssl.
Enabling module rewrite.
Enabling module headers.
To activate the new configuration, you need to run:
  systemctl restart apache2
```

### Step 3: Disable Default Sites (Optional)

If you want to disable the default Apache sites:

```bash
sudo a2dissite 000-default
sudo a2dissite default-ssl
```

### Step 4: Enable the New Sites

```bash
sudo a2ensite app.backcast.duckdns.org
sudo a2ensite api.backcast.duckdns.org
```

**Expected output:**
```
Enabling site app.backcast.duckdns.org.
To activate the new configuration, you need to run:
  systemctl reload apache2
Enabling site api.backcast.duckdns.org.
To activate the new configuration, you need to run:
  systemctl reload apache2
```

### Step 5: Test Configuration

```bash
sudo apache2ctl configtest
```

**Expected output:**
```
Syntax OK
```

If you get warnings about `ServerName`, you can ignore them or add:
```bash
echo "ServerName localhost" | sudo tee -a /etc/apache2/conf-available/servername.conf
sudo a2enconf servername
```

### Step 6: Reload Apache

```bash
sudo systemctl reload apache2
```

### Step 7: Verify Apache Status

```bash
sudo systemctl status apache2
```

**Expected output:**
```
● apache2.service - The Apache HTTP Server
   Loaded: loaded (/lib/systemd/system/apache2.service; enabled; vendor preset: enabled)
  Drop-In: /etc/systemd/system/apache2.service.d
           └─apache2-systemd.conf
   Active: active (running) since ...
```

---

## Prerequisites

### SSL Certificates

You must have SSL certificates installed for `backcast.duckdns.org`:

- **Certificate:** `/etc/ssl/certs/backcast.duckdns.org.crt`
- **Private Key:** `/etc/ssl/private/backcast.duckdns.org.key`

#### Generate Self-Signed Certificate (For Testing Only)

```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/backcast.duckdns.org.key \
  -out /etc/ssl/certs/backcast.duckdns.org.crt \
  -subj "/CN=backcast.duckdns.org"
```

#### Use Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-apache

# Obtain certificate
sudo certbot --apache -d backcast.duckdns.org \
  -d app.backcast.duckdns.org \
  -d api.backcast.duckdns.org \
  -d db.backcast.duckdns.org
```

### Network Connectivity

Apache server must be able to reach Docker server:

```bash
# Test from Apache server
ping -c 3 192.168.1.23
curl -I http://192.168.1.23:8080
```

**Expected results:**
- Ping should succeed
- HTTP response should be `200 OK` or Traefik 404 page

### Firewall Rules

Ensure ports 80 and 443 are open on Apache server:

```bash
# Check firewall status
sudo ufw status

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall if not already enabled
sudo ufw enable
```

---

## Configuration Details

### Frontend VirtualHost (`app.backcast.duckdns.org`)

**Features:**
- HTTP → HTTPS redirect
- SSL termination
- WebSocket support
- Security headers
- Reverse proxy to Traefik

**Backend Target:** `http://192.168.1.23:8080`

**Key Directives:**
- `ProxyPass /` - Proxy all requests
- `ProxyPassReverse /` - Rewrite response headers
- WebSocket support via `ws://` protocol

### Backend API VirtualHost (`api.backcast.duckdns.org`)

**Features:**
- HTTP → HTTPS redirect
- SSL termination
- CORS handling for OPTIONS requests
- Security headers
- Reverse proxy to Traefik

**Backend Target:** `http://192.168.1.23:8080`

**CORS Handling:**
- OPTIONS requests return 200 status
- Allows cross-origin requests from frontend

---

## Verification

### Test From External Browser

1. **Frontend:** https://app.backcast.duckdns.org
   - Should show the React application

2. **Backend API:** https://api.backcast.duckdns.org/docs
   - Should show FastAPI Swagger documentation

3. **API Health Check:** https://api.backcast.duckdns.org/api/v1/health
   - Should return health status (if implemented)

### Test From Command Line

```bash
# Test frontend
curl -I https://app.backcast.duckdns.org

# Test backend API
curl https://api.backcast.duckdns.org/docs

# Test SSL certificate
openssl s_client -connect app.backcast.duckdns.org:443 -servername app.backcast.duckdns.org
```

### Check Apache Logs

```bash
# General error log
sudo tail -f /var/log/apache2/error.log

# Frontend logs
sudo tail -f /var/log/apache2/app.backcast.duckdns.org_error.log
sudo tail -f /var/log/apache2/app.backcast.duckdns.org_access.log

# Backend API logs
sudo tail -f /var/log/apache2/api.backcast.duckdns.org_error.log
sudo tail -f /var/log/apache2/api.backcast.duckdns.org_access.log
```

---

## Troubleshooting

### Issue: 502 Bad Gateway

**Possible causes:**
1. Docker services not running on 192.168.1.23
2. Traefik not accessible from Apache server
3. Firewall blocking connection

**Solutions:**
```bash
# Check if Traefik is accessible
curl -I http://192.168.1.23:8080

# Check Docker services
ssh 192.168.1.23 "cd /home/nicola/dev/backcast_evs/deploy && docker compose --env-file .env.production ps"

# Check firewall
sudo ufw status
```

### Issue: SSL Certificate Error

**Possible causes:**
1. Certificate files not found
2. Certificate expired
3. Certificate mismatch

**Solutions:**
```bash
# Check certificate files exist
ls -la /etc/ssl/certs/backcast.duckdns.org.crt
ls -la /etc/ssl/private/backcast.duckdns.org.key

# Check certificate expiration
openssl x509 -in /etc/ssl/certs/backcast.duckdns.org.crt -noout -dates

# Regenerate certificate if needed
# See "Generate Self-Signed Certificate" section above
```

### Issue: Site Not Loading

**Possible causes:**
1. VirtualHost not enabled
2. DNS not pointing to Apache server
3. Apache not running

**Solutions:**
```bash
# Check if site is enabled
sudo apache2ctl -S | grep backcast

# Check Apache is running
sudo systemctl status apache2

# Check DNS
nslookup app.backcast.duckdns.org
dig app.backcast.duckdns.org

# Reload Apache
sudo systemctl reload apache2
```

### Issue: CORS Errors

**Possible causes:**
1. Backend CORS settings incorrect
2. OPTIONS requests not handled

**Solutions:**
```bash
# Check backend CORS settings
ssh 192.168.1.23 "cat /home/nicola/dev/backcast_evs/deploy/.env.production | grep CORS"

# Verify CORS handling in VirtualHost
grep -A 5 "RewriteCond %{REQUEST_METHOD} OPTIONS" /etc/apache2/sites-available/api.backcast.duckdns.org.conf
```

### Issue: WebSocket Connection Failed

**Possible causes:**
1. WebSocket upgrade not handled
2. Proxy timeout

**Solutions:**
```bash
# Check WebSocket proxy directives
grep -A 2 "ProxyPass.*ws://" /etc/apache2/sites-available/app.backcast.duckdns.org.conf

# Increase timeout if needed
# Add to VirtualHost:
# ProxyTimeout 300
```

---

## Maintenance

### Update Configuration

If you modify the VirtualHost files:

```bash
# 1. Copy new files to Apache server
scp apache/*.conf root@192.168.1.21:/etc/apache2/sites-available/

# 2. Test configuration
ssh root@192.168.1.21 "sudo apache2ctl configtest"

# 3. Reload Apache
ssh root@192.168.1.21 "sudo systemctl reload apache2"
```

### Renew SSL Certificates (Let's Encrypt)

```bash
# Test renewal
sudo certbot renew --dry-run

# Actual renewal (automated by cron)
sudo certbot renew
```

Let's Encrypt certificates are automatically renewed by certbot timer.

### View Apache Metrics

```bash
# Check active connections
sudo apache2ctl status

# Check configuration
sudo apache2ctl -M  # Show loaded modules
sudo apache2ctl -S  # Show VirtualHosts
sudo apache2ctl -v  # Show version
```

---

## Security Hardening

### Enable Security Headers

The configurations already include:
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: no-referrer-when-downgrade

### Additional Security Headers (Optional)

Add to VirtualHost configurations:

```apache
# Content Security Policy
Header always set Content-Security-Policy "default-src 'self'"

# Strict Transport Security (HSTS)
Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"

# Remove Server header
Header always unset Server
```

### Rate Limiting (Optional)

Use mod_evasive for DDoS protection:

```bash
sudo apt-get install libapache2-mod-evasive
sudo a2enmod evasive
```

Create `/etc/apache2/mods-available/evasive.conf`:

```apache
<IfModule mod_evasive20.c>
    DOSHashTableSize 3097
    DOSPageCount 10
    DOSSiteCount 100
    DOSPageInterval 1
    DOSSiteInterval 1
    DOSBlockingPeriod 10
</IfModule>
```

---

## Log Analysis

### Monitor Access Patterns

```bash
# Top 10 IPs
sudo awk '{print $1}' /var/log/apache2/app.backcast.duckdns.org_access.log | sort | uniq -c | sort -rn | head -10

# Top 10 URLs
sudo awk '{print $7}' /var/log/apache2/app.backcast.duckdns.org_access.log | sort | uniq -c | sort -rn | head -10

# HTTP status codes
sudo awk '{print $9}' /var/log/apache2/app.backcast.duckdns.org_access.log | sort | uniq -c | sort -rn
```

### Monitor Errors

```bash
# Recent errors
sudo tail -100 /var/log/apache2/error.log | grep -i error

# 404 errors
sudo grep " 404 " /var/log/apache2/app.backcast.duckdns.org_access.log | tail -20

# 500 errors
sudo grep " 500 " /var/log/apache2/app.backcast.duckdns.org_access.log | tail -20
```

---

## Backup and Recovery

### Backup Apache Configuration

```bash
# Backup all sites
sudo tar czf apache-configs-backup-$(date +%Y%m%d).tar.gz /etc/apache2/

# Backup specific sites
tar czf backcast-apache-vhosts-$(date +%Y%m%d).tar.gz /etc/apache2/sites-available/
```

### Restore Apache Configuration

```bash
# Extract backup
sudo tar xzf apache-configs-backup-YYYYMMDD.tar.gz -C /

# Test and reload
sudo apache2ctl configtest
sudo systemctl reload apache2
```

---

## Additional Resources

### Apache Documentation
- [Apache Module Documentation](https://httpd.apache.org/docs/current/mod/)
- [Apache SSL/TLS Encryption](https://httpd.apache.org/docs/current/ssl/)
- [Apache Proxy Documentation](https://httpd.apache.org/docs/current/mod/mod_proxy.html)

### Useful Commands
```bash
# Show all VirtualHosts
sudo apache2ctl -S

# Show loaded modules
sudo apache2ctl -M

# Graceful restart (finishes existing connections)
sudo apache2ctl graceful

# Check syntax only
sudo apache2ctl -t

# Show version
sudo apache2ctl -v
```

---

## Quick Reference

### Full Deployment Command

```bash
# From Docker server (192.168.1.23)
cd /home/nicola/dev/backcast_evs/deploy
scp apache/*.conf root@192.168.1.21:/etc/apache2/sites-available/
ssh root@192.168.1.21 << 'EOF'
a2enmod proxy proxy_http proxy_pass ssl rewrite headers
a2ensite app.backcast.duckdns.org api.backcast.duckdns.org
apache2ctl configtest
systemctl reload apache2
systemctl status apache2
EOF
```

### Quick Test

```bash
# Test frontend
curl -I https://app.backcast.duckdns.org

# Test backend
curl -I https://api.backcast.duckdns.org/docs

# Test from Apache server
curl -I http://192.168.1.23:8080
```

---

**File:** `/home/nicola/dev/backcast_evs/deploy/apache/README.md`
**Last Updated:** 2026-01-26
**Version:** 1.0
**Apache Server:** 192.168.1.21
**Docker Server:** 192.168.1.23
