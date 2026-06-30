# Static marketing/showcase website (pure HTML/CSS/JS — no build step).
# Served by nginx and routed via Traefik as www.${DOMAIN}.
# Build context is the repo root (see deploy/docker-compose.yml), so paths
# below are relative to the repo root.
FROM nginx:alpine

# Custom nginx config (static serving on :8080)
COPY deploy/website/nginx.conf /etc/nginx/nginx.conf

# Site content
COPY website/ /usr/share/nginx/html

EXPOSE 8080

# nginx:alpine's default ENTRYPOINT/CMD ("nginx -g daemon off;") is sufficient.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1
