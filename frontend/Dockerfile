# syntax=docker/dockerfile:1
# ------------------------------------------------------------------------------
# Production Dockerfile for RosterOps Frontend (T-1001)
# Node.js 20 build stage + Nginx Alpine static server with SPA fallback
# ------------------------------------------------------------------------------

FROM node:20-alpine AS builder

WORKDIR /app

# Copy package dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source and configurations
COPY . .

# Build production bundle with Vite and TypeScript compiler
RUN npm run build

# ------------------------------------------------------------------------------
# Final Runtime Stage: Nginx Alpine
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runner

# Remove default nginx configurations
RUN rm -rf /etc/nginx/conf.d/*

# Copy custom SPA Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
    CMD wget -q --spider http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

