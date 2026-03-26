# Backcast EVS - Redeployment Quick Reference

## 🚀 Quick Commands

```bash
# Navigate to deploy directory
cd /home/nicola/backcast/deploy

# Full redeployment (recommended)
./scripts/redeploy.sh -y

# From specific branch
./scripts/redeploy.sh -b main -y

# Quick restart (no rebuild)
./scripts/redeploy.sh -n -y

# Development/testing (no backup)
./scripts/redeploy.sh -s -n -y
```

## 📋 Script Options

| Flag | Description |
|------|-------------|
| `-h` | Show help |
| `-b BRANCH` | Specify branch |
| `-s` | Skip backup |
| `-n` | Skip build |
| `-m` | Skip migrations |
| `-y` | Auto-confirm |
| `-v` | Verbose output |

## 🔍 Verification Commands

```bash
# Check service status
docker compose --env-file .env.production ps

# View logs
docker compose --env-file .env.production logs -f

# Check specific service
docker compose --env-file .env.production logs backend --tail=50

# Test frontend
curl -H "Host: app.backcast.duckdns.org" http://localhost:8080/

# Test backend
curl -H "Host: api.backcast.duckdns.org" http://localhost:8080/docs

# Database version
docker compose --env-file .env.production exec postgres psql -U backcast_prod -d backcast_evs -c "SELECT version_num FROM alembic_version;"
```

## 🌐 Access URLs

| Service | URL |
|---------|-----|
| Frontend | https://app.backcast.duckdns.org |
| Backend | https://api.backcast.duckdns.org |
| API Docs | https://api.backcast.duckdns.org/docs |
| Traefik | http://traefik.backcast.duckdns.org:8080/dashboard/ |

## 💾 Backup Commands

```bash
# List backups
ls -lh backup_*.sql.gz

# Restore from backup
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker compose --env-file .env.production exec -T postgres psql -U backcast_prod backcast_evs

# Manual backup
docker compose --env-file .env.production exec postgres pg_dump -U backcast_prod backcast_evs | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not running | `docker info` |
| Build fails | Check logs: `docker compose --env-file .env.production build --no-cache` |
| Services not starting | Check logs: `docker compose --env-file .env.production logs <service>` |
| Migration fails | Restore from backup or check database connection |
| Can't access services | Check Traefik and verify port 8080 |

## 📊 What Gets Deployed

1. ✅ Git pull (latest changes)
2. ✅ Database backup (timestamped)
3. ✅ Container rebuild (backend + frontend)
4. ✅ Service restart
5. ✅ Database migrations
6. ✅ Verification checks

## 🔄 Deployment Process

```
Prerequisites Check
    ↓
Git Pull
    ↓
Database Backup
    ↓
Container Rebuild (5-15 min)
    ↓
Service Restart
    ↓
Database Migrations
    ↓
Verification
    ↓
Complete! ✅
```

## 📝 Common Scenarios

### Production Deployment
```bash
./scripts/redeploy.sh -y
```
- Full backup
- Complete rebuild
- All migrations
- Full verification

### Testing New Feature
```bash
./scripts/redeploy.sh -b feature-branch -y
```
- Deploy from feature branch
- All safety checks included

### Quick Config Change
```bash
./scripts/redeploy.sh -s -n -m -y
```
- Skip backup/build/migrations
- Just restart services
- Fastest option

### Emergency Rollback
```bash
# Stop services
docker compose --env-file .env.production down

# Restore backup
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker compose --env-file .env.production exec -T postgres psql -U backcast_prod backcast_evs

# Restart
docker compose --env-file .env.production up -d
```

## 🔧 Management Commands

```bash
# Stop all services
docker compose --env-file .env.production down

# Start all services
docker compose --env-file .env.production up -d

# Restart specific service
docker compose --env-file .env.production restart backend

# View resource usage
docker stats

# Clean up old images
docker image prune -a

# Check disk usage
docker system df
```

## 📞 Support

- **Full Guide**: See REDEPLOYMENT_GUIDE.md
- **Deployment Info**: See DEPLOYMENT_GUIDE.md
- **Quick Reference**: See QUICK_REFERENCE.md

## ⏱️ Typical Timings

| Operation | Time |
|-----------|------|
| Git pull | 10-30 seconds |
| Database backup | 30-60 seconds |
| Container rebuild | 5-15 minutes |
| Service restart | 30-60 seconds |
| Migrations | 10-30 seconds |
| **Total (full deploy)** | **6-17 minutes** |
| **Total (no rebuild)** | **1-2 minutes** |

---

**Script Location**: `/home/nicola/backcast/deploy/scripts/redeploy.sh`
**Version**: 1.0
**Last Updated**: 2026-03-15
