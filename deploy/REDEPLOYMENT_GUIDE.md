# Backcast EVS - Redeployment Guide

## Quick Redeployment Script

A comprehensive script has been created to automate the redeployment process.

## Location

`/home/nicola/backcast/deploy/scripts/redeploy.sh`

## Quick Start

### Standard Redeployment (Interactive)
```bash
cd /home/nicola/backcast/deploy
./scripts/redeploy.sh
```

### Non-Interactive Redeployment
```bash
cd /home/nicola/backcast/deploy
./scripts/redeploy.sh -y
```

## Usage Options

```bash
./scripts/redeploy.sh [options]
```

### Available Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and usage examples |
| `-b, --branch BRANCH` | Specify git branch to pull from (default: current branch) |
| `-s, --skip-backup` | Skip database backup (NOT recommended for production) |
| `-n, --no-build` | Skip container rebuild, use existing images |
| `-m, --no-migrate` | Skip database migrations |
| `-y, --yes` | Auto-confirm all prompts (non-interactive mode) |
| `-v, --verbose` | Enable verbose output |

## Common Scenarios

### 1. Full Redeployment from Current Branch
**Use when:** You want to deploy latest changes with all safety checks

```bash
cd /home/nicola/backcast/deploy
./scripts/redeploy.sh -y
```

**What it does:**
- Pulls latest git changes
- Creates database backup
- Rebuilds containers
- Restarts services
- Runs migrations
- Verifies deployment

### 2. Redeploy from Different Branch
**Use when:** You need to deploy from a specific branch

```bash
cd /home/nicola/backcast/deploy
./scripts/redeploy.sh -b main -y
```

### 3. Quick Restart (No Rebuild)
**Use when:** You just need to restart services without rebuilding

```bash
cd /home/nicola/backcast/deploy
./scripts/redeploy.sh -n -y
```

**What it does:**
- Pulls latest git changes
- Creates database backup
- Restarts services (no rebuild)
- Runs migrations
- Verifies deployment

### 4. Development Quick Test
**Use when:** You're testing changes frequently and don't need backups

```bash
cd /home/nicola/backcast/deploy
./scripts/redeploy.sh -s -n -y
```

**What it does:**
- Pulls latest git changes
- Restarts services (no backup, no rebuild)
- Runs migrations
- Verifies deployment

⚠️ **Warning:** This skips database backup - not recommended for production!

### 5. Configuration Changes Only
**Use when:** You've only changed configuration, not code

```bash
cd /home/nicola/backcast/deploy
./scripts/redeploy.sh -s -n -m -y
```

**What it does:**
- Pulls latest git changes
- Restarts services (no backup, no rebuild, no migrations)
- Verifies deployment

## What the Script Does

### 1. Prerequisites Check
- Verifies Docker is running
- Checks for required files (docker-compose.yml, .env.production)
- Validates directory structure

### 2. Git Pull
- Pulls latest changes from specified branch
- Shows current branch information
- Handles branch switching if requested

### 3. Database Backup
- Creates timestamped backup: `backup_YYYYMMDD_HHMMSS.sql.gz`
- Stores backup in deploy directory
- Shows backup size when complete

### 4. Container Rebuild
- Rebuilds backend and frontend images
- Shows build progress
- Takes 5-15 minutes depending on system

### 5. Service Restart
- Stops and starts all containers
- Maintains database volume
- Waits for services to stabilize

### 6. Database Migrations
- Runs Alembic migrations
- Applies any pending schema changes
- Shows migration version

### 7. Verification
- Checks service status
- Tests API endpoints
- Verifies frontend accessibility
- Shows migration version

## Troubleshooting

### Script Fails at Prerequisites Check
**Problem:** Docker not running or missing files

**Solution:**
```bash
# Check Docker status
docker info

# Verify you're in the correct directory
cd /home/nicola/backcast/deploy
ls -la docker-compose.yml .env.production
```

### Git Pull Fails
**Problem:** Uncommitted changes or branch conflicts

**Solution:**
```bash
cd /home/nicola/backcast

# Stash local changes
git stash

# Or commit them first
git add .
git commit -m "WIP"
```

