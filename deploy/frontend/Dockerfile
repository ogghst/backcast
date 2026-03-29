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
ARG VITE_GIT_SHA=dev
ARG VITE_BUILD_DATE=dev

# Set build-time environment variables
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WEBSOCKET_URL=${VITE_WEBSOCKET_URL}
ENV VITE_GIT_SHA=${VITE_GIT_SHA}
ENV VITE_BUILD_DATE=${VITE_BUILD_DATE}

# Build the application (skip TypeScript check)
# Increase Node.js heap size to prevent out of memory errors
ENV NODE_OPTIONS="--max-old-space-size=4096"
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
