# Adminer Database Management Guide

## Overview

Adminer is a lightweight database management tool that provides a web-based UI to interact with your PostgreSQL database. It's available at **http://localhost:7090** when running.

## Quick Start

### Starting Adminer

```bash
docker-compose up -d adminer
```

### Accessing Adminer

1. Open your browser and navigate to: **http://localhost:7090**
2. Use the following credentials to log in:

| Field | Value |
|-------|-------|
| **System** | PostgreSQL |
| **Server** | postgres |
| **Username** | backcast |
| **Password** | backcast |
| **Database** | backcast_evs |

### Stopping Adminer

```bash
docker-compose stop adminer
```

### Removing Adminer

```bash
docker-compose down adminer
```

## Features

Adminer provides a full-featured database management interface:

- **Browse Tables**: View all tables, their structure, and data
- **Run SQL Queries**: Execute custom SQL queries with syntax highlighting
- **Edit Data**: Insert, update, and delete records directly
- **Import/Export**: Import SQL dumps or export database structure and data
- **Schema Management**: Create, alter, and drop tables, columns, and indexes
- **User Management**: Manage database users and permissions
- **Visual Query Builder**: Build queries visually without writing SQL

## Configuration

The Adminer service is configured in `docker-compose.yml` with:

```yaml
adminer:
  image: adminer:latest
  container_name: backcast_evs_adminer
  ports:
    - "7090:8080"
  environment:
    ADMINER_DEFAULT_SERVER: postgres
    ADMINER_DESIGN: nette
  depends_on:
    postgres:
      condition: service_healthy
  restart: unless-stopped
```

### Environment Variables

- `ADMINER_DEFAULT_SERVER`: Pre-fills the server field with "postgres"
- `ADMINER_DESIGN`: Uses the "nette" theme for a modern look

### Auto-Restart

The `restart: unless-stopped` policy ensures Adminer automatically restarts if it crashes or if Docker restarts.

## Tips

### Viewing Migration History

To check which Alembic migrations have been applied:
1. Go to SQL command in Adminer
2. Run: `SELECT * FROM alembic_version;`

### Inspecting Entity Versions

To view version history for an entity (e.g., projects):
```sql
SELECT * FROM project_version ORDER BY created_at DESC;
```

### Database Backup

1. Click on "Export" in the left menu
2. Select "SQL" format
3. Choose "Data and Structure"
4. Click "Export" to download the SQL dump

### Quick Table Search

Use the search box at the top to quickly filter tables by name.

## Security Notes

> [!WARNING]
> The default credentials (`backcast:backcast`) are for development only.
> 
> In production environments:
> - Use strong passwords
> - Restrict network access to Adminer
> - Consider using authentication proxies
> - Never expose Adminer directly to the internet

## Troubleshooting

### Cannot Connect to Database

**Error**: "Connection refused" or "Unable to connect"

**Solution**: Ensure PostgreSQL is running:
```bash
docker-compose ps postgres
docker-compose up -d postgres
```

### Port Already in Use

**Error**: "Port 7090 is already allocated"

**Solution**: Change the port in `docker-compose.yml`:
```yaml
ports:
  - "7091:8080"  # Use a different port
```

### Slow Performance

If Adminer is slow with large tables:
- Use filters and LIMIT clauses in queries
- Export/import operations on large datasets may take time
- Consider using pagination when browsing data

## Comparison with Other Tools

| Feature | Adminer | pgAdmin | psql |
|---------|---------|---------|------|
| **Web UI** | ✅ | ✅ | ❌ |
| **Lightweight** | ✅ | ❌ | ✅ |
| **Single File** | ✅ | ❌ | ✅ |
| **Visual Query Builder** | ✅ | ✅ | ❌ |
| **Advanced Features** | 🟡 | ✅ | 🟡 |

Adminer is ideal for quick database inspections and simple operations without the overhead of heavier tools like pgAdmin.

## Related Documentation

- [Alembic Docker Guide](./alembic_docker_guide.md) - Database migrations
- [Backend Architecture](./backend_architecture.md) - Application architecture
- [Data Model](./data_model.md) - Database schema documentation