### Database Backup Fails
**Problem:** PostgreSQL not ready or connection issues

**Solution:**
```bash
cd /home/nicola/backcast/deploy

# Check PostgreSQL status
docker compose --env-file .env.production ps postgres

# Check PostgreSQL logs
docker compose --env-file .env.production logs postgres
```

### Container Build Fails
**Problem:** Build errors or missing dependencies

**Solution:**
```bash
cd /home/nicola/backcast/deploy

# Check build logs
docker compose --env-file .env.production build --no-cache

# Fix any build errors and retry
```

### Services Not Starting
**Problem:** Container startup failures

**Solution:**
```bash
cd /home/nicola/backcast/deploy

# Check service logs
docker compose --env-file .env.production logs backend
docker compose --env-file .env.production logs frontend

# Restart specific service
docker compose --env-file .env.production restart backend
```

### Migrations Fail
**Problem:** Database migration errors

**Solution:**
```bash
cd /home/nicola/backcast/deploy

# Check migration status
docker compose --env-file .env.production exec postgres psql -U backcast_prod -d backcast_evs -c "SELECT * FROM alembic_version;"

# Restore from backup if needed
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker compose --env-file .env.production exec -T postgres psql -U backcast_prod backcast_evs
```

## Manual Verification

After deployment, verify services are working:

```bash
cd /home/nicola/backcast/deploy

# Check service status
docker compose --env-file .env.production ps

# Check backend logs
docker compose --env-file .env.production logs backend --tail=50

# Test frontend
curl -H "Host: app.backcast.duckdns.org" http://localhost:8080/

# Test backend API
curl -H "Host: api.backcast.duckdns.org" http://localhost:8080/docs

# Check database version
docker compose --env-file .env.production exec postgres psql -U backcast_prod -d backcast_evs -c "SELECT version_num FROM alembic_version;"
```

## Access URLs

After successful deployment:

| Service | URL |
|---------|-----|
| Frontend | http://app.backcast.duckdns.org:8080 |
| Frontend (SSL) | https://app.backcast.duckdns.org |
| Backend API | http://api.backcast.duckdns.org:8080 |
| Backend API (SSL) | https://api.backcast.duckdns.org |
| API Documentation | https://api.backcast.duckdns.org/docs |
| Traefik Dashboard | http://traefik.backcast.duckdns.org:8080/dashboard/ |

## Backup Management

### List Backups
```bash
cd /home/nicola/backcast/deploy
ls -lh backup_*.sql.gz
```

### Restore from Backup
```bash
cd /home/nicola/backcast/deploy

# Restore specific backup
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker compose --env-file .env.production exec -T postgres psql -U backcast_prod backcast_evs
```

### Clean Old Backups
```bash
cd /home/nicola/backcast/deploy

# Keep only last 5 backups
ls -t backup_*.sql.gz | tail -n +6 | xargs rm -f
```

## Integration with CI/CD

For automated deployments, use the non-interactive mode:

```bash
#!/bin/bash
# Example CI/CD deployment script

set -e  # Exit on error

# Navigate to deploy directory
cd /home/nicola/backcast/deploy

# Run deployment in non-interactive mode
./scripts/redeploy.sh -b main -y -v

# Check exit code
if [ $? -eq 0 ]; then
    echo "Deployment successful!"
    exit 0
else
    echo "Deployment failed!"
    exit 1
fi
```

## Best Practices

1. **Always use backups in production** - Don't use `-s` flag unless necessary
2. **Test in development first** - Deploy to development environment before production
3. **Monitor logs** - Use `-v` flag to see detailed output
4. **Keep backups** - Don't delete backups immediately after deployment
5. **Verify after deployment** - Check service status and test key functionality
6. **Document changes** - Keep track of what's being deployed
7. **Use specific branches** - Deploy from specific branches, not just "current"

## Support

For issues or questions:
- Check logs: `docker compose --env-file .env.production logs -f`
- Check service status: `docker compose --env-file .env.production ps`
- Review this guide
- Check DEPLOYMENT_GUIDE.md for detailed deployment information

## Version History

- **v1.0** (2026-03-15): Initial release with comprehensive automation
