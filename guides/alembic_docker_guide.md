# Alembic Docker Migration Guide

This guide explains how to use the Alembic Docker image to manage database migrations for the Backcast EVS project.

## Overview

The Alembic service is configured as a Docker container that connects to the PostgreSQL database and runs database migrations. It uses Docker Compose profiles to run on-demand rather than starting automatically.

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL service running (automatically started with `docker-compose up`)

## Building the Alembic Image

The Alembic image is built using the project's `Dockerfile.alembic`:

```bash
docker-compose build alembic
```

## Running Migrations

### Upgrade to Latest Version

To apply all pending migrations:

```bash
docker-compose run --rm alembic upgrade head
```

### Downgrade Migrations

To rollback the last migration:

```bash
docker-compose run --rm alembic downgrade -1
```

To rollback to a specific revision:

```bash
docker-compose run --rm alembic downgrade <revision_id>
```

### Create New Migration

To auto-generate a new migration based on model changes:

```bash
docker-compose run --rm alembic revision --autogenerate -m "Description of changes"
```

To create an empty migration file:

```bash
docker-compose run --rm alembic revision -m "Description of changes"
```

### View Migration History

To see all migrations:

```bash
docker-compose run --rm alembic history
```

To see the current migration version:

```bash
docker-compose run --rm alembic current
```

## Architecture

### Components

1. **Dockerfile.alembic**: Multi-stage Dockerfile that:
   - Uses Python 3.12 slim base image
   - Installs `uv` package manager for fast dependency installation
   - Copies project dependencies and application code
   - Sets up the entrypoint script

2. **docker-entrypoint-alembic.sh**: Entry point script that:
   - Waits for PostgreSQL to be ready (health check)
   - Runs the requested Alembic command using `uv run`

3. **docker-compose.yml**: Orchestration configuration that:
   - Defines the Alembic service with proper environment variables
   - Sets up dependency on PostgreSQL with health check
   - Uses the `migrations` profile for on-demand execution

### Environment Variables

The following environment variables are configured in `docker-compose.yml`:

| Variable | Value | Description |
|----------|-------|-------------|
| `POSTGRES_HOST` | `postgres` | PostgreSQL container hostname |
| `POSTGRES_USER` | `backcast` | Database user |
| `POSTGRES_PASSWORD` | `backcast` | Database password |
| `POSTGRES_DB` | `backcast_evs` | Database name |
| `DATABASE_URL` | `postgresql+asyncpg://...` | SQLAlchemy async connection string |
| `SECRET_KEY` | (configured) | Application secret key |
| `DEBUG` | `True` | Debug mode flag |

## Tips

### Using Profiles

The Alembic service uses the `migrations` profile, which means it won't start automatically when you run `docker-compose up`. This is intentional to keep migrations as explicit, on-demand operations.

### Container Cleanup

The `--rm` flag in the examples above automatically removes the container after the command completes. This keeps your system clean.

### Local Development

For local development without Docker, you can still use Alembic directly:

```bash
# Make sure your .env file has the correct DATABASE_URL
uv run alembic upgrade head
```

## Troubleshooting

### Connection Issues

If you see connection errors, ensure:
1. PostgreSQL service is running: `docker-compose ps postgres`
2. Database credentials match between `.env` and `docker-compose.yml`
3. The PostgreSQL port (5433) is not blocked by another service

### Permission Issues

If the entrypoint script fails to execute:

```bash
chmod +x docker-entrypoint-alembic.sh
docker-compose build alembic
```

### Debugging

To get a shell inside the Alembic container:

```bash
docker-compose run --rm --entrypoint /bin/bash alembic
```

## Integration with CI/CD

You can integrate this into your CI/CD pipeline:

```yaml
# Example for GitHub Actions
- name: Run database migrations
  run: |
    docker-compose up -d postgres
    docker-compose run --rm alembic upgrade head
```

## Security Notes

> [!WARNING]
> The default credentials (`backcast:backcast`) are for development only. In production:
> - Use strong, unique passwords
> - Store credentials in a secrets manager
> - Use environment-specific configuration files
> - Never commit production credentials to version control
