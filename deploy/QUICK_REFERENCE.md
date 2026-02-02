# Backcast EVS - Quick Reference Card

**Environment:** Production | **Domain:** backcast.duckdns.org | **Deploy Date:** 2026-01-26

---

## Critical Credentials

```
PostgreSQL Password: backcast
PostgreSQL User: backcast_prod
SECRET_KEY: LcOCnNRRouE0uIXQDVQeZ8LE6zKxwHyiGa9JXP5fxa1szWoU7Epwt4Lq69m7iMzq++9FqbBA6ZqHr8cJVejKew==
Traefik Dashboard Username: admin
Traefik Dashboard Password: backcast
```

**Default User Accounts (after seeding):**
```
Admin: admin@backcast.org / adminadmin
All others: *@backcast.org / backcast
```

**Save these securely!** They are needed for recovery and re-deployment.

---

## Essential Commands

### Status Check
```bash
cd /home/nicola/dev/backcast_evs/deploy
docker compose --env-file .env.production ps
```

### View Logs
```bash
# All services, follow
docker compose --env-file .env.production logs -f

# Specific service
docker compose --env-file .env.production logs -f backend
docker compose --env-file .env.production logs -f frontend
docker compose --env-file .env.production logs -f postgres
```

### Restart Services
```bash
# All services
docker compose --env-file .env.production restart

# Single service
docker compose --env-file .env.production restart backend
```

### Full Rebuild
```bash
git pull
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d
docker compose --env-file .env.production run --rm alembic
```

### Stop/Start
```bash
# Stop (keeps data)
docker compose --env-file .env.production down

# Start
docker compose --env-file .env.production up -d

# Stop AND DELETE DATA (WARNING!)
docker compose --env-file .env.production down -v
```

---

## Database Management

### Access PostgreSQL
```bash
docker exec -it backcast_evs_postgres psql -U backcast_prod -d backcast_evs
```

### Backup Database
```bash
docker exec backcast_evs_postgres pg_dump -U backcast_prod backcast_evs | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore Database
```bash
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker exec -i backcast_evs_postgres psql -U backcast_prod backcast_evs
```

### Run Migrations
```bash
docker compose --env-file .env.production run --rm alembic
```

### Reseed Database

**⚠️ Always backup first!**
```bash
# Backup
docker exec backcast_evs_postgres pg_dump -U backcast_prod backcast_evs | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**Simple Reseed (Safe - adds missing data only):**
```bash
# 1. Copy seed files into container
docker cp /home/nicola/dev/backcast_evs/backend/seed backcast_evs_backend:/app/

# 2. Run seeder
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

**Quick Verification:**
```bash
docker exec -it backcast_evs_postgres psql -U backcast_prod -d backcast_evs -c "SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'departments', COUNT(*) FROM departments;"
```

**Expected Results:** 5 users, 4 departments (plus projects, WBEs, cost elements)

**Default Accounts:**
- admin@backcast.org / adminadmin (Admin)
- pm@backcast.org / backcast (Project Manager)
- viewer@backcast.org / backcast (Viewer)
- eng.lead@backcast.org / backcast (Engineering Lead)
- const.super@backcast.org / backcast (Construction Super)

---

## Troubleshooting

### Service Not Starting?
```bash
# Check logs
docker compose --env-file .env.production logs <service>

# Check ports
sudo netstat -tulpn | grep 8080

# Check disk space
df -h
docker system df
```

### Database Issues?
```bash
# Check PostgreSQL is healthy
docker compose --env-file .env.production ps postgres

# Check database connection
docker exec backcast_evs_backend pg_isready -h postgres -U backcast_prod
```

### Clean Up Docker
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (WARNING: can delete data!)
docker volume prune

# Clean build cache
docker builder prune
```

---

## URLs

| Service | URL | Authentication |
|---------|-----|----------------|
| Frontend | https://app.backcast.duckdns.org | None |
| Backend API | https://api.backcast.duckdns.org | API tokens |
| API Docs | https://api.backcast.duckdns.org/docs | None |
| Adminer (DB) | http://db.backcast.duckdns.org | IP whitelist |
| Traefik Dashboard | http://traefik.backcast.duckdns.org:8080/dashboard/ | admin/backcast |

---

## LAN Access (From 192.168.1.x Network)

To access services from your local network, add these entries to `/etc/hosts`:

```bash
# On Linux/Mac
sudo nano /etc/hosts

# On Windows (run Notepad as Administrator)
# C:\Windows\System32\drivers\etc\hosts
```

**Add these lines:**
```hosts
192.168.1.23  api.backcast.duckdns.org
192.168.1.23  app.backcast.duckdns.org
192.168.1.23  db.backcast.duckdns.org
192.168.1.23  traefik.backcast.duckdns.org
```

**Then access:**
- Frontend: http://app.backcast.duckdns.org:8080
- Backend API: http://api.backcast.duckdns.org:8080
- Adminer: http://db.backcast.duckdns.org:8080
- Traefik Dashboard: http://traefik.backcast.duckdns.org:8080/dashboard/ (admin/backcast)

---

## System Info

| Item | Value |
|------|-------|
| Docker Server | 192.168.1.23 |
| Apache Server | 192.168.1.21 |
| Network Name | traefik-public |
| Database Host | postgres (internal) |
| Database Port | 5432 |
| Traefik Port | 8080 |

---

## Common Issues & Solutions

### Port 8080 Already in Use
```bash
# Find process using port
sudo lsof -i :8080

# Kill if needed
sudo kill <PID>
```

### Permission Denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Out of Disk Space
```bash
# Check Docker usage
docker system df

# Clean up
docker system prune -a --volumes
```

### Health Check Failing (but service works)
This is usually OK - health check endpoint may not be implemented. Service is still functional.

---

## Backup Checklist

### Daily (Automated if possible)
- [ ] Database backup
- [ ] Check service logs for errors
- [ ] Verify disk space

### Weekly
- [ ] Review Docker logs
- [ ] Check for security updates
- [ ] Test backup restoration

### Monthly
- [ ] Full system backup (volumes)
- [ ] Update dependencies
- [ ] Review access logs

---

## Emergency Contacts

| Role | Contact |
|------|---------|
| System Admin | nicola@backcast.duckdns.org |
| Server Access | SSH: 192.168.1.23, 192.168.1.21 |

---

## Quick Deployment Copy-Paste

**Full Restart (keeps data):**
```bash
cd /home/nicola/dev/backcast_evs/deploy && docker compose --env-file .env.production down && docker compose --env-file .env.production up -d
```

**Check Status:**
```bash
cd /home/nicola/dev/backcast_evs/deploy && docker compose --env-file .env.production ps
```

**View Logs:**
```bash
cd /home/nicola/dev/backcast_evs/deploy && docker compose --env-file .env.production logs -f --tail=50
```

---

**File:** `/home/nicola/dev/backcast_evs/deploy/QUICK_REFERENCE.md`
**Last Updated:** 2026-01-26
**Version:** 1.0
